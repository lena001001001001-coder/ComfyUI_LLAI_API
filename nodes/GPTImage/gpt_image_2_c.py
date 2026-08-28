"""LLAI low-cost 4K gpt-image-2-c text-to-image node."""

import json
import time

import requests
from PIL import Image

from ..Sora2.kuai_utils import env_or, http_headers_auth_only, http_headers_multipart, raise_for_bad_status
from .gpt_image import (
    MAX_EDIT_IMAGES,
    _collect_edit_images,
    _extract_image_outputs,
    _outputs_to_tensor_and_refs,
    _summarize_response,
)
from ..Sora2.kuai_utils import save_image_to_buffer


MODEL = "gpt-image-2-c"
DEFAULT_API_BASE = "https://api.llaiapi.host"
DEFAULT_ENDPOINT = "/v1/images/generations"

# Exact values documented by the OpenAI-compatible image generation endpoint.
SIZES = [
    "auto",
    "1024x1024（1:1）",
    "1536x1024（3:2）",
    "1024x1536（2:3）",
    "2048x2048（1:1）",
    "2048x1152（16:9）",
    "3840x2160（16:9）",
    "2160x3840（9:16）",
]
LEGACY_RESOLUTIONS = ["1K", "2K", "4K"]
# Pixel-size choices shown by the 图像比例 widget. 1K/2K/4K belong only to
# the separate 分辨率 widget and are intentionally not listed here.
RESOLUTION_OPTIONS = SIZES
SIZE_VALUES = {
    "auto": "auto",
    "1024x1024（1:1）": "1024x1024",
    "1536x1024（3:2）": "1536x1024",
    "1024x1536（2:3）": "1024x1536",
    "2048x2048（1:1）": "2048x2048",
    "2048x1152（16:9）": "2048x1152",
    "3840x2160（16:9）": "3840x2160",
    "2160x3840（9:16）": "2160x3840",
}
SIZE_BY_RESOLUTION = {
    "1K": {"1024x1024": "1024x1024", "1536x1024": "1536x1024", "1024x1536": "1024x1536"},
    "2K": {"1024x1024": "2048x2048", "1536x1024": "2048x1152", "2048x2048": "2048x2048", "2048x1152": "2048x1152"},
    "4K": {"1024x1024": "3840x2160", "1536x1024": "3840x2160", "1024x1536": "2160x3840", "3840x2160": "3840x2160", "2160x3840": "2160x3840"},
}
# Additional proportions exposed only by the full-size node.  Each entry is
# the exact pixel size sent for the selected 1K/2K/4K resolution tier.
FULL_SIZE_RATIO_SIZES = {
    "1:1": {"1K": "1024x1024", "2K": "1920x1920", "4K": "2880x2880"},
    "2:3": {"1K": "1024x1536", "2K": "1536x2304", "4K": "2336x3504"},
    "3:2": {"1K": "1536x1024", "2K": "2304x1536", "4K": "3504x2336"},
    "4:3": {"1K": "1536x1152", "2K": "2048x1536", "4K": "3264x2448"},
    "3:4": {"1K": "1152x1536", "2K": "1536x2048", "4K": "2448x3264"},
    "9:16": {"1K": "864x1536", "2K": "1440x2560", "4K": "2016x3584"},
    "16:9": {"1K": "1536x864", "2K": "2560x1440", "4K": "3584x2016"},
    "9:21": {"1K": "864x2016", "2K": "1152x2688", "4K": "1632x3808"},
    "21:9": {"1K": "2016x864", "2K": "2688x1152", "4K": "3808x1632"},
    "1:3": {"1K": "1024x3072", "2K": "1920x5760", "4K": "2880x8640"},
    "3:1": {"1K": "3072x1024", "2K": "5760x1920", "4K": "8640x2880"},
}
FULL_SIZE_RATIO_OPTIONS = ["auto", *FULL_SIZE_RATIO_SIZES]
FORMATS = ["png", "jpeg", "webp"]
QUALITIES = ["auto", "low", "medium", "high"]

K_PROMPT = "提示词"
K_RATIO = "图像比例"
K_RESOLUTION = "分辨率"
K_ASPECT_RATIO = "图像比例"
K_API_KEY = "API密钥"
K_API_BASE = "API地址"
K_TIMEOUT = "超时秒数"
K_FORMAT = "输出格式"
K_QUALITY = "图像质量"
K_SEED = "seed"
EDIT_IMAGE_KEYS = [f"参考图{idx}" for idx in range(1, MAX_EDIT_IMAGES + 1)]
MAX_REFERENCE_DIMENSION = 2048
REFERENCE_JPEG_QUALITY = 85


def _build_compact_edit_image_files(images):
    """Encode references compactly so a 15-image multipart request is not dropped in transit."""
    files = []
    total_bytes = 0
    for index, pil in enumerate(images, start=1):
        image = pil.convert("RGB")
        width, height = image.size
        scale = min(1.0, MAX_REFERENCE_DIMENSION / max(width, height))
        if scale < 1.0:
            image = image.resize(
                (max(1, round(width * scale)), max(1, round(height * scale))),
                Image.Resampling.LANCZOS,
            )
        buffer = save_image_to_buffer(image, fmt="jpeg", quality=REFERENCE_JPEG_QUALITY)
        total_bytes += len(buffer.getvalue())
        files.append(("image[]", (f"reference_{index:02d}.jpg", buffer, "image/jpeg")))
    # This is a guardrail for proxies that reject unusually large multipart bodies.
    if total_bytes > 45 * 1024 * 1024:
        raise RuntimeError(
            f"15张参考图压缩后仍有 {total_bytes / 1024 / 1024:.1f}MB，超过安全上传大小；"
            "请先降低输入图分辨率或分批处理。"
        )
    return files


LEGACY_ASPECT_RATIOS = [
    "由尺寸决定",
    "1:1（正方形）",
    "3:2（横版）",
    "2:3（竖版）",
    "16:9（4K横版）",
    "9:16（4K竖版）",
]
LEGACY_SIZE_TABLE = {
    ("1K（标准）", "1:1（正方形）"): "1024x1024",
    ("1K（标准）", "3:2（横版）"): "1536x1024",
    ("1K（标准）", "2:3（竖版）"): "1024x1536",
    ("2K（高清）", "1:1（正方形）"): "2048x2048",
    ("2K（高清）", "16:9（4K横版）"): "2048x1152",
    ("4K（超清）", "16:9（4K横版）"): "3840x2160",
    ("4K（超清）", "9:16（4K竖版）"): "2160x3840",
}


def resolve_size(size, aspect_ratio="由尺寸决定"):
    """Return an API size and accept labels saved by earlier node versions."""
    legacy_size_names = {"1K": "1K（标准）", "2K": "2K（高清）", "4K": "4K（超清）"}
    size = legacy_size_names.get(size, size)
    if size in FULL_SIZE_RATIO_SIZES and aspect_ratio in LEGACY_RESOLUTIONS:
        return FULL_SIZE_RATIO_SIZES[size][aspect_ratio]
    if size == "auto" and aspect_ratio in LEGACY_RESOLUTIONS:
        return "auto"
    # New UI: the pixel-size selector is named 比例 and the 1K/2K/4K
    # selector is named 分辨率. Explicit pixel sizes take precedence.
    if size in SIZE_VALUES:
        # The UI now supplies 比例 first and 分辨率 second. Keep the
        # selected proportion while scaling it to the chosen resolution.
        return SIZE_BY_RESOLUTION.get(aspect_ratio, {}).get(size, SIZE_VALUES[size])
    if size == "auto" and aspect_ratio in {"1K", "2K", "4K"}:
        return aspect_ratio
    if size in {"auto", "auto（默认）"}:
        return "auto"
    if size in {"1K（标准）", "2K（高清）", "4K（超清）"}:
        try:
            return LEGACY_SIZE_TABLE[(size, aspect_ratio)]
        except KeyError as exc:
            raise ValueError(f"gpt-image-2-c 不支持旧组合：{size} + {aspect_ratio}") from exc
    value = SIZE_VALUES.get(size, str(size or "auto").split("（", 1)[0])
    if value not in set(SIZE_VALUES.values()):
        raise ValueError(f"gpt-image-2-c 不支持尺寸：{size}")
    return value


def build_payload(prompt, size, output_format, quality):
    # The gpt-image-2-c model page says this model currently does not support n.
    payload = {"model": MODEL, "prompt": prompt, "size": size}
    if output_format != "png":
        payload["format"] = output_format
    if quality != "auto":
        payload["quality"] = quality
    return payload


def resolve_endpoint(api_address):
    address = str(api_address or DEFAULT_ENDPOINT).strip().rstrip("/")
    if address.startswith("/"):
        return f"{DEFAULT_API_BASE}{address}"
    if address.endswith(DEFAULT_ENDPOINT):
        return address
    return f"{address}{DEFAULT_ENDPOINT}"


def check_model_access(session, endpoint, headers):
    models_endpoint = endpoint.split(DEFAULT_ENDPOINT, 1)[0] + "/v1/models"
    try:
        response = session.get(models_endpoint, headers=headers, timeout=(15, 30))
        if response.status_code != 200:
            return f"模型列表检查返回 HTTP {response.status_code}"
        payload = response.json()
        models = payload.get("data", []) if isinstance(payload, dict) else []
        model_ids = {
            str(item.get("id", ""))
            for item in models
            if isinstance(item, dict)
        }
        if MODEL in model_ids:
            return "当前密钥可在模型列表中看到 gpt-image-2-c"
        return "当前密钥的模型列表中没有 gpt-image-2-c"
    except Exception as exc:
        return f"模型列表检查失败：{type(exc).__name__}"


class GPTImage2CLowCost4K:
    @classmethod
    def INPUT_TYPES(cls):
        optional_images = {
            key: ("IMAGE", {"tooltip": f"连接后切换为图生图；参考图{idx}，最多15张"})
            for idx, key in enumerate(EDIT_IMAGE_KEYS, start=1)
        }
        return {
            "required": {
                K_PROMPT: (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "必填，图像描述提示词，接口文档限制最多 1000 个字符",
                    },
                ),
                K_RESOLUTION: (
                    LEGACY_RESOLUTIONS,
                    {
                        "default": "1K",
                        "tooltip": "选择分辨率档位：1K、2K、4K",
                    },
                ),
                K_RATIO: (
                    RESOLUTION_OPTIONS,
                    {
                        "default": "1024x1024（1:1）",
                        "tooltip": "选择输出比例；切换分辨率后将按对应档位生成",
                    },
                ),
                K_API_KEY: (
                    "STRING",
                    {"default": "", "tooltip": "留空使用环境变量 KUAI_API_KEY"},
                ),
            },
            "optional": {
                **optional_images,
                K_API_BASE: (
                    "STRING",
                    {"default": DEFAULT_ENDPOINT, "tooltip": "OpenAI 绘图端点"},
                ),
                K_TIMEOUT: (
                    "INT",
                    {"default": 1800, "min": 30, "max": 9999, "tooltip": "请求超时秒数"},
                ),
                K_FORMAT: (
                    FORMATS,
                    {"default": "png", "tooltip": "文档支持 png、jpeg、webp"},
                ),
                K_QUALITY: (
                    QUALITIES,
                    {"default": "medium", "tooltip": "文档支持 auto、low、medium、high"},
                ),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "生成信息", "响应JSON摘要")
    FUNCTION = "generate"
    CATEGORY = "LLAI/GPTImage"

    def generate(self, **kwargs):
        prompt = str(kwargs.get(K_PROMPT, ""))
        api_key = env_or(kwargs.get(K_API_KEY, ""), "KUAI_API_KEY")
        if not prompt.strip():
            raise ValueError("提示词不能为空")
        if len(prompt) > 1000:
            raise ValueError(f"提示词不能超过 1000 个字符，当前为 {len(prompt)} 个字符")
        if not api_key:
            raise RuntimeError("API Key 未配置")

        ratio_label = kwargs.get(K_RATIO)
        size_label = kwargs.get(K_RESOLUTION, "1K")
        # Accept old workflows where 分辨率 carried the pixel-size value.
        if ratio_label is None and size_label in RESOLUTION_OPTIONS:
            ratio_label, size_label = size_label, "1K"
        size = resolve_size(ratio_label or "1024x1024（1:1）", size_label)
        output_format = kwargs.get(K_FORMAT, "png")
        quality = kwargs.get(K_QUALITY, "auto")
        endpoint = resolve_endpoint(kwargs.get(K_API_BASE, DEFAULT_ENDPOINT))
        timeout = int(kwargs.get(K_TIMEOUT, 1800))

        session = requests.Session()
        session.trust_env = False
        headers = http_headers_auth_only(api_key)
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        # 有任意参考图时自动切换到 OpenAI 兼容图片编辑接口；未连接参考图则保持文生图。
        connected = [(key, kwargs.get(key)) for key in EDIT_IMAGE_KEYS if kwargs.get(key) is not None]
        if connected:
            named_images = [(key, value) for key, value in connected if value is not None]
            images = _collect_edit_images(named_images)
            files = _build_compact_edit_image_files([pil for _, pil in images])
            form_data = {"model": MODEL, "prompt": prompt, "size": size}
            if output_format != "png":
                form_data["format"] = output_format
            if quality != "auto":
                form_data["quality"] = quality
            try:
                response = session.post(
                    f"{endpoint.rsplit('/v1/images/generations', 1)[0]}/v1/images/edits",
                    files=files,
                    data=form_data,
                    headers=http_headers_multipart(api_key),
                    timeout=(30, timeout),
                )
            except requests.exceptions.ConnectionError as exc:
                raise RuntimeError("LLAI 图像编辑后端在返回 HTTP 响应前断开连接；请确认 gpt-image-2-c 渠道支持图生图。") from exc
            raise_for_bad_status(response, "gpt-image-2-c 图生图失败")
            data = response.json()
            outputs = _extract_image_outputs(data, fallback_format=output_format)
            image, _ = _outputs_to_tensor_and_refs(outputs, timeout)
            info = json.dumps({"model": MODEL, "mode": "image-to-image", "size": size,
                               "format": output_format, "quality": quality,
                               "input_image_count": len(images), "image_count": len(outputs)},
                              ensure_ascii=False, indent=2)
            return image, info, _summarize_response(data)

        payload = build_payload(prompt, size, output_format, quality)

        started_at = time.monotonic()
        try:
            response = session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=(30, timeout),
            )
        except requests.exceptions.ConnectionError as exc:
            elapsed = time.monotonic() - started_at
            access_result = check_model_access(session, endpoint, headers)
            group_hint = (
                "当前为 2K/4K，请确认密钥属于支持这些尺寸的 gpt-绘图分组。"
                if size not in {"auto", "1024x1024", "1536x1024", "1024x1536"}
                else "当前为 1K/auto；若模型可见仍断开，请服务商检查生成线路。"
            )
            raise RuntimeError(
                "LLAI 图像后端在返回 HTTP 响应前断开连接。"
                f"等待 {elapsed:.1f} 秒，接口={endpoint}，模型={MODEL}，尺寸={size}。"
                f"权限诊断：{access_result}。{group_hint}"
                "请求已按模型详情移除 n；为避免可能重复扣费，节点不会自动重试。"
            ) from exc

        raise_for_bad_status(response, "gpt-image-2-c 生图失败")
        data = response.json()
        outputs = _extract_image_outputs(data, fallback_format=output_format)
        image, _ = _outputs_to_tensor_and_refs(outputs, timeout)
        output_refs = [
            output["value"] if output["source"] == "url" else f"<{output['source']} omitted>"
            for output in outputs
        ]
        info = json.dumps(
            {
                "model": MODEL,
                "endpoint": endpoint,
                "size": size,
                "format": output_format,
                "quality": quality,
                "image_count": len(outputs),
                "output_refs": output_refs,
            },
            ensure_ascii=False,
            indent=2,
        )
        return image, info, _summarize_response(data)


class GPTImage2CFullSize(GPTImage2CLowCost4K):
    """与低价节点功能完全相同的独立全尺寸节点。"""

    @classmethod
    def INPUT_TYPES(cls):
        inputs = super().INPUT_TYPES()
        # This is a ComfyUI execution/cache seed.  The gpt-image-2-c relay
        # does not document a seed request field, so it is intentionally not
        # sent to the API; changing it forces a fresh node execution.
        inputs["required"][K_SEED] = (
            "INT",
            {
                "default": 0,
                "min": 0,
                "max": 0xFFFFFFFFFFFFFFFF,
                "control_after_generate": True,
                "tooltip": "仅控制 ComfyUI 重新执行；接口请求不会发送 seed 字段",
            },
        )
        inputs["required"][K_RATIO] = (
            FULL_SIZE_RATIO_OPTIONS,
            {"default": "1:1", "tooltip": "全尺寸比例，按 1K/2K/4K 分辨率生成"},
        )
        return inputs
