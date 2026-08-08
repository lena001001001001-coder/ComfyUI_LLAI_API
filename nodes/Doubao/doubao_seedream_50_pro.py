"""LLAI Doubao Seedream 5.0 Pro text-to-image node."""

import requests

from ..GPTImage.gpt_image import (
    _extract_image_outputs,
    _outputs_to_tensor_and_refs,
    _summarize_response,
)
from ..Sora2.kuai_utils import env_or, http_headers_auth_only, raise_for_bad_status


MODEL = "doubao-seedream-5-0-pro-260628"
ENDPOINT = "https://api.llaiapi.host/v1/images/generations"
SIZE_LEVELS = ["1K", "1.5K", "2K"]
RESPONSE_FORMATS = ["url", "b64_json"]

RATIO_OPTIONS_1K = [
    "1024x1024（1:1 方图）", "1152x864（4:3 横图）", "864x1152（3:4 竖图）",
    "1424x800（16:9 横图）", "800x1424（9:16 竖图）",
    "1248x832（3:2 横图）", "832x1248（2:3 竖图）", "1568x672（21:9 超宽图）",
]
RATIO_OPTIONS_15K = [
    "1536x1536（1:1 方图）", "1792x1344（4:3 横图）", "1344x1792（3:4 竖图）",
    "2048x1152（16:9 横图）", "1152x2048（9:16 竖图）",
    "1872x1248（3:2 横图）", "1248x1872（2:3 竖图）", "2352x1008（21:9 超宽图）",
]
RATIO_OPTIONS_2K = [
    "2048x2048（1:1 方图）", "2368x1776（4:3 横图）", "1776x2368（3:4 竖图）",
    "2816x1584（16:9 横图）", "1584x2816（9:16 竖图）",
    "2496x1664（3:2 横图）", "1664x2496（2:3 竖图）", "3136x1344（21:9 超宽图）",
]
RATIO_OPTIONS_BY_SIZE = {"1K": RATIO_OPTIONS_1K, "1.5K": RATIO_OPTIONS_15K, "2K": RATIO_OPTIONS_2K}
ALL_RATIO_OPTIONS = RATIO_OPTIONS_1K + RATIO_OPTIONS_15K + RATIO_OPTIONS_2K

RATIO_PROMPTS = {
    "1:1": "1:1 比例的正方形图片",
    "4:3": "4:3 比例的横向图片",
    "3:4": "3:4 比例的竖向图片",
    "16:9": "16:9 比例的横向图片",
    "9:16": "9:16 比例的竖向图片",
    "3:2": "3:2 比例的横向图片",
    "2:3": "2:3 比例的竖向图片",
    "21:9": "21:9 比例的超宽横向图片",
}


def _ratio_text(ratio: str) -> str:
    value = str(ratio or "")
    if "（" in value:
        return value.split("（", 1)[1].split(" ", 1)[0]
    return value


def _resolve_ratio(size: str, ratio: str) -> str:
    options = RATIO_OPTIONS_BY_SIZE.get(size)
    if size not in SIZE_LEVELS:
        raise ValueError(f"不支持的分辨率档位：{size}")
    if ratio not in options:
        raise ValueError(f"{size} 不支持该 ratio：{ratio}")
    return _ratio_text(ratio)


def build_payload(prompt: str, size: str, ratio: str, watermark: bool, response_format: str) -> dict:
    if response_format not in RESPONSE_FORMATS:
        raise ValueError(f"不支持的返回格式：{response_format}")
    ratio_key = _resolve_ratio(size, ratio)
    ratio_prompt = RATIO_PROMPTS.get(ratio_key, ratio_key)
    return {
        "model": MODEL,
        "prompt": f"{str(prompt).rstrip()}\n\n构图要求：请生成 {ratio_prompt}。",
        "size": size,
        "response_format": response_format,
        "watermark": bool(watermark),
    }


class LLDoubaoSeedream50ProTextToImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "必填，支持中文或英文提示词"}),
                "size": (SIZE_LEVELS, {"default": "2K", "tooltip": "Seedream 5.0 Pro 官方分辨率档位：1K、1.5K、2K"}),
                "watermark": ("BOOLEAN", {"default": False, "tooltip": "开启后添加 AI 生成水印"}),
                "response_format": (RESPONSE_FORMATS, {"default": "url", "tooltip": "url 或 b64_json；该项在节点上隐藏"}),
                "api_key": ("STRING", {"default": "", "tooltip": "LLAI API 密钥；留空时读取 KUAI_API_KEY"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "control_after_generate": True, "tooltip": "仅控制 ComfyUI 执行，不发送给接口"}),
                "ratio": (ALL_RATIO_OPTIONS, {"default": RATIO_OPTIONS_2K[0], "tooltip": "根据 size 档位切换官方比例"}),
            },
            "optional": {"timeout": ("INT", {"default": 1800, "min": 30, "max": 9999})},
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "图片结果", "响应摘要")
    FUNCTION = "generate"
    CATEGORY = "LLAI/Doubao"

    def generate(self, prompt, size, watermark, response_format, api_key, seed, ratio, timeout=1800):
        _ = seed
        prompt = str(prompt or "").strip()
        if not prompt:
            raise ValueError("提示词不能为空")
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点中填写或设置环境变量 KUAI_API_KEY")
        payload = build_payload(prompt, size, ratio, watermark, response_format)
        print(f"[LLAI] Doubao Seedream 5.0 Pro size={size}, ratio={ratio}")
        headers = http_headers_auth_only(api_key)
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        session = requests.Session()
        session.trust_env = False
        try:
            response = session.post(ENDPOINT, json=payload, headers=headers, timeout=(30, int(timeout)))
        except requests.RequestException as exc:
            raise RuntimeError(f"[LLAI] Doubao Seedream 5.0 Pro 请求失败：{exc}") from exc
        raise_for_bad_status(response, "Doubao Seedream 5.0 Pro 文生图失败")
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Doubao Seedream 5.0 Pro 返回了非 JSON 响应") from exc
        outputs = _extract_image_outputs(data, fallback_format="jpeg")
        image, _ = _outputs_to_tensor_and_refs(outputs, int(timeout))
        refs = [item["value"] if item["source"] == "url" else f"<{item['source']} omitted>" for item in outputs]
        print(f"[LLAI] Doubao Seedream 5.0 Pro 文生图完成，生成 {len(outputs)} 张图像")
        return (image, "\n".join(refs), _summarize_response(data))
