#!/usr/bin/env python3
"""Offline tests for GPT Image 2 ComfyUI nodes."""

import base64
import inspect
import io
import json
import os
import sys

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

    assert NODE_DISPLAY_NAME_MAPPINGS["GPTImage2Edit"] == "🍐 GPT Image 2 图片编辑"
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
    assert NODE_DISPLAY_NAME_MAPPINGS["GPTImage2EditImages"] == "🍐 GPT Image 2 多图改图"

    node_class = NODE_CLASS_MAPPINGS["GPTImage2EditImages"]
    inputs = node_class.INPUT_TYPES()
    required = inputs["required"]
    optional = inputs["optional"]

    assert node_class.CATEGORY == "KuAi/GPTImage"
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
    assert files[0][1][0] == "image_01.png"
    assert files[0][1][2] == "image/png"
    encoded = files[0][1][1].getvalue()
    assert encoded.startswith(b"\x89PNG")
    assert Image.open(io.BytesIO(encoded)).mode == "RGBA"
    assert files[1][1][0] == "image_02.png"


def test_collect_edit_images_expands_torch_batches_in_socket_order():
    from nodes.GPTImage.gpt_image import _collect_edit_images

    collected = _collect_edit_images([("image_1", _make_image_tensor(batch=2)), ("image_2", _make_image_tensor(batch=1))])

    assert len(collected) == 3
    assert [item[0] for item in collected] == ["image_1[0]", "image_1[1]", "image_2[0]"]
    assert all(isinstance(item[1], Image.Image) for item in collected)


def test_collect_edit_images_supports_single_3d_tensor_numpy_batch_and_none():
    from nodes.GPTImage.gpt_image import _collect_edit_images

    collected = _collect_edit_images([
        ("image_1", _make_single_image_tensor()),
        ("image_2", None),
        ("image_3", _make_image_numpy(batch=2)),
    ])

    assert [item[0] for item in collected] == ["image_1[0]", "image_3[0]", "image_3[1]"]
    assert len(collected) == 3


def test_collect_edit_images_rejects_more_than_15_images():
    from nodes.GPTImage.gpt_image import _collect_edit_images

    with pytest.raises(RuntimeError, match="参考图数量不能超过 15 张，当前为 16 张"):
        _collect_edit_images([("image_1", _make_image_tensor(batch=16))])


def test_collect_edit_images_rejects_no_images():
    from nodes.GPTImage.gpt_image import _collect_edit_images

    with pytest.raises(RuntimeError, match="至少需要提供一张图片"):
        _collect_edit_images([("image_1", None), ("image_2", None)])


def test_extract_image_outputs_supports_data_array_url():
    from nodes.GPTImage.gpt_image import _extract_image_outputs

    outputs = _extract_image_outputs({"data": [{"url": "https://example.test/a.png"}]})

    assert outputs == [{"source": "url", "value": "https://example.test/a.png", "mime": "image/png"}]


def test_extract_image_outputs_supports_data_array_b64_json():
    from nodes.GPTImage.gpt_image import _extract_image_outputs

    outputs = _extract_image_outputs({"data": [{"b64_json": "YWJj"}], "output_format": "jpeg"})

    assert outputs == [{"source": "b64_json", "value": "data:image/jpeg;base64,YWJj", "mime": "image/jpeg"}]


def test_extract_image_outputs_supports_data_object_b64_json():
    from nodes.GPTImage.gpt_image import _extract_image_outputs

    outputs = _extract_image_outputs({"data": {"b64_json": "YWJj"}}, fallback_format="webp")

    assert outputs == [{"source": "b64_json", "value": "data:image/webp;base64,YWJj", "mime": "image/webp"}]


def test_extract_image_outputs_supports_top_level_b64_json():
    from nodes.GPTImage.gpt_image import _extract_image_outputs

    outputs = _extract_image_outputs({"b64_json": "YWJj"}, fallback_format="png")

    assert outputs == [{"source": "b64_json", "value": "data:image/png;base64,YWJj", "mime": "image/png"}]


def test_extract_image_outputs_ignores_null_b64_json_values():
    from nodes.GPTImage.gpt_image import _extract_image_outputs

    with pytest.raises(RuntimeError, match="响应中没有图像数据"):
        _extract_image_outputs({"data": [{"b64_json": None}], "b64_json": None})


def test_extract_image_outputs_supports_choices_url_and_data_url():
    from nodes.GPTImage.gpt_image import _extract_image_outputs

    outputs = _extract_image_outputs({
        "choices": [
            {"message": {"content": "https://example.test/a.png"}},
            {"message": {"content": "data:image/png;base64,YWJj"}},
        ]
    })

    assert outputs == [
        {"source": "url", "value": "https://example.test/a.png", "mime": "image/png"},
        {"source": "data_url", "value": "data:image/png;base64,YWJj", "mime": "image/png"},
    ]


def test_extract_image_outputs_error_uses_truncated_summary_without_full_base64():
    from nodes.GPTImage.gpt_image import _extract_image_outputs

    payload = {"data": {"not_image": "x", "b64_json": ""}, "debug": "A" * 500}

    with pytest.raises(RuntimeError) as exc_info:
        _extract_image_outputs(payload)

    message = str(exc_info.value)
    assert "响应中没有图像数据" in message
    assert "A" * 500 not in message


def test_summarize_response_omits_full_b64_and_data_urls():
    from nodes.GPTImage.gpt_image import _summarize_response

    summary = _summarize_response({
        "data": {"b64_json": "B" * 120},
        "url": "data:image/png;base64," + "C" * 120,
        "message": "D" * 200,
    })
    parsed = json.loads(summary)

    assert parsed["data"]["b64_json"] == "<base64 omitted, 120 chars>"
    assert parsed["url"] == "<data URL omitted, 142 chars>"
    assert parsed["message"] == "D" * 117 + "..."


def test_outputs_to_tensor_and_refs_decodes_data_url():
    from nodes.GPTImage.gpt_image import _outputs_to_tensor_and_refs

    image_tensor, refs = _outputs_to_tensor_and_refs(
        [{"source": "data_url", "value": _make_png_data_url(), "mime": "image/png"}],
        timeout=1,
    )

    assert tuple(image_tensor.shape) == (1, 2, 2, 3)
    assert refs.startswith("data:image/png;base64,")


def test_generate_node_posts_expected_json_and_decodes_b64(monkeypatch):
    import nodes.GPTImage.gpt_image as gpt_image

    calls = []

    def fake_post(url, json=None, headers=None, timeout=None, **kwargs):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout, "kwargs": kwargs})
        b64_json = base64.b64encode(_make_png_bytes()).decode("utf-8")
        return FakeResponse({"data": [{"b64_json": b64_json}], "output_format": "png"})

    monkeypatch.setattr(gpt_image.requests, "post", fake_post)

    image, refs = gpt_image.GPTImage2Generate().generate(
        prompt="a cat",
        model="gpt-image-2",
        resolution="1K（标清）",
        aspect_ratio="1:1（正方形）",
        n=1,
        api_key="test-key",
        api_base="https://api.example.test",
        timeout=12,
        format="jpeg",
        quality="high",
    )

    assert calls[0]["url"] == "https://api.example.test/v1/images/generations"
    assert calls[0]["json"] == {
        "model": "gpt-image-2",
        "prompt": "a cat",
        "n": 1,
        "size": "1024x1024",
        "format": "jpeg",
        "quality": "high",
    }
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert tuple(image.shape) == (1, 2, 2, 3)
    assert json.loads(refs) == {
        "model": "gpt-image-2",
        "resolution": "1K",
        "aspect_ratio": "1:1",
        "size": "1024x1024",
        "n": 1,
        "format": "jpeg",
        "quality": "high",
        "image_count": 1,
    }


def test_edit_images_node_posts_multipart_and_returns_summary(monkeypatch):
    import nodes.GPTImage.gpt_image as gpt_image

    calls = []
    b64_json = base64.b64encode(_make_png_bytes()).decode("utf-8")

    def fake_post(url, files=None, data=None, headers=None, timeout=None, **kwargs):
        calls.append({"url": url, "files": files, "data": data, "headers": headers, "timeout": timeout, "kwargs": kwargs})
        return FakeResponse({"data": {"b64_json": b64_json}, "output_format": "png", "debug": "D" * 200})

    monkeypatch.setattr(gpt_image.requests, "post", fake_post)

    image, refs, summary = gpt_image.GPTImage2EditImages().edit(
        image_1=_make_image_tensor(batch=2),
        prompt="combine them",
        model="gpt-image-2",
        resolution="auto（默认）",
        aspect_ratio="1:1（正方形）",
        n=1,
        api_key="test-key",
        format="webp",
        quality="high",
        background="opaque",
        moderation="low",
        api_base="https://api.example.test",
        timeout=12,
    )

    assert calls[0]["url"] == "https://api.example.test/v1/images/edits"
    assert [part[0] for part in calls[0]["files"]] == ["image[]", "image[]"]
    assert calls[0]["data"] == {
        "model": "gpt-image-2",
        "prompt": "combine them",
        "n": "1",
        "size": "auto",
        "format": "webp",
        "quality": "high",
        "background": "opaque",
        "moderation": "low",
    }
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert tuple(image.shape) == (1, 2, 2, 3)
    assert json.loads(refs) == {
        "model": "gpt-image-2",
        "resolution": "auto",
        "aspect_ratio": "1:1",
        "size": "auto",
        "n": 1,
        "format": "webp",
        "quality": "high",
        "image_count": 1,
        "input_image_count": 2,
        "background": "opaque",
        "moderation": "low",
    }
    assert b64_json not in summary
    assert "<base64 omitted" in summary
    assert "D" * 200 not in summary


def test_legacy_edit_node_posts_multipart_and_decodes_b64(monkeypatch):
    import nodes.GPTImage.gpt_image as gpt_image

    get_calls = []
    post_calls = []
    output_b64 = base64.b64encode(_make_png_bytes()).decode("utf-8")

    def fake_get(url, timeout=None, **kwargs):
        get_calls.append({"url": url, "timeout": timeout, "kwargs": kwargs})
        if url.endswith(".jpg"):
            return FakeResponse({}, content=_make_png_bytes(mode="RGB"), text="", status_code=200)
        return FakeResponse({}, content=_make_png_bytes(), text="", status_code=200)

    def fake_post(url, files=None, data=None, headers=None, timeout=None, **kwargs):
        post_calls.append({"url": url, "files": files, "data": data, "headers": headers, "timeout": timeout, "kwargs": kwargs})
        return FakeResponse({"data": {"b64_json": output_b64}, "output_format": "png"})

    monkeypatch.setattr(gpt_image.requests, "get", fake_get)
    monkeypatch.setattr(gpt_image.requests, "post", fake_post)

    image, refs = gpt_image.GPTImage2Edit().edit(
        image_url_1="https://example.test/input.jpg",
        image_url_2="https://example.test/overlay.png",
        prompt="combine",
        model="gpt-image-2",
        resolution="1K（标清）",
        aspect_ratio="1:1（正方形）",
        n=2,
        api_key="test-key",
        format="webp",
        quality="high",
        background="transparent",
        moderation="low",
        api_base="https://api.example.test",
        timeout=12,
    )

    assert [call["url"] for call in get_calls] == [
        "https://example.test/input.jpg",
        "https://example.test/overlay.png",
    ]
    assert post_calls[0]["url"] == "https://api.example.test/v1/images/edits"
    assert [part[0] for part in post_calls[0]["files"]] == ["image[]", "image[]"]
    assert post_calls[0]["files"][0][1][0] == "image_01.png"
    assert post_calls[0]["files"][0][1][2] == "image/png"
    assert post_calls[0]["data"] == {
        "model": "gpt-image-2",
        "prompt": "combine",
        "n": "2",
        "size": "1024x1024",
        "format": "webp",
        "quality": "high",
        "background": "transparent",
        "moderation": "low",
    }
    assert post_calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert tuple(image.shape) == (1, 2, 2, 3)
    assert json.loads(refs) == {
        "model": "gpt-image-2",
        "resolution": "1K",
        "aspect_ratio": "1:1",
        "size": "1024x1024",
        "n": 2,
        "format": "webp",
        "quality": "high",
        "image_count": 1,
        "input_image_count": 2,
        "background": "transparent",
        "moderation": "low",
    }
