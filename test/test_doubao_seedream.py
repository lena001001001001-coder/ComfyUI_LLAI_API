#!/usr/bin/env python3
"""Offline tests for the LLAI Doubao Seedream 4.5 node."""

import json

import pytest
import torch


def test_doubao_seedream_registration_and_interface():
    from nodes.Doubao import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    node_class = NODE_CLASS_MAPPINGS["LLDoubaoSeedream45TextToImage"]
    inputs = node_class.INPUT_TYPES()

    assert NODE_DISPLAY_NAME_MAPPINGS["LLDoubaoSeedream45TextToImage"] == "LL-doubao-seedream-4.5-文生图"
    assert node_class.CATEGORY == "LLAI/Doubao"
    assert node_class.RETURN_TYPES == ("IMAGE", "STRING", "STRING")
    assert inputs["required"]["response_format"][0] == ["url", "b64_json"]
    assert inputs["required"]["size"][0] == ["2K", "4K"]
    assert inputs["required"]["size"][1]["default"] == "2K"
    assert len(inputs["optional"]["ratio"][0]) == 15
    assert inputs["required"]["seed"][1]["control_after_generate"] is True
    assert inputs["required"]["seed"][1]["max"] == 0xFFFFFFFFFFFFFFFF


def test_doubao_seedream_sizes_match_documented_limits():
    from nodes.Doubao.doubao_seedream import (
        MAX_ASPECT_RATIO,
        MAX_PIXELS,
        MIN_ASPECT_RATIO,
        MIN_PIXELS,
        RATIO_OPTIONS_BY_SIZE,
        SIZE_OPTIONS,
        resolve_output_size,
        resolve_size,
    )

    assert len(RATIO_OPTIONS_BY_SIZE["2K"]) == 9
    assert len(RATIO_OPTIONS_BY_SIZE["4K"]) == 6
    for label, value in SIZE_OPTIONS.items():
        assert resolve_size(label) == value
        if "x" not in value:
            continue
        width, height = (int(part) for part in value.split("x"))
        assert MIN_PIXELS <= width * height <= MAX_PIXELS
        assert MIN_ASPECT_RATIO <= width / height <= MAX_ASPECT_RATIO
    assert resolve_output_size("2K", RATIO_OPTIONS_BY_SIZE["2K"][0]) == "2048x2048"
    assert resolve_output_size("4K", RATIO_OPTIONS_BY_SIZE["4K"][0]) == "3840x2160"


@pytest.mark.parametrize("size", ["1024x1024", "8192x4096", "bad-size"])
def test_doubao_seedream_rejects_invalid_sizes(size):
    from nodes.Doubao.doubao_seedream import resolve_size

    with pytest.raises(ValueError):
        resolve_size(size)


def test_doubao_seedream_payload_uses_documented_fields():
    from nodes.Doubao.doubao_seedream import MODEL, build_payload

    assert build_payload("一座雪山", "2K", "2560x1440（16:9 横图）", False, "url") == {
        "model": MODEL,
        "prompt": "一座雪山",
        "size": "2560x1440",
        "sequential_image_generation": "disabled",
        "stream": False,
        "response_format": "url",
        "watermark": False,
    }


def test_doubao_seedream_calls_llai_and_parses_url(monkeypatch):
    from nodes.Doubao import doubao_seedream as module

    class FakeResponse:
        status_code = 200
        text = "OK"

        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"data": [{"url": "https://example.com/seedream.jpeg"}], "created": 1}

    class FakeSession:
        trust_env = True

        def post(self, url, **kwargs):
            assert url == module.ENDPOINT
            assert kwargs["json"]["model"] == module.MODEL
            assert "seed" not in kwargs["json"]
            assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
            return FakeResponse()

    monkeypatch.setattr(module.requests, "Session", FakeSession)
    monkeypatch.setattr(
        module,
        "_outputs_to_tensor_and_refs",
        lambda outputs, timeout: (torch.zeros((1, 2, 2, 3)), "ignored"),
    )

    image, result_ref, summary = module.LLDoubaoSeedream45TextToImage().generate(
        prompt="一座雪山",
        size="2K",
        watermark=False,
        response_format="url",
        api_key="sk-test",
        seed=1234,
        timeout=60,
        ratio="2048x2048（1:1 方图）",
    )

    assert tuple(image.shape) == (1, 2, 2, 3)
    assert result_ref == "https://example.com/seedream.jpeg"
    assert json.loads(summary)["created"] == 1
