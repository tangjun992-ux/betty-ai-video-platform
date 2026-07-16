# Motion fixture library (canonical sample pair)

Generated, license-free assets for **input** validation of Motion Transfer.

| File | Role |
|------|------|
| `still.png` | Target character still (512×768) |
| `ref.mp4` | Short reference motion (2s) |

**Honesty:** These are *inputs* for pipeline/contract tests — not Act-One / Kling Motion quality references.
Live paid runs are gated by `MOTION_FIXTURE_LIVE=1`.

Regenerate:
```bash
cd backend && python scripts/generate_motion_fixtures.py
```
