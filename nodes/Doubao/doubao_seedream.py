"""LLAI Doubao Seedream 4.5 text-to-image node."""

import json
import re

import requests

from ..GPTImage.gpt_image import (
    _extract_image_outputs,
    _outputs_to_tensor_and_refs,
    _summarize_response,
)
from ..Sora2.kuai_utils import env_or, http_headers_auth_only, raise_for_bad_status


MODEL = "doubao-seedream-4-5-251128"
ENDPOINT = "https://api.llaiapi.host/v1/images/generations"
MIN_PIXELS = 2560 * 1440
MAX_PIXELS = 4096 * 4096
MIN_ASPECT_RATIO = 1 / 16
MAX_ASPECT_RATIO = 16

SIZE_LEVELS = ["2K", "4K"]
RATIO_OPTIONS_2K = [
    "2048x2048（1:1 方图）",
    "2560x1440（16:9 横图）",
    "1440x2560（9:16 竖图）",
    "2304x1728（4:3 横图）",
    "1728x2304（3:4 竖图）",
    "2496x1664（3:2 横图）",
    "1664x2496（2:3 竖图）",
    "2560x1600（16:10 横图）",
    "1600x2560（10:16 竖图）",
]
RATIO_OPTIONS_4K = [
    "3840x2160（4K 16:9 横图）",
    "2160x3840（4K 9:16 竖图）",
    "3072x2304（4K 4:3 横图）",
    "2304x3072（4K 3:4 竖图）",
    "3072x3072（4K 1:1 方图）",
    "4096x4096（最大方图）",
]
RATIO_OPTIONS_BY_SIZE = {
    "2K": RATIO_OPTIONS_2K,
    "4K": RATIO_OPTIONS_4K,
}
ALL_RATIO_OPTIONS = RATIO_OPTIONS_2K + RATIO_OPTIONS_4K
SIZE_OPTIONS = {
    "2K（模型自适应）": "2K",
    "4K（模型自适应）": "4K",
    "2048x2048（1:1 方图）": "2048x2048",
    "2560x1440（16:9 横图）": "2560x1440",
    "1440x2560（9:16 竖图）": "1440x2560",
    "2304x1728（4:3 横图）": "2304x1728",
    "1728x2304（3:4 竖图）": "1728x2304",
    "2496x1664（3:2 横图）": "2496x1664",
    "1664x2496（2:3 竖图）": "1664x2496",
    "2560x1600（16:10 横图）": "2560x1600",
    "1600x2560（10:16 竖图）": "1600x2560",
    "3840x2160（4K 16:9 横图）": "3840x2160",
    "2160x3840（4K 9:16 竖图）": "2160x3840",
    "3072x2304（4K 4:3 横图）": "3072x2304",
    "2304x3072（4K 3:4 竖图）": "2304x3072",
    "3072x3072（4K 1:1 方图）": "3072x3072",
    "4096x4096（最大方图）": "4096x4096",
}
RESPONSE_FORMATS = ["url", "b64_json"]


def resolve_size(size_label: str) -> str:
    """Resolve a UI label and enforce the documented Seedream 4.5 limits."""
    size = SIZE_OPTIONS.get(size_label, str(size_label or "").strip())
    if size in {"2K", "4K"}:
        return size

    match = re.fullmatch(r"(\d+)x(\d+)", size)
    if not match:
        raise ValueError(f"不支持的尺寸：{size_label}")

    width, height = (int(value) for value in match.groups())
    pixels = width * height
    ratio = width / height
    if not MIN_PIXELS <= pixels <= MAX_PIXELS:
        raise ValueError(
            f"尺寸 {size} 的总像素必须在 {MIN_PIXELS} 到 {MAX_PIXELS} 之间"
        )
    if not MIN_ASPECT_RATIO <= ratio <= MAX_ASPECT_RATIO:
        raise ValueError(f"尺寸 {size} 的宽高比必须在 1:16 到 16:1 之间")
    return size


def resolve_output_size(size: str, ratio: str) -> str:
    if size not in SIZE_LEVELS:
        # Accept the single-size values saved by the first node version.
        return resolve_size(size)
    allowed_ratios = RATIO_OPTIONS_BY_SIZE[size]
    if ratio not in allowed_ratios:
        raise ValueError(f"{size} 不支持该 ratio：{ratio}")
    return resolve_size(ratio)


def build_payload(
    prompt: str,
    size: str,
    ratio: str,
    watermark: bool,
    response_format: str,
) -> dict:
    if response_format not in RESPONSE_FORMATS:
        raise ValueError(f"不支持的返回格式：{response_format}")
    return {
        "model": MODEL,
        "prompt": prompt,
        "size": resolve_output_size(size, ratio),
        "sequential_image_generation": "disabled",
        "stream": False,
        "response_format": response_format,
        "watermark": bool(watermark),
    }


class LLDoubaoSeedream45TextToImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "必填，支持中文或英文的图像生成提示词",
                    },
                ),
                "size": (
                    SIZE_LEVELS,
                    {
                        "default": "2K",
                        "tooltip": "选择 2K 或 4K 分辨率档位",
                    },
                ),
                "watermark": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "开启后在右下角添加“AI生成”水印",
                    },
                ),
                "response_format": (
                    RESPONSE_FORMATS,
                    {
                        "default": "url",
                        "tooltip": "url 链接有效期为 24 小时；也可直接返回 Base64",
                    },
                ),
                "api_key": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "LLAI API 密钥；留空时读取环境变量 KUAI_API_KEY",
                    },
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
            },
            "optional": {
                "timeout": (
                    "INT",
                    {
                        "default": 1800,
                        "min": 30,
                        "max": 9999,
                        "tooltip": "等待接口响应的最长秒数",
                    },
                ),
                "ratio": (
                    ALL_RATIO_OPTIONS,
                    {
                        "default": RATIO_OPTIONS_2K[0],
                        "tooltip": "根据 size 档位显示对应的输出尺寸",
                    },
                ),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "图片结果", "响应摘要")
    FUNCTION = "generate"
    CATEGORY = "LLAI/Doubao"

    def generate(
        self,
        prompt,
        size,
        watermark,
        response_format,
        api_key,
        seed,
        timeout=1800,
        ratio=RATIO_OPTIONS_2K[0],
    ):
        _ = seed
        prompt = str(prompt or "").strip()
        if not prompt:
            raise ValueError("提示词不能为空")

        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点中填写或设置环境变量 KUAI_API_KEY")

        payload = build_payload(prompt, size, ratio, watermark, response_format)
        headers = http_headers_auth_only(api_key)
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})

        session = requests.Session()
        session.trust_env = False
        try:
            response = session.post(
                ENDPOINT,
                json=payload,
                headers=headers,
                timeout=(30, int(timeout)),
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"[LLAI] Doubao Seedream 4.5 请求失败：{exc}") from exc

        raise_for_bad_status(response, "Doubao Seedream 4.5 文生图失败")
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Doubao Seedream 4.5 返回了非 JSON 响应") from exc

        outputs = _extract_image_outputs(data, fallback_format="jpeg")
        image, _ = _outputs_to_tensor_and_refs(outputs, int(timeout))
        refs = [
            item["value"] if item["source"] == "url" else f"<{item['source']} omitted>"
            for item in outputs
        ]
        print(f"[LLAI] Doubao Seedream 4.5 文生图完成，生成 {len(outputs)} 张图像")
        return (image, "\n".join(refs), _summarize_response(data))
