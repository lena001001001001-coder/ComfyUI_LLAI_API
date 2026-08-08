"""Offline checks for Doubao Seedream 5.0 Pro."""


def test_registration_and_documented_sizes():
    from nodes.Doubao import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from nodes.Doubao.doubao_seedream_50_pro import (
        MODEL, RATIO_OPTIONS_1K, RATIO_OPTIONS_15K, RATIO_OPTIONS_2K,
    )
    key = "LLDoubaoSeedream50ProTextToImage"
    assert key in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS[key] == "LL-doubao-seedream-5.0pro-文生图"
    assert MODEL == "doubao-seedream-5-0-pro-260628"
    assert len(RATIO_OPTIONS_1K) == len(RATIO_OPTIONS_15K) == len(RATIO_OPTIONS_2K) == 8
    assert "1424x800（16:9 横图）" in RATIO_OPTIONS_1K
    assert "2048x1152（16:9 横图）" in RATIO_OPTIONS_15K
    assert "2816x1584（16:9 横图）" in RATIO_OPTIONS_2K


def test_payload_uses_pro_resolution_alias_and_prompt_ratio():
    from nodes.Doubao.doubao_seedream_50_pro import RATIO_OPTIONS_1K, build_payload
    payload = build_payload("小猫", "1K", "1248x832（3:2 横图）", False, "url")
    assert payload["model"] == "doubao-seedream-5-0-pro-260628"
    assert payload["size"] == "1K"
    assert "3:2 比例的横向图片" in payload["prompt"]
    assert "stream" not in payload
    assert "sequential_image_generation" not in payload
