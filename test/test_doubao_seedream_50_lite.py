"""Offline checks for the combined Doubao Seedream 5.0 Lite node."""

import pytest
import torch


def test_seedream_50_lite_registration_and_interface():
    from nodes.Doubao import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from nodes.Doubao.doubao_seedream_50_lite import (
        ALL_RATIO_OPTIONS,
        MAX_IMAGES,
        MODEL,
        REFERENCE_IMAGE_KEYS,
        SIZE_LEVELS,
    )

    key = "LLDoubaoSeedream50Lite"
    node_class = NODE_CLASS_MAPPINGS[key]
    inputs = node_class.INPUT_TYPES()

    assert NODE_DISPLAY_NAME_MAPPINGS[key] == "LL-doubao-seedream-5.0lite"
    assert MODEL == "doubao-seedream-5-0-260128"
    assert node_class.CATEGORY == "LLAI/Doubao"
    assert inputs["required"]["size"][0] == SIZE_LEVELS
    assert inputs["required"]["ratio"][0] == ALL_RATIO_OPTIONS
    assert MAX_IMAGES == 14
    assert len(REFERENCE_IMAGE_KEYS) == MAX_IMAGES
    assert all(inputs["optional"][name][0] == "IMAGE" for name in REFERENCE_IMAGE_KEYS)


def test_seedream_50_lite_payload_switches_mode():
    from nodes.Doubao.doubao_seedream_50_lite import build_payload

    text_payload = build_payload("未来城市", "2K", "2848x1600（16:9 横图）", "png", "url", False)
    image_payload = build_payload(
        "改成水彩",
        "3K",
        "2592x3456（3:4 竖图）",
        "jpeg",
        "b64_json",
        True,
        image=["data:image/jpeg;base64,one", "data:image/jpeg;base64,two"],
    )

    assert text_payload == {
        "model": "doubao-seedream-5-0-260128",
        "prompt": "未来城市",
        "size": "2848x1600",
        "sequential_image_generation": "disabled",
        "output_format": "png",
        "response_format": "url",
        "watermark": False,
    }
    assert image_payload["image"] == [
        "data:image/jpeg;base64,one",
        "data:image/jpeg;base64,two",
    ]
    assert image_payload["size"] == "2592x3456"


def test_seedream_50_lite_calls_llai_for_text_and_image(monkeypatch):
    from nodes.Doubao import doubao_seedream_50_lite as module

    payloads = []

    class FakeResponse:
        status_code = 200
        text = ""

        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"data": [{"url": "https://example.com/result.png"}]}

    class FakeSession:
        trust_env = True

        def post(self, url, json, headers, timeout):
            assert url == "https://api.llaiapi.host/v1/images/generations"
            payloads.append(json)
            return FakeResponse()

    monkeypatch.setattr(module.requests, "Session", FakeSession)
    monkeypatch.setattr(module, "_outputs_to_tensor_and_refs", lambda outputs, timeout: ("image", []))
    monkeypatch.setattr(
        module,
        "_image_data_url_45",
        lambda image, index=0: f"data:image/jpeg;base64,reference-{int(image[0, 0, 0, 0])}-{index}",
    )

    node = module.LLDoubaoSeedream50Lite()
    common = {
        "size": "2K",
        "output_format": "png",
        "watermark": False,
        "response_format": "url",
        "api_key": "sk-test",
        "seed": 1,
        "ratio": "2048x2048（1:1 方图）",
        "timeout": 60,
    }
    assert node.generate(prompt="文生图", **common)[0] == "image"
    assert "image" not in payloads[0]

    reference_1 = torch.ones((1, 2, 2, 3))
    reference_2 = torch.full((1, 2, 2, 3), 2.0)
    assert node.generate(prompt="图生图", 参考图=reference_1, 参考图8=reference_2, **common)[0] == "image"
    assert payloads[1]["image"] == [
        "data:image/jpeg;base64,reference-1-0",
        "data:image/jpeg;base64,reference-2-0",
    ]


def test_seedream_50_lite_rejects_more_than_14_images():
    from nodes.Doubao.doubao_seedream_50_lite import LLDoubaoSeedream50Lite

    with pytest.raises(ValueError, match="最多支持 14 张参考图"):
        LLDoubaoSeedream50Lite().generate(
            prompt="图生图",
            size="2K",
            output_format="png",
            watermark=False,
            response_format="url",
            api_key="sk-test",
            seed=1,
            ratio="2048x2048（1:1 方图）",
            参考图=torch.zeros((15, 2, 2, 3)),
        )
