"""Combined LLAI Doubao Seedream 5.0 Lite text-to-image and image-to-image node."""

import requests

from .doubao_seedream_45_i2i import _image_data_url_45
from ..GPTImage.gpt_image import (
    _extract_image_outputs,
    _outputs_to_tensor_and_refs,
    _summarize_response,
)
from ..Sora2.kuai_utils import env_or, http_headers_auth_only, raise_for_bad_status


MODEL = "doubao-seedream-5-0-260128"
ENDPOINT = "https://api.llaiapi.host/v1/images/generations"
SIZE_LEVELS = ["2K", "3K"]
OUTPUT_FORMATS = ["png", "jpeg"]
RESPONSE_FORMATS = ["url", "b64_json"]
MAX_IMAGES = 14
REFERENCE_IMAGE_KEYS = ["参考图"] + [f"参考图{i}" for i in range(2, MAX_IMAGES + 1)]

RATIO_OPTIONS_2K = [
    "2048x2048（1:1 方图）",
    "2304x1728（4:3 横图）",
    "1728x2304（3:4 竖图）",
    "2848x1600（16:9 横图）",
    "1600x2848（9:16 竖图）",
    "2496x1664（3:2 横图）",
    "1664x2496（2:3 竖图）",
    "3136x1344（21:9 超宽图）",
]
RATIO_OPTIONS_3K = [
    "3072x3072（1:1 方图）",
    "3456x2592（4:3 横图）",
    "2592x3456（3:4 竖图）",
    "4096x2304（16:9 横图）",
    "2304x4096（9:16 竖图）",
    "3744x2496（3:2 横图）",
    "2496x3744（2:3 竖图）",
    "4704x2016（21:9 超宽图）",
]
RATIO_OPTIONS_BY_SIZE = {"2K": RATIO_OPTIONS_2K, "3K": RATIO_OPTIONS_3K}
ALL_RATIO_OPTIONS = RATIO_OPTIONS_2K + RATIO_OPTIONS_3K


def resolve_output_size(size: str, ratio: str) -> str:
    if size not in SIZE_LEVELS:
        raise ValueError(f"不支持的分辨率档位：{size}")
    if ratio not in RATIO_OPTIONS_BY_SIZE[size]:
        raise ValueError(f"{size} 不支持该 ratio：{ratio}")
    return ratio.split("（", 1)[0]


def build_payload(
    prompt: str,
    size: str,
    ratio: str,
    output_format: str,
    response_format: str,
    watermark: bool,
    image=None,
) -> dict:
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"不支持的图片格式：{output_format}")
    if response_format not in RESPONSE_FORMATS:
        raise ValueError(f"不支持的返回格式：{response_format}")

    payload = {
        "model": MODEL,
        "prompt": str(prompt).strip(),
        "size": resolve_output_size(size, ratio),
        "sequential_image_generation": "disabled",
        "output_format": output_format,
        "response_format": response_format,
        "watermark": bool(watermark),
    }
    if image is not None:
        payload["image"] = image
    return payload


class LLDoubaoSeedream50Lite:
    """Generate from text, or edit with up to 14 connected reference images."""

    @classmethod
    def INPUT_TYPES(cls):
        optional_images = {
            name: (
                "IMAGE",
                {"tooltip": f"可选{name}；连接任意参考图后自动切换为图生图，最多 {MAX_IMAGES} 张"},
            )
            for name in REFERENCE_IMAGE_KEYS
        }
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "必填；无参考图时文生图，有参考图时图生图",
                    },
                ),
                "size": (
                    SIZE_LEVELS,
                    {
                        "default": "2K",
                        "tooltip": "Seedream 5.0 Lite 官方分辨率档位：2K、3K",
                    },
                ),
                "output_format": (
                    OUTPUT_FORMATS,
                    {"default": "png", "tooltip": "生成图片的文件格式"},
                ),
                "watermark": (
                    "BOOLEAN",
                    {"default": False, "tooltip": "开启后添加 AI 生成水印"},
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
                        "tooltip": "用于控制 ComfyUI 是否重新执行；接口请求不发送 seed 字段",
                    },
                ),
                "ratio": (
                    ALL_RATIO_OPTIONS,
                    {"default": RATIO_OPTIONS_2K[0], "tooltip": "根据 size 档位切换官方比例"},
                ),
            },
            "optional": {
                **optional_images,
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

    def generate(
        self,
        prompt,
        size,
        output_format,
        watermark,
        response_format,
        api_key,
        seed,
        ratio=None,
        参考图=None,
        timeout=1800,
        **kwargs,
    ):
        _ = seed
        prompt = str(prompt or "").strip()
        if not prompt:
            raise ValueError("提示词不能为空")

        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点中填写或设置环境变量 KUAI_API_KEY")

        selected_ratio = ratio or RATIO_OPTIONS_2K[0]
        images = []
        image_inputs = [参考图] + [kwargs.get(name) for name in REFERENCE_IMAGE_KEYS[1:]]
        for value in image_inputs:
            if value is None:
                continue
            batch_size = int(value.shape[0]) if hasattr(value, "shape") and len(value.shape) == 4 else 1
            for index in range(batch_size):
                if len(images) >= MAX_IMAGES:
                    raise ValueError(f"Seedream 5.0 Lite 最多支持 {MAX_IMAGES} 张参考图")
                images.append(_image_data_url_45(value, index=index))

        image_data = None
        if images:
            image_data = images[0] if len(images) == 1 else images
            print(f"[LLAI] Doubao Seedream 5.0 Lite 检测到 {len(images)} 张参考图，切换为图生图")

        payload = build_payload(
            prompt=prompt,
            size=size,
            ratio=selected_ratio,
            output_format=output_format,
            response_format=response_format,
            watermark=watermark,
            image=image_data,
        )
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
            raise RuntimeError(f"[LLAI] Doubao Seedream 5.0 Lite 请求失败：{exc}") from exc

        mode = "图生图" if image_data is not None else "文生图"
        raise_for_bad_status(response, f"Doubao Seedream 5.0 Lite {mode}失败")
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Doubao Seedream 5.0 Lite 返回了非 JSON 响应") from exc

        outputs = _extract_image_outputs(data, fallback_format=output_format)
        image, _ = _outputs_to_tensor_and_refs(outputs, int(timeout))
        refs = [
            item["value"] if item["source"] == "url" else f"<{item['source']} omitted>"
            for item in outputs
        ]
        print(f"[LLAI] Doubao Seedream 5.0 Lite {mode}完成，生成 {len(outputs)} 张图像")
        return image, "\n".join(refs), _summarize_response(data)
