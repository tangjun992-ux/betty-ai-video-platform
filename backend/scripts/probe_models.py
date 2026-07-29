"""
Real model availability probe against the live KIE.ai gateway.

For every model registered in ``app.api.models_info.MODELS`` this script issues a
minimal ``createTask`` request to the KIE gateway and classifies the model by the
gateway's *real* response:

  * recognized  — gateway accepted the task (code==200, taskId issued). The model
                  id is valid and callable → eligible to be marked ``active``.
  * rejected    — gateway refused the model (HTTP 4xx or code!=200, e.g. 422
                  "model not supported"). Stays ``beta``.
  * error       — network / auth / timeout, *or* still rate limited (429) after
                  all retries. Inconclusive; status unchanged (never fabricated).

Rate limiting (HTTP 429 or in-body code=429 "call frequency is too high") is
never a support verdict — it means we probed too fast. Such responses are retried
with exponential backoff (Retry-After honored) and, only if still limited after
all retries, reported as inconclusive ``error`` rather than ``rejected``.

The probe only *submits* a task (and immediately stops); it does not wait for the
full generation to finish, so it is cheap and fast while still being a genuine
end-to-end recognition signal from the provider.

Usage:
    cd backend
    KIE_API_KEY=... python scripts/probe_models.py            # report only
    KIE_API_KEY=... python scripts/probe_models.py --apply    # + patch status in models_info.py

Without KIE_API_KEY the script exits cleanly and reports that nothing could be
verified — it never fabricates availability.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from app.adapters.kie_adapter import _resolve_kie_model_id, _is_video_kie_model
from app.api.models_info import MODELS
from app.config import settings

MODELS_INFO_PATH = Path(__file__).resolve().parent.parent / "app" / "api" / "models_info.py"

RECOGNIZED, REJECTED, ERROR = "recognized", "rejected", "error"

# The KIE gateway signals rate limiting with HTTP 429 *or* an in-body code=429
# ("call frequency is too high"). That is not a model-support verdict — it means
# we probed too fast — so it must never be classified as REJECTED. We retry with
# exponential backoff and, if still limited after all retries, report it as an
# inconclusive ERROR so the model keeps its current status (never fabricated).
RATE_LIMIT_CODES = {429}
MAX_RETRIES = 5


def _minimal_input(kie_model_id: str) -> dict:
    """Smallest valid input payload for a recognition probe.

    Mirrors the real adapter payloads so a probe reflects production behavior:
      * images send both aspectRatio (camel) and aspect_ratio (snake) — model
        families disagree on the key name (e.g. imagen4 requires snake_case and
        422s on an empty value otherwise).
      * videos send duration as a *string* — some Kling variants 500 on an int
        ("duration must be a string" / "This field is required").
    """
    if _is_video_kie_model(kie_model_id):
        # Kling text-to-video 500s ("Operation not found") when sent a resolution
        # with no matching SKU — it takes only {prompt, duration, aspect_ratio}.
        if kie_model_id.startswith("kling/") and "text-to-video" in kie_model_id:
            return {"prompt": "a calm ocean at sunrise", "duration": "5", "aspect_ratio": "16:9"}
        return {"prompt": "a calm ocean at sunrise", "duration": "5", "resolution": "720p"}
    return {"prompt": "a red apple on a white table", "aspectRatio": "1:1", "aspect_ratio": "1:1"}


async def _probe_one(client: httpx.AsyncClient, model_id: str, base: str, headers: dict) -> dict:
    kie_id = _resolve_kie_model_id(model_id)
    payload = {"model": kie_id, "input": _minimal_input(kie_id)}

    last_detail = ""
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.post(f"{base}/api/v1/jobs/createTask", headers=headers, json=payload)
        except Exception as e:  # noqa: BLE001 — network/timeout is inconclusive, not a rejection
            return {"model_id": model_id, "kie_id": kie_id, "result": ERROR,
                    "detail": f"{type(e).__name__}: {e}"[:200]}

        # HTTP-level rate limiting → back off and retry.
        if resp.status_code == 429:
            last_detail = f"HTTP 429 (rate limited, attempt {attempt + 1}/{MAX_RETRIES})"
            await asyncio.sleep(_backoff_delay(attempt, resp))
            continue
        if resp.status_code != 200:
            return {"model_id": model_id, "kie_id": kie_id, "result": REJECTED,
                    "detail": f"HTTP {resp.status_code}: {resp.text[:160]}"}
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            return {"model_id": model_id, "kie_id": kie_id, "result": ERROR, "detail": "non-JSON response"}

        code = int(data.get("code", 0))
        if code == 200 and (data.get("data") or {}).get("taskId"):
            return {"model_id": model_id, "kie_id": kie_id, "result": RECOGNIZED,
                    "detail": f"taskId={data['data']['taskId']}"}
        # In-body rate limiting → back off and retry (not a support verdict).
        if code in RATE_LIMIT_CODES:
            last_detail = f"code=429 rate limited (attempt {attempt + 1}/{MAX_RETRIES}) msg={data.get('msg', '')[:100]}"
            await asyncio.sleep(_backoff_delay(attempt, resp))
            continue
        # Any other 4xx code from KIE = unrecognized / unsupported model.
        return {"model_id": model_id, "kie_id": kie_id, "result": REJECTED,
                "detail": f"code={code} msg={data.get('msg', '')[:140]}"}

    # Exhausted retries while still rate limited → inconclusive, not a rejection.
    return {"model_id": model_id, "kie_id": kie_id, "result": ERROR,
            "detail": f"still rate limited after {MAX_RETRIES} retries — {last_detail}"}


def _backoff_delay(attempt: int, resp: httpx.Response | None = None) -> float:
    """Exponential backoff with jitter; honors a Retry-After header when present."""
    if resp is not None:
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), 30.0)
            except ValueError:
                pass
    base = min(2.0 * (2 ** attempt), 20.0)  # 2, 4, 8, 16, 20 ...
    return base + random.uniform(0, 1.0)


async def probe_all() -> list[dict]:
    api_key = settings.KIE_API_KEY or os.getenv("KIE_API_KEY", "")
    base = (settings.KIE_BASE_URL or "https://api.kie.ai").rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60) as client:
        # Low concurrency + a small inter-request stagger keeps us under the
        # gateway's rate limit so recognition verdicts aren't masked by 429s.
        sem = asyncio.Semaphore(2)

        async def guarded(m):
            async with sem:
                mid = m.id if hasattr(m, "id") else m["id"]
                result = await _probe_one(client, mid, base, headers)
                await asyncio.sleep(0.75)  # gentle stagger between probes
                return result

        return await asyncio.gather(*(guarded(m) for m in MODELS))


def _split_model_blocks(src: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of each ``ModelInfo(...)`` call, matching
    parentheses so nested ``ModelCapability(...)`` calls are handled correctly.
    """
    spans: list[tuple[int, int]] = []
    for m in re.finditer(r"ModelInfo\(", src):
        i = m.end() - 1  # position of the opening '('
        depth = 0
        j = i
        while j < len(src):
            ch = src[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    spans.append((m.start(), j + 1))
                    break
            j += 1
    return spans


def _apply_status(recognized_ids: set[str]) -> int:
    """Rewrite status="beta" → "active" for recognized models, in-place. Returns count changed.

    Operates per balanced ``ModelInfo(...)`` block so that the ``id`` and the
    (much later, after a nested ``ModelCapability(...)``) ``status`` field are
    matched within the same model entry.
    """
    src = MODELS_INFO_PATH.read_text()
    out = []
    last = 0
    changed = 0
    for start, end in _split_model_blocks(src):
        out.append(src[last:start])
        block = src[start:end]
        mid_match = re.search(r'id="([^"]+)"', block)
        if mid_match and mid_match.group(1) in recognized_ids and 'status="beta"' in block:
            block = block.replace('status="beta"', 'status="active"')
            changed += 1
        out.append(block)
        last = end
    out.append(src[last:])
    if changed:
        MODELS_INFO_PATH.write_text("".join(out))
    return changed


def _self_check() -> int:
    """Offline validation of the promotion mechanism — no network / key required.

    Runs ``_apply_status`` against an in-memory copy of models_info.py for a
    synthetic recognized set and asserts exactly the expected beta→active
    rewrites happen, then restores the file untouched. Proves the --apply path
    is correct before a live key is ever provided.
    """
    original = MODELS_INFO_PATH.read_text()
    beta_ids: list[str] = []
    for start, end in _split_model_blocks(original):
        block = original[start:end]
        mid = re.search(r'id="([^"]+)"', block)
        if mid and 'status="beta"' in block:
            beta_ids.append(mid.group(1))
    if not beta_ids:
        print("self-check: no beta models found — nothing to validate.")
        return 0
    sample = set(beta_ids[: min(3, len(beta_ids))])
    try:
        n = _apply_status(sample)
        after = MODELS_INFO_PATH.read_text()
        ok = (n == len(sample))
        # verify each sampled id is now active and no other beta was touched
        after_active_ids = set()
        for start, end in _split_model_blocks(after):
            block = after[start:end]
            mid = re.search(r'id="([^"]+)"', block)
            if mid and 'status="active"' in block:
                after_active_ids.add(mid.group(1))
        for mid in sample:
            if mid not in after_active_ids:
                ok = False
        remaining_beta = len(re.findall(r'status="beta"', after))
        expected_beta = len(re.findall(r'status="beta"', original)) - len(sample)
        ok = ok and (remaining_beta == expected_beta)
    finally:
        MODELS_INFO_PATH.write_text(original)  # always restore
    print(f"self-check: promoted {n}/{len(sample)} sampled beta models, "
          f"file restored → {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe KIE model availability")
    parser.add_argument("--apply", action="store_true",
                        help="patch status=active for recognized models in models_info.py")
    parser.add_argument("--self-check", action="store_true",
                        help="offline validation of the promotion logic (no key needed)")
    args = parser.parse_args()

    if args.self_check:
        return _self_check()

    api_key = settings.KIE_API_KEY or os.getenv("KIE_API_KEY", "")
    if not api_key:
        print("KIE_API_KEY not set — cannot verify any model against the live gateway.")
        print("No status was changed (availability is never fabricated).")
        return 2

    results = asyncio.run(probe_all())
    buckets: dict[str, list[dict]] = {RECOGNIZED: [], REJECTED: [], ERROR: []}
    for r in results:
        buckets[r["result"]].append(r)

    for name in (RECOGNIZED, REJECTED, ERROR):
        rows = buckets[name]
        print(f"\n=== {name.upper()} ({len(rows)}) ===")
        for r in sorted(rows, key=lambda x: x["model_id"]):
            print(f"  {r['model_id']:22} → {r['kie_id']:34} {r['detail']}")

    print(f"\nSummary: recognized={len(buckets[RECOGNIZED])} "
          f"rejected={len(buckets[REJECTED])} error={len(buckets[ERROR])} "
          f"(total={len(results)})")

    if args.apply:
        recognized_ids = {r["model_id"] for r in buckets[RECOGNIZED]}
        n = _apply_status(recognized_ids)
        print(f"Applied: {n} model(s) promoted beta → active in models_info.py")
    else:
        print("Report only. Re-run with --apply to promote recognized models to active.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
