"""LLAI Doubao Seedream 4.0 image-to-image node."""

import base64
import io

import requests

from ..GPTImage.gpt_image import _extract_image_outputs, _outputs_to_tensor_and_refs, _summarize_response
from ..Sora2.kuai_utils import env_or, http_headers_auth_only, raise_for_bad_status, save_image_to_buffer, to_pil_from_comfy

MODEL = "doubao-seedream-4-0-250828"
ENDPOINT = "https://api.llaiapi.host/v1/images/generations"
SIZE_LEVELS = ["1K", "2K", "4K"]
SUPPORTED_SIZE_LEVELS = ["1K", "2K", "4K"]
RATIOS = {
    "1K": ["1024x1024", "1152x864", "864x1152", "1280x720", "720x1280", "1248x832", "832x1248", "1512x648"],
    "2K": ["2048x2048", "2304x1728", "1728x2304", "2848x1600", "1600x2848", "2496x1664", "1664x2496", "3136x1344"],
    "4K": ["4096x4096", "4704x3520", "3520x4704", "5504x3040", "3040x5504", "4992x3328", "3328x4992", "6240x2656"],
}
_RATIO_DESC = {
    "1024x1024": "1:1 方图", "1152x864": "4:3 横图", "864x1152": "3:4 竖图",
    "1280x720": "16:9 横图", "720x1280": "9:16 竖图", "1248x832": "3:2 横图",
    "832x1248": "2:3 竖图", "1512x648": "21:9 超宽图", "2048x2048": "1:1 方图",
    "2304x1728": "4:3 横图", "1728x2304": "3:4 竖图", "2848x1600": "16:9 横图",
    "1600x2848": "9:16 竖图", "2496x1664": "3:2 横图", "1664x2496": "2:3 竖图",
    "3136x1344": "21:9 超宽图", "4096x4096": "1:1 方图", "4704x3520": "4:3 横图",
    "3520x4704": "3:4 竖图", "5504x3040": "16:9 横图", "3040x5504": "9:16 竖图",
    "4992x3328": "3:2 横图", "3328x4992": "2:3 竖图", "6240x2656": "21:9 超宽图",
}
RATIO_LABELS = {s: [f"{v}（{_RATIO_DESC[v]}）" for v in vals] for s, vals in RATIOS.items()}
MAX_IMAGES = 14


def _size_value(size, ratio):
    if size not in SUPPORTED_SIZE_LEVELS:
        raise ValueError(f"不支持的 size: {size}")
    raw = str(ratio or "").split("（", 1)[0]
    if raw not in RATIOS[size]:
        raw = RATIOS[size][0]
    return raw


def _image_data_url(image, index=0):
    pil = to_pil_from_comfy(image, index=index)
    buf = save_image_to_buffer(pil, fmt="png", quality=95)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


class LLDoubaoSeedream40ImageToImage:
    @classmethod
    def INPUT_TYPES(cls):
        optional = {f"参考图{i}": ("IMAGE", {"tooltip": f"可选参考图 {i}"}) for i in range(2, MAX_IMAGES + 1)}
        return {"required": {
            "参考图1": ("IMAGE", {"tooltip": "必填，支持最多 14 张参考图"}),
            "prompt": ("STRING", {"multiline": True, "default": ""}),
            "size": (SIZE_LEVELS, {"default": "2K", "tooltip": "节点提供 1K、2K、4K 分辨率档位"}),
            "ratio": (RATIO_LABELS["2K"], {"default": RATIO_LABELS["2K"][0]}),
            "watermark": ("BOOLEAN", {"default": False}),
            "response_format": (["url", "b64_json"], {"default": "url"}),
            "api_key": ("STRING", {"default": ""}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "control_after_generate": True}),
        }, "optional": {**optional, "timeout": ("INT", {"default": 1800, "min": 30, "max": 9999})}}

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "图片结果", "响应摘要")
    FUNCTION = "generate"
    CATEGORY = "LLAI/Doubao"

    def generate(self, 参考图1, prompt, size, ratio, watermark, response_format, api_key, seed, timeout=1800, **kwargs):
        _ = seed
        if not str(prompt or "").strip():
            raise ValueError("提示词不能为空")
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置")
        images = []
        for name, value in [("参考图1", 参考图1)] + [(f"参考图{i}", kwargs.get(f"参考图{i}")) for i in range(2, MAX_IMAGES + 1)]:
            if value is None:
                continue
            count = int(value.shape[0]) if hasattr(value, "shape") and len(value.shape) == 4 else 1
            for idx in range(count):
                if len(images) >= MAX_IMAGES:
                    raise ValueError("Seedream 4.0 最多支持 14 张参考图")
                images.append(_image_data_url(value, idx))
        if not images:
            raise ValueError("至少需要一张参考图")
        payload = {"model": MODEL, "prompt": str(prompt).strip(), "image": images[0] if len(images) == 1 else images,
                   "size": _size_value(size, ratio), "sequential_image_generation": "disabled", "stream": False,
                   "response_format": response_format, "watermark": bool(watermark)}
        headers = http_headers_auth_only(api_key)
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        session = requests.Session(); session.trust_env = False
        try:
            response = session.post(ENDPOINT, json=payload, headers=headers, timeout=(30, int(timeout)))
        except requests.RequestException as exc:
            raise RuntimeError(f"Doubao Seedream 4.0 图生图请求失败: {exc}") from exc
        raise_for_bad_status(response, "Doubao Seedream 4.0 图生图失败")
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("接口返回了非 JSON 响应") from exc
        outputs = _extract_image_outputs(data, fallback_format="jpeg")
        image, _ = _outputs_to_tensor_and_refs(outputs, int(timeout))
        refs = [item["value"] if item["source"] == "url" else f"<{item['source']} omitted>" for item in outputs]
        return image, "\n".join(refs), _summarize_response(data)
