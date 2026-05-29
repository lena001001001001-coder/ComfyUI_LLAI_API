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

RESOLUTIONS = [
    "auto（默认）",
    "1K（标清）",
    "2K（高清）",
    "4K（超清）",
]
RESOLUTION_KEY_MAP = {
    "auto（默认）": "auto",
    "1K（标清）": "1K",
    "2K（高清）": "2K",
    "4K（超清）": "4K",
}

ASPECT_RATIOS = [
    "1:1（正方形）",
    "3:2（横版）",
    "2:3（竖版）",
    "4:3（横版偏方）",
    "3:4（竖版偏方）",
    "5:4（横版海报）",
    "4:5（竖版海报）",
    "16:9（宽屏横版）",
    "9:16（宽屏竖版）",
    "2:1（长横图）",
    "1:2（长竖图）",
    "21:9（超宽横图）",
    "9:21（超长竖图）",
    "1:3（超长竖图）",
    "1:4（超长竖图）",
    "1:6（超长竖图）",
]
ASPECT_RATIO_KEY_MAP = {label: label.split("（", 1)[0] for label in ASPECT_RATIOS}

SIZE_TABLE = {
    "1:1":  {"1K": "1024x1024", "2K": "1920x1920", "4K": "2880x2880"},
    "3:2":  {"1K": "1536x1024", "2K": "2304x1536", "4K": "3504x2336"},
    "2:3":  {"1K": "1024x1536", "2K": "1536x2304", "4K": "2336x3504"},
    "4:3":  {"1K": "1536x1152", "2K": "2048x1536", "4K": "3264x2448"},
    "3:4":  {"1K": "1152x1536", "2K": "1536x2048", "4K": "2448x3264"},
    "5:4":  {"1K": "1280x1024", "2K": "2080x1664", "4K": "3200x2560"},
    "4:5":  {"1K": "1024x1280", "2K": "1664x2080", "4K": "2560x3200"},
    "16:9": {"1K": "1536x864",  "2K": "2560x1440", "4K": "3584x2016"},
    "9:16": {"1K": "864x1536",  "2K": "1440x2560", "4K": "2016x3584"},
    "2:1":  {"1K": "1536x768",  "2K": "2560x1280", "4K": "3808x1904"},
    "1:2":  {"1K": "768x1536",  "2K": "1280x2560", "4K": "1904x3808"},
    "21:9": {"1K": "2016x864",  "2K": "2688x1152", "4K": "3808x1632"},
    "9:21": {"1K": "864x2016",  "2K": "1152x2688", "4K": "1632x3808"},
    "1:3":  {"1K": "1024x3072", "2K": "1920x5760", "4K": "2880x8640"},
    "1:4":  {"1K": "1024x4096", "2K": "1920x7680", "4K": "2880x11520"},
    "1:6":  {"1K": "1024x6144", "2K": "1920x11520", "4K": "2880x17280"},
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


def _string_or_empty(value) -> str:
    return value.strip() if isinstance(value, str) else ""


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

    b64_json = _string_or_empty(item.get("b64_json"))
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

        top_level_b64 = _string_or_empty(data.get("b64_json"))
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


def _resolve_size(resolution: str, aspect_ratio: str) -> str:
    """根据分辨率与比例下拉值解析为 API 真正使用的 pixel size 字符串。"""
    res_key = RESOLUTION_KEY_MAP.get(resolution, resolution)
    if res_key == "auto":
        return "auto"
    ratio_key = ASPECT_RATIO_KEY_MAP.get(aspect_ratio, aspect_ratio)
    table = SIZE_TABLE.get(ratio_key)
    if not table:
        raise RuntimeError(f"未知的图像比例: {aspect_ratio}")
    size = table.get(res_key)
    if not size:
        raise RuntimeError(f"未知的分辨率档位: {resolution}")
    return size


def _build_generation_info(
    model: str,
    resolution: str,
    aspect_ratio: str,
    size: str,
    n: int,
    output_format: str,
    quality: str,
    image_count: int,
    **extras,
) -> str:
    """生成节点对外的「生成信息」JSON 字符串。"""
    info = {
        "model": model,
        "resolution": RESOLUTION_KEY_MAP.get(resolution, resolution),
        "aspect_ratio": ASPECT_RATIO_KEY_MAP.get(aspect_ratio, aspect_ratio),
        "size": size,
        "n": int(n),
        "format": output_format,
        "quality": quality,
        "image_count": image_count,
    }
    info.update(extras)
    return json.dumps(info, ensure_ascii=False, indent=2)


def _build_generation_payload(model: str, prompt: str, n: int, resolution: str, aspect_ratio: str, output_format: str = "png", quality: str = "auto") -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "n": int(n),
        "size": _resolve_size(resolution, aspect_ratio),
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
    resolution: str,
    aspect_ratio: str,
    output_format: str = "png",
    quality: str = "auto",
    background: str = "auto",
    moderation: str = "auto",
) -> dict:
    form_data = {
        "model": model,
        "prompt": prompt,
        "n": str(int(n)),
        "size": _resolve_size(resolution, aspect_ratio),
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


def _build_edit_url_files(image_urls: list, timeout: int) -> list:
    images = []
    for index, url in enumerate(image_urls, start=1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            pil = Image.open(io.BytesIO(resp.content))
            images.append(pil.copy())
        except Exception as exc:
            raise RuntimeError(f"下载参考图失败: image_url_{index} - {_truncate_string(url, 200)} - {exc}") from exc
    return _build_edit_image_files(images)


# ============================================================
# 中文参数键 -> 内部变量名 映射表
# 注：参数名直接以中文（带 emoji）展示在节点界面上
# ============================================================

K_PROMPT = "提示词"
K_MODEL = "模型"
K_RESOLUTION = "分辨率"
K_ASPECT_RATIO = "图像比例"
K_N = "生成数量"
K_API_KEY = "API密钥"
K_API_BASE = "API地址"
K_TIMEOUT = "超时秒数"
K_FORMAT = "输出格式"
K_QUALITY = "图像质量"
K_BACKGROUND = "背景"
K_MODERATION = "内容审核"
K_IMAGE_URL_1 = "图片URL1"
K_IMAGE_URL_2 = "图片URL2"
K_IMAGE_URL_3 = "图片URL3"
K_IMAGE_URL_4 = "图片URL4"


class GPTImage2Generate:
    """GPT Image 2 文生图节点"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                K_PROMPT: ("STRING", {"multiline": True, "default": "", "tooltip": "图像描述提示词"}),
                K_MODEL: (MODELS, {"default": "gpt-image-2", "tooltip": "模型选择"}),
                K_RESOLUTION: (RESOLUTIONS, {"default": "2K（高清）", "tooltip": "分辨率档位（auto/1K/2K/4K），选 auto 时忽略比例"}),
                K_ASPECT_RATIO: (ASPECT_RATIOS, {"default": "1:1（正方形）", "tooltip": "图像比例，与分辨率组合得到实际像素尺寸"}),
                K_N: ("INT", {"default": 1, "min": 1, "max": 10, "tooltip": "生成数量（1-10张）"}),
                K_API_KEY: ("STRING", {"default": "", "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"}),
            },
            "optional": {
                K_API_BASE: ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API服务器地址"}),
                K_TIMEOUT: ("INT", {"default": 1800, "min": 30, "max": 9999, "tooltip": "超时时间(秒)"}),
                K_FORMAT: (FORMATS, {"default": "png", "tooltip": "输出格式（可选 png、jpeg、webp）"}),
                K_QUALITY: (QUALITY_OPTIONS, {"default": "auto", "tooltip": "图像质量（可选 low、medium、high、auto）"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("图像", "生成信息")
    FUNCTION = "generate"
    CATEGORY = "🍐LLAI/GPTImage"

    def generate(self, **kwargs):
        prompt = kwargs.get(K_PROMPT, "")
        model = kwargs.get(K_MODEL, "gpt-image-2")
        resolution = kwargs.get(K_RESOLUTION, "2K（高清）")
        aspect_ratio = kwargs.get(K_ASPECT_RATIO, "1:1（正方形）")
        n = kwargs.get(K_N, 1)
        api_key = kwargs.get(K_API_KEY, "")
        api_base = kwargs.get(K_API_BASE, "https://api.llaiapi.host")
        timeout = kwargs.get(K_TIMEOUT, 1800)
        output_format = kwargs.get(K_FORMAT, "png")
        quality = kwargs.get(K_QUALITY, "auto")

        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点参数或环境变量 KUAI_API_KEY 中设置")
        if not prompt.strip():
            raise RuntimeError("提示词不能为空")

        payload = _build_generation_payload(model, prompt, n, resolution, aspect_ratio, output_format, quality)
        resp = requests.post(
            f"{api_base.rstrip('/')}/v1/images/generations",
            json=payload,
            headers=http_headers_auth_only(api_key),
            timeout=timeout,
        )
        raise_for_bad_status(resp, "GPTImage文生图失败")
        data = resp.json()

        outputs = _extract_image_outputs(data, fallback_format=output_format)
        image_tensor, _ = _outputs_to_tensor_and_refs(outputs, timeout)
        info = _build_generation_info(
            model, resolution, aspect_ratio, _resolve_size(resolution, aspect_ratio),
            n, output_format, quality, image_count=len(outputs),
        )
        print(f"[GPTImage] 文生图完成，生成 {len(outputs)} 张图像")
        return (image_tensor, info)


class GPTImage2Edit:
    """GPT Image 2 图片编辑节点（支持1-4张图片URL）"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                K_IMAGE_URL_1: ("STRING", {"default": "", "tooltip": "图片URL 1（必填）"}),
                K_PROMPT: ("STRING", {"multiline": True, "default": "", "tooltip": "编辑描述提示词"}),
                K_MODEL: (EDIT_MODELS, {"default": "gpt-image-2", "tooltip": "模型选择"}),
                K_RESOLUTION: (RESOLUTIONS, {"default": "2K（高清）", "tooltip": "分辨率档位（auto/1K/2K/4K），选 auto 时忽略比例"}),
                K_ASPECT_RATIO: (ASPECT_RATIOS, {"default": "1:1（正方形）", "tooltip": "图像比例，与分辨率组合得到实际像素尺寸"}),
                K_N: ("INT", {"default": 1, "min": 1, "max": 10, "tooltip": "生成数量（输出图片张数，1-10张）"}),
                K_API_KEY: ("STRING", {"default": "", "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"}),
            },
            "optional": {
                K_IMAGE_URL_2: ("STRING", {"default": "", "tooltip": "图片URL 2（可选附加参考图）"}),
                K_IMAGE_URL_3: ("STRING", {"default": "", "tooltip": "图片URL 3（可选附加参考图）"}),
                K_IMAGE_URL_4: ("STRING", {"default": "", "tooltip": "图片URL 4（可选附加参考图）"}),
                K_FORMAT: (FORMATS, {"default": "png", "tooltip": "输出格式（可选 png、jpeg、webp）"}),
                K_QUALITY: (QUALITY_OPTIONS, {"default": "auto", "tooltip": "图像质量（可选 low、medium、high、auto）"}),
                K_BACKGROUND: (["auto", "transparent", "opaque"], {"default": "auto", "tooltip": "背景透明度（auto 自动、transparent 透明、opaque 不透明）"}),
                K_MODERATION: (["auto", "low"], {"default": "auto", "tooltip": "内容审核级别（auto 默认、low 较宽松）"}),
                K_API_BASE: ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API服务器地址"}),
                K_TIMEOUT: ("INT", {"default": 1800, "min": 30, "max": 9999, "tooltip": "超时时间(秒)"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("图像", "生成信息")
    FUNCTION = "edit"
    CATEGORY = "🍐LLAI/GPTImage"

    def edit(self, **kwargs):
        image_url_1 = kwargs.get(K_IMAGE_URL_1, "")
        prompt = kwargs.get(K_PROMPT, "")
        model = kwargs.get(K_MODEL, "gpt-image-2")
        resolution = kwargs.get(K_RESOLUTION, "2K（高清）")
        aspect_ratio = kwargs.get(K_ASPECT_RATIO, "1:1（正方形）")
        n = kwargs.get(K_N, 1)
        api_key = kwargs.get(K_API_KEY, "")
        image_url_2 = kwargs.get(K_IMAGE_URL_2, "")
        image_url_3 = kwargs.get(K_IMAGE_URL_3, "")
        image_url_4 = kwargs.get(K_IMAGE_URL_4, "")
        output_format = kwargs.get(K_FORMAT, "png")
        quality = kwargs.get(K_QUALITY, "auto")
        background = kwargs.get(K_BACKGROUND, "auto")
        moderation = kwargs.get(K_MODERATION, "auto")
        api_base = kwargs.get(K_API_BASE, "https://api.llaiapi.host")
        timeout = kwargs.get(K_TIMEOUT, 1800)

        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点参数或环境变量 KUAI_API_KEY 中设置")
        if not prompt.strip():
            raise RuntimeError("提示词不能为空")
        if not image_url_1.strip():
            raise RuntimeError("至少需要提供一张图片URL")

        image_urls = [u.strip() for u in [image_url_1, image_url_2, image_url_3, image_url_4] if u.strip()]

        files = _build_edit_url_files(image_urls, timeout)

        form_data = {
            "model": model,
            "prompt": prompt,
            "n": str(n),
            "size": _resolve_size(resolution, aspect_ratio),
            "format": output_format,
            "quality": quality,
            "background": background,
            "moderation": moderation,
        }

        resp = requests.post(
            f"{api_base.rstrip('/')}/v1/images/edits",
            files=files,
            data=form_data,
            headers=http_headers_multipart(api_key),
            timeout=timeout,
        )
        raise_for_bad_status(resp, "GPTImage图片编辑失败")
        data = resp.json()

        outputs = _extract_image_outputs(data, fallback_format=output_format)
        image_tensor, _ = _outputs_to_tensor_and_refs(outputs, timeout)
        info = _build_generation_info(
            model, resolution, aspect_ratio, _resolve_size(resolution, aspect_ratio),
            n, output_format, quality, image_count=len(outputs),
            input_image_count=len(image_urls),
            background=background, moderation=moderation,
        )
        print(f"[GPTImage] 图片编辑完成，输入{len(image_urls)}张图，生成{len(outputs)}张图像")
        return (image_tensor, info)


# 多图编辑节点参考图键（image_1..image_15 -> 参考图1..15）
EDIT_IMAGE_KEYS = [f"参考图{idx}" for idx in range(1, MAX_EDIT_IMAGES + 1)]


class GPTImage2EditImages:
    """GPT Image 2 多图改图节点（支持最多15张 ComfyUI IMAGE 参考图）"""

    @classmethod
    def INPUT_TYPES(cls):
        optional_images = {
            EDIT_IMAGE_KEYS[idx - 1]: ("IMAGE", {"tooltip": f"参考图{idx}"})
            for idx in range(2, MAX_EDIT_IMAGES + 1)
        }
        return {
            "required": {
                EDIT_IMAGE_KEYS[0]: ("IMAGE", {"tooltip": "参考图1（必填）"}),
                K_PROMPT: ("STRING", {"multiline": True, "default": "", "tooltip": "编辑描述提示词"}),
                K_MODEL: (EDIT_MODELS, {"default": "gpt-image-2", "tooltip": "模型选择"}),
                K_RESOLUTION: (RESOLUTIONS, {"default": "2K（高清）", "tooltip": "分辨率档位（auto/1K/2K/4K），选 auto 时忽略比例"}),
                K_ASPECT_RATIO: (ASPECT_RATIOS, {"default": "1:1（正方形）", "tooltip": "图像比例，与分辨率组合得到实际像素尺寸"}),
                K_N: ("INT", {"default": 1, "min": 1, "max": 10, "tooltip": "生成数量（输出图片张数，1-10张）"}),
                K_API_KEY: ("STRING", {"default": "", "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"}),
            },
            "optional": {
                **optional_images,
                K_FORMAT: (FORMATS, {"default": "png", "tooltip": "输出格式（可选 png、jpeg、webp）"}),
                K_QUALITY: (QUALITY_OPTIONS, {"default": "auto", "tooltip": "图像质量（可选 low、medium、high、auto）"}),
                K_BACKGROUND: (["auto", "transparent", "opaque"], {"default": "auto", "tooltip": "背景透明度（auto 自动、transparent 透明、opaque 不透明）"}),
                K_MODERATION: (["auto", "low"], {"default": "auto", "tooltip": "内容审核级别（auto 默认、low 较宽松）"}),
                K_API_BASE: ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API服务器地址"}),
                K_TIMEOUT: ("INT", {"default": 1800, "min": 30, "max": 9999, "tooltip": "超时时间(秒)"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "生成信息", "响应JSON摘要")
    FUNCTION = "edit"
    CATEGORY = "🍐LLAI/GPTImage"

    def edit(self, **kwargs):
        prompt = kwargs.get(K_PROMPT, "")
        model = kwargs.get(K_MODEL, "gpt-image-2")
        resolution = kwargs.get(K_RESOLUTION, "2K（高清）")
        aspect_ratio = kwargs.get(K_ASPECT_RATIO, "1:1（正方形）")
        n = kwargs.get(K_N, 1)
        api_key = kwargs.get(K_API_KEY, "")
        output_format = kwargs.get(K_FORMAT, "png")
        quality = kwargs.get(K_QUALITY, "auto")
        background = kwargs.get(K_BACKGROUND, "auto")
        moderation = kwargs.get(K_MODERATION, "auto")
        api_base = kwargs.get(K_API_BASE, "https://api.llaiapi.host")
        timeout = kwargs.get(K_TIMEOUT, 1800)

        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点参数或环境变量 KUAI_API_KEY 中设置")
        if not prompt.strip():
            raise RuntimeError("提示词不能为空")

        named_images = [
            (f"image_{idx}", kwargs.get(EDIT_IMAGE_KEYS[idx - 1]))
            for idx in range(1, MAX_EDIT_IMAGES + 1)
        ]
        collected = _collect_edit_images(named_images)
        files = _build_edit_image_files([pil for _, pil in collected])
        form_data = _build_edit_form_data(model, prompt, n, resolution, aspect_ratio, output_format, quality, background, moderation)

        resp = requests.post(
            f"{api_base.rstrip('/')}/v1/images/edits",
            files=files,
            data=form_data,
            headers=http_headers_multipart(api_key),
            timeout=timeout,
        )
        raise_for_bad_status(resp, "GPTImage多图编辑失败")
        data = resp.json()

        outputs = _extract_image_outputs(data, fallback_format=output_format)
        image_tensor, _ = _outputs_to_tensor_and_refs(outputs, timeout)
        info = _build_generation_info(
            model, resolution, aspect_ratio, _resolve_size(resolution, aspect_ratio),
            n, output_format, quality, image_count=len(outputs),
            input_image_count=len(collected),
            background=background, moderation=moderation,
        )
        print(f"[GPTImage] 多图编辑完成，输入{len(collected)}张图，生成{len(outputs)}张图像")
        return (image_tensor, info, _summarize_response(data))
