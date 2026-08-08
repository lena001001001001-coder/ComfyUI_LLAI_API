"""LLAI Doubao Seedream 4.5 image-to-image node."""

import base64
import io
from PIL import Image
from .doubao_seedream_40_i2i import (
    _summarize_response,
    _extract_image_outputs,
    _outputs_to_tensor_and_refs,
    env_or,
    http_headers_auth_only,
    raise_for_bad_status,
    to_pil_from_comfy,
)
import requests

MODEL = "doubao-seedream-4-5-251128"
ENDPOINT = "https://api.llaiapi.host/v1/images/generations"
SIZE_LEVELS = ["2K", "4K"]
RATIOS = {
    "2K": ["2048x2048（1:1 方图）", "2560x1440（16:9 横图）", "1440x2560（9:16 竖图）", "2304x1728（4:3 横图）", "1728x2304（3:4 竖图）", "2496x1664（3:2 横图）", "1664x2496（2:3 竖图）", "2560x1600（16:10 横图）", "1600x2560（10:16 竖图）"],
    "4K": ["3840x2160（4K 16:9 横图）", "2160x3840（4K 9:16 竖图）", "3072x2304（4K 4:3 横图）", "2304x3072（4K 3:4 竖图）", "3072x3072（4K 1:1 方图）", "4096x4096（最大方图）"],
}
MAX_IMAGES = 14


def _image_data_url_45(image, index=0):
    """Encode a reference image within Seedream's 6000px/30MB input limits."""
    pil = to_pil_from_comfy(image, index=index).convert("RGB")
    longest = max(pil.size)
    if longest > 6000:
        scale = 6000 / longest
        pil = pil.resize((max(1, round(pil.width * scale)), max(1, round(pil.height * scale))), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    pil.save(buffer, format="JPEG", quality=90, optimize=True)
    if buffer.tell() > 30 * 1024 * 1024:
        buffer = io.BytesIO()
        pil.save(buffer, format="JPEG", quality=75, optimize=True)
    if buffer.tell() > 30 * 1024 * 1024:
        raise ValueError("参考图压缩后仍超过 30MB，请使用更小的图片")
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


class LLDoubaoSeedream45ImageToImage:
    @classmethod
    def INPUT_TYPES(cls):
        optional = {f"参考图{i}": ("IMAGE", {"tooltip": f"可选参考图 {i}"}) for i in range(2, MAX_IMAGES + 1)}
        return {"required": {
            "参考图1": ("IMAGE", {"tooltip": "必填，最多 14 张参考图"}),
            "prompt": ("STRING", {"multiline": True, "default": ""}),
            "size": (SIZE_LEVELS, {"default": "2K"}),
            "ratio": (RATIOS["2K"], {"default": RATIOS["2K"][0]}),
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
        raw_ratio = str(ratio or "").split("（", 1)[0]
        if raw_ratio not in [x.split("（", 1)[0] for x in RATIOS.get(size, RATIOS["2K"] )]:
            raw_ratio = RATIOS[size][0].split("（", 1)[0]
        images = []
        for value in [参考图1] + [kwargs.get(f"参考图{i}") for i in range(2, MAX_IMAGES + 1)]:
            if value is None:
                continue
            count = int(value.shape[0]) if hasattr(value, "shape") and len(value.shape) == 4 else 1
            for idx in range(count):
                if len(images) >= MAX_IMAGES:
                    raise ValueError("Seedream 4.5 最多支持 14 张参考图")
                images.append(_image_data_url_45(value, idx))
        payload = {"model": MODEL, "prompt": str(prompt).strip(), "image": images[0] if len(images) == 1 else images,
                   "size": raw_ratio, "sequential_image_generation": "disabled", "stream": False,
                   "response_format": response_format, "watermark": bool(watermark)}
        headers = http_headers_auth_only(api_key)
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        session = requests.Session(); session.trust_env = False
        response = session.post(ENDPOINT, json=payload, headers=headers, timeout=(30, int(timeout)))
        raise_for_bad_status(response, "Doubao Seedream 4.5 图生图失败")
        data = response.json()
        outputs = _extract_image_outputs(data, fallback_format="jpeg")
        image, _ = _outputs_to_tensor_and_refs(outputs, int(timeout))
        refs = [item["value"] if item["source"] == "url" else f"<{item['source']} omitted>" for item in outputs]
        return image, "\n".join(refs), _summarize_response(data)
