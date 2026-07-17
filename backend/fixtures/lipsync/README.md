# Lipsync / Talking Avatar fixtures

| File | Role | Notes |
|------|------|-------|
| `portrait.png` | Cartoon stick-figure still | **Negative control** — not photoreal; use to prove bad inputs fail as digital humans |
| `line.wav` | Steady tone (~2s) | **Negative control** — not speech (`energy_cv≈0.13`) |
| `photo_face.jpg` | Photoreal portrait | Positive-control face for accuracy eval |
| `speech_zh.wav` | Spoken Chinese (~6s, espeak-ng) | Positive-control audio |
| `last_run.json` | Latest live evidence metadata | May point at expiring tempfile URLs |

## Accuracy eval

```bash
cd backend
python3 scripts/lipsync_accuracy_eval.py
# Spend KIE credits on photoreal+speech re-run:
LIPSYNC_ACCURACY_LIVE=1 python3 scripts/lipsync_accuracy_eval.py
```

Report: `fixtures/audit/lipsync_accuracy_latest.json`  
Write-up: `docs/LIPSYNC_DIGITAL_HUMAN_ACCURACY.md`

Harness: `LIPSYNC_FIXTURE_LIVE=1` via `scripts/fixture_derivative_harness.py`.
