"""LLAI Doubao Seedream 4.0 text-to-image node."""

import json

import requests

from ..GPTImage.gpt_image import (
    _extract_image_outputs,
    _outputs_to_tensor_and_refs,
    _summarize_response,
)
from ..Sora2.kuai_utils import env_or, http_headers_auth_only, raise_for_bad_status
MODEL = "doubao-seedream-4-0-250828"
ENDPOINT = "https://api.llaiapi.host/v1/images/generations"
RESPONSE_FORMATS = ["url", "b64_json"]
MIN_PIXELS = 1280 * 720
MAX_PIXELS = 4096 * 4096
MIN_ASPECT_RATIO = 1 / 16
MAX_ASPECT_RATIO = 16

SIZE_LEVELS = ["1K", "2K", "4K"]
SUPPORTED_SIZE_LEVELS = ["1K", "2K", "4K"]
RATIO_OPTIONS_1K = [
    "1024x1024（1:1 方图）", "1152x864（4:3 横图）", "864x1152（3:4 竖图）",
    "1280x720（16:9 横图）", "720x1280（9:16 竖图）",
    "1248x832（3:2 横图）", "832x1248（2:3 竖图）", "1512x648（21:9 超宽图）",
]
RATIO_OPTIONS_2K = [
    "2048x2048（1:1 方图）", "2304x1728（4:3 横图）", "1728x2304（3:4 竖图）",
    "2848x1600（16:9 横图）", "1600x2848（9:16 竖图）",
    "2496x1664（3:2 横图）", "1664x2496（2:3 竖图）", "3136x1344（21:9 超宽图）",
]
RATIO_OPTIONS_4K = [
    "4096x4096（1:1 方图）", "4704x3520（4:3 横图）", "3520x4704（3:4 竖图）",
    "5504x3040（16:9 横图）", "3040x5504（9:16 竖图）",
    "4992x3328（3:2 横图）", "3328x4992（2:3 竖图）", "6240x2656（21:9 超宽图）",
]
RATIO_OPTIONS_BY_SIZE = {"1K": RATIO_OPTIONS_1K, "2K": RATIO_OPTIONS_2K, "4K": RATIO_OPTIONS_4K}
ALL_RATIO_OPTIONS = RATIO_OPTIONS_1K + RATIO_OPTIONS_2K + RATIO_OPTIONS_4K
LEGACY_RATIO_MAP = {
    "1536x1024": "1248x832",
    "1024x1536": "832x1248",
    "2560x1440": "2848x1600",
    "1440x2560": "1600x2848",
    "3840x2160": "5504x3040",
    "2160x3840": "3040x5504",
    "3072x2304": "4704x3520",
    "2304x3072": "3520x4704",
}
RATIO_PROMPTS = {
    "1024x1024": "请生成 1:1 比例的正方形图片。",
    "1152x864": "请生成 4:3 比例的横向图片。",
    "864x1152": "请生成 3:4 比例的竖向图片。",
    "1280x720": "请生成 16:9 比例的横向图片。",
    "720x1280": "请生成 9:16 比例的竖向图片。",
    "1248x832": "请生成 3:2 比例的横向图片。",
    "832x1248": "请生成 2:3 比例的竖向图片。",
    "1512x648": "请生成 21:9 比例的超宽横向图片。",
    "2048x2048": "请生成 1:1 比例的正方形图片。",
    "2304x1728": "请生成 4:3 比例的横向图片。",
    "1728x2304": "请生成 3:4 比例的竖向图片。",
    "2848x1600": "请生成 16:9 比例的横向图片。",
    "1600x2848": "请生成 9:16 比例的竖向图片。",
    "2496x1664": "请生成 3:2 比例的横向图片。",
    "1664x2496": "请生成 2:3 比例的竖向图片。",
    "3136x1344": "请生成 21:9 比例的超宽横向图片。",
    "4096x4096": "请生成 1:1 比例的正方形图片。",
    "4704x3520": "请生成 4:3 比例的横向图片。",
    "3520x4704": "请生成 3:4 比例的竖向图片。",
    "5504x3040": "请生成 16:9 比例的横向图片。",
    "3040x5504": "请生成 9:16 比例的竖向图片。",
    "4992x3328": "请生成 3:2 比例的横向图片。",
    "3328x4992": "请生成 2:3 比例的竖向图片。",
    "6240x2656": "请生成 21:9 比例的超宽横向图片。",
}


def resolve_size(size_label: str) -> str:
    value = str(size_label or "").strip()
    if value in SUPPORTED_SIZE_LEVELS:
        return value
    value = value.split("（", 1)[0]
    try:
        width, height = (int(part) for part in value.split("x"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"不支持的尺寸：{size_label}") from exc
    pixels = width * height
    aspect = width / height
    if not MIN_PIXELS <= pixels <= MAX_PIXELS:
        raise ValueError(f"尺寸 {value} 的总像素必须在 {MIN_PIXELS} 到 {MAX_PIXELS} 之间")
    if not MIN_ASPECT_RATIO <= aspect <= MAX_ASPECT_RATIO:
        raise ValueError(f"尺寸 {value} 的宽高比必须在 1:16 到 16:1 之间")
    return f"{width}x{height}"


def resolve_output_size(size: str, ratio: str) -> str:
    if size not in SUPPORTED_SIZE_LEVELS:
        return resolve_size(size)
    if not ratio:
        ratio = RATIO_OPTIONS_BY_SIZE[size][0]
    requested = resolve_size(ratio)
    allowed = {resolve_size(option) for option in RATIO_OPTIONS_BY_SIZE[size]}
    requested = LEGACY_RATIO_MAP.get(requested, requested)
    if requested not in allowed:
        raise ValueError(f"尺寸 {requested} 不属于 Seedream 4.0 的 {size} 官方尺寸，请刷新节点后重新选择 ratio")
    return requested


def build_payload(prompt: str, size: str, ratio: str, watermark: bool, response_format: str) -> dict:
    if response_format not in RESPONSE_FORMATS:
        raise ValueError(f"不支持的返回格式：{response_format}")
    mapped_size = resolve_output_size(size, ratio)
    request_size = size if size in SUPPORTED_SIZE_LEVELS else mapped_size
    request_prompt = prompt
    if size in SUPPORTED_SIZE_LEVELS:
        request_prompt = f"{prompt.rstrip()}\n\n构图要求：{RATIO_PROMPTS[mapped_size]}"
    return {
        "model": MODEL,
        "prompt": request_prompt,
        "size": request_size,
        "sequential_image_generation": "disabled",
        "stream": False,
        "response_format": response_format,
        "watermark": bool(watermark),
    }


class LLDoubaoSeedream40TextToImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {"multiline": True, "default": "", "tooltip": "必填，支持中文或英文的图像生成提示词"},
                ),
                "size": (
                    SIZE_LEVELS,
                    {"default": "2K", "tooltip": "节点提供 1K、2K、4K 分辨率档位"},
                ),
                "watermark": (
                    "BOOLEAN",
                    {"default": False, "tooltip": "开启后在右下角添加“AI生成”水印"},
                ),
                "response_format": (
                    RESPONSE_FORMATS,
                    {"default": "url", "tooltip": "url 链接有效期为 24 小时；也可返回 Base64"},
                ),
                "api_key": (
                    "STRING",
                    {"default": "", "tooltip": "LLAI API 密钥；留空时读取环境变量 KUAI_API_KEY"},
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                        "tooltip": "用于控制 ComfyUI 是否重新执行生成；接口请求不发送 seed 字段",
                    },
                ),
                "ratio": (
                    ALL_RATIO_OPTIONS,
                    {"default": RATIO_OPTIONS_2K[0], "tooltip": "根据 size 档位显示对应的输出尺寸"},
                ),
            },
            "optional": {
                "timeout": (
                    "INT",
                    {"default": 1800, "min": 30, "max": 9999, "tooltip": "等待接口响应的最长秒数"},
                ),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "图片结果", "响应摘要")
    FUNCTION = "generate"
    CATEGORY = "LLAI/Doubao"

    def generate(self, prompt, size, watermark, response_format, api_key, seed, timeout=1800, ratio=None):
        _ = seed
        prompt = str(prompt or "").strip()
        if not prompt:
            raise ValueError("提示词不能为空")
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点中填写或设置环境变量 KUAI_API_KEY")

        ratio = ratio or RATIO_OPTIONS_BY_SIZE.get(size, RATIO_OPTIONS_2K)[0]
        payload = build_payload(prompt, size, ratio, watermark, response_format)
        print(
            f"[LLAI] Doubao Seedream 4.0 size={payload['size']} "
            f"(官方档位模式，ratio={ratio})"
        )
        headers = http_headers_auth_only(api_key)
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        session = requests.Session()
        session.trust_env = False
        try:
            response = session.post(ENDPOINT, json=payload, headers=headers, timeout=(30, int(timeout)))
        except requests.RequestException as exc:
            raise RuntimeError(f"[LLAI] Doubao Seedream 4.0 请求失败：{exc}") from exc

        raise_for_bad_status(response, "Doubao Seedream 4.0 文生图失败")
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Doubao Seedream 4.0 返回了非 JSON 响应") from exc

        outputs = _extract_image_outputs(data, fallback_format="jpeg")
        image, _ = _outputs_to_tensor_and_refs(outputs, int(timeout))
        refs = [item["value"] if item["source"] == "url" else f"<{item['source']} omitted>" for item in outputs]
        print(f"[LLAI] Doubao Seedream 4.0 文生图完成，生成 {len(outputs)} 张图像")
        return (image, "\n".join(refs), _summarize_response(data))
