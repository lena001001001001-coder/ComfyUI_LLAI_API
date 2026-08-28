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


def test_gpt_image_2_c_uses_documented_sizes_and_omits_n():
    from nodes.GPTImage.gpt_image_2_c import SIZES, build_payload, resolve_endpoint, resolve_size

    assert [resolve_size(label) for label in SIZES] == [
        "auto",
        "1024x1024",
        "1536x1024",
        "1024x1536",
        "2048x2048",
        "2048x1152",
        "3840x2160",
        "2160x3840",
    ]
    assert build_payload("test", "1024x1024", "png", "auto") == {
        "model": "gpt-image-2-c",
        "prompt": "test",
        "size": "1024x1024",
    }
    assert "n" not in build_payload("test", "3840x2160", "jpeg", "high")
    assert resolve_endpoint("/v1/images/generations") == "https://api.llaiapi.host/v1/images/generations"


def test_gpt_image_2_c_interface_matches_model_card():
    from nodes.GPTImage import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    node_class = NODE_CLASS_MAPPINGS["GPTImage2CLowCost4K"]
    inputs = node_class.INPUT_TYPES()

    assert NODE_DISPLAY_NAME_MAPPINGS["GPTImage2CLowCost4K"] == "LL-gpt image-2-c低价"
    assert list(inputs["required"]) == ["提示词", "分辨率", "图像比例", "API密钥"]
    assert inputs["required"]["图像比例"][1]["default"] == "1024x1024（1:1）"
    assert inputs["required"]["分辨率"][1]["default"] == "1K"
    assert inputs["optional"]["API地址"][1]["default"] == "/v1/images/generations"
    assert inputs["optional"]["输出格式"][0] == ["png", "jpeg", "webp"]
    assert inputs["optional"]["图像质量"][0] == ["auto", "low", "medium", "high"]
    assert node_class.RETURN_TYPES == ("IMAGE", "STRING", "STRING")


def test_gpt_image_2_c_rejects_prompt_over_1000_characters():
    from nodes.GPTImage.gpt_image_2_c import GPTImage2CLowCost4K, K_PROMPT

    with pytest.raises(ValueError, match="1000"):
        GPTImage2CLowCost4K().generate(**{K_PROMPT: "a" * 1001})


def test_extract_image_outputs_accepts_llai_url_and_base64_aliases():
    from nodes.GPTImage.gpt_image import _extract_image_outputs

    url_outputs = _extract_image_outputs({"data": {"output": {"image_url": "https://example.com/a.png"}}})
    assert url_outputs[0]["value"] == "https://example.com/a.png"

    b64_outputs = _extract_image_outputs({"images": [{"base64": "YWJj"}]}, fallback_format="jpeg")
    assert b64_outputs[0]["value"] == "data:image/jpeg;base64,YWJj"


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


def test_gemini_generate_retries_text_only_route_until_image(monkeypatch):
    pytest.importorskip("comfy")
    pytest.importorskip("comfy_execution")

    repo_parent = Path(__file__).resolve().parent.parent.parent
    if str(repo_parent) not in sys.path:
        sys.path.insert(0, str(repo_parent))

    from ComfyUI_LLAI_API import nodes_image_generator as image_nodes

    png_b64 = base64.b64encode(_make_png_bytes()).decode("ascii")
    responses = [
        FakeResponse({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "wrong chat route"}]}}]}),
        FakeResponse({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": png_b64}}]}}]}),
    ]
    monkeypatch.setattr(image_nodes.requests, "post", lambda *args, **kwargs: responses.pop(0))
    monkeypatch.setattr(image_nodes.time, "sleep", lambda _seconds: None)

    class FakeProgress:
        def update_absolute(self, _value):
            pass

    result = image_nodes.RelayImageGenerator()._gemini_generate(
        "https://api.llaiapi.host",
        "sk-test",
        "gemini-3-pro-image-preview",
        "draw a circle",
        "1:1",
        "1K",
        [],
        1,
        FakeProgress(),
    )

    assert image_nodes.RelayImageGenerator()._response_has_image(result)
    assert responses == []


def test_gemini_generate_raises_after_repeated_text_only_routes(monkeypatch):
    pytest.importorskip("comfy")
    pytest.importorskip("comfy_execution")

    repo_parent = Path(__file__).resolve().parent.parent.parent
    if str(repo_parent) not in sys.path:
        sys.path.insert(0, str(repo_parent))

    from ComfyUI_LLAI_API import nodes_image_generator as image_nodes

    calls = []
    text_only = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "wrong chat route"}]}}]}
    monkeypatch.setattr(
        image_nodes.requests,
        "post",
        lambda *args, **kwargs: calls.append(1) or FakeResponse(text_only),
    )
    monkeypatch.setattr(image_nodes.time, "sleep", lambda _seconds: None)

    class FakeProgress:
        def update_absolute(self, _value):
            pass

    with pytest.raises(RuntimeError, match="错误路由到聊天渠道"):
        image_nodes.RelayImageGenerator()._gemini_generate(
            "https://api.llaiapi.host",
            "sk-test",
            "gemini-3-pro-image-preview",
            "draw a circle",
            "1:1",
            "1K",
            [],
            1,
            FakeProgress(),
        )

    assert len(calls) == image_nodes.BANANA_IMAGE_MAX_ATTEMPTS


def test_gpt_image2_retries_http_200_without_image(monkeypatch):
    pytest.importorskip("comfy")
    pytest.importorskip("comfy_execution")

    repo_parent = Path(__file__).resolve().parent.parent.parent
    if str(repo_parent) not in sys.path:
        sys.path.insert(0, str(repo_parent))

    from ComfyUI_LLAI_API import nodes_image_generator as image_nodes

    responses = [
        FakeResponse({"message": "channel returned no image"}),
        FakeResponse({"data": [{"b64_json": base64.b64encode(_make_png_bytes()).decode("ascii")}]}),
    ]
    monkeypatch.setattr(
        image_nodes,
        "_post_with_timing",
        lambda _label, _kwargs: responses.pop(0),
    )
    monkeypatch.setattr(image_nodes.time, "sleep", lambda _seconds: None)

    class FakeProgress:
        def update_absolute(self, _value):
            pass

    result = image_nodes.RelayImageGenerator()._gpt_image2_openai_generate(
        "https://api.llaiapi.host",
        "sk-test",
        "gpt-image-2",
        "draw a circle",
        "1:1",
        "1K",
        "medium",
        "low",
        [],
        1800,
        FakeProgress(),
    )

    assert result["data"][0]["b64_json"]
    assert responses == []


def test_gpt_image2_retries_transient_http_errors(monkeypatch):
    pytest.importorskip("comfy")
    pytest.importorskip("comfy_execution")

    repo_parent = Path(__file__).resolve().parent.parent.parent
    if str(repo_parent) not in sys.path:
        sys.path.insert(0, str(repo_parent))

    from ComfyUI_LLAI_API import nodes_image_generator as image_nodes

    responses = [
        FakeResponse({}, status_code=503, text="no distributor"),
        FakeResponse({"data": [{"url": "https://example.com/result.png"}]}),
    ]
    monkeypatch.setattr(
        image_nodes,
        "_post_with_timing",
        lambda _label, _kwargs: responses.pop(0),
    )
    monkeypatch.setattr(image_nodes.time, "sleep", lambda _seconds: None)

    class FakeProgress:
        def update_absolute(self, _value):
            pass

    result = image_nodes.RelayImageGenerator()._gpt_image2_openai_generate(
        "https://api.llaiapi.host",
        "sk-test",
        "gpt-image-2",
        "draw a circle",
        "1:1",
        "1K",
        "medium",
        "low",
        [],
        1800,
        FakeProgress(),
    )

    assert result["data"][0]["url"].endswith("result.png")
    assert responses == []


def test_complete_gpt_image2_generator_exposes_timeout_after_seed():
    pytest.importorskip("comfy")
    pytest.importorskip("comfy_execution")

    repo_parent = Path(__file__).resolve().parent.parent.parent
    if str(repo_parent) not in sys.path:
        sys.path.insert(0, str(repo_parent))

    from ComfyUI_LLAI_API import nodes_image_generator as image_nodes

    inputs = image_nodes.RelayGPTImage2Generator.INPUT_TYPES()
    required_names = list(inputs["required"].keys())

    assert image_nodes.GPT_IMAGE2_DEFAULT_TIMEOUT == 1800
    assert image_nodes.GPT_IMAGE2_TIMEOUTS == {"1K": 1800, "2K": 1800, "4K": 1800}
    assert required_names.index("timeout") > required_names.index("seed")
    assert inputs["required"]["timeout"][1]["default"] == 1800
    assert inputs["required"]["timeout"][1]["min"] == 30
    assert inputs["required"]["timeout"][1]["max"] == 9999


def test_complete_gpt_image2_generator_passes_timeout(monkeypatch):
    pytest.importorskip("comfy")
    pytest.importorskip("comfy_execution")

    repo_parent = Path(__file__).resolve().parent.parent.parent
    if str(repo_parent) not in sys.path:
        sys.path.insert(0, str(repo_parent))

    from ComfyUI_LLAI_API import nodes_image_generator as image_nodes

    captured = {}

    def fake_build_info(self, api_base, model, apikey, unique_id, platform=None, api_format=None):
        return json.dumps({
            "apikey": "sk-test",
            "api_base": api_base,
            "model": model,
            "platform": platform,
            "api_format": api_format,
            "task_type": "image",
        })

    def fake_generate_image(self, **kwargs):
        captured.update(kwargs)
        return ("image", "response", "")

    monkeypatch.setattr(image_nodes.RelayGPTImage2Generator, "_build_info", fake_build_info)
    monkeypatch.setattr(image_nodes.RelayImageGenerator, "generate_image", fake_generate_image)

    node = image_nodes.RelayGPTImage2Generator()
    result = node.generate_complete_image(
        task_type="image",
        platform="gpt-image2",
        api_format="v1/images",
        api_base="https://api.llaiapi.host",
        model="gpt-image-2",
        apikey="sk-test",
        prompt="一只鸟",
        ratio="1:1",
        size="1K",
        seed=123,
        quality="medium",
        moderation="low",
        timeout=2400,
        unique_id="node-1",
    )

    assert result == ("image", "response", "")
    assert captured["timeout"] == 2400
