"""Offline checks for the combined Doubao Seedream 5.0 Pro node."""

import torch


def test_seedream_50_pro_combined_registration_and_interface():
    from nodes.Doubao import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from nodes.Doubao.doubao_seedream_50_pro import ALL_RATIO_OPTIONS, SIZE_LEVELS
    from nodes.Doubao.doubao_seedream_50_pro_combined import REFERENCE_IMAGE_KEYS

    key = "LLDoubaoSeedream50Pro"
    node_class = NODE_CLASS_MAPPINGS[key]
    inputs = node_class.INPUT_TYPES()

    assert NODE_DISPLAY_NAME_MAPPINGS[key] == "LL-doubao-seedream-5.0pro"
    assert node_class.CATEGORY == "LLAI/Doubao"
    assert inputs["required"]["size"][0] == SIZE_LEVELS
    assert inputs["required"]["ratio"][0] == ALL_RATIO_OPTIONS
    assert len(REFERENCE_IMAGE_KEYS) == 10
    assert all(inputs["optional"][name][0] == "IMAGE" for name in REFERENCE_IMAGE_KEYS)
    assert "batch_count" not in inputs["required"]
    assert "batch_count" not in inputs["optional"]


def test_seedream_50_pro_combined_without_image_uses_text_to_image(monkeypatch):
    from nodes.Doubao import doubao_seedream_50_pro_combined as module

    calls = []

    def fake_generate(self, **kwargs):
        calls.append(kwargs)
        return "text-image", "text-ref", "text-summary"

    monkeypatch.setattr(module.LLDoubaoSeedream50ProTextToImage, "generate", fake_generate)
    result = module.LLDoubaoSeedream50Pro().generate(
        prompt="未来都市",
        size="1.5K",
        watermark=False,
        response_format="url",
        api_key="sk-test",
        seed=1,
        ratio="2048x1152（16:9 横图）",
        timeout=60,
    )

    assert result == ("text-image", "text-ref", "text-summary")
    assert len(calls) == 1
    assert calls[0]["prompt"] == "未来都市"
    assert calls[0]["ratio"] == "2048x1152（16:9 横图）"


def test_seedream_50_pro_combined_with_images_uses_image_to_image(monkeypatch):
    from nodes.Doubao import doubao_seedream_50_pro_combined as module

    calls = []

    def fake_generate(self, **kwargs):
        calls.append(kwargs)
        return "edit-image", "edit-ref", "edit-summary"

    monkeypatch.setattr(module.LLDoubaoSeedream50ProImageToImage, "generate", fake_generate)
    image_4 = torch.zeros((1, 2, 2, 3))
    image_8 = torch.ones((1, 2, 2, 3))
    result = module.LLDoubaoSeedream50Pro().generate(
        prompt="改成水彩风格",
        size="2K",
        watermark=False,
        response_format="url",
        api_key="sk-test",
        seed=2,
        ratio="2816x1584（16:9 横图）",
        timeout=60,
        参考图4=image_4,
        参考图8=image_8,
    )

    assert result == ("edit-image", "edit-ref", "edit-summary")
    assert len(calls) == 1
    assert calls[0]["参考图1"] is image_4
    assert calls[0]["参考图2"] is image_8
    assert calls[0]["prompt"] == "改成水彩风格"
    assert calls[0]["ratio"] == "2816x1584（16:9 横图）"
