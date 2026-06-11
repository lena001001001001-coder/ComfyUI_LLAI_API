import os
import io
import base64
import typing
import numpy as np
import requests
from PIL import Image

def env_or(value: str, env_name: str) -> str:
    """优先使用参数，其次使用环境变量"""
    if value and str(value).strip():
        return value
    return os.environ.get(env_name, "").strip()

def to_pil_from_comfy(image_any, index: int = 0) -> Image.Image:
    """将 ComfyUI IMAGE 转换为 PIL.Image"""
    try:
        import torch
        is_torch = True
    except Exception:
        is_torch = False

    arr = image_any
    if is_torch:
        import torch
        if isinstance(arr, torch.Tensor):
            if arr.dim() == 4:
                arr = arr[index]
            arr = arr.detach().cpu().numpy()

    if isinstance(arr, np.ndarray):
        if arr.ndim == 4:
            arr = arr[index]
        if arr.dtype != np.uint8:
            arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
        if arr.ndim == 3 and arr.shape[2] in (1, 3, 4):
            if arr.shape[2] == 1:
                arr = np.repeat(arr, 3, axis=2)
            return Image.fromarray(arr)
        return Image.fromarray(arr)

    if isinstance(arr, Image.Image):
        return arr

    raise ValueError("无法将输入转换为 PIL.Image")

def save_image_to_buffer(pil: Image.Image, fmt: str, quality: int) -> io.BytesIO:
    """保存 PIL 到内存缓冲"""
    fmt = fmt.lower().strip()
    buf = io.BytesIO()
    if fmt == "jpeg":
        pil = pil.convert("RGB")
        pil.save(buf, format="JPEG", quality=int(quality), optimize=True)
    elif fmt == "png":
        pil.save(buf, format="PNG", optimize=True)
    elif fmt == "webp":
        pil = pil.convert("RGB")
        pil.save(buf, format="WEBP", quality=int(quality), method=6)
    else:
        raise ValueError(f"不支持的图片格式: {fmt}")
    buf.seek(0)
    return buf

def pil_to_base64(pil: Image.Image, fmt: str = "PNG", quality: int = 95) -> str:
    """将 PIL 图像转换为 base64 字符串"""
    buf = save_image_to_buffer(pil, fmt, quality)
    return base64.b64encode(buf.read()).decode('utf-8')

def file_to_base64(file_path: str) -> str:
    """将文件转换为 base64 字符串（支持图片、视频、音频等）"""
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_gemini_text_from_response(data: dict) -> str:
    """从 Gemini API 响应中提取文本内容

    Args:
        data: Gemini API 返回的 JSON 数据

    Returns:
        提取的文本内容，如果没有文本则返回 finishReason
    """
    try:
        candidates = data.get("candidates", []) if isinstance(data, dict) else []
        if not candidates:
            return ""

        candidate = candidates[0] or {}
        content = candidate.get("content", {}) if isinstance(candidate, dict) else {}
        parts = content.get("parts", []) if isinstance(content, dict) else []

        texts = []
        for part in parts:
            if isinstance(part, dict) and "text" in part:
                text = str(part.get("text", "")).strip()
                if text:
                    texts.append(text)

        if texts:
            return "\n".join(texts)

        # 回退：返回 finishReason（用于调试）
        finish_reason = str(candidate.get("finishReason", "")).strip()
        return finish_reason
    except Exception:
        return ""


def ensure_list_from_urls(urls_str: str) -> typing.List[str]:
    """将分隔的 URL 字符串拆分为列表"""
    if isinstance(urls_str, list):
        return [u for u in urls_str if str(u).strip()]
    if not isinstance(urls_str, str):
        urls_str = str(urls_str or "")
    parts = [p.strip() for p in urls_str.replace(";", ",").replace("\n", ",").split(",")]
    return [p for p in parts if p]

def http_headers_json(api_key: str = "") -> dict:
    headers = {"Accept": "application/json", "Content-Type": "application/json; charset=utf-8"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    return headers

def http_headers_auth_only(api_key: str = "") -> dict:
    """仅包含认证头，用于 requests.post(..., json=payload) 时避免编码冲突"""
    headers = {}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    return headers

def http_headers_multipart(api_key: str = "") -> dict:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    return headers

def raise_for_bad_status(resp: requests.Response, hint: str = ""):
    try:
        resp.raise_for_status()
    except Exception as e:
        text = ""
        try:
            text = resp.text
        except Exception:
            pass
        raise RuntimeError(f"{hint} HTTP {resp.status_code} {str(e)}: {text}")

def json_get(d: dict, path: str, default=None):
    """简易 JSON path 提取"""
    cur = d
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _first_non_empty(*values):
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def extract_error_message_from_json(data):
    if not isinstance(data, dict):
        return ""

    error = data.get("error")
    if isinstance(error, dict):
        msg = _first_non_empty(
            error.get("message"),
            error.get("msg"),
            error.get("detail"),
            error.get("reason"),
            error.get("error"),
        )
        if msg:
            return msg

    msg = _first_non_empty(
        data.get("message"),
        data.get("msg"),
        data.get("detail"),
        data.get("reason"),
        data.get("error_message"),
        data.get("failure_reason"),
        data.get("fail_reason"),
    )
    if msg:
        return msg

    nested_msg = _first_non_empty(
        json_get(data, "error.message", ""),
        json_get(data, "error.detail", ""),
        json_get(data, "result.error_message", ""),
        json_get(data, "result.error.message", ""),
        json_get(data, "moderation.message", ""),
        json_get(data, "safety.message", ""),
    )
    return nested_msg


def extract_error_message_from_response(resp):
    try:
        data = resp.json()
    except Exception:
        data = None

    msg = extract_error_message_from_json(data) if data is not None else ""
    if msg:
        return msg

    try:
        text = (resp.text or "").strip()
    except Exception:
        text = ""

    return text or f"HTTP {getattr(resp, 'status_code', 'unknown')}"


def extract_task_failure_detail(data):
    if not isinstance(data, dict):
        return ""

    return _first_non_empty(
        data.get("error_message"),
        data.get("failure_reason"),
        data.get("fail_reason"),
        data.get("reason"),
        data.get("message"),
        json_get(data, "error.message", ""),
        json_get(data, "error.detail", ""),
        json_get(data, "result.error_message", ""),
        json_get(data, "result.error.message", ""),
    ) or extract_error_message_from_json(data)


# ============================================================
# Sora2 模型配置中心
# ============================================================

# 模型定义：用于下拉列表
SORA2_MODELS = [
    "sora-2-all",
    "sora-2-pro-all",
    "sora-2-vip-all",  # 新增
]

# 模型分类：用于时长参数映射
SORA2_MODEL_CATEGORIES = {
    # 标准模型：使用 duration_sora2 (10/15秒)
    "standard": ["sora-2-all", "sora-2-vip-all"],

    # Pro 模型：使用 duration_sora2pro (15/25秒)
    "pro": ["sora-2-pro-all"],
}

def get_duration_for_sora2_model(model: str, duration_sora2: str, duration_sora2pro: str) -> int:
    """
    根据模型名称返回对应的时长参数

    Args:
        model: 模型名称（可能是下拉选择或自定义输入）
        duration_sora2: sora-2 标准模型的时长
        duration_sora2pro: sora-2-pro 模型的时长

    Returns:
        int: 时长（秒）

    逻辑：
        1. 精确匹配：检查模型是否在 standard/pro 列表中
        2. 前缀匹配：检查模型名称前缀（支持自定义模型）
        3. 默认回退：未知模型使用 duration_sora2
    """
    model = model.strip().lower()

    # 精确匹配：标准模型
    if model in [m.lower() for m in SORA2_MODEL_CATEGORIES["standard"]]:
        return int(duration_sora2)

    # 精确匹配：Pro 模型
    if model in [m.lower() for m in SORA2_MODEL_CATEGORIES["pro"]]:
        return int(duration_sora2pro)

    # 前缀匹配：支持自定义模型（如 sora-2-pro-custom）
    if model.startswith("sora-2-pro"):
        return int(duration_sora2pro)

    # 默认回退：未知模型使用标准时长
    return int(duration_sora2)


def get_duration_for_grok_model(model: str) -> int:
    """
    根据 Grok 模型名称返回对应的时长参数

    Args:
        model: 模型名称（可能包含时长说明，如 "grok-video-3-10s (10秒)"）

    Returns:
        int: 时长（秒）

    模型映射：
        - grok-video-3 → 6秒
        - grok-video-3-10s → 10秒
        - grok-video-3-15s → 15秒
    """
    model = model.strip().lower()

    # 提取实际模型名称（去掉括号中的说明）
    if " (" in model:
        model = model.split(" (")[0].strip()

    # 精确匹配
    if "15s" in model or model.endswith("-15"):
        return 15
    elif "10s" in model or model.endswith("-10"):
        return 10
    else:
        # 默认 6 秒（包括 grok-video-3 和未知模型）
        return 6
