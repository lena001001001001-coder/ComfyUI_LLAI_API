"""Grok 视频生成节点"""

import json
import os
import time
import requests
from ..Sora2.kuai_utils import (
    env_or,
    http_headers_json,
    http_headers_auth_only,
    ensure_list_from_urls,
    extract_error_message_from_response,
    extract_task_failure_detail,
)


class GrokCreateVideo:
    """创建 Grok 视频生成任务"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "视频生成提示词（支持中英文）"
                }),
                "model": (["grok-video-3 (6秒)", "grok-video-3-10s (10秒)", "grok-video-3-15s (15秒)"], {
                    "default": "grok-video-3 (6秒)",
                    "tooltip": "选择 Grok 模型"
                }),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {
                    "default": "3:2",
                    "tooltip": "视频宽高比"
                }),
                "size": (["720P", "1080P"], {
                    "default": "1080P",
                    "tooltip": "视频分辨率"
                }),
                "enhance_prompt": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "自动将中文提示词优化并翻译为英文"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"
                }),
            },
            "optional": {
                "image_urls": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "参考图片URL（多个用逗号、分号或换行分隔）"
                }),
                "custom_model": ("STRING", {
                    "default": "",
                    "tooltip": "自定义模型（留空使用下拉模型）"
                }),
                "api_base": ("STRING", {
                    "default": "https://api.llaiapi.host",
                    "tooltip": "API端点地址"
                }),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "提示词",
            "model": "模型",
            "aspect_ratio": "宽高比",
            "size": "分辨率",
            "enhance_prompt": "提示词增强",
            "api_key": "API密钥",
            "image_urls": "参考图片URL",
            "custom_model": "自定义模型",
            "api_base": "API地址"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("任务ID", "状态", "增强提示词")
    FUNCTION = "create"
    CATEGORY = "🍐LLAI/Grok"

    def create(self, prompt, model, aspect_ratio, size, enhance_prompt, api_key="", image_urls="", api_base="https://api.llaiapi.host", custom_model=""):
        """创建 Grok 视频生成任务"""
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点参数或环境变量中设置 KUAI_API_KEY")

        api_base = api_base.rstrip("/")
        headers = http_headers_auth_only(api_key)

        # 提取实际的模型名称（去掉时长说明）
        actual_model = model.split(" (")[0] if " (" in model else model
        effective_model = (custom_model or "").strip() or actual_model

        # 根据 effective_model 判断是否支持 1080P（只有 15 秒模型支持）
        effective_size = size
        if "15s" not in effective_model.lower() and size == "1080P":
            effective_size = "720P"
            print(f"[ComfyUI_LLAI_API] 警告：{effective_model} 不支持 1080P，已自动降级到 720P")

        # 解析图片URL列表
        images = ensure_list_from_urls(image_urls) if image_urls else []

        payload = {
            "model": effective_model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "size": effective_size,
            "enhance_prompt": bool(enhance_prompt),
            "images": images
        }

        print(f"[ComfyUI_LLAI_API] Grok 创建视频任务: {prompt[:50]}...")
        print(f"[ComfyUI_LLAI_API] 模型: {effective_model}, 宽高比: {aspect_ratio}, 分辨率: {effective_size}")
        if enhance_prompt:
            print(f"[ComfyUI_LLAI_API] 提示词增强: 已启用")

        try:
            resp = requests.post(
                f"{api_base}/v1/video/create",
                json=payload,
                headers=headers,
                timeout=30
            )
            if resp.status_code >= 400:
                detail = extract_error_message_from_response(resp)
                raise RuntimeError(f"Grok 视频创建失败: {detail}")

            result = resp.json()
            task_id = result.get("id", "")
            status = result.get("status", "pending")
            enhanced_prompt = result.get("enhanced_prompt", "")

            print(f"[ComfyUI_LLAI_API] Grok 任务已创建: {task_id}, 状态: {status}")
            if enhanced_prompt and enhanced_prompt != prompt:
                print(f"[ComfyUI_LLAI_API] 增强后的提示词: {enhanced_prompt[:100]}...")

            return (task_id, status, enhanced_prompt)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Grok 视频创建失败: {str(e)}")


class GrokQueryVideo:
    """查询 Grok 视频生成任务状态"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "task_id": ("STRING", {
                    "default": "",
                    "tooltip": "任务ID"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"
                }),
            },
            "optional": {
                "api_base": ("STRING", {
                    "default": "https://api.llaiapi.host",
                    "tooltip": "API端点地址"
                }),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "task_id": "任务ID",
            "api_key": "API密钥",
            "api_base": "API地址"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("任务ID", "状态", "视频URL", "增强提示词", "状态更新时间")
    FUNCTION = "query"
    CATEGORY = "🍐LLAI/Grok"

    def query(self, task_id, api_key="", api_base="https://api.llaiapi.host"):
        """查询 Grok 视频生成任务状态"""
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点参数或环境变量中设置 KUAI_API_KEY")

        if not task_id:
            raise RuntimeError("任务ID不能为空")

        api_base = api_base.rstrip("/")
        headers = http_headers_json(api_key)

        print(f"[ComfyUI_LLAI_API] Grok 查询任务: {task_id}")

        try:
            resp = requests.get(
                f"{api_base}/v1/video/query",
                params={"id": task_id},
                headers=headers,
                timeout=30
            )
            if resp.status_code >= 400:
                detail = extract_error_message_from_response(resp)
                raise RuntimeError(f"Grok 视频查询失败: {detail}")

            result = resp.json()
            status = result.get("status", "unknown")
            video_url = result.get("video_url") or ""
            enhanced_prompt = result.get("enhanced_prompt", "")
            status_update_time = int(result.get("status_update_time", 0))

            if status == "failed":
                fail_detail = extract_task_failure_detail(result)
                if not fail_detail:
                    fail_detail = json.dumps(result, ensure_ascii=False)
                raise RuntimeError(f"Grok 视频任务失败: {fail_detail}")

            if status == "completed" and not str(video_url).strip():
                missing_detail = extract_task_failure_detail(result) or "任务已完成但未返回视频URL"
                raise RuntimeError(f"Grok 视频查询失败: {missing_detail}")

            print(f"[ComfyUI_LLAI_API] Grok 任务状态: {status}")
            if video_url:
                print(f"[ComfyUI_LLAI_API] Grok 视频URL: {video_url}")

            return (task_id, status, video_url, enhanced_prompt, status_update_time)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Grok 视频查询失败: {str(e)}")


class GrokCreateAndWait:
    """创建 Grok 视频并等待完成（一键生成）"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "视频生成提示词"
                }),
                "model": (["grok-video-3 (6秒)", "grok-video-3-10s (10秒)", "grok-video-3-15s (15秒)"], {
                    "default": "grok-video-3 (6秒)",
                    "tooltip": "选择 Grok 模型"
                }),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {
                    "default": "3:2",
                    "tooltip": "视频宽高比"
                }),
                "size": (["720P", "1080P"], {
                    "default": "1080P",
                    "tooltip": "视频分辨率"
                }),
                                "enhance_prompt": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "自动将中文提示词优化并翻译为英文"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"
                }),
            },
            "optional": {
                "image_urls": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "参考图片URL（多个用逗号、分号或换行分隔）"
                }),
                "custom_model": ("STRING", {
                    "default": "",
                    "tooltip": "自定义模型（留空使用下拉模型）"
                }),
                "api_base": ("STRING", {
                    "default": "https://api.llaiapi.host",
                    "tooltip": "API端点地址"
                }),
                "max_wait_time": ("INT", {
                    "default": 1200,
                    "min": 60,
                    "max": 1800,
                    "tooltip": "最大等待时间（秒）"
                }),
                "poll_interval": ("INT", {
                    "default": 10,
                    "min": 5,
                    "max": 60,
                    "tooltip": "轮询间隔（秒）"
                }),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "提示词",
            "model": "模型",
            "aspect_ratio": "宽高比",
            "size": "分辨率",
            "enhance_prompt": "提示词增强",
            "api_key": "API密钥",
            "image_urls": "参考图片URL",
            "custom_model": "自定义模型",
            "api_base": "API地址",
            "max_wait_time": "最大等待时间",
            "poll_interval": "轮询间隔"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("任务ID", "状态", "视频URL", "增强提示词")
    FUNCTION = "create_and_wait"
    CATEGORY = "🍐LLAI/Grok"

    def create_and_wait(self, prompt, model, aspect_ratio, size, enhance_prompt=True, api_key="",
                       image_urls="", api_base="https://api.llaiapi.host",
                       max_wait_time=1200, poll_interval=10, custom_model=""):
        """创建 Grok 视频并等待完成"""
        # 创建任务
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

        # 如果已经完成，直接返回
        if status in ["completed", "failed"]:
            querier = GrokQueryVideo()
            task_id, status, video_url, enhanced_prompt, _ = querier.query(task_id, api_key, api_base)
            return (task_id, status, video_url, enhanced_prompt)

        # 轮询等待完成
        print(f"[ComfyUI_LLAI_API] Grok 等待视频生成完成，最多等待 {max_wait_time} 秒...")

        querier = GrokQueryVideo()
        elapsed = 0

        while elapsed < max_wait_time:
            time.sleep(poll_interval)
            elapsed += poll_interval

            try:
                task_id, status, video_url, enhanced_prompt, _ = querier.query(task_id, api_key, api_base)

                if status == "completed":
                    print(f"[ComfyUI_LLAI_API] Grok 视频生成完成！")
                    return (task_id, status, video_url, enhanced_prompt)

                print(f"[ComfyUI_LLAI_API] Grok 任务进行中... 已等待 {elapsed}/{max_wait_time} 秒")

            except RuntimeError:
                raise
            except Exception as e:
                print(f"[ComfyUI_LLAI_API] Grok 查询出错: {str(e)}")
                # 继续等待，不立即失败

        # 超时
        raise RuntimeError(
            f"Grok 视频生成超时（等待了 {max_wait_time} 秒）。"
            f"任务ID: {task_id}，可使用查询节点继续检查状态。"
        )


class GrokImage2Video:
    """Grok 图生视频创建节点（支持 0-3 张图片）"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "视频生成提示词"
                }),
                "model": (["grok-video-3 (6秒)", "grok-video-3-10s (10秒)", "grok-video-3-15s (15秒)"], {
                    "default": "grok-video-3 (6秒)",
                    "tooltip": "选择 Grok 模型"
                }),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {
                    "default": "3:2",
                    "tooltip": "视频宽高比"
                }),
                "size": (["720P", "1080P"], {
                    "default": "720P",
                    "tooltip": "视频分辨率（暂只支持720P）"
                }),
                "enhance_prompt": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "自动将中文提示词优化并翻译为英文"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"
                }),
            },
            "optional": {
                "image_url_1": ("STRING", {
                    "forceInput": True,
                    "tooltip": "第1张参考图片URL（来自图片上传节点）"
                }),
                "image_url_2": ("STRING", {
                    "forceInput": True,
                    "tooltip": "第2张参考图片URL（可选）"
                }),
                "image_url_3": ("STRING", {
                    "forceInput": True,
                    "tooltip": "第3张参考图片URL（可选）"
                }),
                "api_base": ("STRING", {
                    "default": "https://api.llaiapi.host",
                    "tooltip": "API端点地址"
                }),
                "custom_model": ("STRING", {
                    "default": "",
                    "tooltip": "自定义模型（留空使用下拉模型）"
                }),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "提示词",
            "model": "模型",
            "aspect_ratio": "宽高比",
            "size": "分辨率",
            "enhance_prompt": "提示词增强",
            "api_key": "API密钥",
            "image_url_1": "参考图片1",
            "image_url_2": "参考图片2",
            "image_url_3": "参考图片3",
            "custom_model": "自定义模型",
            "api_base": "API地址"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("任务ID", "状态", "增强提示词", "状态更新时间")
    FUNCTION = "create"
    CATEGORY = "🍐LLAI/Grok"

    def create(self, prompt, model, aspect_ratio, size, enhance_prompt=True, api_key="",
               image_url_1="", image_url_2="", image_url_3="",
               api_base="https://api.llaiapi.host", custom_model=""):
        """创建 Grok 图生视频任务"""
        # 1. 解析 API key
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点参数或环境变量中设置 KUAI_API_KEY")

        # 2. 收集图片 URL（过滤空字符串）
        images_list = []
        for url in [image_url_1, image_url_2, image_url_3]:
            url_stripped = (url or "").strip()
            if url_stripped:
                images_list.append(url_stripped)

        # 验证图片数量（最多3张）
        if len(images_list) > 3:
            raise RuntimeError(f"最多支持3张参考图片，当前提供了 {len(images_list)} 张")

        # 3. 构建请求
        api_base = api_base.rstrip("/")
        headers = http_headers_auth_only(api_key)

        # 提取实际的模型名称（去掉时长说明）
        actual_model = model.split(" (")[0] if " (" in model else model
        effective_model = (custom_model or "").strip() or actual_model

        # 根据 effective_model 判断是否支持 1080P（只有 15 秒模型支持）
        effective_size = size
        if "15s" not in effective_model.lower() and size == "1080P":
            effective_size = "720P"
            print(f"[ComfyUI_LLAI_API] 警告：{effective_model} 不支持 1080P，已自动降级到 720P")

        payload = {
            "model": effective_model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "size": effective_size,
            "enhance_prompt": bool(enhance_prompt),
            "images": images_list
        }

        # 日志输出
        if images_list:
            print(f"[ComfyUI_LLAI_API] Grok 图生视频任务: {prompt[:50]}... (图片数: {len(images_list)})")
        else:
            print(f"[ComfyUI_LLAI_API] Grok 文生视频任务: {prompt[:50]}...")
        print(f"[ComfyUI_LLAI_API] 模型: {effective_model}, 宽高比: {aspect_ratio}, 分辨率: {effective_size}")

        # 4. 调用 API
        try:
            resp = requests.post(
                f"{api_base}/v1/video/create",
                json=payload,
                headers=headers,
                timeout=30
            )
            if resp.status_code >= 400:
                detail = extract_error_message_from_response(resp)
                raise RuntimeError(f"Grok 视频创建失败: {detail}")

            result = resp.json()
            task_id = result.get("id", "")
            status = result.get("status", "pending")
            enhanced_prompt = result.get("enhanced_prompt", "")
            status_update_time = int(result.get("status_update_time", 0))

            if not task_id:
                raise RuntimeError(f"创建响应缺少任务 ID")

            print(f"[ComfyUI_LLAI_API] Grok 视频任务已创建: {task_id}, 状态: {status}")

            return (task_id, status, enhanced_prompt, status_update_time)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Grok 视频创建失败: {str(e)}")


class GrokImage2VideoAndWait:
    """Grok 图生视频一键生成节点（支持 0-3 张图片）"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "视频生成提示词"
                }),
                "model": (["grok-video-3 (6秒)", "grok-video-3-10s (10秒)"], {
                    "default": "grok-video-3 (6秒)",
                    "tooltip": "选择 Grok 模型"
                }),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {
                    "default": "3:2",
                    "tooltip": "视频宽高比"
                }),
                "size": (["720P", "1080P"], {
                    "default": "720P",
                    "tooltip": "视频分辨率（暂只支持720P）"
                }),
                "enhance_prompt": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "自动将中文提示词优化并翻译为英文"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"
                }),
            },
            "optional": {
                "image_url_1": ("STRING", {
                    "forceInput": True,
                    "tooltip": "第1张参考图片URL（来自图片上传节点）"
                }),
                "image_url_2": ("STRING", {
                    "forceInput": True,
                    "tooltip": "第2张参考图片URL（可选）"
                }),
                "image_url_3": ("STRING", {
                    "forceInput": True,
                    "tooltip": "第3张参考图片URL（可选）"
                }),
                "api_base": ("STRING", {
                    "default": "https://api.llaiapi.host",
                    "tooltip": "API端点地址"
                }),
                "custom_model": ("STRING", {
                    "default": "",
                    "tooltip": "自定义模型（留空使用下拉模型）"
                }),
                "max_wait_time": ("INT", {
                    "default": 1200,
                    "min": 60,
                    "max": 1800,
                    "tooltip": "最大等待时间（秒）"
                }),
                "poll_interval": ("INT", {
                    "default": 10,
                    "min": 5,
                    "max": 60,
                    "tooltip": "轮询间隔（秒）"
                }),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "提示词",
            "model": "模型",
            "aspect_ratio": "宽高比",
            "size": "分辨率",
            "enhance_prompt": "提示词增强",
            "api_key": "API密钥",
            "image_url_1": "参考图片1",
            "image_url_2": "参考图片2",
            "image_url_3": "参考图片3",
            "api_base": "API地址",
            "custom_model": "自定义模型",
            "max_wait_time": "最大等待时间",
            "poll_interval": "轮询间隔"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("任务ID", "状态", "视频URL", "增强提示词")
    FUNCTION = "create_and_wait"
    CATEGORY = "🍐LLAI/Grok"

    def create_and_wait(self, prompt, model, aspect_ratio, size, enhance_prompt=True,
                       api_key="", image_url_1="", image_url_2="", image_url_3="",
                       api_base="https://api.llaiapi.host",
                       max_wait_time=1200, poll_interval=10, custom_model=""):
        """创建 Grok 图生视频并等待完成"""
        # 1. 创建任务
        creator = GrokImage2Video()
        task_id, status, enhanced_prompt, _ = creator.create(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            size=size,
            enhance_prompt=enhance_prompt,
            api_key=api_key,
            image_url_1=image_url_1,
            image_url_2=image_url_2,
            image_url_3=image_url_3,
            api_base=api_base,
            custom_model=custom_model,
        )

        # 2. 如果已经完成，直接返回
        if status in ["completed", "failed"]:
            querier = GrokQueryVideo()
            task_id, status, video_url, enhanced_prompt, _ = querier.query(task_id, api_key, api_base)
            return (task_id, status, video_url, enhanced_prompt)

        # 3. 轮询等待完成
        print(f"[ComfyUI_LLAI_API] Grok 等待视频生成完成，最多等待 {max_wait_time} 秒...")

        querier = GrokQueryVideo()
        elapsed = 0

        while elapsed < max_wait_time:
            time.sleep(poll_interval)
            elapsed += poll_interval

            try:
                task_id, status, video_url, enhanced_prompt, _ = querier.query(task_id, api_key, api_base)

                if status == "completed":
                    print(f"[ComfyUI_LLAI_API] Grok 视频生成完成！")
                    return (task_id, status, video_url, enhanced_prompt)

                print(f"[ComfyUI_LLAI_API] Grok 任务进行中... 已等待 {elapsed}/{max_wait_time} 秒")

            except RuntimeError:
                raise
            except Exception as e:
                print(f"[ComfyUI_LLAI_API] Grok 查询出错: {str(e)}")
                # 继续等待，不立即失败

        # 4. 超时
        raise RuntimeError(
            f"Grok 视频生成超时（等待了 {max_wait_time} 秒）。"
            f"任务ID: {task_id}，可使用查询节点继续检查状态。"
        )


class GrokText2Video:
    """Grok 文生视频创建节点"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "视频生成提示词"
                }),
                "model": (["grok-video-3 (6秒)", "grok-video-3-10s (10秒)", "grok-video-3-15s (15秒)"], {
                    "default": "grok-video-3 (6秒)",
                    "tooltip": "选择 Grok 模型"
                }),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {
                    "default": "3:2",
                    "tooltip": "视频宽高比"
                }),
                "size": (["720P", "1080P"], {
                    "default": "720P",
                    "tooltip": "视频分辨率（暂只支持720P）"
                }),
                                "enhance_prompt": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "自动将中文提示词优化并翻译为英文"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"
                }),
            },
            "optional": {
                "api_base": ("STRING", {
                    "default": "https://api.llaiapi.host",
                    "tooltip": "API端点地址"
                }),
                "custom_model": ("STRING", {
                    "default": "",
                    "tooltip": "自定义模型（留空使用下拉模型）"
                }),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "提示词",
            "model": "模型",
            "aspect_ratio": "宽高比",
            "size": "分辨率",
            "enhance_prompt": "提示词增强",
            "api_key": "API密钥",
            "api_base": "API地址",
            "custom_model": "自定义模型"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("任务ID", "状态", "增强提示词")
    FUNCTION = "create"
    CATEGORY = "🍐LLAI/Grok"

    def create(self, prompt, model, aspect_ratio, size, enhance_prompt=True, api_key="", api_base="https://api.llaiapi.host", custom_model=""):
        """创建 Grok 文生视频任务"""
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点参数或环境变量中设置 KUAI_API_KEY")

        api_base = api_base.rstrip("/")
        headers = http_headers_auth_only(api_key)

        # 提取实际的模型名称（去掉时长说明）
        actual_model = model.split(" (")[0] if " (" in model else model
        effective_model = (custom_model or "").strip() or actual_model

        # 根据 effective_model 判断是否支持 1080P（只有 15 秒模型支持）
        effective_size = size
        if "15s" not in effective_model.lower() and size == "1080P":
            effective_size = "720P"
            print(f"[ComfyUI_LLAI_API] 警告：{effective_model} 不支持 1080P，已自动降级到 720P")

        payload = {
            "model": effective_model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "size": effective_size,
            "enhance_prompt": bool(enhance_prompt),
            "images": []  # 文生视频不需要图片
        }

        print(f"[ComfyUI_LLAI_API] Grok 文生视频任务: {prompt[:50]}...")
        print(f"[ComfyUI_LLAI_API] 模型: {effective_model}, 宽高比: {aspect_ratio}, 分辨率: {effective_size}")

        try:
            resp = requests.post(
                f"{api_base}/v1/video/create",
                json=payload,
                headers=headers,
                timeout=30
            )
            if resp.status_code >= 400:
                detail = extract_error_message_from_response(resp)
                raise RuntimeError(f"Grok 文生视频创建失败: {detail}")

            result = resp.json()
            task_id = result.get("id", "")
            status = result.get("status", "pending")
            enhanced_prompt = result.get("enhanced_prompt", "")

            print(f"[ComfyUI_LLAI_API] Grok 文生视频任务已创建: {task_id}, 状态: {status}")

            return (task_id, status, enhanced_prompt)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Grok 文生视频创建失败: {str(e)}")


class GrokText2VideoAndWait:
    """Grok 文生视频一键生成节点"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "视频生成提示词"
                }),
                "model": (["grok-video-3 (6秒)", "grok-video-3-10s (10秒)"], {
                    "default": "grok-video-3 (6秒)",
                    "tooltip": "选择 Grok 模型"
                }),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {
                    "default": "3:2",
                    "tooltip": "视频宽高比"
                }),
                "size": (["720P", "1080P"], {
                    "default": "720P",
                    "tooltip": "视频分辨率（暂只支持720P）"
                }),
                                "enhance_prompt": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "自动将中文提示词优化并翻译为英文"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"
                }),
            },
            "optional": {
                "api_base": ("STRING", {
                    "default": "https://api.llaiapi.host",
                    "tooltip": "API端点地址"
                }),
                "custom_model": ("STRING", {
                    "default": "",
                    "tooltip": "自定义模型（留空使用下拉模型）"
                }),
                "max_wait_time": ("INT", {
                    "default": 1200,
                    "min": 60,
                    "max": 1800,
                    "tooltip": "最大等待时间（秒）"
                }),
                "poll_interval": ("INT", {
                    "default": 10,
                    "min": 5,
                    "max": 60,
                    "tooltip": "轮询间隔（秒）"
                }),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "提示词",
            "model": "模型",
            "aspect_ratio": "宽高比",
            "size": "分辨率",
            "enhance_prompt": "提示词增强",
            "api_key": "API密钥",
            "api_base": "API地址",
            "custom_model": "自定义模型",
            "max_wait_time": "最大等待时间",
            "poll_interval": "轮询间隔"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("任务ID", "状态", "视频URL", "增强提示词")
    FUNCTION = "create_and_wait"
    CATEGORY = "🍐LLAI/Grok"

    def create_and_wait(self, prompt, model, aspect_ratio, size, enhance_prompt=True,
                       api_key="", api_base="https://api.llaiapi.host",
                       max_wait_time=1200, poll_interval=10, custom_model=""):
        """创建 Grok 文生视频并等待完成"""
        # 1. 创建任务
        creator = GrokText2Video()
        task_id, status, enhanced_prompt = creator.create(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            size=size,
            enhance_prompt=enhance_prompt,
            api_key=api_key,
            api_base=api_base,
            custom_model=custom_model,
        )

        # 2. 如果已经完成，直接返回
        if status in ["completed", "failed"]:
            querier = GrokQueryVideo()
            task_id, status, video_url, enhanced_prompt, _ = querier.query(task_id, api_key, api_base)
            return (task_id, status, video_url, enhanced_prompt)

        # 3. 轮询等待完成
        print(f"[ComfyUI_LLAI_API] Grok 等待文生视频完成，最多等待 {max_wait_time} 秒...")

        querier = GrokQueryVideo()
        elapsed = 0

        while elapsed < max_wait_time:
            time.sleep(poll_interval)
            elapsed += poll_interval

            try:
                task_id, status, video_url, enhanced_prompt, _ = querier.query(task_id, api_key, api_base)

                if status == "completed":
                    print(f"[ComfyUI_LLAI_API] Grok 文生视频完成！")
                    return (task_id, status, video_url, enhanced_prompt)

                print(f"[ComfyUI_LLAI_API] Grok 任务进行中... 已等待 {elapsed}/{max_wait_time} 秒")

            except RuntimeError:
                raise
            except Exception as e:
                print(f"[ComfyUI_LLAI_API] Grok 查询出错: {str(e)}")
                # 继续等待，不立即失败

        # 4. 超时
        raise RuntimeError(
            f"Grok 文生视频超时（等待了 {max_wait_time} 秒）。"
            f"任务ID: {task_id}，可使用查询节点继续检查状态。"
        )


def explain_grok_extend_error(detail: str) -> str:
    if "task_origin_not_exist" not in detail:
        return f"Grok 扩展视频失败: {detail}"

    return (
        "Grok 扩展视频失败：原始视频任务不存在或不可扩展。"
        "请确认 task_id 是否来自首段视频节点的真实输出、首段生成和扩展是否使用同一个 API 地址、"
        "以及当前 API Key 是否属于创建该任务的同一账号。"
        f" 后端详情: {detail}"
    )


class GrokExtendVideo:
    """创建 Grok 扩展视频任务"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "扩展视频提示词"}),
                "task_id": ("STRING", {"default": "", "tooltip": "待扩展的视频任务ID"}),
                "model": (["grok-video-3"], {"default": "grok-video-3", "tooltip": "选择 Grok 模型"}),
                "start_time": ("INT", {"default": 10, "min": 1, "max": 9999, "tooltip": "从第几秒开始扩展"}),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {"default": "3:2", "tooltip": "视频宽高比"}),
                "size": (["720P", "1080P"], {"default": "720P", "tooltip": "视频分辨率"}),
                "upscale": ("BOOLEAN", {"default": False, "tooltip": "是否启用放大"}),
                "api_key": ("STRING", {"default": "", "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"}),
            },
            "optional": {
                "api_base": ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API端点地址"}),
                "custom_model": ("STRING", {"default": "", "tooltip": "自定义模型（留空使用下拉模型）"}),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "扩展提示词", "task_id": "任务ID", "model": "模型",
            "start_time": "开始扩展时间", "aspect_ratio": "宽高比", "size": "分辨率",
            "upscale": "是否放大", "api_key": "API密钥", "api_base": "API地址", "custom_model": "自定义模型"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("任务ID", "状态", "扩展提示词", "状态更新时间", "视频时长")
    FUNCTION = "create"
    CATEGORY = "🍐LLAI/Grok"

    def create(self, prompt, task_id, model, start_time, aspect_ratio, size, upscale=False,
               api_key="", api_base="https://api.llaiapi.host", custom_model=""):
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 未配置，请在节点参数或环境变量中设置 KUAI_API_KEY")
        if not str(task_id).strip():
            raise RuntimeError("任务ID不能为空")
        if not str(prompt).strip():
            raise RuntimeError("提示词不能为空")
        try:
            normalized_start_time = int(start_time)
        except (TypeError, ValueError):
            raise RuntimeError("start_time 必须是整数")
        if normalized_start_time <= 0:
            raise RuntimeError("start_time 必须大于 0")

        api_base = api_base.rstrip("/")
        headers = http_headers_auth_only(api_key)
        effective_model = (custom_model or "").strip() or model
        total_duration = normalized_start_time + (6 if effective_model == "grok-video-3" else 6)

        payload = {
            "model": effective_model,
            "prompt": prompt,
            "task_id": task_id,
            "aspect_ratio": aspect_ratio,
            "size": size,
            "start_time": normalized_start_time,
            "upscale": bool(upscale),
        }

        print(f"[ComfyUI_LLAI_API] Grok 扩展视频任务: {task_id} 从 {normalized_start_time}s 开始扩展")
        print(f"[ComfyUI_LLAI_API] 模型: {effective_model}, 宽高比: {aspect_ratio}, 分辨率: {size}")

        try:
            resp = requests.post(f"{api_base}/v1/video/extend", json=payload, headers=headers, timeout=30)
            if resp.status_code >= 400:
                detail = extract_error_message_from_response(resp)
                raise RuntimeError(explain_grok_extend_error(detail))

            result = resp.json()
            new_task_id = result.get("id", "")
            status = result.get("status", "pending")
            enhanced_prompt = result.get("enhanced_prompt") or prompt
            status_update_time = int(result.get("status_update_time", 0))

            if not new_task_id:
                raise RuntimeError("创建响应缺少任务 ID")

            print(f"[ComfyUI_LLAI_API] Grok 扩展任务已创建: {new_task_id}, 状态: {status}")
            return (new_task_id, status, enhanced_prompt, status_update_time, total_duration)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Grok 扩展视频失败: {str(e)}")


class GrokExtendVideoAndWait:
    """创建 Grok 扩展视频并等待完成"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "扩展视频提示词"}),
                "task_id": ("STRING", {"default": "", "tooltip": "待扩展的视频任务ID"}),
                "model": (["grok-video-3"], {"default": "grok-video-3", "tooltip": "选择 Grok 模型"}),
                "start_time": ("INT", {"default": 10, "min": 1, "max": 9999, "tooltip": "从第几秒开始扩展"}),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {"default": "3:2", "tooltip": "视频宽高比"}),
                "size": (["720P", "1080P"], {"default": "720P", "tooltip": "视频分辨率"}),
                "upscale": ("BOOLEAN", {"default": False, "tooltip": "是否启用放大"}),
                "api_key": ("STRING", {"default": "", "tooltip": "API密钥（留空使用环境变量 KUAI_API_KEY）"}),
            },
            "optional": {
                "api_base": ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API端点地址"}),
                "custom_model": ("STRING", {"default": "", "tooltip": "自定义模型（留空使用下拉模型）"}),
                "max_wait_time": ("INT", {"default": 1200, "min": 60, "max": 1800, "tooltip": "最大等待时间（秒）"}),
                "poll_interval": ("INT", {"default": 10, "min": 5, "max": 60, "tooltip": "轮询间隔（秒）"}),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "扩展提示词", "task_id": "任务ID", "model": "模型",
            "start_time": "开始扩展时间", "aspect_ratio": "宽高比", "size": "分辨率",
            "upscale": "是否放大", "api_key": "API密钥", "api_base": "API地址",
            "custom_model": "自定义模型", "max_wait_time": "最大等待时间", "poll_interval": "轮询间隔"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("任务ID", "状态", "视频URL", "扩展提示词", "视频时长")
    FUNCTION = "create_and_wait"
    CATEGORY = "🍐LLAI/Grok"

    def create_and_wait(self, prompt, task_id, model, start_time, aspect_ratio, size, upscale=False,
                       api_key="", api_base="https://api.llaiapi.host", custom_model="",
                       max_wait_time=1200, poll_interval=10):
        creator = GrokExtendVideo()
        new_task_id, status, enhanced_prompt, _, total_duration = creator.create(
            prompt=prompt, task_id=task_id, model=model, start_time=start_time,
            aspect_ratio=aspect_ratio, size=size, upscale=upscale,
            api_key=api_key, api_base=api_base, custom_model=custom_model,
        )

        if status == "completed":
            querier = GrokQueryVideo()
            new_task_id, status, video_url, enhanced_prompt, _ = querier.query(new_task_id, api_key, api_base)
            return (new_task_id, status, video_url, enhanced_prompt, total_duration)
        if status == "failed":
            raise RuntimeError(f"Grok 扩展视频失败: {enhanced_prompt or '任务创建失败'}")

        print(f"[ComfyUI_LLAI_API] Grok 等待扩展视频完成，最多等待 {max_wait_time} 秒...")

        querier = GrokQueryVideo()
        elapsed = 0

        while elapsed < max_wait_time:
            time.sleep(poll_interval)
            elapsed += poll_interval

            try:
                new_task_id, status, video_url, enhanced_prompt, _ = querier.query(new_task_id, api_key, api_base)
                if status == "completed":
                    print(f"[ComfyUI_LLAI_API] Grok 扩展视频完成！")
                    return (new_task_id, status, video_url, enhanced_prompt, total_duration)
                print(f"[ComfyUI_LLAI_API] Grok 扩展任务进行中... 已等待 {elapsed}/{max_wait_time} 秒")
            except RuntimeError:
                raise
            except Exception as e:
                print(f"[ComfyUI_LLAI_API] Grok 查询出错: {str(e)}")

        raise RuntimeError(
            f"Grok 扩展视频超时（等待了 {max_wait_time} 秒）。"
            f"任务ID: {new_task_id}，可使用查询节点继续检查状态。"
        )
