"""Offline checks for the combined Doubao Seedream 4.5 node."""

import torch


def test_seedream_45_combined_registration_and_interface():
    from nodes.Doubao import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from nodes.Doubao.doubao_seedream import ALL_RATIO_OPTIONS, SIZE_LEVELS
    from nodes.Doubao.doubao_seedream_45_combined import REFERENCE_IMAGE_KEYS

    key = "LLDoubaoSeedream45"
    node_class = NODE_CLASS_MAPPINGS[key]
    inputs = node_class.INPUT_TYPES()

    assert NODE_DISPLAY_NAME_MAPPINGS[key] == "LL-doubao-seedream-4.5"
    assert node_class.CATEGORY == "LLAI/Doubao"
    assert inputs["required"]["size"][0] == SIZE_LEVELS
    assert inputs["required"]["ratio"][0] == ALL_RATIO_OPTIONS
    assert len(REFERENCE_IMAGE_KEYS) == 14
    assert all(inputs["optional"][name][0] == "IMAGE" for name in REFERENCE_IMAGE_KEYS)
    assert "batch_count" not in inputs["required"]
    assert "batch_count" not in inputs["optional"]


def test_seedream_45_combined_without_image_uses_text_to_image(monkeypatch):
    from nodes.Doubao import doubao_seedream_45_combined as module

    calls = []

    def fake_generate(self, **kwargs):
        calls.append(kwargs)
        return "text-image", "text-ref", "text-summary"

    monkeypatch.setattr(module.LLDoubaoSeedream45TextToImage, "generate", fake_generate)
    result = module.LLDoubaoSeedream45().generate(
        prompt="雪山日出",
        size="2K",
        watermark=False,
        response_format="url",
        api_key="sk-test",
        seed=1,
        ratio="2560x1440（16:9 横图）",
        timeout=60,
    )

    assert result == ("text-image", "text-ref", "text-summary")
    assert len(calls) == 1
    assert calls[0]["prompt"] == "雪山日出"
    assert calls[0]["ratio"] == "2560x1440（16:9 横图）"


def test_seedream_45_combined_with_images_uses_image_to_image(monkeypatch):
    from nodes.Doubao import doubao_seedream_45_combined as module

    calls = []

    def fake_generate(self, **kwargs):
        calls.append(kwargs)
        return "edit-image", "edit-ref", "edit-summary"

    monkeypatch.setattr(module.LLDoubaoSeedream45ImageToImage, "generate", fake_generate)
    image_2 = torch.zeros((1, 2, 2, 3))
    image_9 = torch.ones((1, 2, 2, 3))
    result = module.LLDoubaoSeedream45().generate(
        prompt="改成电影夜景",
        size="4K",
        watermark=False,
        response_format="url",
        api_key="sk-test",
        seed=2,
        ratio="3840x2160（4K 16:9 横图）",
        timeout=60,
        参考图2=image_2,
        参考图9=image_9,
    )

    assert result == ("edit-image", "edit-ref", "edit-summary")
    assert len(calls) == 1
    assert calls[0]["参考图1"] is image_2
    assert calls[0]["参考图2"] is image_9
    assert calls[0]["prompt"] == "改成电影夜景"
    assert calls[0]["ratio"] == "3840x2160（4K 16:9 横图）"
