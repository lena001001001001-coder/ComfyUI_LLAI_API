#!/usr/bin/env python3
"""Offline tests for GPT Image 2 ComfyUI nodes."""

import base64
import inspect
import io
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class FakeResponse:
    def __init__(self, payload, status_code=200, text="OK", content=b""):
        self._payload = payload
        self.status_code = status_code
        self.text = text
        self.content = content

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _make_image_tensor(batch=1, width=4, height=3, channels=3):
    values = np.linspace(0, 1, batch * height * width * channels, dtype=np.float32)
    return torch.from_numpy(values.reshape(batch, height, width, channels))


def _make_single_image_tensor(width=4, height=3, channels=3):
    values = np.linspace(0, 1, height * width * channels, dtype=np.float32)
    return torch.from_numpy(values.reshape(height, width, channels))


def _make_image_numpy(batch=1, width=4, height=3, channels=3):
    values = np.linspace(0, 1, batch * height * width * channels, dtype=np.float32)
    return values.reshape(batch, height, width, channels)


def _make_png_bytes(color=(255, 0, 0, 255), mode="RGBA"):
    pil = Image.new(mode, (2, 2), color)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return buf.getvalue()


def _make_png_data_url():
    return "data:image/png;base64," + base64.b64encode(_make_png_bytes()).decode("utf-8")


def test_gpt_image_generate_interface_includes_format_and_quality():
    from nodes.GPTImage import NODE_CLASS_MAPPINGS

    node_class = NODE_CLASS_MAPPINGS["GPTImage2Generate"]
    inputs = node_class.INPUT_TYPES()

    assert node_class.RETURN_TYPES == ("IMAGE", "STRING")
    assert node_class.RETURN_NAMES == ("图像", "生成信息")
    assert "format" in inputs["optional"]
    assert "quality" in inputs["optional"]
    assert inputs["optional"]["format"][0] == ["png", "jpeg", "webp"]
    assert inputs["optional"]["quality"][0] == ["auto", "low", "medium", "high"]

    labels = node_class.INPUT_LABELS()
    assert labels["format"] == "输出格式（png/jpeg/webp）"
    assert labels["quality"] == "图像质量（清晰度等级）"


def test_gpt_image_generate_includes_experimental_aspect_ratios():
    from nodes.GPTImage import NODE_CLASS_MAPPINGS
    from nodes.GPTImage.gpt_image import _resolve_size

    node_class = NODE_CLASS_MAPPINGS["GPTImage2Generate"]
    inputs = node_class.INPUT_TYPES()
    aspect_ratios = inputs["required"]["aspect_ratio"][0]

    expected = [
        "1:3（超长竖图）",
        "1:4（超长竖图）",
        "1:6（超长竖图）",
    ]

    for ratio in expected:
        assert ratio in aspect_ratios
        assert _resolve_size("2K（高清）", ratio) != "auto"


def test_legacy_url_edit_node_interface_is_preserved():
    from nodes.GPTImage import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    node_class = NODE_CLASS_MAPPINGS["GPTImage2Edit"]
    inputs = node_class.INPUT_TYPES()
    optional = inputs["optional"]

    assert NODE_DISPLAY_NAME_MAPPINGS["GPTImage2Edit"] == "LL GPT Image 2 图片编辑"
    assert node_class.RETURN_TYPES == ("IMAGE", "STRING")
    assert node_class.RETURN_NAMES == ("图像", "生成信息")
    assert "image_url_1" in inputs["required"]
    for name in ["image_url_2", "image_url_3", "image_url_4"]:
        assert name in optional
    assert optional["background"][0] == ["auto", "transparent", "opaque"]

    params = list(inspect.signature(node_class.edit).parameters)
    assert params == [
        "self",
        "image_url_1",
        "prompt",
        "model",
        "resolution",
        "aspect_ratio",
        "n",
        "api_key",
        "image_url_2",
        "image_url_3",
        "image_url_4",
        "format",
        "quality",
        "background",
        "moderation",
        "api_base",
        "timeout",
    ]


def test_gpt_image_edit_images_node_registered_and_has_15_image_inputs():
    from nodes.GPTImage import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    assert "GPTImage2EditImages" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["GPTImage2EditImages"] == "LL GPT Image 2 图生图"

    node_class = NODE_CLASS_MAPPINGS["GPTImage2EditImages"]
    inputs = node_class.INPUT_TYPES()
    required = inputs["required"]
    optional = inputs["optional"]

    assert node_class.CATEGORY == "LLAI/GPTImage"
    assert node_class.RETURN_TYPES == ("IMAGE", "STRING", "STRING")
    assert node_class.RETURN_NAMES == ("图像", "生成信息", "响应JSON摘要")
    assert "image_1" in required
    assert optional["background"][0] == ["auto", "transparent", "opaque"]
    for idx in range(2, 16):
        assert f"image_{idx}" in optional
        assert optional[f"image_{idx}"][0] == "IMAGE"

    labels = node_class.INPUT_LABELS()
    for idx in range(1, 16):
        assert labels[f"image_{idx}"] == f"参考图{idx}"
    for name in ["prompt", "model", "resolution", "aspect_ratio", "n", "api_key", "format", "quality", "background", "moderation", "api_base", "timeout"]:
        assert name in labels

    params = inspect.signature(node_class.edit).parameters
    for idx in range(2, 16):
        assert params[f"image_{idx}"].default is None
    assert params["format"].default == "png"
    assert params["quality"].default == "auto"
    assert params["background"].default == "auto"
    assert params["moderation"].default == "auto"


def test_build_generation_payload_omits_default_optional_fields():
    from nodes.GPTImage.gpt_image import _build_generation_payload

    payload = _build_generation_payload("gpt-image-2", "a cat", 1, "auto（默认）", "1:1（正方形）", "png", "auto")

    assert payload == {"model": "gpt-image-2", "prompt": "a cat", "n": 1, "size": "auto"}


def test_build_generation_payload_sends_non_default_format_and_quality():
    from nodes.GPTImage.gpt_image import _build_generation_payload

    payload = _build_generation_payload("gpt-image-2", "a cat", 2, "1K（标清）", "1:1（正方形）", "jpeg", "high")

    assert payload == {
        "model": "gpt-image-2",
        "prompt": "a cat",
        "n": 2,
        "size": "1024x1024",
        "format": "jpeg",
        "quality": "high",
    }


def test_build_edit_form_data_omits_default_optional_fields():
    from nodes.GPTImage.gpt_image import _build_edit_form_data

    form = _build_edit_form_data("gpt-image-2", "merge them", 1, "auto（默认）", "1:1（正方形）", "png", "auto", "auto", "auto")

    assert form == {"model": "gpt-image-2", "prompt": "merge them", "n": "1", "size": "auto"}


def test_build_edit_form_data_sends_non_default_optional_fields():
    from nodes.GPTImage.gpt_image import _build_edit_form_data

    form = _build_edit_form_data("gpt-image-2", "merge them", 3, "1K（标清）", "3:2（横版）", "webp", "high", "opaque", "low")

    assert form == {
        "model": "gpt-image-2",
        "prompt": "merge them",
        "n": "3",
        "size": "1536x1024",
        "format": "webp",
        "quality": "high",
        "background": "opaque",
        "moderation": "low",
    }


def test_build_edit_image_files_uses_image_array_field_and_preserves_rgba_png():
    from nodes.GPTImage.gpt_image import EDIT_IMAGE_FIELD, _build_edit_image_files

    images = [Image.new("RGBA", (2, 2), (255, 0, 0, 128)), Image.new("RGB", (2, 2), (0, 255, 0))]
    files = _build_edit_image_files(images)

    assert EDIT_IMAGE_FIELD == "image[]"
    assert len(files) == 2
    assert files[0][0] == "image[]"
    assert files[0][1][0] == "edit-1.png"
    assert files[0][2] == "image/png"
    assert files[0][1][2] == _make_png_bytes()
    assert files[1][1][0] == "edit-2.png"
    assert files[1][2] == "image/png"


def test_build_edit_image_files_rejects_empty_image_list():
    from nodes.GPTImage.gpt_image import _build_edit_image_files

    with pytest.raises(ValueError):
        _build_edit_image_files([])


def test_banana2_generator_exposes_banana_pro_platform_and_model():
    pytest.importorskip("comfy")
    pytest.importorskip("comfy_execution")

    repo_parent = Path(__file__).resolve().parent.parent.parent
    if str(repo_parent) not in sys.path:
        sys.path.insert(0, str(repo_parent))

    from ComfyUI_LLAI_API import nodes_image_generator as image_nodes

    inputs = image_nodes.RelayBanana2ImageGenerator.INPUT_TYPES()

    assert image_nodes.RelayBanana2ImageGenerator.PLATFORM_LIST == ["banana-2", "banana-pro"]
    assert inputs["required"]["platform"][0] == ["banana-2", "banana-pro"]
    assert inputs["required"]["model"][0] == ["gemini-3.1-flash-image-preview", "gemini-3-pro-image-preview"]
    assert image_nodes.IMAGE_RATIOS_BY_PLATFORM["banana-pro"] == image_nodes.BANANA_PRO_RATIOS
    assert "4:5" in inputs["required"]["ratio"][0]
    assert "5:4" in inputs["required"]["ratio"][0]

    info = image_nodes.RelayBanana2ImageGenerator()._build_info(
        "https://api.llaiapi.host",
        "gemini-3-pro-image-preview",
        "",
        None,
        "banana-pro",
        "v1beta/models",
    )
    payload = json.loads(info)

    assert payload["platform"] == "banana-pro"
    assert payload["api_format"] == "v1beta/models"
    assert payload["model"] == "gemini-3-pro-image-preview"
