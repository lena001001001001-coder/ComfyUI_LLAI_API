"""Grok 瑙嗛鐢熸垚鑺傜偣"""

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
    """鍒涘缓 Grok 瑙嗛鐢熸垚浠诲姟"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "瑙嗛鐢熸垚鎻愮ず璇嶏紙鏀寔涓嫳鏂囷級"
                }),
                "model": (["grok-video-3 (6绉?", "grok-video-3-10s (10绉?", "grok-video-3-15s (15绉?"], {
                    "default": "grok-video-3 (6绉?",
                    "tooltip": "閫夋嫨 Grok 妯″瀷"
                }),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {
                    "default": "3:2",
                    "tooltip": "瑙嗛瀹介珮姣?
                }),
                "size": (["720P", "1080P"], {
                    "default": "1080P",
                    "tooltip": "瑙嗛鍒嗚鲸鐜?
                }),
                "enhance_prompt": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "鑷姩灏嗕腑鏂囨彁绀鸿瘝浼樺寲骞剁炕璇戜负鑻辨枃"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API瀵嗛挜锛堢暀绌轰娇鐢ㄧ幆澧冨彉閲?KUAI_API_KEY锛?
                }),
            },
            "optional": {
                "image_urls": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "鍙傝€冨浘鐗嘦RL锛堝涓敤閫楀彿銆佸垎鍙锋垨鎹㈣鍒嗛殧锛?
                }),
                "custom_model": ("STRING", {
                    "default": "",
                    "tooltip": "鑷畾涔夋ā鍨嬶紙鐣欑┖浣跨敤涓嬫媺妯″瀷锛?
                }),
                "api_base": ("STRING", {
                    "default": "https://api.llaiapi.host",
                    "tooltip": "API绔偣鍦板潃"
                }),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "鎻愮ず璇?,
            "model": "妯″瀷",
            "aspect_ratio": "瀹介珮姣?,
            "size": "鍒嗚鲸鐜?,
            "enhance_prompt": "鎻愮ず璇嶅寮?,
            "api_key": "API瀵嗛挜",
            "image_urls": "鍙傝€冨浘鐗嘦RL",
            "custom_model": "鑷畾涔夋ā鍨?,
            "api_base": "API鍦板潃"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("浠诲姟ID", "鐘舵€?, "澧炲己鎻愮ず璇?)
    FUNCTION = "create"
    CATEGORY = "馃崘LLAI/Grok"

    def create(self, prompt, model, aspect_ratio, size, enhance_prompt, api_key="", image_urls="", api_base="https://api.llaiapi.host", custom_model=""):
        """鍒涘缓 Grok 瑙嗛鐢熸垚浠诲姟"""
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 鏈厤缃紝璇峰湪鑺傜偣鍙傛暟鎴栫幆澧冨彉閲忎腑璁剧疆 KUAI_API_KEY")

        api_base = api_base.rstrip("/")
        headers = http_headers_auth_only(api_key)

        # 鎻愬彇瀹為檯鐨勬ā鍨嬪悕绉帮紙鍘绘帀鏃堕暱璇存槑锛?        actual_model = model.split(" (")[0] if " (" in model else model
        effective_model = (custom_model or "").strip() or actual_model

        # 鏍规嵁 effective_model 鍒ゆ柇鏄惁鏀寔 1080P锛堝彧鏈?15 绉掓ā鍨嬫敮鎸侊級
        effective_size = size
        if "15s" not in effective_model.lower() and size == "1080P":
            effective_size = "720P"
            print(f"[ComfyUI_LLAI_API] 璀﹀憡锛歿effective_model} 涓嶆敮鎸?1080P锛屽凡鑷姩闄嶇骇鍒?720P")

        # 瑙ｆ瀽鍥剧墖URL鍒楄〃
        images = ensure_list_from_urls(image_urls) if image_urls else []

        payload = {
            "model": effective_model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "size": effective_size,
            "enhance_prompt": bool(enhance_prompt),
            "images": images
        }

        print(f"[ComfyUI_LLAI_API] Grok 鍒涘缓瑙嗛浠诲姟: {prompt[:50]}...")
        print(f"[ComfyUI_LLAI_API] 妯″瀷: {effective_model}, 瀹介珮姣? {aspect_ratio}, 鍒嗚鲸鐜? {effective_size}")
        if enhance_prompt:
            print(f"[ComfyUI_LLAI_API] 鎻愮ず璇嶅寮? 宸插惎鐢?)

        try:
            resp = requests.post(
                f"{api_base}/v1/video/create",
                json=payload,
                headers=headers,
                timeout=30
            )
            if resp.status_code >= 400:
                detail = extract_error_message_from_response(resp)
                raise RuntimeError(f"Grok 瑙嗛鍒涘缓澶辫触: {detail}")

            result = resp.json()
            task_id = result.get("id", "")
            status = result.get("status", "pending")
            enhanced_prompt = result.get("enhanced_prompt", "")

            print(f"[ComfyUI_LLAI_API] Grok 浠诲姟宸插垱寤? {task_id}, 鐘舵€? {status}")
            if enhanced_prompt and enhanced_prompt != prompt:
                print(f"[ComfyUI_LLAI_API] 澧炲己鍚庣殑鎻愮ず璇? {enhanced_prompt[:100]}...")

            return (task_id, status, enhanced_prompt)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Grok 瑙嗛鍒涘缓澶辫触: {str(e)}")


class GrokQueryVideo:
    """鏌ヨ Grok 瑙嗛鐢熸垚浠诲姟鐘舵€?""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "task_id": ("STRING", {
                    "default": "",
                    "tooltip": "浠诲姟ID"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API瀵嗛挜锛堢暀绌轰娇鐢ㄧ幆澧冨彉閲?KUAI_API_KEY锛?
                }),
            },
            "optional": {
                "api_base": ("STRING", {
                    "default": "https://api.llaiapi.host",
                    "tooltip": "API绔偣鍦板潃"
                }),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "task_id": "浠诲姟ID",
            "api_key": "API瀵嗛挜",
            "api_base": "API鍦板潃"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("浠诲姟ID", "鐘舵€?, "瑙嗛URL", "澧炲己鎻愮ず璇?, "鐘舵€佹洿鏂版椂闂?)
    FUNCTION = "query"
    CATEGORY = "馃崘LLAI/Grok"

    def query(self, task_id, api_key="", api_base="https://api.llaiapi.host"):
        """鏌ヨ Grok 瑙嗛鐢熸垚浠诲姟鐘舵€?""
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 鏈厤缃紝璇峰湪鑺傜偣鍙傛暟鎴栫幆澧冨彉閲忎腑璁剧疆 KUAI_API_KEY")

        if not task_id:
            raise RuntimeError("浠诲姟ID涓嶈兘涓虹┖")

        api_base = api_base.rstrip("/")
        headers = http_headers_json(api_key)

        print(f"[ComfyUI_LLAI_API] Grok 鏌ヨ浠诲姟: {task_id}")

        try:
            resp = requests.get(
                f"{api_base}/v1/video/query",
                params={"id": task_id},
                headers=headers,
                timeout=30
            )
            if resp.status_code >= 400:
                detail = extract_error_message_from_response(resp)
                raise RuntimeError(f"Grok 瑙嗛鏌ヨ澶辫触: {detail}")

            result = resp.json()
            status = result.get("status", "unknown")
            video_url = result.get("video_url") or ""
            enhanced_prompt = result.get("enhanced_prompt", "")
            status_update_time = int(result.get("status_update_time", 0))

            if status == "failed":
                fail_detail = extract_task_failure_detail(result)
                if not fail_detail:
                    fail_detail = json.dumps(result, ensure_ascii=False)
                raise RuntimeError(f"Grok 瑙嗛浠诲姟澶辫触: {fail_detail}")

            if status == "completed" and not str(video_url).strip():
                missing_detail = extract_task_failure_detail(result) or "浠诲姟宸插畬鎴愪絾鏈繑鍥炶棰慤RL"
                raise RuntimeError(f"Grok 瑙嗛鏌ヨ澶辫触: {missing_detail}")

            print(f"[ComfyUI_LLAI_API] Grok 浠诲姟鐘舵€? {status}")
            if video_url:
                print(f"[ComfyUI_LLAI_API] Grok 瑙嗛URL: {video_url}")

            return (task_id, status, video_url, enhanced_prompt, status_update_time)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Grok 瑙嗛鏌ヨ澶辫触: {str(e)}")


class GrokCreateAndWait:
    """鍒涘缓 Grok 瑙嗛骞剁瓑寰呭畬鎴愶紙涓€閿敓鎴愶級"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "瑙嗛鐢熸垚鎻愮ず璇?
                }),
                "model": (["grok-video-3 (6绉?", "grok-video-3-10s (10绉?", "grok-video-3-15s (15绉?"], {
                    "default": "grok-video-3 (6绉?",
                    "tooltip": "閫夋嫨 Grok 妯″瀷"
                }),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {
                    "default": "3:2",
                    "tooltip": "瑙嗛瀹介珮姣?
                }),
                "size": (["720P", "1080P"], {
                    "default": "1080P",
                    "tooltip": "瑙嗛鍒嗚鲸鐜?
                }),
                                "enhance_prompt": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "鑷姩灏嗕腑鏂囨彁绀鸿瘝浼樺寲骞剁炕璇戜负鑻辨枃"
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API瀵嗛挜锛堢暀绌轰娇鐢ㄧ幆澧冨彉閲?KUAI_API_KEY锛?
                }),
            },
            "optional": {
                "image_urls": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "鍙傝€冨浘鐗嘦RL锛堝涓敤閫楀彿銆佸垎鍙锋垨鎹㈣鍒嗛殧锛?
                }),
                "custom_model": ("STRING", {
                    "default": "",
                    "tooltip": "鑷畾涔夋ā鍨嬶紙鐣欑┖浣跨敤涓嬫媺妯″瀷锛?
                }),
                "api_base": ("STRING", {
                    "default": "https://api.llaiapi.host",
                    "tooltip": "API绔偣鍦板潃"
                }),
                "max_wait_time": ("INT", {
                    "default": 1200,
                    "min": 60,
                    "max": 1800,
                    "tooltip": "鏈€澶х瓑寰呮椂闂达紙绉掞級"
                }),
                "poll_interval": ("INT", {
                    "default": 10,
                    "min": 5,
                    "max": 60,
                    "tooltip": "杞闂撮殧锛堢锛?
                }),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "鎻愮ず璇?,
            "model": "妯″瀷",
            "aspect_ratio": "瀹介珮姣?,
            "size": "鍒嗚鲸鐜?,
            "enhance_prompt": "鎻愮ず璇嶅寮?,
            "api_key": "API瀵嗛挜",
            "image_urls": "鍙傝€冨浘鐗嘦RL",
            "custom_model": "鑷畾涔夋ā鍨?,
            "api_base": "API鍦板潃",
            "max_wait_time": "鏈€澶х瓑寰呮椂闂?,
            "poll_interval": "杞闂撮殧"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("浠诲姟ID", "鐘舵€?, "瑙嗛URL", "澧炲己鎻愮ず璇?)
    FUNCTION = "create_and_wait"
    CATEGORY = "馃崘LLAI/Grok"

    def create_and_wait(self, prompt, model, aspect_ratio, size, enhance_prompt=True, api_key="",
                       image_urls="", api_base="https://api.llaiapi.host",
                       max_wait_time=1200, poll_interval=10, custom_model=""):
        """鍒涘缓 Grok 瑙嗛骞剁瓑寰呭畬鎴?""
        # 鍒涘缓浠诲姟
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

        # 濡傛灉宸茬粡瀹屾垚锛岀洿鎺ヨ繑鍥?        if status in ["completed", "failed"]:
            querier = GrokQueryVideo()
            task_id, status, video_url, enhanced_prompt, _ = querier.query(task_id, api_key, api_base)
            return (task_id, status, video_url, enhanced_prompt)

        # 杞绛夊緟瀹屾垚
        print(f"[ComfyUI_LLAI_API] Grok 绛夊緟瑙嗛鐢熸垚瀹屾垚锛屾渶澶氱瓑寰?{max_wait_time} 绉?..")

        querier = GrokQueryVideo()
        elapsed = 0

        while elapsed < max_wait_time:
            time.sleep(poll_interval)
            elapsed += poll_interval

            try:
                task_id, status, video_url, enhanced_prompt, _ = querier.query(task_id, api_key, api_base)

                if status == "completed":
                    print(f"[ComfyUI_LLAI_API] Grok 瑙嗛鐢熸垚瀹屾垚锛?)
                    return (task_id, status, video_url, enhanced_prompt)

                print(f"[ComfyUI_LLAI_API] Grok 浠诲姟杩涜涓?.. 宸茬瓑寰?{elapsed}/{max_wait_time} 绉?)

            except RuntimeError:
                raise
            except Exception as e:
                print(f"[ComfyUI_LLAI_API] Grok 鏌ヨ鍑洪敊: {str(e)}")
                # 缁х画绛夊緟锛屼笉绔嬪嵆澶辫触

        # 瓒呮椂
        raise RuntimeError(
            f"Grok 瑙嗛鐢熸垚瓒呮椂锛堢瓑寰呬簡 {max_wait_time} 绉掞級銆?
            f"浠诲姟ID: {task_id}锛屽彲浣跨敤鏌ヨ鑺傜偣缁х画妫€鏌ョ姸鎬併€?
        )



def explain_grok_extend_error(detail: str) -> str:
    if "task_origin_not_exist" not in detail:
        return f"Grok 鎵╁睍瑙嗛澶辫触: {detail}"

    return (
        "Grok 鎵╁睍瑙嗛澶辫触锛氬師濮嬭棰戜换鍔′笉瀛樺湪鎴栦笉鍙墿灞曘€?
        "璇风‘璁?task_id 鏄惁鏉ヨ嚜棣栨瑙嗛鑺傜偣鐨勭湡瀹炶緭鍑恒€侀娈电敓鎴愬拰鎵╁睍鏄惁浣跨敤鍚屼竴涓?API 鍦板潃銆?
        "浠ュ強褰撳墠 API Key 鏄惁灞炰簬鍒涘缓璇ヤ换鍔＄殑鍚屼竴璐﹀彿銆?
        f" 鍚庣璇︽儏: {detail}"
    )


class GrokExtendVideo:
    """鍒涘缓 Grok 鎵╁睍瑙嗛浠诲姟"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "鎵╁睍瑙嗛鎻愮ず璇?}),
                "task_id": ("STRING", {"default": "", "tooltip": "寰呮墿灞曠殑瑙嗛浠诲姟ID"}),
                "model": (["grok-video-3"], {"default": "grok-video-3", "tooltip": "閫夋嫨 Grok 妯″瀷"}),
                "start_time": ("INT", {"default": 10, "min": 1, "max": 9999, "tooltip": "浠庣鍑犵寮€濮嬫墿灞?}),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {"default": "3:2", "tooltip": "瑙嗛瀹介珮姣?}),
                "size": (["720P", "1080P"], {"default": "720P", "tooltip": "瑙嗛鍒嗚鲸鐜?}),
                "upscale": ("BOOLEAN", {"default": False, "tooltip": "鏄惁鍚敤鏀惧ぇ"}),
                "api_key": ("STRING", {"default": "", "tooltip": "API瀵嗛挜锛堢暀绌轰娇鐢ㄧ幆澧冨彉閲?KUAI_API_KEY锛?}),
            },
            "optional": {
                "api_base": ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API绔偣鍦板潃"}),
                "custom_model": ("STRING", {"default": "", "tooltip": "鑷畾涔夋ā鍨嬶紙鐣欑┖浣跨敤涓嬫媺妯″瀷锛?}),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "鎵╁睍鎻愮ず璇?, "task_id": "浠诲姟ID", "model": "妯″瀷",
            "start_time": "寮€濮嬫墿灞曟椂闂?, "aspect_ratio": "瀹介珮姣?, "size": "鍒嗚鲸鐜?,
            "upscale": "鏄惁鏀惧ぇ", "api_key": "API瀵嗛挜", "api_base": "API鍦板潃", "custom_model": "鑷畾涔夋ā鍨?
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("浠诲姟ID", "鐘舵€?, "鎵╁睍鎻愮ず璇?, "鐘舵€佹洿鏂版椂闂?, "瑙嗛鏃堕暱")
    FUNCTION = "create"
    CATEGORY = "馃崘LLAI/Grok"

    def create(self, prompt, task_id, model, start_time, aspect_ratio, size, upscale=False,
               api_key="", api_base="https://api.llaiapi.host", custom_model=""):
        api_key = env_or(api_key, "KUAI_API_KEY")
        if not api_key:
            raise RuntimeError("API Key 鏈厤缃紝璇峰湪鑺傜偣鍙傛暟鎴栫幆澧冨彉閲忎腑璁剧疆 KUAI_API_KEY")
        if not str(task_id).strip():
            raise RuntimeError("浠诲姟ID涓嶈兘涓虹┖")
        if not str(prompt).strip():
            raise RuntimeError("鎻愮ず璇嶄笉鑳戒负绌?)
        try:
            normalized_start_time = int(start_time)
        except (TypeError, ValueError):
            raise RuntimeError("start_time 蹇呴』鏄暣鏁?)
        if normalized_start_time <= 0:
            raise RuntimeError("start_time 蹇呴』澶т簬 0")

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

        print(f"[ComfyUI_LLAI_API] Grok 鎵╁睍瑙嗛浠诲姟: {task_id} 浠?{normalized_start_time}s 寮€濮嬫墿灞?)
        print(f"[ComfyUI_LLAI_API] 妯″瀷: {effective_model}, 瀹介珮姣? {aspect_ratio}, 鍒嗚鲸鐜? {size}")

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
                raise RuntimeError("鍒涘缓鍝嶅簲缂哄皯浠诲姟 ID")

            print(f"[ComfyUI_LLAI_API] Grok 鎵╁睍浠诲姟宸插垱寤? {new_task_id}, 鐘舵€? {status}")
            return (new_task_id, status, enhanced_prompt, status_update_time, total_duration)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Grok 鎵╁睍瑙嗛澶辫触: {str(e)}")


class GrokExtendVideoAndWait:
    """鍒涘缓 Grok 鎵╁睍瑙嗛骞剁瓑寰呭畬鎴?""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "鎵╁睍瑙嗛鎻愮ず璇?}),
                "task_id": ("STRING", {"default": "", "tooltip": "寰呮墿灞曠殑瑙嗛浠诲姟ID"}),
                "model": (["grok-video-3"], {"default": "grok-video-3", "tooltip": "閫夋嫨 Grok 妯″瀷"}),
                "start_time": ("INT", {"default": 10, "min": 1, "max": 9999, "tooltip": "浠庣鍑犵寮€濮嬫墿灞?}),
                "aspect_ratio": (["2:3", "3:2", "1:1"], {"default": "3:2", "tooltip": "瑙嗛瀹介珮姣?}),
                "size": (["720P", "1080P"], {"default": "720P", "tooltip": "瑙嗛鍒嗚鲸鐜?}),
                "upscale": ("BOOLEAN", {"default": False, "tooltip": "鏄惁鍚敤鏀惧ぇ"}),
                "api_key": ("STRING", {"default": "", "tooltip": "API瀵嗛挜锛堢暀绌轰娇鐢ㄧ幆澧冨彉閲?KUAI_API_KEY锛?}),
            },
            "optional": {
                "api_base": ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API绔偣鍦板潃"}),
                "custom_model": ("STRING", {"default": "", "tooltip": "鑷畾涔夋ā鍨嬶紙鐣欑┖浣跨敤涓嬫媺妯″瀷锛?}),
                "max_wait_time": ("INT", {"default": 1200, "min": 60, "max": 1800, "tooltip": "鏈€澶х瓑寰呮椂闂达紙绉掞級"}),
                "poll_interval": ("INT", {"default": 10, "min": 5, "max": 60, "tooltip": "杞闂撮殧锛堢锛?}),
            }
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "鎵╁睍鎻愮ず璇?, "task_id": "浠诲姟ID", "model": "妯″瀷",
            "start_time": "寮€濮嬫墿灞曟椂闂?, "aspect_ratio": "瀹介珮姣?, "size": "鍒嗚鲸鐜?,
            "upscale": "鏄惁鏀惧ぇ", "api_key": "API瀵嗛挜", "api_base": "API鍦板潃",
            "custom_model": "鑷畾涔夋ā鍨?, "max_wait_time": "鏈€澶х瓑寰呮椂闂?, "poll_interval": "杞闂撮殧"
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("浠诲姟ID", "鐘舵€?, "瑙嗛URL", "鎵╁睍鎻愮ず璇?, "瑙嗛鏃堕暱")
    FUNCTION = "create_and_wait"
    CATEGORY = "馃崘LLAI/Grok"

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
            raise RuntimeError(f"Grok 鎵╁睍瑙嗛澶辫触: {enhanced_prompt or '浠诲姟鍒涘缓澶辫触'}")

        print(f"[ComfyUI_LLAI_API] Grok 绛夊緟鎵╁睍瑙嗛瀹屾垚锛屾渶澶氱瓑寰?{max_wait_time} 绉?..")

        querier = GrokQueryVideo()
        elapsed = 0

        while elapsed < max_wait_time:
            time.sleep(poll_interval)
            elapsed += poll_interval

            try:
                new_task_id, status, video_url, enhanced_prompt, _ = querier.query(new_task_id, api_key, api_base)
                if status == "completed":
                    print(f"[ComfyUI_LLAI_API] Grok 鎵╁睍瑙嗛瀹屾垚锛?)
                    return (new_task_id, status, video_url, enhanced_prompt, total_duration)
                print(f"[ComfyUI_LLAI_API] Grok 鎵╁睍浠诲姟杩涜涓?.. 宸茬瓑寰?{elapsed}/{max_wait_time} 绉?)
            except RuntimeError:
                raise
            except Exception as e:
                print(f"[ComfyUI_LLAI_API] Grok 鏌ヨ鍑洪敊: {str(e)}")

        raise RuntimeError(
            f"Grok 鎵╁睍瑙嗛瓒呮椂锛堢瓑寰呬簡 {max_wait_time} 绉掞級銆?
            f"浠诲姟ID: {new_task_id}锛屽彲浣跨敤鏌ヨ鑺傜偣缁х画妫€鏌ョ姸鎬併€?
        )

