#!/usr/bin/env python3
"""Fine-grained digital-human / lipsync content-accuracy evaluation.

Layers:
  A) Offline Ken Burns (DEMO_GENERATION=1) — must FAIL as digital human
  B) Folded live evidence (fixtures/lipsync/last_run.json) — A/V + motion metrics
  C) Product Demo API contract (tier=demo enqueue shape)
  D) Optional paid re-run with photoreal face + real speech
     (LIPSYNC_ACCURACY_LIVE=1) via KieAdapter directly

Usage:
  cd backend && python3 scripts/lipsync_accuracy_eval.py
  LIPSYNC_ACCURACY_LIVE=1 python3 scripts/lipsync_accuracy_eval.py
"""
from __future__ import annotations

import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import time
import uuid
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures" / "lipsync"
PORTRAIT = FIX / "portrait.png"
LINE = FIX / "line.wav"
LAST = FIX / "last_run.json"
REPORT = ROOT / "fixtures" / "audit" / "lipsync_accuracy_latest.json"
ARTIFACT = Path("/opt/cursor/artifacts/lipsync_accuracy")


def _ffprobe(path: str | Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries",
        "stream=codec_type,codec_name,duration,width,height,sample_rate,channels:"
        "format=duration,size,bit_rate",
        "-of", "json",
        str(path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        return {"error": (p.stderr or "")[:300]}
    return json.loads(p.stdout or "{}")


def _download(url: str, dest: Path) -> bool:
    import urllib.request
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BettyLipsyncAccuracy/1.0"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            dest.write_bytes(resp.read())
        return dest.is_file() and dest.stat().st_size > 500
    except Exception as e:
        print(f"download fail: {e}")
        return False


def _resolve_folded_local(url: str) -> Path | None:
    """Prefer cached artifacts when tempfile CDN returns 403/expired."""
    for p in (
        ARTIFACT / "B_folded_last_run.mp4",
        ARTIFACT / "last_run.mp4",
        Path("/tmp/lipsync_acc/last_run.mp4"),
    ):
        if p.is_file() and p.stat().st_size > 500:
            return p
    return None


def _local_from_media_url(url: str) -> Path | None:
    if not url:
        return None
    marker = "/api/v1/media/"
    if marker in url:
        rel = url.split(marker, 1)[1]
        from app.config import settings
        p = Path(settings.STORAGE_LOCAL_PATH) / rel
        return p if p.is_file() else None
    if url.startswith("/") and Path(url).is_file():
        return Path(url)
    return None


def _audio_metrics(path: Path) -> dict:
    """Speechlikeness proxies from PCM WAV (or extract from video)."""
    wav = path
    tmp = None
    if path.suffix.lower() in (".mp4", ".mov", ".webm"):
        tmp = Path(tempfile.mkdtemp()) / "a.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
             "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1", str(tmp)],
            check=True, timeout=60,
        )
        wav = tmp
    with wave.open(str(wav), "rb") as w:
        n = w.getnframes()
        fr = w.getframerate()
        samples = struct.unpack("<" + "h" * n, w.readframes(n))
    hop = max(1, int(fr * 0.05))
    rms = []
    for i in range(0, len(samples) - hop, hop):
        chunk = samples[i : i + hop]
        rms.append(math.sqrt(sum(x * x for x in chunk) / len(chunk)))
    mean = sum(rms) / len(rms) if rms else 0.0
    var = sum((r - mean) ** 2 for r in rms) / len(rms) if rms else 0.0
    std = math.sqrt(var)
    zcr = sum(
        1 for i in range(1, len(samples)) if (samples[i - 1] >= 0) != (samples[i] >= 0)
    ) / max(1, len(samples))
    silence = sum(1 for r in rms if r < 500) / max(1, len(rms))
    energy_cv = std / (mean + 1e-9)
    # Tone ≈ low zcr + low energy_cv; speech ≈ higher energy_cv and mid zcr
    speechlike = 0
    if mean > 200 and silence < 0.85:
        speechlike = 2
        if energy_cv >= 0.35:
            speechlike = 4
        elif energy_cv >= 0.2:
            speechlike = 3
        if 0.04 <= zcr <= 0.25:
            speechlike = min(5, speechlike + 1)
        if energy_cv < 0.18 and zcr < 0.05:
            speechlike = 1  # steady tone
    return {
        "duration_s": round(n / fr, 3),
        "sample_rate": fr,
        "rms_mean": round(mean, 1),
        "energy_cv": round(energy_cv, 3),
        "zcr": round(zcr, 4),
        "silence_ratio": round(silence, 3),
        "speechlike_score_0_to_5": speechlike,
        "class": (
            "tone_or_steady"
            if speechlike <= 1
            else ("speech_candidate" if speechlike >= 3 else "weak_speech")
        ),
    }


def _motion_metrics(video: Path, fps: int = 5) -> dict:
    from PIL import Image, ImageChops, ImageStat

    td = Path(tempfile.mkdtemp())
    pattern = td / "f_%03d.jpg"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vf", f"fps={fps},scale=640:-1", "-q:v", "3", str(pattern)],
        check=True, timeout=90,
    )
    frames = sorted(td.glob("f_*.jpg"))
    if len(frames) < 2:
        return {"error": "too_few_frames", "n_frames": len(frames)}
    imgs = [Image.open(f).convert("L") for f in frames]
    w, h = imgs[0].size
    diffs = [
        ImageStat.Stat(ImageChops.difference(a, b)).mean[0]
        for a, b in zip(imgs, imgs[1:])
    ]
    mx1, mx2 = int(w * 0.3), int(w * 0.7)
    my1, my2 = int(h * 0.45), int(h * 0.65)
    ey1, ey2 = int(h * 0.25), int(h * 0.40)
    mouth = [
        ImageStat.Stat(
            ImageChops.difference(a.crop((mx1, my1, mx2, my2)), b.crop((mx1, my1, mx2, my2)))
        ).mean[0]
        for a, b in zip(imgs, imgs[1:])
    ]
    eyes = [
        ImageStat.Stat(
            ImageChops.difference(a.crop((mx1, ey1, mx2, ey2)), b.crop((mx1, ey1, mx2, ey2)))
        ).mean[0]
        for a, b in zip(imgs, imgs[1:])
    ]
    m_mean = sum(mouth) / len(mouth)
    e_mean = sum(eyes) / len(eyes)
    f_mean = sum(diffs) / len(diffs)
    # Digital-human talking: expect mouth motion meaningfully above noise
    mouth_score = 0
    if m_mean >= 8:
        mouth_score = 5
    elif m_mean >= 4:
        mouth_score = 4
    elif m_mean >= 2:
        mouth_score = 3
    elif m_mean >= 1:
        mouth_score = 2
    elif m_mean >= 0.5:
        mouth_score = 1
    ratio = m_mean / (e_mean + 1e-6)
    return {
        "n_frames": len(frames),
        "frame_mad_mean": round(f_mean, 3),
        "mouth_roi_mad_mean": round(m_mean, 3),
        "eye_roi_mad_mean": round(e_mean, 3),
        "mouth_over_eye_ratio": round(ratio, 3),
        "mouth_motion_score_0_to_5": mouth_score,
        "first_frame": str(frames[0]),
        "unique_colors_frame0": _unique_colors(Image.open(frames[0])),
    }


def _unique_colors(im) -> int:
    c = im.convert("RGB").getcolors(maxcolors=200000)
    return len(c) if c else 200001


def _identity_metrics(ref_image: Path, video: Path) -> dict:
    from PIL import Image, ImageChops, ImageStat

    td = Path(tempfile.mkdtemp())
    frame = td / "id.jpg"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vf", "select=eq(n\\,0),scale=512:-1", "-frames:v", "1", "-q:v", "2", str(frame)],
        check=True, timeout=60,
    )
    a = Image.open(ref_image).convert("RGB")
    b = Image.open(frame).convert("RGB")
    b = b.resize(a.size)
    mad = ImageStat.Stat(ImageChops.difference(a, b)).mean[0]
    h1, h2 = a.histogram(), b.histogram()
    n = len(h1)
    m1, m2 = sum(h1) / n, sum(h2) / n
    num = sum((x - m1) * (y - m2) for x, y in zip(h1, h2))
    den = (sum((x - m1) ** 2 for x in h1) * sum((y - m2) ** 2 for y in h2)) ** 0.5
    corr = num / den if den else 0.0
    # Lower MAD + higher hist corr → identity preserved
    if mad < 15 and corr > 0.7:
        id_score = 5
    elif mad < 40 and corr > 0.4:
        id_score = 4
    elif mad < 80 and corr > 0.2:
        id_score = 3
    elif mad < 120:
        id_score = 2
    else:
        id_score = 1
    return {
        "pixel_mad": round(mad, 2),
        "hist_corr": round(corr, 4),
        "identity_score_0_to_5": id_score,
        "note": "High identity with near-zero mouth motion = frozen portrait, not talking avatar",
    }


def _score_bundle(
    *,
    mode: str,
    model: str,
    path: Path,
    ref_image: Path | None,
    expect_silent: bool,
) -> dict:
    probe = _ffprobe(path)
    streams = probe.get("streams") or []
    has_v = any(s.get("codec_type") == "video" for s in streams)
    has_a = any(s.get("codec_type") == "audio" for s in streams)
    audio = _audio_metrics(path) if has_a else {
        "speechlike_score_0_to_5": 0, "class": "none", "duration_s": 0,
    }
    motion = _motion_metrics(path) if has_v else {"mouth_motion_score_0_to_5": 0}
    identity = (
        _identity_metrics(ref_image, path)
        if ref_image and ref_image.is_file() and has_v
        else {"identity_score_0_to_5": 0}
    )

    scores = {
        "audio_present": 5 if has_a else 0,
        "audio_speechlike": audio.get("speechlike_score_0_to_5", 0),
        "mouth_motion": motion.get("mouth_motion_score_0_to_5", 0),
        "identity_preserve": identity.get("identity_score_0_to_5", 0),
        "model_honesty": (
            5 if (expect_silent and model == "demo-lipsync")
            or (not expect_silent and "avatar" in (model or ""))
            else 2
        ),
    }
    # Digital-human accuracy weights talking behavior, not just identity freeze
    dh = round(
        0.25 * scores["audio_present"]
        + 0.25 * scores["audio_speechlike"]
        + 0.35 * scores["mouth_motion"]
        + 0.15 * scores["identity_preserve"],
        2,
    )
    # Special case: Ken Burns with high identity + no audio → not DH
    if expect_silent:
        passes = False
        verdict = (
            "NOT a digital human — Ken Burns still-image zoom; silent; no visemes. "
            "Acceptable only as offline preview with DEMO watermark."
        )
    elif dh >= 3.2 and scores["mouth_motion"] >= 3 and scores["audio_speechlike"] >= 3:
        passes = True
        verdict = "Passes proxy digital-human bar (A/V + measurable mouth motion)."
    elif has_a and has_v and scores["mouth_motion"] <= 1:
        passes = False
        verdict = (
            "FAIL as talking digital human — video+audio exist but mouth motion is "
            "near-static (frozen identity). Typical of cartoon/tone inputs or failed lipsync."
        )
    else:
        passes = False
        verdict = "Weak digital-human signal; does not meet talking-avatar accuracy bar."

    return {
        "mode": mode,
        "model": model,
        "path": str(path),
        "has_video": has_v,
        "has_audio": has_a,
        "probe_streams": [
            {k: s.get(k) for k in ("codec_type", "codec_name", "width", "height", "sample_rate")}
            for s in streams
        ],
        "audio_metrics": audio,
        "motion_metrics": motion,
        "identity_metrics": identity,
        "scores_0_to_5": scores,
        "digital_human_accuracy_0_to_5": dh,
        "passes_as_digital_human": passes,
        "verdict": verdict,
    }


def eval_offline_demo() -> dict:
    os.environ["DEMO_GENERATION"] = "1"
    sys.path.insert(0, str(ROOT))
    from app.adapters.demo_provider import (
        MEDIA_URL_PREFIX, demo_mode_active, render_demo_video,
    )
    from app.config import settings

    assert demo_mode_active(), "DEMO_GENERATION=1 must activate demo mode"
    media_root = Path(settings.STORAGE_LOCAL_PATH)
    uploads = media_root / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    dest = uploads / f"acc_portrait_{uuid.uuid4().hex[:8]}.png"
    dest.write_bytes(PORTRAIT.read_bytes())
    base_url = f"{MEDIA_URL_PREFIX}/uploads/{dest.name}"
    v_url, thumb = render_demo_video(
        "你好，我是数字人测试", "720x1280", 5, "portrait", base_url,
    )
    local = _local_from_media_url(v_url)
    if not local:
        return {"ok": False, "error": f"cannot resolve {v_url}", "mode": "offline_demo"}
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    out_copy = ARTIFACT / "A_offline_kenburns.mp4"
    out_copy.write_bytes(local.read_bytes())
    scored = _score_bundle(
        mode="offline_demo_ken_burns",
        model="demo-lipsync",
        path=local,
        ref_image=PORTRAIT,
        expect_silent=True,
    )
    return {
        "ok": True,
        "mode": "offline_demo_ken_burns",
        "model": "demo-lipsync",
        "media_url": v_url,
        "thumbnail": thumb,
        "artifact": str(out_copy),
        "analysis": scored,
        "honesty": (
            "Product UI 'Demo · 标准唇形' is MISLEADING when DEMO_GENERATION/no-keys: "
            "output is Ken Burns zoom, silent, DEMO watermark — not lip sync."
        ),
    }


def eval_folded_live() -> dict:
    if not LAST.is_file():
        return {"ok": False, "skipped": True, "reason": "no last_run.json"}
    data = json.loads(LAST.read_text(encoding="utf-8"))
    url = data.get("media_url") or ""
    model = data.get("model") or ""
    if not data.get("ok") or not url:
        return {"ok": False, "evidence": data}
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    dest = ARTIFACT / "B_folded_last_run.mp4"
    cached = _resolve_folded_local(url)
    if cached and cached.resolve() != dest.resolve():
        dest.write_bytes(cached.read_bytes())
        source = f"local_cache:{cached}"
    elif _download(url, dest):
        source = "cdn_download"
    elif cached:
        dest = cached
        source = f"local_cache:{cached}"
    else:
        return {
            "ok": False,
            "error": "download failed (URL may have expired) and no local cache",
            "model": model,
            "media_url": url,
        }
    scored = _score_bundle(
        mode="folded_live_last_run",
        model=model,
        path=dest,
        ref_image=PORTRAIT,
        expect_silent=False,
    )
    scored["caveat"] = (
        "Fixture portrait.png is a stick-figure cartoon; line.wav is a steady tone "
        "(energy_cv≈0.13). Even real kling/ai-avatar-pro cannot invent photoreal talking "
        "from these inputs — identity freeze + tone audio is expected failure mode."
    )
    scored["input_fixture_quality"] = {
        "portrait": "cartoon_stick_figure_not_photoreal",
        "audio": "sine_or_steady_tone_not_speech",
    }
    return {
        "ok": True,
        "mode": "folded_live_last_run",
        "model": model,
        "media_url": url,
        "cost": data.get("cost"),
        "source": source,
        "artifact": str(dest),
        "analysis": scored,
    }


def eval_product_demo_api() -> dict:
    os.environ.pop("DEMO_GENERATION", None)
    from importlib import reload
    import app.adapters.demo_provider as dp
    reload(dp)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.adapters.demo_provider import demo_mode_active

    if demo_mode_active():
        return {
            "ok": False,
            "skipped": True,
            "reason": "demo_mode_active — cannot test product demo live path",
        }

    c = TestClient(app)
    email = f"ls_acc_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Test1234!",
            "username": f"u{uuid.uuid4().hex[:6]}",
        },
    )
    token = (reg.json() or {}).get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    files = {
        "image_file": ("portrait.png", PORTRAIT.read_bytes(), "image/png"),
        "audio_file": ("line.wav", LINE.read_bytes(), "audio/wav"),
    }
    data = {"tier": "demo", "voice_id": "zh-CN-XiaoxiaoNeural"}
    r = c.post("/api/v1/lipsync", headers=headers, files=files, data=data)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return {
        "ok": r.status_code in (200, 201, 202),
        "mode": "product_demo_contract",
        "status_code": r.status_code,
        "response": {
            k: body.get(k)
            for k in ("task_id", "estimated_cost_credits", "tier", "detail")
        },
        "demo_mode_active": False,
        "expected_upstream": "kling/ai-avatar-pro @ ~480p (product Demo≠Ken Burns when keys present)",
        "note": (
            "Contract only — celery worker may not complete in-process. "
            "Layer D exercises KieAdapter outframe with photoreal+speech."
        ),
    }


def _ensure_speech_wav() -> Path:
    out = FIX / "speech_zh.wav"
    if out.is_file() and out.stat().st_size > 1000:
        return out
    # Prefer espeak-ng; fall back to ffmpeg multi-tone envelope (still not speech)
    if subprocess.run(["which", "espeak-ng"], capture_output=True).returncode == 0:
        subprocess.run(
            [
                "espeak-ng", "-v", "zh",
                "你好，我是数字人测试，今天天气很好。",
                "-w", str(out),
            ],
            check=True, timeout=30,
        )
    else:
        # AM-modulated tone as weak speech surrogate
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi",
                "-i", "sine=f=180:d=3,volume=0.4",
                "-af", "volume=1+0.8*sin(2*PI*t*3)",
                str(out),
            ],
            check=True, timeout=30,
        )
    return out


def _ensure_photo_face() -> Path:
    out = FIX / "photo_face.jpg"
    if out.is_file() and out.stat().st_size > 5000:
        return out
    # Prefer already-downloaded artifact; else Unsplash portrait
    art = ARTIFACT / "photo_face.jpg"
    if art.is_file():
        out.write_bytes(art.read_bytes())
        return out
    url = (
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d"
        "?w=512&h=640&fit=crop&crop=faces"
    )
    if _download(url, out):
        return out
    # Fall back to stick figure (will fail accuracy — documented)
    out = PORTRAIT
    return out


def eval_live_photoreal() -> dict:
    want = os.getenv("LIPSYNC_ACCURACY_LIVE", "").lower() in ("1", "true", "yes", "on")
    if not want:
        return {
            "ok": False,
            "skipped": True,
            "reason": "Set LIPSYNC_ACCURACY_LIVE=1 to spend KIE credits on photoreal+speech re-run",
        }

    os.environ.pop("DEMO_GENERATION", None)
    from importlib import reload
    import app.adapters.demo_provider as dp
    reload(dp)
    from app.adapters.demo_provider import demo_mode_active
    from app.adapters.kie_adapter import KieAdapter
    import asyncio

    if demo_mode_active():
        return {"ok": False, "skipped": True, "reason": "demo_mode_active"}

    photo = _ensure_photo_face()
    speech = _ensure_speech_wav()
    adapter = KieAdapter()

    async def _run():
        img_url = await adapter.upload_public_url(
            photo.read_bytes(),
            filename=f"acc_face_{uuid.uuid4().hex[:8]}.jpg",
            content_type="image/jpeg" if photo.suffix.lower() in (".jpg", ".jpeg") else "image/png",
        )
        aud_url = await adapter.upload_public_url(
            speech.read_bytes(),
            filename=f"acc_speech_{uuid.uuid4().hex[:8]}.wav",
            content_type="audio/wav",
        )
        res = await adapter.generate_lipsync(
            image_url=img_url,
            audio_url=aud_url,
            prompt="a person talking naturally to camera, accurate lip sync",
            model_id="kling/ai-avatar-pro",
            resolution="480p",
        )
        return res

    t0 = time.time()
    try:
        res = asyncio.run(_run())
    except Exception as e:
        return {"ok": False, "error": str(e)[:500], "mode": "live_photoreal_speech"}

    ARTIFACT.mkdir(parents=True, exist_ok=True)
    dest = ARTIFACT / "D_live_photoreal_speech.mp4"
    if not _download(res.media_url, dest):
        return {
            "ok": False,
            "error": "download failed",
            "media_url": res.media_url,
            "model": res.model,
        }
    scored = _score_bundle(
        mode="live_photoreal_speech",
        model=res.model or "kling/ai-avatar-pro",
        path=dest,
        ref_image=photo,
        expect_silent=False,
    )
    # Persist evidence (overwrite last_run with better sample)
    LAST.write_text(
        json.dumps(
            {
                "ok": True,
                "media_url": res.media_url,
                "model": res.model,
                "tier": "demo",
                "source": "lipsync_accuracy_eval_photoreal",
                "inputs": {
                    "image": str(photo.name),
                    "audio": str(speech.name),
                },
                "elapsed_s": round(time.time() - t0, 1),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "digital_human_accuracy_0_to_5": scored["digital_human_accuracy_0_to_5"],
                "passes_as_digital_human": scored["passes_as_digital_human"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "ok": True,
        "mode": "live_photoreal_speech",
        "model": res.model,
        "media_url": res.media_url,
        "elapsed_s": round(time.time() - t0, 1),
        "artifact": str(dest),
        "inputs": {"image": str(photo), "audio": str(speech)},
        "analysis": scored,
    }


def main() -> int:
    report = {
        "suite": "lipsync_accuracy_eval",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fixtures": {
            "portrait_bytes": PORTRAIT.is_file() and PORTRAIT.stat().st_size,
            "portrait_class": "cartoon_stick_figure",
            "line_wav_bytes": LINE.is_file() and LINE.stat().st_size,
            "line_wav_class": "steady_tone_not_speech",
        },
        "layers": {},
    }

    print("=== A) Offline Ken Burns (DEMO_GENERATION=1) ===")
    offline = eval_offline_demo()
    report["layers"]["A_offline_demo"] = offline
    print(json.dumps(offline.get("analysis") or offline, ensure_ascii=False, indent=2)[:1500])

    print("=== B) Folded live last_run (stick+tone) ===")
    os.environ.pop("DEMO_GENERATION", None)
    folded = eval_folded_live()
    report["layers"]["B_folded_live"] = folded
    print(json.dumps(folded.get("analysis") or folded, ensure_ascii=False, indent=2)[:1500])

    print("=== C) Product Demo API contract (tier=demo) ===")
    product = eval_product_demo_api()
    report["layers"]["C_product_demo"] = product
    print(json.dumps(product, ensure_ascii=False, indent=2)[:1200])

    print("=== D) Live photoreal + speech (optional) ===")
    live = eval_live_photoreal()
    report["layers"]["D_live_photoreal"] = live
    print(json.dumps(live.get("analysis") or live, ensure_ascii=False, indent=2)[:1500])

    a_acc = (offline.get("analysis") or {}).get("digital_human_accuracy_0_to_5")
    b_acc = (folded.get("analysis") or {}).get("digital_human_accuracy_0_to_5")
    d_acc = (live.get("analysis") or {}).get("digital_human_accuracy_0_to_5")
    report["professional_summary"] = {
        "offline_demo_is_digital_human": False,
        "offline_accuracy": a_acc,
        "folded_stick_tone_accuracy": b_acc,
        "folded_passes": (folded.get("analysis") or {}).get("passes_as_digital_human"),
        "live_photoreal_accuracy": d_acc,
        "live_photoreal_passes": (live.get("analysis") or {}).get("passes_as_digital_human"),
        "root_causes_of_user_complaint": [
            "双轨混淆：产品档 Demo(4积分) ≠ 运行时 DEMO_GENERATION Ken Burns",
            "UI『标准唇形』在离线时完全失实；有 Key 时 Demo/Studio 常同为 kling/ai-avatar-pro",
            "历史 fixture 简笔画+正弦波会让真链路也『不像数字人』（口型 MAD≈1，口/眼运动比<1）",
            "音色列表展示 Azure Neural id，实际上游映射到 Rachel/Adam，音色不一致",
        ],
        "key_finding": (
            "用户选免费 Demo 却觉得『不像数字人』，需按路径诊断："
            "(1) 离线 Ken Burns → 必然失败（无声+缩放）；"
            "(2) 真链路但输入非真人脸/非语音 → 身份冻结、口型近零；"
            "(3) 真链路+真人脸+语音 → 才可评口型准确度。"
        ),
        "recommendations": [
            "结果 JSON 写明 mode=ken_burns|kling_avatar，任务页强制展示",
            "Demo 文案改为『480p 口型（需模型 Key）/ 离线为预览动效』",
            "fixture 换真人脸+真实语音后再做回归门槛",
            "Studio vs Demo 若同 SKU，诚实写『同模型·积分差异』",
            "音色 UI 标注实际上游映射",
        ],
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nWrote", REPORT)
    print(json.dumps(report["professional_summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
