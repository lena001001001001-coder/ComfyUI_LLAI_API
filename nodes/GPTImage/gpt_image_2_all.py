"""gpt-image-2-all 节点"""

import io
import json

import numpy as np
import requests
import torch
from PIL import Image

from ..Sora2.kuai_utils import env_or, http_headers_auth_only, raise_for_bad_status

MODELS = ["gpt-image-2-all"]
SIZES = ["1024x1024", "1536x1024", "1024x1536"]


def _extract_generation_result(payload: dict):
    """从 API 响应中提取图片 URL 列表"""
    items = payload.get("data") or []
    urls = [item.get("url", "").strip() for item in items if item.get("url")]
    if not urls:
        raise RuntimeError(f"响应中没有图像URL: {json.dumps(payload, ensure_ascii=False)}")
    return urls


def _url_to_tensor(url: str, timeout: int) -> torch.Tensor:
    """从 URL 下载图片并转换为 ComfyUI IMAGE tensor"""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    pil = Image.open(io.BytesIO(resp.content)).convert("RGB")
    arr = np.array(pil).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]


# 中文参数键 -> 内部变量名
K_PROMPT = "提示词"
K_MODEL = "模型"
K_SIZE = "图像尺寸"
K_N = "生成数量"
K_API_KEY = "API密钥"
K_API_BASE = "API地址"
K_TIMEOUT = "超时秒数"
K_IMAGE_URL = [
    "图片URL1",
    "图片URL2",
    "图片URL3",
    "图片URL4",
    "图片URL5",
]


class GPTImage2AllGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                K_PROMPT: ("STRING", {"multiline": True, "default": "", "tooltip": "图像描述提示词"}),
                K_MODEL: (MODELS, {"default": "gpt-image-2-all", "tooltip": "模型选择"}),
                K_SIZE: (SIZES, {"default": "1024x1024", "tooltip": "输出图像尺寸"}),
                K_N: ("INT", {"default": 1, "min": 1, "max": 10, "tooltip": "生成数量"}),
                K_API_KEY: ("STRING", {"default": "", "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"}),
            },
            "optional": {
                K_API_BASE: ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API服务器地址"}),
                K_TIMEOUT: ("INT", {"default": 120, "min": 1, "max": 1800, "tooltip": "超时时间(秒)"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("图像", "图片URL", "revised_prompt", "原始响应")
    FUNCTION = "generate"
    CATEGORY = "KuAi/GPTImage"

    def generate(self, **kwargs):
        prompt = kwargs.get(K_PROMPT, "")
        model = kwargs.get(K_MODEL, "gpt-image-2-all")
        size = kwargs.get(K_SIZE, "1024x1024")
        n = kwargs.get(K_N, 1)
        api_key = kwargs.get(K_API_KEY, "")
        api_base = kwargs.get(K_API_BASE, "https://api.llaiapi.host")
        timeout = kwargs.get(K_TIMEOUT, 120)

        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置")
        if not prompt.strip():
            raise RuntimeError("提示词不能为空")

        payload = {
            "model": model,
            "size": size,
            "n": n,
            "prompt": prompt,
        }
        resp = requests.post(
            f"{api_base.rstrip('/')}/v1/images/generations",
            json=payload,
            headers=http_headers_auth_only(api_key),
            timeout=timeout,
        )
        raise_for_bad_status(resp, "gpt-image-2-all生图失败")
        data = resp.json()

        urls = _extract_generation_result(data)
        revised = [str(item.get("revised_prompt", "")) for item in (data.get("data") or [])]
        raw = json.dumps(data, ensure_ascii=False)
        image = torch.cat([_url_to_tensor(url, timeout) for url in urls], dim=0)
        return (image, "\n".join(urls), "\n".join(revised), raw)


class GPTImage2AllEdit:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                K_IMAGE_URL[0]: ("STRING", {"default": "", "tooltip": "第1张图片URL"}),
                K_PROMPT: ("STRING", {"multiline": True, "default": "", "tooltip": "图像编辑提示词"}),
                K_MODEL: (MODELS, {"default": "gpt-image-2-all", "tooltip": "模型选择"}),
                K_SIZE: (SIZES, {"default": "1024x1024", "tooltip": "输出图像尺寸"}),
                K_N: ("INT", {"default": 1, "min": 1, "max": 10, "tooltip": "生成数量"}),
                K_API_KEY: ("STRING", {"default": "", "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"}),
            },
            "optional": {
                K_IMAGE_URL[1]: ("STRING", {"default": "", "tooltip": "第2张图片URL"}),
                K_IMAGE_URL[2]: ("STRING", {"default": "", "tooltip": "第3张图片URL"}),
                K_IMAGE_URL[3]: ("STRING", {"default": "", "tooltip": "第4张图片URL"}),
                K_IMAGE_URL[4]: ("STRING", {"default": "", "tooltip": "第5张图片URL"}),
                K_API_BASE: ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API服务器地址"}),
                K_TIMEOUT: ("INT", {"default": 120, "min": 1, "max": 1800, "tooltip": "超时时间(秒)"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("图像", "图片URL", "revised_prompt", "原始响应")
    FUNCTION = "edit"
    CATEGORY = "KuAi/GPTImage"

    def edit(self, **kwargs):
        prompt = kwargs.get(K_PROMPT, "")
        model = kwargs.get(K_MODEL, "gpt-image-2-all")
        size = kwargs.get(K_SIZE, "1024x1024")
        n = kwargs.get(K_N, 1)
        api_key = kwargs.get(K_API_KEY, "")
        api_base = kwargs.get(K_API_BASE, "https://api.llaiapi.host")
        timeout = kwargs.get(K_TIMEOUT, 120)

        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置")
        urls_in = [str(kwargs.get(key, "")).strip() for key in K_IMAGE_URL]
        image_urls = [url for url in urls_in if url]
        if not image_urls:
            raise RuntimeError("至少需要提供一张图片URL")
        if not prompt.strip():
            raise RuntimeError("提示词不能为空")

        payload = {
            "model": model,
            "size": size,
            "n": n,
            "prompt": prompt,
            "image": image_urls,
        }
        resp = requests.post(
            f"{api_base.rstrip('/')}/v1/images/generations",
            json=payload,
            headers=http_headers_auth_only(api_key),
            timeout=timeout,
        )
        raise_for_bad_status(resp, "gpt-image-2-all编辑图失败")
        data = resp.json()

        urls = _extract_generation_result(data)
        revised = [str(item.get("revised_prompt", "")) for item in (data.get("data") or [])]
        raw = json.dumps(data, ensure_ascii=False)
        image = torch.cat([_url_to_tensor(url, timeout) for url in urls], dim=0)
        return (image, "\n".join(urls), "\n".join(revised), raw)
