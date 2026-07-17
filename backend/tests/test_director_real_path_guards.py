"""Guards that real Director runs don't silently fake digital humans."""
from pathlib import Path


def test_kie_seed_coercion_accepts_hex_digest():
    src = Path(__file__).resolve().parents[1] / "app" / "adapters" / "kie_adapter.py"
    text = src.read_text(encoding="utf-8")
    assert 'int(str(seed), 16)' in text
    assert 'payload["seed"] = int(seed)' in text


def test_real_lipsync_does_not_ken_burns_when_deps_missing():
    src = Path(__file__).resolve().parents[1] / "app" / "director.py"
    text = src.read_text(encoding="utf-8")
    assert "真实生成不会回退 Ken Burns" in text
    assert "if use_demo_l:" in text
    # Preview Ken Burns must be gated on use_demo_l alone, not missing deps
    assert "if use_demo_l or not (img_pub and aud_pub):" not in text


def test_tts_failure_marks_step_failed():
    src = Path(__file__).resolve().parents[1] / "app" / "director.py"
    text = src.read_text(encoding="utf-8")
    assert 'step.status = "failed"' in text
    assert "配音失败" in text
