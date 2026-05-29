# GPT Image 2 ComfyUI Multi-Image Nodes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance GPT Image 2 text-to-image controls and add a ComfyUI-native multi-image edit node that accepts up to 15 `IMAGE` references without breaking existing workflows.

**Architecture:** Keep GPT Image 2 node logic in `nodes/GPTImage/gpt_image.py`, add small focused helper functions for payloads, multipart files, ComfyUI batch expansion, response parsing, tensor conversion, and safe response summaries. Register the new `GPTImage2EditImages` through `nodes/GPTImage/__init__.py`, while preserving the public interface of the existing URL-based `GPTImage2Edit`.

**Tech Stack:** Python, ComfyUI custom node API, `requests`, `PIL`, `numpy`, `torch`, `pytest` for offline tests.

---

## Scope Check

This is one cohesive subsystem: GPT Image 2 image generation/editing nodes inside the existing ComfyUI_LLAI_API plugin. Do not split into separate implementation plans.

Do not add CSV batch processing, mask editing, `input_fidelity`, `output_compression`, or a standalone API key node. Do not delete or rename existing node IDs.

## Grounding Notes

- Local generation API: `/workspace/apis/gpt-image-2/生图.md` defines `POST /v1/images/generations` with `model`, `prompt`, `n`, `size`, `format`, `quality`.
- Local edit API: `/workspace/apis/gpt-image-2/改图.md` defines `POST /v1/images/edits`; `image` is required and may be an image array under 16 images and 50MB each. It lists `quality`, `size`, `background`, and `moderation`, and response examples include `data.b64_json` plus `output_format`.
- OpenAI docs confirm `gpt-image-2` supports image generation/editing, flexible sizes, and high-fidelity image inputs. The image guide shows multi-image edit examples using multipart `image[]`.
- ComfyUI official custom node docs require node classes to define `INPUT_TYPES`, `RETURN_TYPES`, `FUNCTION`, and `CATEGORY`. `INPUT_TYPES()` must return a dict with `required` and may include `optional`.
- ComfyUI `IMAGE` is singular as a type name, but the value is a batch tensor. Official walkthrough examples describe receiving an `IMAGE` batch, so this plan explicitly expands `[B,H,W,C]` instead of silently using index 0.
- ComfyUI optional inputs are only supplied when connected or configured. Every optional `IMAGE` and optional widget must therefore have a default in `GPTImage2EditImages.edit()`.
- Existing repo style uses Chinese labels, `🍐LLAI/...` categories, `NODE_CLASS_MAPPINGS`, `NODE_DISPLAY_NAME_MAPPINGS`, and `env_or(api_key, "KUAI_API_KEY")`.

## File Structure

- Modify `nodes/GPTImage/gpt_image.py`
  - Add constants: `EDIT_IMAGE_FIELD`, `MAX_EDIT_IMAGES`, `IMAGE_MIME_BY_FORMAT`.
  - Replace narrow `_extract_urls()` behavior with `_extract_image_outputs()` plus compatibility wrapper.
  - Add helpers: `_summarize_response()`, `_output_to_tensor()`, `_outputs_to_tensor_and_refs()`, `_build_generation_payload()`, `_build_edit_form_data()`, `_image_batch_count()`, `_collect_edit_images()`, `_build_edit_image_files()`.
  - Enhance `GPTImage2Generate` with `format` and `quality`.
  - Keep `GPTImage2Edit` interface compatible, but reuse the new response parser.
  - Add `GPTImage2EditImages`.
- Modify `nodes/GPTImage/__init__.py`
  - Import/register `GPTImage2EditImages`.
  - Add display name `🍐 GPT Image 2 多图改图`.
- Create `test/test_gpt_image_nodes.py`
  - Offline pytest coverage for ComfyUI node interface shape, legacy compatibility, payloads, multipart fields, batch expansion, response parsing, summaries, and node-level HTTP calls with monkeypatch.

## Task 0: Verify Test Prerequisites

**Files:**
- Verify only.

- [ ] **Step 1: Check required Python modules**

Run:

```bash
python - <<'PY'
import importlib.util
missing = [name for name in ["pytest", "numpy", "torch", "PIL", "requests"] if importlib.util.find_spec(name) is None]
if missing:
    raise SystemExit("Missing required test modules: " + ", ".join(missing))
print("Required test modules are available")
PY
```

Expected: prints `Required test modules are available`.

If this fails, stop and report the missing modules. Do not use `python test/test_gpt_image_nodes.py` as a fallback; pytest-style tests will not execute that way.

## Task 1: Add Failing Offline Tests

**Files:**
- Create: `test/test_gpt_image_nodes.py`
- Read-only context: `nodes/GPTImage/gpt_image.py`
- Read-only context: `nodes/GPTImage/__init__.py`

- [ ] **Step 1: Write the failing test file**

Create `test/test_gpt_image_nodes.py` with this complete content:

```python
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
    assert node_class.RETURN_NAMES == ("图像", "图片URL")
    assert "format" in inputs["optional"]
    assert "quality" in inputs["optional"]
    assert inputs["optional"]["format"][0] == ["png", "jpeg", "webp"]
    assert inputs["optional"]["quality"][0] == ["auto", "low", "medium", "high"]

    labels = node_class.INPUT_LABELS()
    assert labels["format"] == "输出格式（png/jpeg/webp）"
    assert labels["quality"] == "图像质量（清晰度等级）"


def test_legacy_url_edit_node_interface_is_preserved():
    from nodes.GPTImage import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    node_class = NODE_CLASS_MAPPINGS["GPTImage2Edit"]
    inputs = node_class.INPUT_TYPES()
    optional = inputs["optional"]

    assert NODE_DISPLAY_NAME_MAPPINGS["GPTImage2Edit"] == "🍐 GPT Image 2 图片编辑"
    assert node_class.RETURN_TYPES == ("IMAGE", "STRING")
    assert node_class.RETURN_NAMES == ("图像", "图片URL")
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
        "size",
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

    assert node_class.CATEGORY == "🍐LLAI/GPTImage"
    assert node_class.RETURN_TYPES == ("IMAGE", "STRING", "STRING")
    assert node_class.RETURN_NAMES == ("图像", "图片URL/DataURL", "响应JSON摘要")
    assert "image_1" in required
    for idx in range(2, 16):
        assert f"image_{idx}" in optional
        assert optional[f"image_{idx}"][0] == "IMAGE"

    labels = node_class.INPUT_LABELS()
    for idx in range(1, 16):
        assert labels[f"image_{idx}"] == f"参考图{idx}"
    for name in ["prompt", "model", "size", "n", "api_key", "format", "quality", "background", "moderation", "api_base", "timeout"]:
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

    payload = _build_generation_payload("gpt-image-2", "a cat", 1, "auto（默认）", "png", "auto")

    assert payload == {"model": "gpt-image-2", "prompt": "a cat", "n": 1, "size": "auto"}


def test_build_generation_payload_sends_non_default_format_and_quality():
    from nodes.GPTImage.gpt_image import _build_generation_payload

    payload = _build_generation_payload("gpt-image-2", "a cat", 2, "1024x1024（1:1｜正方形）", "jpeg", "high")

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

    form = _build_edit_form_data("gpt-image-2", "merge them", 1, "auto（默认）", "png", "auto", "auto", "auto")

    assert form == {"model": "gpt-image-2", "prompt": "merge them", "n": "1", "size": "auto"}


def test_build_edit_form_data_sends_non_default_optional_fields():
    from nodes.GPTImage.gpt_image import _build_edit_form_data

    form = _build_edit_form_data("gpt-image-2", "merge them", 3, "1536x1024（3:2｜横版）", "webp", "high", "opaque", "low")

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
        size="1024x1024（1:1｜正方形）",
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
    assert refs.startswith("data:image/png;base64,")


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
        size="auto（默认）",
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
    assert refs.startswith("data:image/png;base64,")
    assert b64_json not in summary
    assert "<base64 omitted" in summary
    assert "D" * 200 not in summary
```

- [ ] **Step 2: Run tests and verify red state**

Run:

```bash
python -m pytest test/test_gpt_image_nodes.py -q
```

Expected: FAIL. The first failures should mention missing `GPTImage2EditImages`, missing helper functions such as `_build_generation_payload`, or missing `format`/`quality` inputs.

- [ ] **Step 3: Commit the failing tests**

```bash
git add test/test_gpt_image_nodes.py
git commit -m "test: cover GPT Image 2 ComfyUI node behavior"
```

## Task 2: Add Response Parsing and Tensor Conversion Helpers

**Files:**
- Modify: `nodes/GPTImage/gpt_image.py`
- Test: `test/test_gpt_image_nodes.py`

- [ ] **Step 1: Update imports and constants**

Replace the import block and constants near the top of `nodes/GPTImage/gpt_image.py` with:

```python
"""GPT Image 2 节点 - 文生图和图片编辑"""

import base64
import io
import json
import re

import requests
import numpy as np
import torch
from PIL import Image

from ..Sora2.kuai_utils import (
    env_or,
    http_headers_auth_only,
    http_headers_multipart,
    raise_for_bad_status,
    save_image_to_buffer,
    to_pil_from_comfy,
)

MODELS = ["gpt-image-2"]
EDIT_MODELS = ["gpt-image-2"]
SIZES = [
    "auto（默认）",
    "1024x1024（1:1｜正方形）",
    "1536x1024（3:2｜横版）",
    "1024x1536（2:3｜竖版）",
    "2048x2048（1:1｜2K正方形）",
    "2048x1152（16:9｜2K横版）",
    "3840x2160（16:9｜4K横版）",
    "2160x3840（9:16｜4K竖版）",
]
SIZE_MAP = {
    "auto（默认）": "auto",
    "1024x1024（1:1｜正方形）": "1024x1024",
    "1536x1024（3:2｜横版）": "1536x1024",
    "1024x1536（2:3｜竖版）": "1024x1536",
    "2048x2048（1:1｜2K正方形）": "2048x2048",
    "2048x1152（16:9｜2K横版）": "2048x1152",
    "3840x2160（16:9｜4K横版）": "3840x2160",
    "2160x3840（9:16｜4K竖版）": "2160x3840",
}
FORMATS = ["png", "jpeg", "webp"]
QUALITY_OPTIONS = ["auto", "low", "medium", "high"]
EDIT_IMAGE_FIELD = "image[]"
MAX_EDIT_IMAGES = 15
IMAGE_MIME_BY_FORMAT = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "webp": "image/webp",
}
```

- [ ] **Step 2: Replace `_extract_urls()` and `_url_to_tensor()`**

Replace the existing `_extract_urls()` and `_url_to_tensor()` functions with:

```python
def _normalize_output_format(output_format: str) -> str:
    value = str(output_format or "png").strip().lower()
    if value == "jpg":
        return "jpeg"
    return value if value in IMAGE_MIME_BY_FORMAT else "png"


def _mime_for_format(output_format: str) -> str:
    return IMAGE_MIME_BY_FORMAT[_normalize_output_format(output_format)]


def _truncate_string(value: str, max_length: int = 120) -> str:
    value = str(value)
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


def _summarize_response(value) -> str:
    def sanitize(item):
        if isinstance(item, dict):
            result = {}
            for key, sub_value in item.items():
                if key == "b64_json" and isinstance(sub_value, str):
                    result[key] = f"<base64 omitted, {len(sub_value)} chars>"
                else:
                    result[key] = sanitize(sub_value)
            return result
        if isinstance(item, list):
            return [sanitize(sub_value) for sub_value in item]
        if isinstance(item, str):
            if item.startswith("data:image/"):
                return f"<data URL omitted, {len(item)} chars>"
            return _truncate_string(item)
        return item

    return json.dumps(sanitize(value), ensure_ascii=False)


def _data_url_from_b64(b64_json: str, output_format: str) -> str:
    return f"data:{_mime_for_format(output_format)};base64,{b64_json}"


def _output_from_value(value: str, output_format: str):
    value = str(value or "").strip()
    if not value:
        return None
    if value.startswith("data:image/"):
        mime_match = re.match(r"^data:([^;,]+)", value)
        return {"source": "data_url", "value": value, "mime": mime_match.group(1) if mime_match else _mime_for_format(output_format)}
    if value.startswith("http://") or value.startswith("https://"):
        return {"source": "url", "value": value, "mime": "image/png"}
    return None


def _outputs_from_data_item(item, output_format: str) -> list:
    if not isinstance(item, dict):
        return []

    outputs = []
    url_output = _output_from_value(item.get("url", ""), output_format)
    if url_output:
        outputs.append(url_output)

    b64_json = str(item.get("b64_json", "")).strip()
    if b64_json:
        outputs.append({"source": "b64_json", "value": _data_url_from_b64(b64_json, output_format), "mime": _mime_for_format(output_format)})

    return outputs


def _extract_image_outputs(data: dict, fallback_format: str = "png") -> list:
    if isinstance(data, dict):
        output_format = _normalize_output_format(data.get("output_format") or fallback_format)
    else:
        output_format = _normalize_output_format(fallback_format)

    outputs = []
    if isinstance(data, dict):
        data_value = data.get("data")
        if isinstance(data_value, list):
            for item in data_value:
                outputs.extend(_outputs_from_data_item(item, output_format))
        elif isinstance(data_value, dict):
            outputs.extend(_outputs_from_data_item(data_value, output_format))

        top_level_b64 = str(data.get("b64_json", "")).strip()
        if top_level_b64:
            outputs.append({"source": "b64_json", "value": _data_url_from_b64(top_level_b64, output_format), "mime": _mime_for_format(output_format)})

        choices = data.get("choices") or []
        if isinstance(choices, list):
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
                output = _output_from_value(message.get("content", ""), output_format)
                if output:
                    outputs.append(output)

    if not outputs:
        raise RuntimeError(f"响应中没有图像数据: {_summarize_response(data)}")
    return outputs


def _extract_urls(data: dict) -> list:
    return [item["value"] for item in _extract_image_outputs(data)]


def _output_to_tensor(output: dict, timeout: int) -> torch.Tensor:
    value = output["value"]
    if value.startswith("data:"):
        try:
            content = base64.b64decode(value.split(",", 1)[1], validate=True)
        except Exception as exc:
            raise RuntimeError(f"响应图像 base64 解码失败: {_truncate_string(str(exc), 200)}") from exc
    else:
        try:
            resp = requests.get(value, timeout=timeout)
            resp.raise_for_status()
            content = resp.content
        except Exception as exc:
            raise RuntimeError(f"下载图像失败: {_truncate_string(value, 200)} - {exc}") from exc

    pil = Image.open(io.BytesIO(content)).convert("RGB")
    arr = np.array(pil).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None,]


def _url_to_tensor(url: str, timeout: int) -> torch.Tensor:
    return _output_to_tensor({"source": "data_url" if str(url).startswith("data:") else "url", "value": url, "mime": "image/png"}, timeout)


def _outputs_to_tensor_and_refs(outputs: list, timeout: int):
    tensors = [_output_to_tensor(output, timeout) for output in outputs]
    return torch.cat(tensors, dim=0), "\n".join(output["value"] for output in outputs)
```

- [ ] **Step 3: Run parser and tensor tests**

Run:

```bash
python -m pytest \
  test/test_gpt_image_nodes.py::test_extract_image_outputs_supports_data_array_url \
  test/test_gpt_image_nodes.py::test_extract_image_outputs_supports_data_array_b64_json \
  test/test_gpt_image_nodes.py::test_extract_image_outputs_supports_data_object_b64_json \
  test/test_gpt_image_nodes.py::test_extract_image_outputs_supports_top_level_b64_json \
  test/test_gpt_image_nodes.py::test_extract_image_outputs_supports_choices_url_and_data_url \
  test/test_gpt_image_nodes.py::test_extract_image_outputs_error_uses_truncated_summary_without_full_base64 \
  test/test_gpt_image_nodes.py::test_summarize_response_omits_full_b64_and_data_urls \
  test/test_gpt_image_nodes.py::test_outputs_to_tensor_and_refs_decodes_data_url \
  -q
```

Expected: PASS.

- [ ] **Step 4: Commit helper implementation**

```bash
git add nodes/GPTImage/gpt_image.py test/test_gpt_image_nodes.py
git commit -m "feat: parse GPT Image 2 image responses"
```

## Task 3: Add Payload, Multipart, and ComfyUI Batch Helpers

**Files:**
- Modify: `nodes/GPTImage/gpt_image.py`
- Test: `test/test_gpt_image_nodes.py`

- [ ] **Step 1: Add request and batch helper functions**

Insert this block immediately before `class GPTImage2Generate`:

```python
def _api_size(size: str) -> str:
    return SIZE_MAP.get(size, size)


def _build_generation_payload(model: str, prompt: str, n: int, size: str, output_format: str = "png", quality: str = "auto") -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "n": int(n),
        "size": _api_size(size),
    }
    if output_format != "png":
        payload["format"] = output_format
    if quality != "auto":
        payload["quality"] = quality
    return payload


def _build_edit_form_data(
    model: str,
    prompt: str,
    n: int,
    size: str,
    output_format: str = "png",
    quality: str = "auto",
    background: str = "auto",
    moderation: str = "auto",
) -> dict:
    form_data = {
        "model": model,
        "prompt": prompt,
        "n": str(int(n)),
        "size": _api_size(size),
    }
    if output_format != "png":
        form_data["format"] = output_format
    if quality != "auto":
        form_data["quality"] = quality
    if background != "auto":
        form_data["background"] = background
    if moderation != "auto":
        form_data["moderation"] = moderation
    return form_data


def _image_batch_count(image_any) -> int:
    if isinstance(image_any, torch.Tensor) and image_any.dim() == 4:
        return int(image_any.shape[0])
    if isinstance(image_any, np.ndarray) and image_any.ndim == 4:
        return int(image_any.shape[0])
    return 1


def _collect_edit_images(named_images: list) -> list:
    collected = []
    for input_name, image_any in named_images:
        if image_any is None:
            continue
        count = _image_batch_count(image_any)
        for index in range(count):
            if len(collected) >= MAX_EDIT_IMAGES:
                current = len(collected) + 1
                raise RuntimeError(f"参考图数量不能超过 15 张，当前为 {current} 张")
            try:
                pil = to_pil_from_comfy(image_any, index=index)
            except Exception as exc:
                raise RuntimeError(f"参考图转换失败: {input_name}[{index}] - {exc}") from exc
            collected.append((f"{input_name}[{index}]", pil))
    if not collected:
        raise RuntimeError("至少需要提供一张图片")
    return collected


def _build_edit_image_files(images: list) -> list:
    files = []
    for index, pil in enumerate(images, start=1):
        try:
            buffer = save_image_to_buffer(pil, fmt="png", quality=95)
        except Exception as exc:
            raise RuntimeError(f"参考图编码失败: image_{index:02d} - {exc}") from exc
        files.append((EDIT_IMAGE_FIELD, (f"image_{index:02d}.png", buffer, "image/png")))
    return files
```

- [ ] **Step 2: Run helper tests**

Run:

```bash
python -m pytest \
  test/test_gpt_image_nodes.py::test_build_generation_payload_omits_default_optional_fields \
  test/test_gpt_image_nodes.py::test_build_generation_payload_sends_non_default_format_and_quality \
  test/test_gpt_image_nodes.py::test_build_edit_form_data_omits_default_optional_fields \
  test/test_gpt_image_nodes.py::test_build_edit_form_data_sends_non_default_optional_fields \
  test/test_gpt_image_nodes.py::test_build_edit_image_files_uses_image_array_field_and_preserves_rgba_png \
  test/test_gpt_image_nodes.py::test_collect_edit_images_expands_torch_batches_in_socket_order \
  test/test_gpt_image_nodes.py::test_collect_edit_images_supports_single_3d_tensor_numpy_batch_and_none \
  test/test_gpt_image_nodes.py::test_collect_edit_images_rejects_more_than_15_images \
  test/test_gpt_image_nodes.py::test_collect_edit_images_rejects_no_images \
  -q
```

Expected: PASS.

- [ ] **Step 3: Commit helper implementation**

```bash
git add nodes/GPTImage/gpt_image.py test/test_gpt_image_nodes.py
git commit -m "feat: build GPT Image 2 request helpers"
```

## Task 4: Enhance `GPTImage2Generate`

**Files:**
- Modify: `nodes/GPTImage/gpt_image.py`
- Test: `test/test_gpt_image_nodes.py`

- [ ] **Step 1: Add `format` and `quality` to optional inputs**

In `GPTImage2Generate.INPUT_TYPES()`, replace the `optional` dict with:

```python
            "optional": {
                "api_base": ("STRING", {"default": "https://api.kuai.host", "tooltip": "API服务器地址"}),
                "timeout": ("INT", {"default": 1800, "min": 30, "max": 9999, "tooltip": "超时时间(秒)"}),
                "format": (FORMATS, {"default": "png", "tooltip": "输出格式（可选 png、jpeg、webp）"}),
                "quality": (QUALITY_OPTIONS, {"default": "auto", "tooltip": "图像质量（可选 low、medium、high、auto）"}),
            }
```

- [ ] **Step 2: Add labels**

In `GPTImage2Generate.INPUT_LABELS()`, add:

```python
            "format": "输出格式（png/jpeg/webp）",
            "quality": "图像质量（清晰度等级）",
```

Keep `RETURN_NAMES = ("图像", "图片URL")` for UI compatibility with older workflows, even though the second output may now be a DataURL.

- [ ] **Step 3: Replace `generate()`**

Replace the full `GPTImage2Generate.generate()` method with:

```python
    def generate(self, prompt, model, size, n, api_key, api_base="https://api.kuai.host", timeout=1800, format="png", quality="auto"):
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点参数或环境变量 KUAI_API_KEY 中设置")
        if not prompt.strip():
            raise RuntimeError("提示词不能为空")

        payload = _build_generation_payload(model, prompt, n, size, format, quality)
        resp = requests.post(
            f"{api_base.rstrip('/')}/v1/images/generations",
            json=payload,
            headers=http_headers_auth_only(api_key),
            timeout=timeout,
        )
        raise_for_bad_status(resp, "GPTImage文生图失败")
        data = resp.json()

        outputs = _extract_image_outputs(data, fallback_format=format)
        image_tensor, refs = _outputs_to_tensor_and_refs(outputs, timeout)
        print(f"[GPTImage] 文生图完成，生成 {len(outputs)} 张图像")
        return (image_tensor, refs)
```

- [ ] **Step 4: Run generation tests**

Run:

```bash
python -m pytest \
  test/test_gpt_image_nodes.py::test_gpt_image_generate_interface_includes_format_and_quality \
  test/test_gpt_image_nodes.py::test_build_generation_payload_omits_default_optional_fields \
  test/test_gpt_image_nodes.py::test_build_generation_payload_sends_non_default_format_and_quality \
  test/test_gpt_image_nodes.py::test_generate_node_posts_expected_json_and_decodes_b64 \
  -q
```

Expected: PASS.

- [ ] **Step 5: Commit generation enhancement**

```bash
git add nodes/GPTImage/gpt_image.py test/test_gpt_image_nodes.py
git commit -m "feat: add GPT Image 2 generation output controls"
```

## Task 5: Update Existing URL Edit Node Internals Only

**Files:**
- Modify: `nodes/GPTImage/gpt_image.py`
- Test: `test/test_gpt_image_nodes.py`

- [ ] **Step 1: Replace only the response parsing tail of `GPTImage2Edit.edit()`**

In `GPTImage2Edit.edit()`, replace the block after `data = resp.json()` through the return statement with:

```python
        outputs = _extract_image_outputs(data, fallback_format=format)
        image_tensor, refs = _outputs_to_tensor_and_refs(outputs, timeout)
        print(f"[GPTImage] 图片编辑完成，输入{len(image_urls)}张图，生成{len(outputs)}张图像")
        return (image_tensor, refs)
```

Do not change the old node's class name, input names, `RETURN_TYPES`, `RETURN_NAMES`, `FUNCTION`, display name, or method parameters.

- [ ] **Step 2: Run legacy compatibility and parser tests**

Run:

```bash
python -m pytest \
  test/test_gpt_image_nodes.py::test_legacy_url_edit_node_interface_is_preserved \
  test/test_gpt_image_nodes.py::test_extract_image_outputs_supports_data_object_b64_json \
  test/test_gpt_image_nodes.py::test_extract_image_outputs_supports_data_array_b64_json \
  -q
```

Expected: PASS.

- [ ] **Step 3: Commit URL edit parser update**

```bash
git add nodes/GPTImage/gpt_image.py test/test_gpt_image_nodes.py
git commit -m "fix: support GPT Image 2 edit base64 responses"
```

## Task 6: Add and Register `GPTImage2EditImages`

**Files:**
- Modify: `nodes/GPTImage/gpt_image.py`
- Modify: `nodes/GPTImage/__init__.py`
- Test: `test/test_gpt_image_nodes.py`

- [ ] **Step 1: Add the new class after `GPTImage2Edit`**

Append this complete class to `nodes/GPTImage/gpt_image.py` after `GPTImage2Edit`:

```python
class GPTImage2EditImages:
    """GPT Image 2 多图改图节点（支持最多15张 ComfyUI IMAGE 参考图）"""

    @classmethod
    def INPUT_TYPES(cls):
        optional_images = {
            f"image_{idx}": ("IMAGE", {"tooltip": f"参考图{idx}"})
            for idx in range(2, MAX_EDIT_IMAGES + 1)
        }
        return {
            "required": {
                "image_1": ("IMAGE", {"tooltip": "参考图1（必填）"}),
                "prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "编辑描述提示词"}),
                "model": (EDIT_MODELS, {"default": "gpt-image-2", "tooltip": "模型选择"}),
                "size": (SIZES, {"default": "auto（默认）", "tooltip": "输出图像尺寸（分辨率、比例与用途）"}),
                "n": ("INT", {"default": 1, "min": 1, "max": 10, "tooltip": "生成数量（输出图片张数，1-10张）"}),
                "api_key": ("STRING", {"default": "", "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"}),
            },
            "optional": {
                **optional_images,
                "format": (FORMATS, {"default": "png", "tooltip": "输出格式（可选 png、jpeg、webp）"}),
                "quality": (QUALITY_OPTIONS, {"default": "auto", "tooltip": "图像质量（可选 low、medium、high、auto）"}),
                "background": (["auto", "opaque"], {"default": "auto", "tooltip": "背景（auto 自动、opaque 不透明）"}),
                "moderation": (["auto", "low"], {"default": "auto", "tooltip": "内容审核级别（auto 默认、low 较宽松）"}),
                "api_base": ("STRING", {"default": "https://api.kuai.host", "tooltip": "API服务器地址"}),
                "timeout": ("INT", {"default": 1800, "min": 30, "max": 9999, "tooltip": "超时时间(秒)"}),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        labels = {f"image_{idx}": f"参考图{idx}" for idx in range(1, MAX_EDIT_IMAGES + 1)}
        labels.update({
            "prompt": "编辑提示词（修改要求）",
            "model": "模型（GPT Image 2）",
            "size": "图像尺寸（分辨率/比例）",
            "n": "生成数量（输出图片张数）",
            "api_key": "API密钥",
            "format": "输出格式（png/jpeg/webp）",
            "quality": "图像质量（清晰度等级）",
            "background": "背景（自动/不透明）",
            "moderation": "内容审核（安全级别）",
            "api_base": "API地址",
            "timeout": "超时（秒）",
        })
        return labels

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "图片URL/DataURL", "响应JSON摘要")
    FUNCTION = "edit"
    CATEGORY = "🍐LLAI/GPTImage"

    def edit(
        self,
        image_1,
        prompt,
        model,
        size,
        n,
        api_key,
        image_2=None,
        image_3=None,
        image_4=None,
        image_5=None,
        image_6=None,
        image_7=None,
        image_8=None,
        image_9=None,
        image_10=None,
        image_11=None,
        image_12=None,
        image_13=None,
        image_14=None,
        image_15=None,
        format="png",
        quality="auto",
        background="auto",
        moderation="auto",
        api_base="https://api.kuai.host",
        timeout=1800,
    ):
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点参数或环境变量 KUAI_API_KEY 中设置")
        if not prompt.strip():
            raise RuntimeError("提示词不能为空")

        named_images = [
            ("image_1", image_1),
            ("image_2", image_2),
            ("image_3", image_3),
            ("image_4", image_4),
            ("image_5", image_5),
            ("image_6", image_6),
            ("image_7", image_7),
            ("image_8", image_8),
            ("image_9", image_9),
            ("image_10", image_10),
            ("image_11", image_11),
            ("image_12", image_12),
            ("image_13", image_13),
            ("image_14", image_14),
            ("image_15", image_15),
        ]
        collected = _collect_edit_images(named_images)
        files = _build_edit_image_files([pil for _, pil in collected])
        form_data = _build_edit_form_data(model, prompt, n, size, format, quality, background, moderation)

        resp = requests.post(
            f"{api_base.rstrip('/')}/v1/images/edits",
            files=files,
            data=form_data,
            headers=http_headers_multipart(api_key),
            timeout=timeout,
        )
        raise_for_bad_status(resp, "GPTImage多图编辑失败")
        data = resp.json()

        outputs = _extract_image_outputs(data, fallback_format=format)
        image_tensor, refs = _outputs_to_tensor_and_refs(outputs, timeout)
        print(f"[GPTImage] 多图编辑完成，输入{len(collected)}张图，生成{len(outputs)}张图像")
        return (image_tensor, refs, _summarize_response(data))
```

- [ ] **Step 2: Register the node**

Replace the first import line in `nodes/GPTImage/__init__.py` with:

```python
from .gpt_image import GPTImage2Generate, GPTImage2Edit, GPTImage2EditImages
```

Update `NODE_CLASS_MAPPINGS`:

```python
NODE_CLASS_MAPPINGS = {
    "GPTImage2Generate": GPTImage2Generate,
    "GPTImage2Edit": GPTImage2Edit,
    "GPTImage2EditImages": GPTImage2EditImages,
    **({
        "GPTImage2AllGenerate": GPTImage2AllGenerate,
        "GPTImage2AllEdit": GPTImage2AllEdit,
    } if GPTImage2AllGenerate and GPTImage2AllEdit else {}),
}
```

Update `NODE_DISPLAY_NAME_MAPPINGS`:

```python
NODE_DISPLAY_NAME_MAPPINGS = {
    "GPTImage2Generate": "🍐 GPT Image 2 文生图",
    "GPTImage2Edit": "🍐 GPT Image 2 图片编辑",
    "GPTImage2EditImages": "🍐 GPT Image 2 多图改图",
    **({
        "GPTImage2AllGenerate": "🍐 gpt-image-2-all生图",
        "GPTImage2AllEdit": "🍐 gpt-image-2-all编辑图",
    } if GPTImage2AllGenerate and GPTImage2AllEdit else {}),
}
```

- [ ] **Step 3: Run new node and node-level request tests**

Run:

```bash
python -m pytest \
  test/test_gpt_image_nodes.py::test_gpt_image_edit_images_node_registered_and_has_15_image_inputs \
  test/test_gpt_image_nodes.py::test_edit_images_node_posts_multipart_and_returns_summary \
  test/test_gpt_image_nodes.py::test_build_edit_form_data_omits_default_optional_fields \
  test/test_gpt_image_nodes.py::test_build_edit_image_files_uses_image_array_field_and_preserves_rgba_png \
  test/test_gpt_image_nodes.py::test_collect_edit_images_expands_torch_batches_in_socket_order \
  -q
```

Expected: PASS.

- [ ] **Step 4: Commit new node and registration together**

```bash
git add nodes/GPTImage/gpt_image.py nodes/GPTImage/__init__.py test/test_gpt_image_nodes.py
git commit -m "feat: add GPT Image 2 multi-image edit node"
```

## Task 7: Full Offline Validation and Explicit Node Import Check

**Files:**
- Verify: `test/test_gpt_image_nodes.py`
- Verify: `nodes/GPTImage/__init__.py`
- Verify: `diagnose.py`

- [ ] **Step 1: Run all GPT Image tests**

Run:

```bash
python -m pytest test/test_gpt_image_nodes.py -q
```

Expected: all tests PASS.

- [ ] **Step 2: Run explicit GPTImage registration check**

Run:

```bash
python - <<'PY'
from nodes.GPTImage import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

required = ["GPTImage2Generate", "GPTImage2Edit", "GPTImage2EditImages"]
for name in required:
    assert name in NODE_CLASS_MAPPINGS, name
    cls = NODE_CLASS_MAPPINGS[name]
    assert hasattr(cls, "INPUT_TYPES"), name
    assert hasattr(cls, "RETURN_TYPES"), name
    assert hasattr(cls, "FUNCTION"), name
    assert hasattr(cls, "CATEGORY"), name
    assert name in NODE_DISPLAY_NAME_MAPPINGS, name

assert NODE_CLASS_MAPPINGS["GPTImage2EditImages"].CATEGORY == "🍐LLAI/GPTImage"
print("GPTImage nodes import and register correctly")
PY
```

Expected: prints `GPTImage nodes import and register correctly`.

- [ ] **Step 3: Run existing diagnostics as broad regression check**

Run:

```bash
python diagnose.py
```

Expected: diagnostics complete without traceback. This script currently focuses on Sora2, so it is not the proof of GPTImage registration; Step 2 is the GPTImage proof.

- [ ] **Step 4: Commit validation fixes if needed**

If validation required fixes, commit only changed implementation/test files:

```bash
git add nodes/GPTImage/gpt_image.py nodes/GPTImage/__init__.py test/test_gpt_image_nodes.py
git commit -m "fix: stabilize GPT Image 2 node validation"
```

If no files changed after Task 6, skip this commit.

## Task 8: Optional Manual API and ComfyUI UI Verification

**Files:**
- No required code changes.

- [ ] **Step 1: Check API key availability**

Run:

```bash
python - <<'PY'
import os
print("KUAI_API_KEY set:", bool(os.environ.get("KUAI_API_KEY")))
PY
```

Expected: prints `KUAI_API_KEY set: True` or `False`.

- [ ] **Step 2: If API key is set, verify text-to-image**

Run only when `KUAI_API_KEY set: True`:

```bash
python - <<'PY'
from nodes.GPTImage import NODE_CLASS_MAPPINGS
node = NODE_CLASS_MAPPINGS["GPTImage2Generate"]()
image, refs = node.generate(
    prompt="a small red square icon on white background",
    model="gpt-image-2",
    size="1024x1024（1:1｜正方形）",
    n=1,
    api_key="",
    timeout=1800,
    format="png",
    quality="low",
)
print("image shape:", tuple(image.shape))
print("refs prefix:", refs[:80])
PY
```

Expected: prints an image tensor shape like `(1, H, W, 3)` and a URL or `data:image/...` prefix. If the request fails, capture the Chinese error and do not retry automatically with different fields.

- [ ] **Step 3: If API key is set, verify `image[]` is accepted by KuAi edit API**

Run only after Step 2 succeeds and only when `KUAI_API_KEY set: True`:

```bash
python - <<'PY'
import torch
from nodes.GPTImage import NODE_CLASS_MAPPINGS

node = NODE_CLASS_MAPPINGS["GPTImage2EditImages"]()
image_input = torch.zeros(1, 64, 64, 3)
image, refs, summary = node.edit(
    image_1=image_input,
    prompt="turn the square into a simple red app icon",
    model="gpt-image-2",
    size="1024x1024（1:1｜正方形）",
    n=1,
    api_key="",
    timeout=1800,
    format="png",
    quality="low",
)
print("image shape:", tuple(image.shape))
print("refs prefix:", refs[:80])
print("summary prefix:", summary[:120])
PY
```

Expected: the request succeeds. Record whether KuAi accepts multipart field `image[]`; do not add automatic fallback to `image`.

- [ ] **Step 4: If ComfyUI is available, verify UI registration**

Manual check:

1. Restart ComfyUI so custom nodes reload.
2. Confirm `🍐 GPT Image 2 多图改图` appears under `🍐LLAI/GPTImage`.
3. Add the node.
4. Confirm `image_1` is required, `image_2` through `image_15` are optional `IMAGE` inputs, and widget options include `format`, `quality`, `background`, `moderation`, `api_base`, and `timeout`.
5. Connect a batched `IMAGE` output to `image_1` and confirm the workflow queues without ComfyUI validation errors.

Expected: node appears and sockets/widgets match the design. If ComfyUI cannot be started in the current environment, report that UI verification was not performed.

## Self-Review Checklist

- Spec coverage:
  - `GPTImage2Generate` gains `format` and `quality`: Task 4.
  - `GPTImage2EditImages` supports 15 ComfyUI `IMAGE` inputs: Task 6.
  - Existing URL `GPTImage2Edit` remains compatible: Task 5 plus interface snapshot test.
  - No `mask`, no CSV, no API key node, no `input_fidelity`, no `output_compression`: enforced by scope and tasks.
  - Response parser supports URL, data URL, `b64_json`, `data` list/object, top-level `b64_json`, and `choices`: Task 2.
  - `image[]` multipart field is fixed and tested: Tasks 3, 6, and optional Task 8.
  - ComfyUI batch behavior covers torch 4D, numpy 4D, single 3D tensor, `None` optional inputs, RGBA PNG preservation, and 15-image cap: Task 3.
  - Node-level tests prove helpers are actually used by `generate()` and `edit()`: Tasks 4 and 6.
  - GPTImage registration is verified explicitly: Task 7.
- Placeholder scan: no TBD/TODO/fill-in-later steps are present.
- Type consistency: function names, node names, return names, and test references match across tasks.
- Commit hygiene: no feature commit intentionally leaves the new node unregistered or expected tests failing.
