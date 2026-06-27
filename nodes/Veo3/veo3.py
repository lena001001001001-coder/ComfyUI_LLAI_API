import json
import time
import requests
from ..Sora2.kuai_utils import (env_or, ensure_list_from_urls,
                           http_headers_auth_only, json_get)


def _first_non_empty(*values):
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _extract_error_message_from_json(data):
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
        data.get("fail_reason"),
        data.get("failure_reason"),
    )
    if msg:
        return msg

    # 甯歌宓屽瀛楁鍥為€€
    nested_msg = _first_non_empty(
        json_get(data, "error.message", ""),
        json_get(data, "error.detail", ""),
        json_get(data, "moderation.message", ""),
        json_get(data, "safety.message", ""),
    )
    return nested_msg


def _extract_error_message_from_response(resp):
    try:
        data = resp.json()
    except Exception:
        data = None

    msg = _extract_error_message_from_json(data) if data is not None else ""
    if msg:
        return msg

    try:
        text = (resp.text or "").strip()
    except Exception:
        text = ""

    return text or f"HTTP {getattr(resp, 'status_code', 'unknown')}"


class VeoText2Video:
    """浣跨敤 Veo 妯″瀷杩涜鏂囩敓瑙嗛"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "瑙嗛鎻愮ず璇嶏紙鏀寔涓嫳鏂囷級"}),
                "model": ([
                    "veo_3_1-lite",
                    "veo_3_1-lite-4K",
                    "veo_3_1-fast",
                    "veo_3_1-fast-4K",
                    "veo3.1",
                    "veo3",
                    "veo3-fast",
                    "veo3-pro",
                    "veo3.1-fast-components",
                    "veo3.1-4k",
                    "veo3.1-pro-4k",
                ], {"default": "veo_3_1-lite", "tooltip": "妯″瀷閫夋嫨"}),
                "aspect_ratio": (["16:9", "9:16"], {"default": "9:16", "tooltip": "瑙嗛瀹介珮姣?}),
                "enhance_prompt": ("BOOLEAN", {"default": True, "tooltip": "鑷姩灏嗕腑鏂囨彁绀鸿瘝浼樺寲骞剁炕璇戜负鑻辨枃"}),
                "enable_upsample": ("BOOLEAN", {"default": True, "tooltip": "鍚敤瓒呭垎浠ユ彁鍗囪棰戣川閲?}),
            },
            "optional": {
                "api_base": ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API绔偣鍦板潃"}),
                "api_key": ("STRING", {"default": "", "tooltip": "API瀵嗛挜"}),
                "timeout": ("INT", {"default": 1800, "min": 5, "max": 9999, "tooltip": "瓒呮椂鏃堕棿(绉?"}),
                "custom_model": ("STRING", {"default": "", "tooltip": "鑷畾涔夋ā鍨嬪悕锛堢暀绌轰娇鐢ㄤ笅鎷夋ā鍨嬶級"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("浠诲姟ID", "鐘舵€?, "鐘舵€佹洿鏂版椂闂?)
    FUNCTION = "create"
    CATEGORY = "馃崘LLAI/Veo3"

    def create(self, prompt, model, aspect_ratio, enhance_prompt, enable_upsample,
               api_base="https://api.llaiapi.host", api_key="", timeout=120, custom_model=""):

        api_key = env_or(api_key, "KUAI_API_KEY")
        api_base = (api_base or "https://api.llaiapi.host").strip()
        endpoint = api_base.rstrip("/") + "/v1/video/create"
        effective_model = (custom_model or "").strip() or model

        payload = {
            "model": effective_model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "enhance_prompt": bool(enhance_prompt),
            "enable_upsample": bool(enable_upsample),
        }

        try:
            resp = requests.post(endpoint, headers=http_headers_auth_only(api_key), json=payload, timeout=int(timeout))
            if resp.status_code >= 400:
                detail = _extract_error_message_from_response(resp)
                raise RuntimeError(f"鍒涘缓 Veo 瑙嗛澶辫触: {detail}")
            data = resp.json()
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"鍒涘缓 Veo 瑙嗛澶辫触: {str(e)}")

        task_id = data.get("id") or ""
        status = data.get("status") or ""
        status_update_time = int(data.get("status_update_time") or 0)

        if not task_id:
            raise RuntimeError(f"鍒涘缓鍝嶅簲缂哄皯浠诲姟 ID: {json.dumps(data, ensure_ascii=False)}")

        return (task_id, status, status_update_time)

class VeoImage2Video:
    """浣跨敤 Veo 妯″瀷杩涜鍥剧敓瑙嗛"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "瑙嗛鎻愮ず璇嶏紙鏀寔涓嫳鏂囷級"}),
                "model": ([
                    "veo_3_1-lite",
                    "veo_3_1-lite-4K",
                    "veo_3_1-fast",
                    "veo_3_1-fast-4K",
                    "veo3.1",
                    "veo3",
                    "veo3-fast",
                    "veo3-pro",
                    "veo3.1-components",
                    "veo2-fast-components",
                    "veo3.1-fast-components",
                    "veo3.1-4k",
                    "veo3.1-pro-4k",
                ], {"default": "veo_3_1-lite", "tooltip": "妯″瀷閫夋嫨"}),
                "aspect_ratio": (["16:9", "9:16"], {"default": "9:16", "tooltip": "瑙嗛瀹介珮姣?}),
                "enhance_prompt": ("BOOLEAN", {"default": True, "tooltip": "鑷姩灏嗕腑鏂囨彁绀鸿瘝浼樺寲骞剁炕璇戜负鑻辨枃"}),
                "enable_upsample": ("BOOLEAN", {"default": True, "tooltip": "鍚敤瓒呭垎浠ユ彁鍗囪棰戣川閲?}),
            },
            "optional": {
                "image_1": ("STRING", {"default": "", "multiline": False, "tooltip": "鍙傝€冨浘1 URL (棣栧抚)"}),
                "image_2": ("STRING", {"default": "", "multiline": False, "tooltip": "鍙傝€冨浘2 URL (灏惧抚)"}),
                "image_3": ("STRING", {"default": "", "multiline": False, "tooltip": "鍙傝€冨浘3 URL (鍏冪礌)"}),
                "api_base": ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API绔偣鍦板潃"}),
                "api_key": ("STRING", {"default": "", "tooltip": "API瀵嗛挜"}),
                "timeout": ("INT", {"default": 1800, "min": 5, "max": 9999, "tooltip": "瓒呮椂鏃堕棿(绉?"}),
                "custom_model": ("STRING", {"default": "", "tooltip": "鑷畾涔夋ā鍨嬪悕锛堢暀绌轰娇鐢ㄤ笅鎷夋ā鍨嬶級"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("浠诲姟ID", "鐘舵€?, "鐘舵€佹洿鏂版椂闂?)
    FUNCTION = "create"
    CATEGORY = "馃崘LLAI/Veo3"

    def create(self, prompt, model, aspect_ratio, enhance_prompt, enable_upsample,
               image_1="", image_2="", image_3="",
               api_base="https://api.llaiapi.host", api_key="", timeout=120, custom_model=""):

        api_key = env_or(api_key, "KUAI_API_KEY")
        api_base = (api_base or "https://api.llaiapi.host").strip()
        endpoint = api_base.rstrip("/") + "/v1/video/create"
        effective_model = (custom_model or "").strip() or model

        images_list = []
        if image_1 and image_1.strip(): images_list.append(image_1.strip())
        if image_2 and image_2.strip(): images_list.append(image_2.strip())
        if image_3 and image_3.strip(): images_list.append(image_3.strip())

        if not images_list:
            raise RuntimeError("鍥剧敓瑙嗛妯″紡涓嬶紝璇疯嚦灏戞彁渚涗竴涓浘鐗?URL")

        payload = {
            "model": effective_model,
            "prompt": prompt,
            "images": images_list,
            "aspect_ratio": aspect_ratio,
            "enhance_prompt": bool(enhance_prompt),
            "enable_upsample": bool(enable_upsample),
        }

        try:
            resp = requests.post(endpoint, headers=http_headers_auth_only(api_key), json=payload, timeout=int(timeout))
            if resp.status_code >= 400:
                detail = _extract_error_message_from_response(resp)
                raise RuntimeError(f"鍒涘缓 Veo 瑙嗛澶辫触: {detail}")
            data = resp.json()
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"鍒涘缓 Veo 瑙嗛澶辫触: {str(e)}")

        task_id = data.get("id") or ""
        status = data.get("status") or ""
        status_update_time = int(data.get("status_update_time") or 0)

        if not task_id:
            raise RuntimeError(f"鍒涘缓鍝嶅簲缂哄皯浠诲姟 ID: {json.dumps(data, ensure_ascii=False)}")

        return (task_id, status, status_update_time)


class VeoQueryTask:
    """鏌ヨ Veo 瑙嗛浠诲姟"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "task_id": ("STRING", {"default": "", "tooltip": "浠诲姟ID"}),
            },
            "optional": {
                "api_base": ("STRING", {"default": "https://api.llaiapi.host", "tooltip": "API绔偣鍦板潃"}),
                "api_key": ("STRING", {"default": "", "tooltip": "API瀵嗛挜"}),
                "wait": ("BOOLEAN", {"default": True, "tooltip": "鏄惁绛夊緟浠诲姟瀹屾垚"}),
                "poll_interval_sec": ("INT", {"default": 15, "min": 5, "max": 90, "tooltip": "杞闂撮殧(绉?"}),
                "timeout_sec": ("INT", {"default": 1800, "min": 600, "max": 9999, "tooltip": "鎬昏秴鏃舵椂闂?绉?"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("鐘舵€?, "瑙嗛URL", "澧炲己鍚庢彁绀鸿瘝", "鍘熷鍝嶅簲JSON")
    FUNCTION = "query"
    CATEGORY = "馃崘LLAI/Veo3"

    def query(self, task_id, api_base="https://api.llaiapi.host", api_key="", wait=True, poll_interval_sec=5, timeout_sec=600):
        api_key = env_or(api_key, "KUAI_API_KEY")
        endpoint = api_base.rstrip("/") + "/v1/video/query"

        def once():
            try:
                resp = requests.get(endpoint, headers=http_headers_auth_only(api_key), params={"id": task_id}, timeout=60)
                if resp.status_code >= 400:
                    detail = _extract_error_message_from_response(resp)
                    raise RuntimeError(f"鏌ヨ澶辫触: {detail}")
                data = resp.json()
            except RuntimeError:
                raise
            except Exception as e:
                raise RuntimeError(f"鏌ヨ澶辫触: {str(e)}")

            status = data.get("status") or ""
            video_url = data.get("video_url") or ""
            enhanced_prompt = data.get("enhanced_prompt") or ""

            if status == "failed":
                fail_detail = _first_non_empty(
                    data.get("error_message"),
                    data.get("failure_reason"),
                    data.get("fail_reason"),
                    data.get("reason"),
                    data.get("message"),
                    json_get(data, "error.message", ""),
                    json_get(data, "error.detail", ""),
                    json_get(data, "result.error_message", ""),
                    json_get(data, "result.error.message", ""),
                ) or _extract_error_message_from_json(data)

                if not fail_detail:
                    fail_detail = json.dumps(data, ensure_ascii=False)

                raise RuntimeError(f"浠诲姟澶辫触: {fail_detail}")

            if status == "completed" and not str(video_url).strip():
                missing_detail = _first_non_empty(
                    data.get("error_message"),
                    data.get("message"),
                    data.get("reason"),
                ) or "浠诲姟宸插畬鎴愪絾鏈繑鍥炶棰慤RL"
                raise RuntimeError(f"鏌ヨ澶辫触: {missing_detail}")

            return status, video_url, enhanced_prompt, json.dumps(data, ensure_ascii=False)

        if not wait:
            return once()

        print(f"[VeoQueryTask] 寮€濮嬭疆璇换鍔?{task_id}锛岃秴鏃?{timeout_sec} 绉掞紝闂撮殧 {poll_interval_sec} 绉?)
        deadline = time.time() + int(timeout_sec)
        last_raw = ""
        poll_count = 0
        while time.time() < deadline:
            poll_count += 1
            status, video_url, enhanced_prompt, raw = once()
            last_raw = raw
            print(f"[VeoQueryTask] 绗?{poll_count} 娆℃煡璇? 鐘舵€?{status}")
            if status in ("completed", "failed"):
                print(f"[VeoQueryTask] 浠诲姟瀹屾垚: {status}")
                return (status, video_url, enhanced_prompt, raw)
            time.sleep(int(poll_interval_sec))
        
        print(f"[VeoQueryTask] 杞瓒呮椂")
        return ("timeout", "", "", last_raw or json.dumps({"error": "timeout"}, ensure_ascii=False))


class VeoText2VideoAndWait:
    """涓€閿枃鐢熻棰戝苟绛夊緟"""
    @classmethod
    def INPUT_TYPES(cls):
        inputs = VeoText2Video.INPUT_TYPES()
        query_inputs = VeoQueryTask.INPUT_TYPES()["optional"]
        query_inputs.pop("api_base", None)
        query_inputs.pop("api_key", None)
        inputs["optional"].update(query_inputs)
        inputs["optional"].pop("task_id", None)
        inputs["optional"].pop("wait", None)
        return inputs
    
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("鐘舵€?, "瑙嗛URL", "澧炲己鍚庢彁绀鸿瘝", "浠诲姟ID")
    FUNCTION = "run"
    CATEGORY = "馃崘LLAI/Veo3"
    
    def run(self, **kwargs):
        creator_kwargs = {k: v for k, v in kwargs.items() if k in VeoText2Video.INPUT_TYPES()["required"] or k in VeoText2Video.INPUT_TYPES()["optional"]}
        querier_kwargs = {k: v for k, v in kwargs.items() if k in VeoQueryTask.INPUT_TYPES()["optional"]}
        
        creator = VeoText2Video()
        task_id, _, _ = creator.create(**creator_kwargs)
        
        querier_kwargs["api_base"] = creator_kwargs.get("api_base", "https://api.llaiapi.host")
        querier_kwargs["api_key"] = creator_kwargs.get("api_key", "")

        querier = VeoQueryTask()
        status, video_url, enhanced_prompt, _ = querier.query(task_id=task_id, wait=True, **querier_kwargs)
        
        return (status, video_url, enhanced_prompt, task_id)

class VeoImage2VideoAndWait:
    """涓€閿浘鐢熻棰戝苟绛夊緟"""
    @classmethod
    def INPUT_TYPES(cls):
        inputs = VeoImage2Video.INPUT_TYPES()
        query_inputs = VeoQueryTask.INPUT_TYPES()["optional"]
        query_inputs.pop("api_base", None)
        query_inputs.pop("api_key", None)
        inputs["optional"].update(query_inputs)
        inputs["optional"].pop("task_id", None)
        inputs["optional"].pop("wait", None)
        return inputs

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("鐘舵€?, "瑙嗛URL", "澧炲己鍚庢彁绀鸿瘝", "浠诲姟ID")
    FUNCTION = "run"
    CATEGORY = "馃崘LLAI/Veo3"

    def run(self, **kwargs):
        creator_kwargs = {}
        # 浠?kwargs 涓垎绂诲嚭鍒涘缓鑺傜偣鐨勫弬鏁?        creator_input_types = VeoImage2Video.INPUT_TYPES()
        creator_required_keys = creator_input_types["required"].keys()
        creator_optional_keys = creator_input_types["optional"].keys()
        for k, v in kwargs.items():
            if k in creator_required_keys or k in creator_optional_keys:
                creator_kwargs[k] = v

        # 浠?kwargs 涓垎绂诲嚭鏌ヨ鑺傜偣鐨勫弬鏁?        querier_kwargs = {k: v for k, v in kwargs.items() if k in VeoQueryTask.INPUT_TYPES()["optional"]}
        
        creator = VeoImage2Video()
        task_id, _, _ = creator.create(**creator_kwargs)

        querier_kwargs["api_base"] = creator_kwargs.get("api_base", "https://api.llaiapi.host")
        querier_kwargs["api_key"] = creator_kwargs.get("api_key", "")

        querier = VeoQueryTask()
        status, video_url, enhanced_prompt, _ = querier.query(task_id=task_id, wait=True, **querier_kwargs)
        
        return (status, video_url, enhanced_prompt, task_id)


NODE_CLASS_MAPPINGS = {
    "VeoText2Video": VeoText2Video,
    "VeoImage2Video": VeoImage2Video,
    "VeoQueryTask": VeoQueryTask,
    "VeoText2VideoAndWait": VeoText2VideoAndWait,
    "VeoImage2VideoAndWait": VeoImage2VideoAndWait,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VeoText2Video": "馃幀 Veo 鏂囩敓瑙嗛",
    "VeoImage2Video": "馃崘 Veo 鍥剧敓瑙嗛",
    "VeoQueryTask": "馃攳 Veo 鏌ヨ浠诲姟",
    "VeoText2VideoAndWait": "鈿?Veo 涓€閿枃鐢熻棰?,
    "VeoImage2VideoAndWait": "鈿?Veo 涓€閿浘鐢熻棰?,
}

