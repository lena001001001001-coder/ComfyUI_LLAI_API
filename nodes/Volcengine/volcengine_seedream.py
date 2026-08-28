"""Direct Volcengine Ark Seedream image generation node."""

import base64
import io
import re
import requests
import torch
from PIL import Image

from ..GPTImage.gpt_image import _extract_image_outputs, _outputs_to_tensor_and_refs, _summarize_response
from ..Sora2.kuai_utils import http_headers_auth_only, to_pil_from_comfy

ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
MAX_IMAGE_BYTES = 30 * 1024 * 1024

MODEL_LABELS = {
    "Doubao-Seedream-4.0": "doubao-seedream-4-0-250828",
    "Doubao-Seedream-4.5": "doubao-seedream-4-5-251128",
    "Doubao-Seedream-5.0-lite": "doubao-seedream-5-0-lite-260128",
    "Doubao-Seedream-5.0-pro": "doubao-seedream-5-0-pro-260628",
}
MODEL_IDS = {value: value for value in MODEL_LABELS.values()}
MODEL_IDS.update(MODEL_LABELS)
MODEL_IDS["Doubao-Seedream-5.0-lite 260128"] = "doubao-seedream-5-0-lite-260128"

RATIOS = ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9", "9:21"]
SIZES = {
    "doubao-seedream-4-0-250828": {"1K": {"1:1": "1024x1024", "4:3": "1152x864", "3:4": "864x1152", "16:9": "1280x720", "9:16": "720x1280", "3:2": "1248x832", "2:3": "832x1248", "21:9": "1512x648", "9:21": "648x1512"}, "2K": {"1:1": "2048x2048", "4:3": "2304x1728", "3:4": "1728x2304", "16:9": "2848x1600", "9:16": "1600x2848", "3:2": "2496x1664", "2:3": "1664x2496", "21:9": "3136x1344", "9:21": "1344x3136"}, "4K": {"1:1": "4096x4096", "4:3": "4704x3520", "3:4": "3520x4704", "16:9": "5504x3040", "9:16": "3040x5504", "3:2": "4992x3328", "2:3": "3328x4992", "21:9": "6240x2656", "9:21": "2656x6240"}},
    "doubao-seedream-4-5-251128": {"2K": {"1:1": "2048x2048", "4:3": "2304x1728", "3:4": "1728x2304", "16:9": "2848x1600", "9:16": "1600x2848", "3:2": "2496x1664", "2:3": "1664x2496", "21:9": "3136x1344", "9:21": "1344x3136"}, "4K": {"1:1": "4096x4096", "4:3": "4704x3520", "3:4": "3520x4704", "16:9": "5504x3040", "9:16": "3040x5504", "3:2": "4992x3328", "2:3": "3328x4992", "21:9": "6240x2656", "9:21": "2656x6240"}},
    "doubao-seedream-5-0-lite-260128": {"2K": {"1:1": "2048x2048", "4:3": "2304x1728", "3:4": "1728x2304", "16:9": "2848x1600", "9:16": "1600x2848", "3:2": "2496x1664", "2:3": "1664x2496", "21:9": "3136x1344", "9:21": "1344x3136"}, "3K": {"1:1": "3072x3072", "4:3": "3456x2592", "3:4": "2592x3456", "16:9": "4096x2304", "9:16": "2304x4096", "3:2": "3744x2496", "2:3": "2496x3744", "21:9": "4704x2016", "9:21": "2016x4704"}, "4K": {"1:1": "4096x4096", "4:3": "4704x3520", "3:4": "3520x4704", "16:9": "5504x3040", "9:16": "3040x5504", "3:2": "4992x3328", "2:3": "3328x4992", "21:9": "6240x2656", "9:21": "2656x6240"}},
    "doubao-seedream-5-0-pro-260628": {"1K": {"1:1": "1024x1024", "4:3": "1152x864", "3:4": "864x1152", "16:9": "1424x800", "9:16": "800x1424", "3:2": "1248x832", "2:3": "832x1248", "21:9": "1568x672", "9:21": "672x1568"}, "1.5K": {"1:1": "1536x1536", "4:3": "1792x1344", "3:4": "1344x1792", "16:9": "2048x1152", "9:16": "1152x2048", "3:2": "1872x1248", "2:3": "1248x1872", "21:9": "2352x1008", "9:21": "1008x2352"}, "2K": {"1:1": "2048x2048", "4:3": "2368x1776", "3:4": "1776x2368", "16:9": "2816x1584", "9:16": "1584x2816", "3:2": "2496x1664", "2:3": "1664x2496", "21:9": "3136x1344", "9:21": "1344x3136"}},
}
MAX_IMAGES = {model: (10 if "5-0-pro" in model else 14) for model in SIZES}
IMAGE_INPUT_NAMES = ["image"] + [f"image_{index}" for index in range(2, 15)]

CONTENT_REVIEW_MESSAGES = {
    "InputImageSensitiveContentDetected": "触发火山方舟内容审核：输入参考图可能包含敏感内容，请更换或调整图片",
    "InputTextSensitiveContentDetected": "触发火山方舟内容审核：Prompt 可能包含敏感内容，请修改提示词",
    "OutputImageSensitiveContentDetected": "触发火山方舟内容审核：生成结果可能包含敏感内容，本次未返回图片",
}


def _model_id(value):
    model = MODEL_IDS.get(value, value)
    if model not in SIZES:
        raise ValueError(f"不支持的火山方舟模型：{value}")
    return model


def _raise_for_volcengine_error(response):
    if int(getattr(response, "status_code", 0)) < 400:
        return

    try:
        body = response.json()
    except (TypeError, ValueError):
        body = None
    error = body.get("error", {}) if isinstance(body, dict) else {}
    code = str(error.get("code") or "").strip() if isinstance(error, dict) else ""
    message = str(error.get("message") or "").strip() if isinstance(error, dict) else ""
    request_id_match = re.search(r"request\s*id\s*:\s*([A-Za-z0-9_-]+)", message, re.IGNORECASE)
    request_id = request_id_match.group(1) if request_id_match else ""

    chinese = CONTENT_REVIEW_MESSAGES.get(code)
    if not chinese and ("sensitive" in code.lower() or "sensitive" in message.lower()):
        chinese = "触发火山方舟内容审核：请求内容可能包含敏感信息，请调整 Prompt 或参考图"
    if chinese:
        details = [f"错误码：{code}"] if code else []
        if request_id:
            details.append(f"Request ID：{request_id}")
        suffix = f"（{'；'.join(details)}）" if details else ""
        raise RuntimeError(chinese + suffix)

    official = message or getattr(response, "text", "") or "未知错误"
    code_text = f"，错误码：{code}" if code else ""
    raise RuntimeError(f"火山方舟图片生成失败（HTTP {response.status_code}{code_text}）：{official}")


def resolve_size(model, resolution, ratio):
    model = _model_id(model)
    try:
        return SIZES[model][resolution][ratio]
    except KeyError as exc:
        raise ValueError(f"模型 {model} 不支持 {resolution} / {ratio}") from exc


def _image_data_url(image, index):
    pil = to_pil_from_comfy(image, index=index)
    width, height = pil.size
    if width <= 14 or height <= 14:
        raise ValueError("火山方舟参考图宽度和高度必须大于 14px")
    if not 1 / 16 <= width / height <= 16:
        raise ValueError("火山方舟参考图宽高比必须在 1:16 到 16:1 之间")
    if max(pil.size) > 6000:
        scale = 6000 / max(pil.size)
        pil = pil.resize(
            (max(1, round(pil.width * scale)), max(1, round(pil.height * scale))),
            Image.Resampling.LANCZOS,
        )
    if pil.width * pil.height > 36_000_000:
        raise ValueError("火山方舟参考图总像素不能超过 3600 万")
    output = io.BytesIO()
    pil.save(output, format="PNG", optimize=True)
    if output.tell() > MAX_IMAGE_BYTES:
        raise ValueError("[火山方舟] 火山限制单图不超过 30MB，请缩放图像比例或尺寸")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def build_payload(model, prompt, resolution, ratio, images=None):
    model_id = _model_id(model)
    payload = {"model": model_id, "prompt": str(prompt).strip(), "size": resolve_size(model_id, resolution, ratio), "response_format": "b64_json", "watermark": False}
    if model_id != "doubao-seedream-5-0-pro-260628":
        payload.update({"sequential_image_generation": "disabled", "stream": False})
    if images:
        payload["image"] = images[0] if len(images) == 1 else images
    return payload


class LLVolcengineSeedream:
    @classmethod
    def INPUT_TYPES(cls):
        image_inputs = {
            name: (
                "IMAGE",
                {"tooltip": f"可选参考图 {index}；连接任意参考图后自动切换为图生图"},
            )
            for index, name in enumerate(IMAGE_INPUT_NAMES, start=1)
        }
        return {"required": {
            "api_key": (
                "STRING",
                {
                    "default": "",
                    "placeholder": "ark-...",
                    "tooltip": "火山方舟 API Key",
                },
            ),
            "model": (list(MODEL_LABELS), {"default": "Doubao-Seedream-4.5"}),
            "ratio": (RATIOS, {"default": "1:1"}),
            "resolution": (["1K", "1.5K", "2K", "3K", "4K"], {"default": "2K"}),
            "prompt": ("STRING", {"multiline": True, "default": ""}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "control_after_generate": True, "tooltip": "仅控制 ComfyUI 重执行，不发送给火山接口"}),
        }, "optional": {
            **image_inputs,
            "timeout": ("INT", {"default": 1800, "min": 30, "max": 9999}),
        }}

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("图像", "响应摘要")
    FUNCTION = "generate"
    CATEGORY = "LLAI/火山方舟"

    def generate(self, api_key, model, resolution, ratio, prompt, seed, image=None, timeout=1800, **kwargs):
        _ = seed
        if not str(api_key or "").strip():
            raise RuntimeError("火山方舟 API Key 未配置")
        if not str(prompt or "").strip():
            raise ValueError("Prompt 不能为空")
        model_id = _model_id(model)
        image_values = [image] + [kwargs.get(name) for name in IMAGE_INPUT_NAMES[1:]]
        connected = []
        for value in image_values:
            if value is None:
                continue
            count = int(value.shape[0]) if isinstance(value, torch.Tensor) and value.dim() == 4 else 1
            connected.extend((value, index) for index in range(count))
        max_images = MAX_IMAGES[model_id]
        if len(connected) > max_images:
            raise ValueError(f"{model_id} 最多支持 {max_images} 张参考图，当前为 {len(connected)} 张")
        refs = [_image_data_url(value, index) for value, index in connected]
        payload = build_payload(model_id, prompt, resolution, ratio, refs)
        headers = http_headers_auth_only(api_key)
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        session = requests.Session()
        session.trust_env = False
        try:
            response = session.post(ENDPOINT, json=payload, headers=headers, timeout=(30, int(timeout)))
        except requests.RequestException as exc:
            raise RuntimeError(f"火山方舟请求失败：{exc}") from exc
        _raise_for_volcengine_error(response)
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("火山方舟返回了非 JSON 响应") from exc
        outputs = _extract_image_outputs(data, fallback_format="jpeg")
        tensor, _ = _outputs_to_tensor_and_refs(outputs, int(timeout))
        return tensor, _summarize_response(data)
