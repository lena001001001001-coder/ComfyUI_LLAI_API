"""Grok video generation nodes."""

import json
import time

import requests

from ..Sora2.kuai_utils import (
    ensure_list_from_urls,
    env_or,
    extract_error_message_from_response,
    extract_task_failure_detail,
    http_headers_auth_only,
    http_headers_json,
)


DEFAULT_API_BASE = "https://api.llaiapi.host"
GROK_MODELS = [
    "grok-video-3 (6秒)",
    "grok-video-3-10s (10秒)",
    "grok-video-3-15s (15秒)",
]


def _model_id(model: str) -> str:
    """Remove the human-readable duration suffix from a model option."""
    value = str(model or "").strip()
    return value.split(" (", 1)[0] if " (" in value else value


def _effective_model(model: str, custom_model: str = "") -> str:
    return str(custom_model or "").strip() or _model_id(model)


class GrokCreateVideo:
    """Create a Grok text-to-video or image-to-video task."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "视频生成提示词（支持中英文）",
                    },
                ),
                "model": (
                    GROK_MODELS,
                    {
                        "default": GROK_MODELS[0],
                        "tooltip": "选择 Grok 模型",
                    },
                ),
                "aspect_ratio": (
                    ["2:3", "3:2", "1:1"],
                    {"default": "3:2", "tooltip": "视频宽高比"},
                ),
                "size": (
                    ["720P", "1080P"],
                    {"default": "1080P", "tooltip": "视频分辨率"},
                ),
                "enhance_prompt": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "自动优化并翻译提示词为英文",
                    },
                ),
                "api_key": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "API 密钥（留空使用环境变量 KUAI_API_KEY）",
                    },
                ),
            },
            "optional": {
                "image_urls": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "参考图片 URL，多个 URL 用逗号、分号或换行分隔",
                    },
                ),
                "custom_model": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "自定义模型（留空使用下拉模型）",
                    },
                ),
                "api_base": (
                    "STRING",
                    {"default": DEFAULT_API_BASE, "tooltip": "API 地址"},
                ),
            },
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "提示词",
            "model": "模型",
            "aspect_ratio": "宽高比",
            "size": "分辨率",
            "enhance_prompt": "提示词增强",
            "api_key": "API 密钥",
            "image_urls": "参考图片 URL",
            "custom_model": "自定义模型",
            "api_base": "API 地址",
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("任务 ID", "状态", "增强提示词")
    FUNCTION = "create"
    CATEGORY = "LLAI/Grok"

    def create(
        self,
        prompt,
        model,
        aspect_ratio,
        size,
        enhance_prompt,
        api_key="",
        image_urls="",
        api_base=DEFAULT_API_BASE,
        custom_model="",
    ):
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "API Key 未配置，请在节点参数或环境变量中设置 KUAI_API_KEY"
            )

        api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
        effective_model = _effective_model(model, custom_model)
        effective_size = size
        if "15s" not in effective_model.lower() and size == "1080P":
            effective_size = "720P"
            print(
                f"[ComfyUI_LLAI_API] 警告：{effective_model} 不支持 1080P，"
                "已自动降级到 720P"
            )

        payload = {
            "model": effective_model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "size": effective_size,
            "enhance_prompt": bool(enhance_prompt),
            "images": ensure_list_from_urls(image_urls) if image_urls else [],
        }

        print(f"[ComfyUI_LLAI_API] Grok 创建视频任务: {prompt[:50]}...")
        print(
            f"[ComfyUI_LLAI_API] 模型: {effective_model}, "
            f"宽高比: {aspect_ratio}, 分辨率: {effective_size}"
        )

        try:
            response = requests.post(
                f"{api_base}/v1/video/create",
                json=payload,
                headers=http_headers_auth_only(api_key),
                timeout=30,
            )
            if response.status_code >= 400:
                detail = extract_error_message_from_response(response)
                raise RuntimeError(f"Grok 视频创建失败: {detail}")

            result = response.json()
            task_id = result.get("id") or result.get("task_id") or ""
            status = result.get("status") or "pending"
            enhanced_prompt = result.get("enhanced_prompt") or ""
            if not task_id:
                raise RuntimeError(
                    "创建响应缺少任务 ID: "
                    + json.dumps(result, ensure_ascii=False)
                )

            return task_id, status, enhanced_prompt
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Grok 视频创建失败: {exc}") from exc


class GrokImage2Video(GrokCreateVideo):
    """Compatibility wrapper for callers that pass ``images`` directly."""

    def create(
        self,
        prompt,
        model,
        aspect_ratio,
        size,
        enhance_prompt,
        api_key="",
        images="",
        image_urls="",
        api_base=DEFAULT_API_BASE,
        custom_model="",
    ):
        urls = image_urls or images
        task_id, status, enhanced_prompt = super().create(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            size=size,
            enhance_prompt=enhance_prompt,
            api_key=api_key,
            image_urls=urls,
            api_base=api_base,
            custom_model=custom_model,
        )
        return task_id, status, enhanced_prompt, 0


class GrokQueryVideo:
    """Query a Grok video task."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "task_id": ("STRING", {"default": "", "tooltip": "任务 ID"}),
                "api_key": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "API 密钥（留空使用环境变量 KUAI_API_KEY）",
                    },
                ),
            },
            "optional": {
                "api_base": (
                    "STRING",
                    {"default": DEFAULT_API_BASE, "tooltip": "API 地址"},
                ),
            },
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "task_id": "任务 ID",
            "api_key": "API 密钥",
            "api_base": "API 地址",
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("任务 ID", "状态", "视频 URL", "增强提示词", "状态更新时间")
    FUNCTION = "query"
    CATEGORY = "LLAI/Grok"

    def query(self, task_id, api_key="", api_base=DEFAULT_API_BASE):
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "API Key 未配置，请在节点参数或环境变量中设置 KUAI_API_KEY"
            )
        if not str(task_id).strip():
            raise RuntimeError("任务 ID 不能为空")

        api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
        try:
            response = requests.get(
                f"{api_base}/v1/video/query",
                params={"id": task_id},
                headers=http_headers_json(api_key),
                timeout=30,
            )
            if response.status_code >= 400:
                detail = extract_error_message_from_response(response)
                raise RuntimeError(f"Grok 视频查询失败: {detail}")

            result = response.json()
            status = result.get("status") or result.get("state") or "unknown"
            video_url = (
                result.get("video_url")
                or result.get("url")
                or result.get("output_url")
                or ""
            )
            enhanced_prompt = result.get("enhanced_prompt") or ""
            status_update_time = int(result.get("status_update_time") or 0)

            if str(status).lower() in {"failed", "error", "cancelled", "canceled"}:
                detail = extract_task_failure_detail(result) or json.dumps(
                    result, ensure_ascii=False
                )
                raise RuntimeError(f"Grok 视频任务失败: {detail}")

            if str(status).lower() in {"completed", "complete", "success", "done"}:
                if not str(video_url).strip():
                    detail = extract_task_failure_detail(result) or "任务已完成但未返回视频 URL"
                    raise RuntimeError(f"Grok 视频查询失败: {detail}")

            return task_id, status, video_url, enhanced_prompt, status_update_time
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Grok 视频查询失败: {exc}") from exc


class GrokCreateAndWait:
    """Create a Grok task and wait for its video URL."""

    @classmethod
    def INPUT_TYPES(cls):
        inputs = GrokCreateVideo.INPUT_TYPES()
        inputs["optional"].update(
            {
                "max_wait_time": (
                    "INT",
                    {
                        "default": 1200,
                        "min": 60,
                        "max": 3600,
                        "tooltip": "最大等待时间（秒）",
                    },
                ),
                "poll_interval": (
                    "INT",
                    {
                        "default": 10,
                        "min": 5,
                        "max": 60,
                        "tooltip": "轮询间隔（秒）",
                    },
                ),
            }
        )
        return inputs

    @classmethod
    def INPUT_LABELS(cls):
        labels = dict(GrokCreateVideo.INPUT_LABELS())
        labels.update(
            {
                "max_wait_time": "最大等待时间",
                "poll_interval": "轮询间隔",
            }
        )
        return labels

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("任务 ID", "状态", "视频 URL", "增强提示词")
    FUNCTION = "create_and_wait"
    CATEGORY = "LLAI/Grok"

    def create_and_wait(
        self,
        prompt,
        model,
        aspect_ratio,
        size,
        enhance_prompt=True,
        api_key="",
        image_urls="",
        api_base=DEFAULT_API_BASE,
        max_wait_time=1200,
        poll_interval=10,
        custom_model="",
    ):
        creator = GrokCreateVideo()
        task_id, status, enhanced_prompt = creator.create(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            size=size,
            enhance_prompt=enhance_prompt,
            api_key=api_key,
            image_urls=image_urls,
            api_base=api_base,
            custom_model=custom_model,
        )

        terminal_statuses = {
            "completed",
            "complete",
            "success",
            "done",
            "failed",
            "error",
        }
        if str(status).lower() in terminal_statuses:
            if str(status).lower() in {"failed", "error"}:
                raise RuntimeError(f"Grok 视频任务失败: {enhanced_prompt or status}")
            _, status, video_url, enhanced_prompt, _ = GrokQueryVideo().query(
                task_id, api_key, api_base
            )
            return task_id, status, video_url, enhanced_prompt

        print(
            f"[ComfyUI_LLAI_API] 等待 Grok 视频完成，"
            f"最多 {max_wait_time} 秒"
        )
        elapsed = 0
        while elapsed < int(max_wait_time):
            time.sleep(int(poll_interval))
            elapsed += int(poll_interval)
            _, status, video_url, enhanced_prompt_now, _ = GrokQueryVideo().query(
                task_id, api_key, api_base
            )
            if enhanced_prompt_now:
                enhanced_prompt = enhanced_prompt_now
            if str(status).lower() in {"completed", "complete", "success", "done"}:
                return task_id, status, video_url, enhanced_prompt

        raise RuntimeError(
            f"Grok 视频生成超时（等待了 {max_wait_time} 秒），任务 ID: {task_id}"
        )


def explain_grok_extend_error(detail: str) -> str:
    if "task_origin_not_exist" in detail:
        return (
            "Grok 扩展视频失败：原始视频任务不存在或不可扩展。"
            "请确认 task_id 来自首段视频节点，并使用同一 API 地址和账号。"
            f"后端详情：{detail}"
        )
    return f"Grok 扩展视频失败: {detail}"


class GrokExtendVideo:
    """Create a Grok video extension task."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {"default": "", "multiline": True, "tooltip": "扩展视频提示词"},
                ),
                "task_id": ("STRING", {"default": "", "tooltip": "待扩展的视频任务 ID"}),
                "model": (
                    ["grok-video-3"],
                    {"default": "grok-video-3", "tooltip": "选择 Grok 模型"},
                ),
                "start_time": (
                    "INT",
                    {
                        "default": 10,
                        "min": 1,
                        "max": 9999,
                        "tooltip": "从第几秒开始扩展",
                    },
                ),
                "aspect_ratio": (
                    ["2:3", "3:2", "1:1"],
                    {"default": "3:2", "tooltip": "视频宽高比"},
                ),
                "size": (
                    ["720P", "1080P"],
                    {"default": "720P", "tooltip": "视频分辨率"},
                ),
                "upscale": ("BOOLEAN", {"default": False, "tooltip": "是否启用放大"}),
                "api_key": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "API 密钥（留空使用环境变量 KUAI_API_KEY）",
                    },
                ),
            },
            "optional": {
                "api_base": (
                    "STRING",
                    {"default": DEFAULT_API_BASE, "tooltip": "API 地址"},
                ),
                "custom_model": (
                    "STRING",
                    {"default": "", "tooltip": "自定义模型"},
                ),
            },
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "扩展提示词",
            "task_id": "任务 ID",
            "model": "模型",
            "start_time": "开始扩展时间",
            "aspect_ratio": "宽高比",
            "size": "分辨率",
            "upscale": "放大",
            "api_key": "API 密钥",
            "api_base": "API 地址",
            "custom_model": "自定义模型",
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("任务 ID", "状态", "扩展提示词", "状态更新时间", "视频时长")
    FUNCTION = "create"
    CATEGORY = "LLAI/Grok"

    def create(
        self,
        prompt,
        task_id,
        model,
        start_time,
        aspect_ratio,
        size,
        upscale=False,
        api_key="",
        api_base=DEFAULT_API_BASE,
        custom_model="",
    ):
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置")
        if not str(task_id).strip():
            raise RuntimeError("任务 ID 不能为空")
        if not str(prompt).strip():
            raise RuntimeError("提示词不能为空")

        try:
            normalized_start_time = int(start_time)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("start_time 必须是整数") from exc
        if normalized_start_time <= 0:
            raise RuntimeError("start_time 必须大于 0")

        api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
        effective_model = _effective_model(model, custom_model)
        payload = {
            "model": effective_model,
            "prompt": prompt,
            "task_id": task_id,
            "aspect_ratio": aspect_ratio,
            "size": size,
            "start_time": normalized_start_time,
            "upscale": bool(upscale),
        }

        try:
            response = requests.post(
                f"{api_base}/v1/video/extend",
                json=payload,
                headers=http_headers_auth_only(api_key),
                timeout=30,
            )
            if response.status_code >= 400:
                detail = extract_error_message_from_response(response)
                raise RuntimeError(explain_grok_extend_error(detail))

            result = response.json()
            new_task_id = result.get("id") or result.get("task_id") or ""
            status = result.get("status") or "pending"
            enhanced_prompt = result.get("enhanced_prompt") or prompt
            status_update_time = int(result.get("status_update_time") or 0)
            if not new_task_id:
                raise RuntimeError("创建响应缺少任务 ID")

            total_duration = normalized_start_time + 6
            return (
                new_task_id,
                status,
                enhanced_prompt,
                status_update_time,
                total_duration,
            )
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Grok 扩展视频失败: {exc}") from exc


class GrokExtendVideoAndWait:
    """Create a Grok extension task and wait for its video URL."""

    @classmethod
    def INPUT_TYPES(cls):
        inputs = GrokExtendVideo.INPUT_TYPES()
        inputs["optional"].update(
            {
                "max_wait_time": (
                    "INT",
                    {"default": 1200, "min": 60, "max": 3600},
                ),
                "poll_interval": (
                    "INT",
                    {"default": 10, "min": 5, "max": 60},
                ),
            }
        )
        return inputs

    @classmethod
    def INPUT_LABELS(cls):
        labels = dict(GrokExtendVideo.INPUT_LABELS())
        labels.update(
            {
                "max_wait_time": "最大等待时间",
                "poll_interval": "轮询间隔",
            }
        )
        return labels

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("任务 ID", "状态", "视频 URL", "扩展提示词", "视频时长")
    FUNCTION = "create_and_wait"
    CATEGORY = "LLAI/Grok"

    def create_and_wait(
        self,
        prompt,
        task_id,
        model,
        start_time,
        aspect_ratio,
        size,
        upscale=False,
        api_key="",
        api_base=DEFAULT_API_BASE,
        custom_model="",
        max_wait_time=1200,
        poll_interval=10,
    ):
        new_task_id, status, enhanced_prompt, _, total_duration = GrokExtendVideo().create(
            prompt=prompt,
            task_id=task_id,
            model=model,
            start_time=start_time,
            aspect_ratio=aspect_ratio,
            size=size,
            upscale=upscale,
            api_key=api_key,
            api_base=api_base,
            custom_model=custom_model,
        )

        if str(status).lower() in {"failed", "error"}:
            raise RuntimeError(f"Grok 扩展视频失败: {enhanced_prompt}")

        elapsed = 0
        while elapsed < int(max_wait_time):
            if str(status).lower() in {"completed", "complete", "success", "done"}:
                _, status, video_url, enhanced_prompt, _ = GrokQueryVideo().query(
                    new_task_id, api_key, api_base
                )
                return new_task_id, status, video_url, enhanced_prompt, total_duration

            time.sleep(int(poll_interval))
            elapsed += int(poll_interval)
            _, status, video_url, queried_prompt, _ = GrokQueryVideo().query(
                new_task_id, api_key, api_base
            )
            if queried_prompt:
                enhanced_prompt = queried_prompt
            if str(status).lower() in {"completed", "complete", "success", "done"}:
                return new_task_id, status, video_url, enhanced_prompt, total_duration

        raise RuntimeError(
            f"Grok 扩展视频超时（等待了 {max_wait_time} 秒），任务 ID: {new_task_id}"
        )


# Legacy names used by existing batch processors and saved workflows.
GrokText2Video = GrokCreateVideo
GrokText2VideoAndWait = GrokCreateAndWait


NODE_CLASS_MAPPINGS = {
    "GrokCreateVideo": GrokCreateVideo,
    "GrokQueryVideo": GrokQueryVideo,
    "GrokCreateAndWait": GrokCreateAndWait,
    "GrokText2Video": GrokText2Video,
    "GrokText2VideoAndWait": GrokText2VideoAndWait,
    "GrokImage2Video": GrokImage2Video,
    "GrokExtendVideo": GrokExtendVideo,
    "GrokExtendVideoAndWait": GrokExtendVideoAndWait,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GrokCreateVideo": "LL Grok 创建视频",
    "GrokQueryVideo": "LL Grok 查询视频",
    "GrokCreateAndWait": "LL Grok 一键生成视频",
    "GrokText2Video": "LL Grok 文生视频",
    "GrokText2VideoAndWait": "LL Grok 文生视频（一键）",
    "GrokImage2Video": "LL Grok 图生视频",
    "GrokExtendVideo": "LL Grok 扩展视频",
    "GrokExtendVideoAndWait": "LL Grok 扩展视频（一键）",
}
