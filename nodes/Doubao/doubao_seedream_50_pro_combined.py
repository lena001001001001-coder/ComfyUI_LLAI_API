"""Combined LLAI Doubao Seedream 5.0 Pro text-to-image and image-to-image node."""

from .doubao_seedream_50_pro import (
    ALL_RATIO_OPTIONS,
    RATIO_OPTIONS_2K,
    RESPONSE_FORMATS,
    SIZE_LEVELS,
    LLDoubaoSeedream50ProTextToImage,
)
from .doubao_seedream_50_pro_i2i import MAX_IMAGES, LLDoubaoSeedream50ProImageToImage


REFERENCE_IMAGE_KEYS = [f"参考图{i}" for i in range(1, MAX_IMAGES + 1)]


class LLDoubaoSeedream50Pro:
    """Use text-to-image unless at least one optional reference image is connected."""

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
                        "tooltip": "Seedream 5.0 Pro 官方分辨率档位：1K、1.5K、2K",
                    },
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
                        "tooltip": "用于控制 ComfyUI 是否重新执行生成；接口请求不发送 seed 字段",
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
        watermark,
        response_format,
        api_key,
        seed,
        ratio=None,
        timeout=1800,
        **kwargs,
    ):
        connected = [
            (name, kwargs.get(name))
            for name in REFERENCE_IMAGE_KEYS
            if kwargs.get(name) is not None
        ]
        selected_ratio = ratio or RATIO_OPTIONS_2K[0]

        if not connected:
            return LLDoubaoSeedream50ProTextToImage().generate(
                prompt=prompt,
                size=size,
                watermark=watermark,
                response_format=response_format,
                api_key=api_key,
                seed=seed,
                ratio=selected_ratio,
                timeout=timeout,
            )

        _, first_image = connected[0]
        remaining = {
            f"参考图{index}": image
            for index, (_, image) in enumerate(connected[1:], start=2)
        }
        print(f"[LLAI] Doubao Seedream 5.0 Pro 检测到 {len(connected)} 个参考图输入，切换为图生图")
        return LLDoubaoSeedream50ProImageToImage().generate(
            参考图1=first_image,
            prompt=prompt,
            size=size,
            ratio=selected_ratio,
            watermark=watermark,
            response_format=response_format,
            api_key=api_key,
            seed=seed,
            timeout=timeout,
            **remaining,
        )
