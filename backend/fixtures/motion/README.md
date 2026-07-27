# Motion fixture library (canonical sample pair)

Generated, license-free assets for **input** validation of Motion Transfer
against native Kling Motion Control (`kling-3.0/motion-control`).

| File | Role |
|------|------|
| `still.png` | Target character still (512×768) |
| `ref.mp4` | Reference motion driver (**4s**, meets KIE 3–30s rule) |

**Honesty:** These are *inputs* for pipeline/contract tests — not Runway Act-One
quality references. Live paid runs are gated by `MOTION_FIXTURE_LIVE=1`.

Regenerate:
```bash
cd backend && python scripts/generate_motion_fixtures.py
```
