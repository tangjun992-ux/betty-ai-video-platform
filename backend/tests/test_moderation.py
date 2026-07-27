"""Content moderation policy tests (pure, no external deps)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.moderation import check_prompt, is_safe


def test_allows_normal_prompts():
    for p in [
        "a cozy coffee shop at sunset, cinematic lighting",
        "产品广告，极简白背景，柔和布光",
        "a golden retriever puppy playing in autumn leaves",
        "",
    ]:
        assert check_prompt(p).allowed, p
        assert is_safe(p)


def test_blocks_sexual():
    r = check_prompt("nude explicit nsfw content")
    assert not r.allowed and r.category == "sexual" and r.reason


def test_blocks_minors():
    assert not check_prompt("underage child inappropriate").allowed
    assert check_prompt("未成年 幼女").category == "minors"


def test_blocks_deepfake_and_violence_and_illegal():
    assert not check_prompt("deepfake of a president kissing").allowed
    assert check_prompt("graphic beheading gore").category == "violence"
    assert check_prompt("how to make a bomb at home").category == "illegal"


def test_word_boundary_reduces_false_positives():
    # 'class' must not trip 'ass'; 'assessment' must not trip either
    assert check_prompt("a classroom assessment scene").allowed


if __name__ == "__main__":
    test_allows_normal_prompts()
    test_blocks_sexual()
    test_blocks_minors()
    test_blocks_deepfake_and_violence_and_illegal()
    test_word_boundary_reduces_false_positives()
    print("ALL MODERATION TESTS PASSED")
