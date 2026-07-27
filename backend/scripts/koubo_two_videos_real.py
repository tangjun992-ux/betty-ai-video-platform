#!/usr/bin/env python3
"""Generate two distinct real talking-avatar (口播) videos for human QA.

Pipeline per video (honest about TTS):
  1) GPT Image 2 portrait (KIE) — real
  2) Speech via edge-tts (Microsoft Neural) — ElevenLabs/KIE TTS currently 5xx
  3) Kling ai-avatar-pro lipsync (KIE) — real

Outputs under /opt/cursor/artifacts/koubo_two_videos/
"""
from __future__ import annotations

import asyncio
import json
import math
import struct
import subprocess
import tempfile
import time
import urllib.request
import wave
from pathlib import Path

import edge_tts
from PIL import Image, ImageChops, ImageStat

from app.adapters.kie_adapter import KieAdapter

ART = Path("/opt/cursor/artifacts/koubo_two_videos")
REPORT = Path(__file__).resolve().parents[1] / "fixtures" / "audit" / "koubo_two_videos_latest.json"

CASES = [
    {
        "id": "A_earbuds_female",
        "title": "口播 A · 女主播 · 无线耳机种草",
        "portrait_prompt": (
            "Vertical 9:16 studio portrait of a young East Asian woman host, "
            "friendly smile, holding white wireless earbuds case toward camera, "
            "soft three-point lighting, clean light gray background, "
            "professional marketing talking-head, photorealistic skin, chest-up framing"
        ),
        "script": (
            "大家好，今天给大家推荐一款真正能听一整天的无线耳机。"
            "音质干净清晰，降噪很稳，通勤开会都合适。"
            "现在下单还有限时优惠，喜欢的朋友可以冲。"
        ),
        "voice": "zh-CN-XiaoxiaoNeural",
        "aspect": "9:16",
        "size": "720x1280",
    },
    {
        "id": "B_skincare_male",
        "title": "口播 B · 男主播 · 护肤精华讲解",
        "portrait_prompt": (
            "Vertical 9:16 studio portrait of a young East Asian man host, "
            "short neat hair, wearing casual navy shirt, holding a small glass "
            "serum bottle with dropper, warm soft studio lighting, "
            "clean beige background, photorealistic talking-head, chest-up framing"
        ),
        "script": (
            "兄弟们，今天分享一瓶我最近每天都在用的护肤精华。"
            "质地清爽不黏腻，温和好吸收，熬夜后脸也不容易干。"
            "如果你也想把基础护理做扎实，可以试试看。"
        ),
        "voice": "zh-CN-YunxiNeural",
        "aspect": "9:16",
        "size": "720x1280",
    },
]


def _dl(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "BettyKouboQA/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        dest.write_bytes(r.read())


async def _tts(script: str, voice: str, dest_wav: Path) -> dict:
    mp3 = dest_wav.with_suffix(".mp3")
    await edge_tts.Communicate(script, voice).save(str(mp3))
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
         "-ar", "22050", "-ac", "1", str(dest_wav)],
        check=True,
    )
    dur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(dest_wav)], text=True).strip() or "0")
    return {
        "engine": "edge-tts",
        "voice": voice,
        "mp3": str(mp3),
        "wav": str(dest_wav),
        "duration_s": round(dur, 3),
        "bytes": dest_wav.stat().st_size,
        "honesty": "not_elevenlabs_kie; Microsoft Edge Neural TTS fallback while KIE TTS 5xx",
    }


def _analyze_video(video: Path, ref_image: Path) -> dict:
    td = Path(tempfile.mkdtemp())
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vf", "fps=5,scale=480:-1", "-q:v", "3", str(td / "f_%03d.jpg")],
        check=True,
    )
    frames = sorted(td.glob("f_*.jpg"))
    if len(frames) < 2:
        return {"error": "too_few_frames", "n_frames": len(frames)}
    imgs = [Image.open(f).convert("L") for f in frames]
    w, h = imgs[0].size
    mx1, mx2 = int(w * 0.3), int(w * 0.7)
    my1, my2 = int(h * 0.45), int(h * 0.65)
    mouth = [
        ImageStat.Stat(
            ImageChops.difference(a.crop((mx1, my1, mx2, my2)), b.crop((mx1, my1, mx2, my2)))
        ).mean[0]
        for a, b in zip(imgs, imgs[1:])
    ]
    mouth_mean = sum(mouth) / len(mouth)
    first = Image.open(frames[0]).convert("RGB").resize(Image.open(ref_image).size)
    src = Image.open(ref_image).convert("RGB")
    mad = ImageStat.Stat(ImageChops.difference(src, first)).mean[0]
    # save review frames
    review = []
    for i, f in enumerate(frames[:: max(1, len(frames) // 4)][:4]):
        out = video.parent / f"{video.stem}_frame_{i}.jpg"
        Image.open(f).convert("RGB").save(out, quality=90)
        review.append(str(out))
    # audio speechlikeness
    wav = td / "a.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1", str(wav)],
        check=True,
    )
    with wave.open(str(wav), "rb") as wvf:
        n = wvf.getnframes()
        fr = wvf.getframerate()
        samples = struct.unpack("<" + "h" * n, wvf.readframes(n))
    hop = max(1, int(fr * 0.05))
    rms = [
        math.sqrt(sum(x * x for x in samples[i : i + hop]) / hop)
        for i in range(0, len(samples) - hop, hop)
    ]
    mean = sum(rms) / len(rms) if rms else 0
    std = (sum((r - mean) ** 2 for r in rms) / len(rms)) ** 0.5 if rms else 0
    return {
        "n_frames": len(frames),
        "mouth_roi_mad_mean": round(mouth_mean, 3),
        "identity_pixel_mad": round(mad, 2),
        "audio_duration_s": round(n / fr, 3),
        "audio_energy_cv": round(std / (mean + 1e-9), 3),
        "review_frames": review,
        "passes_talking_proxy": mouth_mean >= 2.0 and mad < 80,
    }


async def _one(case: dict, ad: KieAdapter) -> dict:
    cid = case["id"]
    out_dir = ART / cid
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": cid,
        "title": case["title"],
        "script": case["script"],
        "started_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    t0 = time.time()
    print(f"\n=== {case['title']} ===")

    # 1) Portrait
    print("1) GPT Image 2…")
    img_res = await ad.generate_image(
        prompt=case["portrait_prompt"],
        model_id="gpt-image-2",
        size=case["size"],
    )
    portrait = out_dir / "portrait.png"
    _dl(img_res.media_url, portrait)
    meta["portrait"] = {
        "model": img_res.model,
        "url": img_res.media_url,
        "local": str(portrait),
        "bytes": portrait.stat().st_size,
        "cost": img_res.cost,
    }
    print("   portrait", portrait.stat().st_size, img_res.model)

    # 2) TTS
    print("2) edge-tts…")
    speech = out_dir / "narration.wav"
    tts_meta = await _tts(case["script"], case["voice"], speech)
    meta["tts"] = tts_meta
    print("   speech", tts_meta["duration_s"], "s", case["voice"])

    # 3) Upload + lipsync
    print("3) Kling lipsync…")
    img_pub = await ad.upload_public_url(
        portrait.read_bytes(), filename=f"{cid}_portrait.png", content_type="image/png",
    )
    aud_pub = await ad.upload_public_url(
        speech.read_bytes(), filename=f"{cid}_narration.wav", content_type="audio/wav",
    )
    ls = await ad.generate_lipsync(
        image_url=img_pub,
        audio_url=aud_pub,
        prompt="a person talking naturally to camera, accurate lip sync, vertical talking head",
        model_id="kling/ai-avatar-pro",
        resolution="480p",
    )
    video = out_dir / "talking.mp4"
    _dl(ls.media_url, video)
    meta["lipsync"] = {
        "model": ls.model,
        "url": ls.media_url,
        "local": str(video),
        "bytes": video.stat().st_size,
        "cost": ls.cost,
        "mode": "kling_avatar",
    }
    print("   video", video.stat().st_size, ls.model)

    # 4) Analyze
    print("4) analyze…")
    meta["analysis"] = _analyze_video(video, portrait)
    meta["elapsed_s"] = round(time.time() - t0, 1)
    meta["ok"] = bool(meta["analysis"].get("passes_talking_proxy")) and video.stat().st_size > 50_000
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("   ok=", meta["ok"], "mouth=", meta["analysis"].get("mouth_roi_mad_mean"),
          "id_mad=", meta["analysis"].get("identity_pixel_mad"), "elapsed=", meta["elapsed_s"])
    return meta


async def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    ad = KieAdapter()
    results = []
    for case in CASES:
        try:
            results.append(await _one(case, ad))
        except Exception as e:
            err = {
                "id": case["id"],
                "title": case["title"],
                "ok": False,
                "error": str(e)[:500],
            }
            print("FAILED", case["id"], e)
            results.append(err)
            (ART / case["id"]).mkdir(parents=True, exist_ok=True)
            (ART / case["id"] / "meta.json").write_text(
                json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8",
            )

    report = {
        "suite": "koubo_two_videos_real",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform_path": "GPT Image 2 → edge-tts → kling/ai-avatar-pro",
        "tts_honesty": (
            "KIE ElevenLabs TTS still returning internal error; "
            "used Microsoft Edge Neural TTS (edge-tts) so lip-sync could be judged on real speech."
        ),
        "videos": results,
        "pass_count": sum(1 for r in results if r.get("ok")),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (ART / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    # Convenience copies at top level
    for r in results:
        if not r.get("ok"):
            continue
        vid = Path(r["lipsync"]["local"])
        dest = ART / f"{r['id']}.mp4"
        dest.write_bytes(vid.read_bytes())
        por = Path(r["portrait"]["local"])
        (ART / f"{r['id']}_portrait.png").write_bytes(por.read_bytes())
    print("\nWrote", REPORT)
    print(json.dumps({
        "pass_count": report["pass_count"],
        "videos": [
            {
                "id": r.get("id"),
                "ok": r.get("ok"),
                "title": r.get("title"),
                "mp4": (r.get("lipsync") or {}).get("local"),
                "mouth": (r.get("analysis") or {}).get("mouth_roi_mad_mean"),
                "error": r.get("error"),
            }
            for r in results
        ],
    }, ensure_ascii=False, indent=2))
    return 0 if report["pass_count"] == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
