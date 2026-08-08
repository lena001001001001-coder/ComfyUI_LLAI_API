"""LLAI Doubao Seedream 5.0 Pro image-to-image node."""
import requests
from .doubao_seedream_45_i2i import _image_data_url_45
from ..GPTImage.gpt_image import _extract_image_outputs, _outputs_to_tensor_and_refs, _summarize_response
from ..Sora2.kuai_utils import env_or, http_headers_auth_only, raise_for_bad_status

MODEL = "doubao-seedream-5-0-pro-260628"
ENDPOINT = "https://api.llaiapi.host/v1/images/generations"
SIZE_LEVELS = ["1K", "1.5K", "2K"]
RATIOS = {
    "1K": ["1024x1024（1:1 方图）", "1152x864（4:3 横图）", "864x1152（3:4 竖图）", "1424x800（16:9 横图）", "800x1424（9:16 竖图）", "1248x832（3:2 横图）", "832x1248（2:3 竖图）", "1568x672（21:9 超宽图）"],
    "1.5K": ["1536x1536（1:1 方图）", "1792x1344（4:3 横图）", "1344x1792（3:4 竖图）", "2048x1152（16:9 横图）", "1152x2048（9:16 竖图）", "1872x1248（3:2 横图）", "1248x1872（2:3 竖图）", "2352x1008（21:9 超宽图）"],
    "2K": ["2048x2048（1:1 方图）", "2368x1776（4:3 横图）", "1776x2368（3:4 竖图）", "2816x1584（16:9 横图）", "1584x2816（9:16 竖图）", "2496x1664（3:2 横图）", "1664x2496（2:3 竖图）", "3136x1344（21:9 超宽图）"],
}
MAX_IMAGES = 10

class LLDoubaoSeedream50ProImageToImage:
    @classmethod
    def INPUT_TYPES(cls):
        optional = {f"参考图{i}": ("IMAGE", {"tooltip": f"可选参考图 {i}"}) for i in range(2, MAX_IMAGES + 1)}
        return {"required": {"参考图1": ("IMAGE", {"tooltip": "必填，最多 10 张参考图"}), "prompt": ("STRING", {"multiline": True, "default": ""}), "size": (SIZE_LEVELS, {"default": "2K"}), "ratio": (RATIOS["2K"], {"default": RATIOS["2K"][0]}), "watermark": ("BOOLEAN", {"default": False}), "response_format": (["url", "b64_json"], {"default": "url"}), "api_key": ("STRING", {"default": ""}), "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "control_after_generate": True})}, "optional": {**optional, "timeout": ("INT", {"default": 1800, "min": 30, "max": 9999})}}
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "图片结果", "响应摘要")
    FUNCTION = "generate"
    CATEGORY = "LLAI/Doubao"

    def generate(self, 参考图1, prompt, size, ratio, watermark, response_format, api_key, seed, timeout=1800, **kwargs):
        _ = seed
        if not str(prompt or "").strip(): raise ValueError("提示词不能为空")
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key: raise RuntimeError("API Key 未配置")
        valid = {x.split("（", 1)[0] for x in RATIOS[size]}
        raw_ratio = str(ratio or "").split("（", 1)[0]
        if raw_ratio not in valid: raw_ratio = next(iter(valid))
        images = []
        for value in [参考图1] + [kwargs.get(f"参考图{i}") for i in range(2, MAX_IMAGES + 1)]:
            if value is None: continue
            count = int(value.shape[0]) if hasattr(value, "shape") and len(value.shape) == 4 else 1
            for idx in range(count):
                if len(images) >= MAX_IMAGES: raise ValueError("Seedream 5.0 Pro 最多支持 10 张参考图")
                images.append(_image_data_url_45(value, idx))
        # 5.0 Pro accepts resolution tiers; preserve the selected ratio in natural-language prompt guidance.
        ratio_hint = f"\n\n构图要求：生成 {raw_ratio.split('x')[0]}:{raw_ratio.split('x')[1]} 比例的图片。"
        payload = {"model": MODEL, "prompt": str(prompt).strip() + ratio_hint, "image": images[0] if len(images) == 1 else images, "size": size, "response_format": response_format, "watermark": bool(watermark)}
        headers = http_headers_auth_only(api_key); headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        session = requests.Session(); session.trust_env = False
        response = session.post(ENDPOINT, json=payload, headers=headers, timeout=(30, int(timeout)))
        raise_for_bad_status(response, "Doubao Seedream 5.0 Pro 图生图失败")
        data = response.json(); outputs = _extract_image_outputs(data, fallback_format="jpeg")
        image, _ = _outputs_to_tensor_and_refs(outputs, int(timeout))
        refs = [item["value"] if item["source"] == "url" else f"<{item['source']} omitted>" for item in outputs]
        return image, "\n".join(refs), _summarize_response(data)
