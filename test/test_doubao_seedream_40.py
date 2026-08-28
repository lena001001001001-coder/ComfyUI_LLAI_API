#!/usr/bin/env python3
"""Offline interface checks for Doubao Seedream 4.0."""

def test_seedream_40_registration_and_model():
    from nodes.Doubao import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from nodes.Doubao.doubao_seedream_40 import MODEL

    key = "LLDoubaoSeedream40TextToImage"
    assert key in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS[key] == "LL-doubao-seedream-4.0-文生图"
    assert MODEL == "doubao-seedream-4-0-250828"


def test_seedream_40_payload_and_documented_sizes():
    from nodes.Doubao.doubao_seedream_40 import (
        MODEL,
        RATIO_OPTIONS_1K,
        RATIO_OPTIONS_2K,
        RATIO_OPTIONS_4K,
        SIZE_LEVELS,
        LLDoubaoSeedream40TextToImage,
        build_payload,
    )

    assert SIZE_LEVELS == ["1K", "2K", "4K"]
    assert LLDoubaoSeedream40TextToImage.INPUT_TYPES()["required"]["size"][0] == SIZE_LEVELS

    payload = build_payload("星际列车", "2K", "1728x2304（3:4 竖图）", False, "url")
    assert payload["model"] == MODEL
    assert payload["size"] == "2K"
    assert payload["prompt"].endswith("构图要求：请生成 3:4 比例的竖向图片。")
    assert payload["sequential_image_generation"] == "disabled"
    assert build_payload("cat", "4K", RATIO_OPTIONS_4K[0], False, "url")["size"] == "4K"
    assert build_payload("cat", "1K", RATIO_OPTIONS_1K[0], False, "url")["size"] == "1K"
    assert "3:2 比例的横向图片" in build_payload(
        "cat", "1K", "1248x832（3:2 横图）", False, "url"
    )["prompt"]
    legacy = build_payload("cat", "1K", "1536x1024（3:2 横图）", False, "url")
    assert legacy["size"] == "1K"
    assert "3:2 比例的横向图片" in legacy["prompt"]
    assert len(RATIO_OPTIONS_1K) == 8
    assert len(RATIO_OPTIONS_2K) == 8
    assert len(RATIO_OPTIONS_4K) == 8

    assert "1280x720（16:9 横图）" in RATIO_OPTIONS_1K
    assert "2848x1600（16:9 横图）" in RATIO_OPTIONS_2K
    assert "6240x2656（21:9 超宽图）" in RATIO_OPTIONS_4K
    assert [item.split("（", 1)[0] for item in RATIO_OPTIONS_1K] == [
        "1024x1024", "1152x864", "864x1152", "1280x720",
        "720x1280", "1248x832", "832x1248", "1512x648",
    ]


def test_seedream_40_image_to_image_exposes_1k_size():
    from nodes.Doubao.doubao_seedream_40_i2i import (
        LLDoubaoSeedream40ImageToImage,
        RATIO_LABELS,
        SIZE_LEVELS,
        _size_value,
    )

    inputs = LLDoubaoSeedream40ImageToImage.INPUT_TYPES()
    assert SIZE_LEVELS == ["1K", "2K", "4K"]
    assert inputs["required"]["size"][0] == SIZE_LEVELS
    assert _size_value("1K", RATIO_LABELS["1K"][0]) == "1024x1024"
