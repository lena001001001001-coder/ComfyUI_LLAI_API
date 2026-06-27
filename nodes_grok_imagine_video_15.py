import json
import os
import tempfile
import time
from io import BytesIO

import requests
import folder_paths  # type: ignore[reportMissingImports]
from comfy.comfy_types import IO  # type: ignore[reportMissingImports]
from comfy_api.latest._input_impl.video_types import VideoFromFile  # type: ignore[reportMissingImports]

from .utils import tensor2pil
from .config import get_current_base_url


GROK_IMAGINE_VIDEO_15_RESOLUTIONS = ["480p", "720p"]
GROK_IMAGINE_VIDEO_15_ASPECT_RATIOS = ["1:1", "16:9", "9:16"]
GROK_IMAGINE_VIDEO_15_DURATIONS = ["4", "6", "10", "15"]


def _download_video_to_tempfile(url, timeout=120, headers=None):
    resp = requests.get(url, headers=headers, stream=True, timeout=timeout)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    ext = ".mp4"
    if "webm" in content_type:
        ext = ".webm"
    elif "quicktime" in content_type:
        ext = ".mov"
    temp_dir = folder_paths.get_temp_directory()
    os.makedirs(temp_dir, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(suffix=ext, dir=temp_dir)
    try:
        with os.fdopen(fd, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception:
        os.unlink(temp_path)
        raise
    return temp_path


class RelayGrokImagineVideo15:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "model": (["grok-imagine-video-1.5-preview"], {"default": "grok-imagine-video-1.5-preview"}),
                "api_key": ("STRING", {"default": ""}),
                "resolution": (GROK_IMAGINE_VIDEO_15_RESOLUTIONS, {"default": "720p"}),
                "aspect_ratio": (GROK_IMAGINE_VIDEO_15_ASPECT_RATIOS, {"default": "16:9"}),
                "duration": (GROK_IMAGINE_VIDEO_15_DURATIONS, {"default": "4"}),
            },
            "optional": {
                "image": ("IMAGE", {"forceInput": True}),
            },
        }

    RETURN_TYPES = (IO.VIDEO, "STRING", "STRING", "STRING")
    RETURN_NAMES = ("video", "task_id", "response", "video_url")
    FUNCTION = "generate_grok_imagine_video_15"
    CATEGORY = "ComfyUI_LLAI_API"

    def __init__(self):
        self.timeout = 300

    def _err(self, msg):
        full_msg = "[llaiapi] " + msg
        print(full_msg)
        raise RuntimeError(full_msg)

    def _headers_auth(self, api_key):
        return {"Authorization": "Bearer " + api_key}

    def _response_json(self, resp, context):
        try:
            return resp.json()
        except ValueError:
            body = (resp.text or "").strip() or "<empty response body>"
            self._err(context + " returned non-JSON response: HTTP " + str(resp.status_code) + " - " + body[:500])

    def _first_string(self, raw, keys):
        if isinstance(raw, dict):
            for key in keys:
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    return value
                if isinstance(value, dict):
                    nested = self._first_string(value, keys)
                    if nested:
                        return nested
        if isinstance(raw, list):
            for item in raw:
                nested = self._first_string(item, keys)
                if nested:
                    return nested
        return ""

    def _unwrap_payload(self, raw):
        if not isinstance(raw, dict):
            return {}
        data_field = raw.get("data")
        if isinstance(data_field, dict):
            merged = dict(data_field)
            for key in ("fail_reason", "last_error", "error", "message", "video_url", "url", "download_url", "output_url", "file_url", "status", "state"):
                if key not in merged and key in raw:
                    merged[key] = raw[key]
            return merged
        return raw

    def _extract_video_url(self, data):
        if not isinstance(data, dict):
            return ""
        for key in ("video_url", "url", "download_url", "output_url", "file_url", "output"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, dict):
                nested = self._extract_video_url(value)
                if nested:
                    return nested
        for nest_key in ("video", "data", "result"):
            nested = data.get(nest_key)
            if isinstance(nested, dict):
                found = self._extract_video_url(nested)
                if found:
                    return found
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        found = self._extract_video_url(item)
                        if found:
                            return found
                    elif isinstance(item, str) and item.strip():
                        return item
        return ""

    def _extract_status(self, raw):
        payload = self._unwrap_payload(raw)
        status = payload.get("status") or payload.get("state") or raw.get("status") or raw.get("state") or ""
        return str(status).lower().strip(), payload

    def _image_to_base64_uri(self, image_tensor):
        try:
            import base64
            pil_image = tensor2pil(image_tensor)[0]
            buffered = BytesIO()
            pil_image.save(buffered, format="PNG")
            b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return "data:image/png;base64," + b64
        except Exception as e:
            self._err("Error converting image to base64: " + str(e))

    def _normalize_prompt(self, prompt):
        value = str(prompt or "").strip()
        if not value:
            self._err("prompt 不能为空，请先填写后再运行")
        return value

    def _submit(self, base_url, api_key, model, prompt, resolution, aspect_ratio, duration, image):
        url = base_url.rstrip("/") + "/v1/videos/generations"
        payload = {
            "model": model or "grok-imagine-video-1.5-preview",
            "prompt": prompt,
            "resolution": str(resolution or "").strip(),
            "aspect_ratio": str(aspect_ratio or "").strip(),
            "duration": int(duration),
        }
        if not payload["aspect_ratio"]:
            payload["aspect_ratio"] = "16:9"
        if image is not None:
            payload["image"] = {"url": image}
        print("[llaiapi] POST " + url)
        print("[llaiapi] payload=" + json.dumps(payload, ensure_ascii=False)[:800])
        resp = requests.post(url, headers=self._headers_auth(api_key), json=payload, timeout=self.timeout)
        print("[llaiapi] -> " + str(resp.status_code))
        if resp.status_code != 200:
            self._err("grok-imagine-video-1.5 create error: " + str(resp.status_code) + " - " + resp.text[:500])
        raw = self._response_json(resp, "grok-imagine-video-1.5 create " + url)
        task_id = raw.get("task_id") or raw.get("id") or raw.get("request_id") or self._first_string(raw, ["task_id", "id", "request_id"])
        if not task_id:
            self._err("grok-imagine-video-1.5 create response missing task id")
        return str(task_id), raw, payload

    def _query(self, base_url, api_key, task_id):
        url = base_url.rstrip("/") + f"/v1/videos/{task_id}"
        resp = requests.get(url, headers=self._headers_auth(api_key), timeout=self.timeout)
        if resp.status_code != 200:
            self._err("grok-imagine-video-1.5 query error: " + str(resp.status_code) + " - " + resp.text[:500])
        raw = self._response_json(resp, "grok-imagine-video-1.5 query " + url)
        status, payload = self._extract_status(raw)
        video_url = self._extract_video_url(payload) or self._extract_video_url(raw)
        return status, video_url, raw

    def _poll(self, base_url, api_key, task_id, poll_interval, max_wait_time):
        start = time.time()
        last_status = ""
        while True:
            status, video_url, raw = self._query(base_url, api_key, task_id)
            last_status = status
            print("[llaiapi] grok-imagine-video-1.5 poll status=" + str(status) + " video_url=" + (video_url or ""))
            if video_url and status in ("success", "succeed", "completed", "complete", "done", "finished", "succeeded"):
                return video_url, raw
            if status in ("fail", "failed", "error", "cancel", "cancelled", "canceled"):
                self._err("grok-imagine-video-1.5 task failed: " + json.dumps(raw, ensure_ascii=False)[:500])
            if video_url and not status:
                return video_url, raw
            if time.time() - start >= max_wait_time:
                hint = " last_status=" + last_status if last_status else ""
                self._err("grok-imagine-video-1.5 timeout after " + str(max_wait_time) + "s" + hint)
            time.sleep(max(1, int(poll_interval)))

    def generate_grok_imagine_video_15(self, prompt, model, api_key, resolution, aspect_ratio, duration, image=None):
        base_url = get_current_base_url()
        prompt = self._normalize_prompt(prompt)
        api_key = str(api_key or "").strip()
        if not api_key:
            self._err("API key not found. Please fill api_key first.")
        if image is None:
            self._err("grok-imagine-video-1.5-preview 需要上传图像，请先连接一张参考图再运行")
        image_url = self._image_to_base64_uri(image)
        task_id, submit_raw, payload = self._submit(base_url, api_key, model, prompt, resolution, aspect_ratio, duration, image_url)
        video_url, query_raw = self._poll(base_url, api_key, task_id, 5, 1200)
        temp_path = _download_video_to_tempfile(video_url, headers=self._headers_auth(api_key))
        result = {
            "task_id": task_id,
            "submit": submit_raw,
            "query": query_raw,
            "payload": payload,
            "video_url": video_url,
        }
        return (VideoFromFile(temp_path), task_id, json.dumps(result, ensure_ascii=False, indent=2), video_url)


NODE_CLASS_MAPPINGS = {
    "RelayGrokImagineVideo15": RelayGrokImagineVideo15,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RelayGrokImagineVideo15": "LL-grok-imagine-video-1.5",
}
