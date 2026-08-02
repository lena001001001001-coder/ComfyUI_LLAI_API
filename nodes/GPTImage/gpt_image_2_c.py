"""LLAI low-cost 4K gpt-image-2-c text-to-image node."""

import json
import time

import requests

from ..Sora2.kuai_utils import env_or, http_headers_auth_only, raise_for_bad_status
from .gpt_image import _extract_image_outputs, _outputs_to_tensor_and_refs, _summarize_response


MODEL = "gpt-image-2-c"
DEFAULT_API_BASE = "https://api.llaiapi.host"
DEFAULT_ENDPOINT = "/v1/images/generations"

# Exact values documented by the OpenAI-compatible image generation endpoint.
SIZES = [
    "auto（默认）",
    "1024x1024（1K正方形）",
    "1536x1024（1K横版）",
    "1024x1536（1K竖版）",
    "2048x2048（2K正方形）",
    "2048x1152（2K横版）",
    "3840x2160（4K横版）",
    "2160x3840（4K竖版）",
]
LEGACY_RESOLUTIONS = ["1K（标准）", "2K（高清）", "4K（超清）"]
RESOLUTION_OPTIONS = SIZES + LEGACY_RESOLUTIONS
SIZE_VALUES = {label: label.split("（", 1)[0] for label in SIZES}
FORMATS = ["png", "jpeg", "webp"]
QUALITIES = ["auto", "low", "medium", "high"]

K_PROMPT = "提示词"
K_RESOLUTION = "分辨率"
K_ASPECT_RATIO = "图像比例"
K_N = "生成数量"
K_API_KEY = "API密钥"
K_API_BASE = "API地址"
K_TIMEOUT = "超时秒数"
K_FORMAT = "输出格式"
K_QUALITY = "图像质量"


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
    if size == "auto（默认）":
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
                    RESOLUTION_OPTIONS,
                    {
                        "default": "1024x1024（1K正方形）",
                        "tooltip": "模型说明：普通线路支持 1K；gpt-绘图分组支持 1K、2K、4K",
                    },
                ),
                K_ASPECT_RATIO: (
                    LEGACY_ASPECT_RATIOS,
                    {
                        "default": "由尺寸决定",
                        "advanced": True,
                        "tooltip": "兼容旧工作流；新尺寸选项已包含比例，无需修改",
                    },
                ),
                K_N: (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": 10,
                        "advanced": True,
                        "tooltip": "仅兼容旧工作流；该值会被忽略，API 请求不会发送 n",
                    },
                ),
                K_API_KEY: (
                    "STRING",
                    {"default": "", "tooltip": "留空使用环境变量 KUAI_API_KEY"},
                ),
            },
            "optional": {
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
                    {"default": "auto", "tooltip": "文档支持 auto、low、medium、high"},
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

        size_label = kwargs.get(K_RESOLUTION, "1024x1024（1K正方形）")
        aspect_ratio = kwargs.get(K_ASPECT_RATIO, "由尺寸决定")
        size = resolve_size(size_label, aspect_ratio)
        output_format = kwargs.get(K_FORMAT, "png")
        quality = kwargs.get(K_QUALITY, "auto")
        payload = build_payload(prompt, size, output_format, quality)
        endpoint = resolve_endpoint(kwargs.get(K_API_BASE, DEFAULT_ENDPOINT))
        timeout = int(kwargs.get(K_TIMEOUT, 1800))

        session = requests.Session()
        session.trust_env = False
        headers = http_headers_auth_only(api_key)
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

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
