import json
import time

import comfy.utils  # type: ignore[reportMissingImports]
import requests
from comfy.comfy_types import IO  # type: ignore[reportMissingImports]
from comfy_api.latest import io as comfy_io  # type: ignore[reportMissingImports]
from comfy_api.latest import ui as comfy_ui  # type: ignore[reportMissingImports]
from comfy_api_nodes.util import audio_bytes_to_audio_input  # type: ignore[reportMissingImports]
from comfy_execution.graph_utils import ExecutionBlocker  # type: ignore[reportMissingImports]


DEFAULT_BASE_URL = "https://api.llaiapi.host"
DEFAULT_MODEL = "suno_music_open"
SOUND_GENERATION_MODES = ["description", "lyrics"]
SOUND_VERSIONS = ["V3", "V3.5", "V4", "V4.5", "V4.5+", "V5", "V5.5"]
SOUND_VERSION_MODEL_MAP = {
    "V3": "chirp-v3.0",
    "V3.5": "chirp-v3.5",
    "V4": "chirp-v4",
    "V4.5": "chirp-auk",
    "V4.5+": "chirp-bluejay",
    "V5": "chirp-crow",
    "V5.5": "chirp-fenix",
}


class RelaySunoDirectGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("STRING", {"default": "", "password": True}),
                "generation_mode": (SOUND_GENERATION_MODES, {"default": SOUND_GENERATION_MODES[0]}),
                "prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "Song description or lyrics prompt",
                    },
                ),
                "title": ("STRING", {"default": "", "placeholder": "Song title"}),
                "tags": ("STRING", {"default": "", "placeholder": "pop, electronic, cinematic"}),
                "make_instrumental": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": "Instrumental",
                        "label_off": "With vocals",
                    },
                ),
                "version": (SOUND_VERSIONS, {"default": "V5"}),
            },
            "optional": {
                "model": ("STRING", {"default": DEFAULT_MODEL, "placeholder": "suno_music_open"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
                "negative_tags": ("STRING", {"default": "", "placeholder": "optional negative style"}),
                "extend_mode": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": "Extend",
                        "label_off": "Normal",
                    },
                ),
                "continue_clip_id": ("STRING", {"default": "", "placeholder": "previous clip_id"}),
                "continue_at": ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.1}),
                "poll_timeout": ("INT", {"default": 3600, "min": 60, "max": 86400}),
            },
        }

    RETURN_TYPES = (IO.AUDIO, "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio", "clip_id", "task_id", "response", "audio_url")
    FUNCTION = "generate_sound"
    CATEGORY = "RelayAPI"

    def __init__(self):
        self.timeout = 120

    def _err(self, msg):
        full_msg = f"[RelayAPI] {msg}"
        print(full_msg)
        raise RuntimeError(full_msg)

    def _headers(self, api_key):
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _post_json(self, url, api_key, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return requests.post(url, headers=self._headers(api_key), data=body, timeout=self.timeout)

    def _task_id_from(self, result):
        if not isinstance(result, dict):
            return ""
        for key in ("task_id", "taskId", "id", "request_id"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        data = result.get("data")
        if isinstance(data, str) and data.strip():
            return data.strip()
        if isinstance(data, dict):
            for key in ("task_id", "taskId", "id", "request_id", "data"):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        return ""

    def _status_from(self, result):
        data = result.get("data")
        if isinstance(data, dict) and data.get("taskStatus"):
            return str(data.get("taskStatus"))
        if isinstance(data, dict) and data.get("status"):
            return str(data.get("status"))
        if result.get("taskStatus"):
            return str(result.get("taskStatus"))
        if result.get("status"):
            return str(result.get("status"))
        return ""

    def _progress_from(self, result):
        data = result.get("data")
        if isinstance(data, dict) and data.get("progress") is not None:
            return data.get("progress")
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            for item in data["items"]:
                if isinstance(item, dict) and item.get("progress") is not None:
                    return item.get("progress")
        if result.get("progress") is not None:
            return result.get("progress")
        return None

    def _walk_containers(self, value):
        if isinstance(value, dict):
            yield value
            for key in ("data", "clips", "songs", "items", "result_data", "output"):
                nested = value.get(key)
                if isinstance(nested, (dict, list)):
                    yield from self._walk_containers(nested)
        elif isinstance(value, list):
            for item in value:
                yield from self._walk_containers(item)

    def _extract_audio_url(self, result):
        for container in self._walk_containers(result):
            for key in (
                "audio_url",
                "audioUrl",
                "cld2AudioUrl",
                "source_audio_url",
                "sourceAudioUrl",
                "download_url",
                "downloadUrl",
                "output_url",
                "outputUrl",
                "url",
            ):
                val = container.get(key)
                if self._is_valid_audio_url(val):
                    return val
        return ""

    def _extract_clip_id(self, result):
        for container in self._walk_containers(result):
            for key in ("clip_id", "clipId", "id", "song_id", "songId"):
                val = container.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        return ""

    def _is_valid_audio_url(self, url):
        if not isinstance(url, str):
            return False
        cleaned = url.strip()
        if not cleaned.startswith("http"):
            return False
        return "/none." not in cleaned.lower() and cleaned.lower() not in {
            "none",
            "null",
            "undefined",
        }

    def _extract_failure_reason(self, result):
        reasons = []
        data = result.get("data")
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            for item in data["items"]:
                if not isinstance(item, dict):
                    continue
                item_status = item.get("status")
                invalid_url = item.get("cld2AudioUrl") and not self._is_valid_audio_url(item.get("cld2AudioUrl"))
                if item_status in (40, "40") or invalid_url:
                    reason = (
                        item.get("errorMsg")
                        or item.get("errorMsgEn")
                        or item.get("failReason")
                        or item.get("progressMsg")
                        or "Suno returned an invalid audio URL"
                    )
                    clip_id = item.get("clipId") or item.get("clip_id") or item.get("id") or ""
                    reasons.append(f"{clip_id}: {reason}" if clip_id else str(reason))

        for container in self._walk_containers(result):
            for key in ("errorMsg", "errorMsgEn", "fail_reason", "failReason"):
                val = container.get(key)
                if isinstance(val, str) and val.strip() and val.strip() not in reasons:
                    reasons.append(val.strip())

        return "; ".join(reasons)

    def _build_payload(self, generation_mode, title, tags, prompt, make_instrumental, version, model, negative_tags, extend_mode, continue_clip_id, continue_at):
        mv = SOUND_VERSION_MODEL_MAP.get(version, "chirp-crow")
        cleaned_prompt = (prompt or "").strip()
        cleaned_title = (title or "").strip()
        cleaned_tags = (tags or "").strip()
        cleaned_model = (model or DEFAULT_MODEL).strip() or DEFAULT_MODEL
        payload = {
            "model": cleaned_model,
            "mv": mv,
        }

        if generation_mode == SOUND_GENERATION_MODES[0]:
            payload["gpt_description_prompt"] = cleaned_prompt
            payload["prompt"] = ""
            if cleaned_title:
                payload["title"] = cleaned_title
            if cleaned_tags:
                payload["tags"] = cleaned_tags
            if make_instrumental:
                payload["make_instrumental"] = True
        else:
            payload["title"] = cleaned_title
            payload["tags"] = cleaned_tags
            payload["prompt"] = "" if make_instrumental else cleaned_prompt

        neg = (negative_tags or "").strip()
        if neg:
            payload["negative_tags"] = neg

        if extend_mode:
            clip_id = (continue_clip_id or "").strip()
            if not clip_id:
                self._err("continue_clip_id is required when extend mode is enabled.")
            payload["continue_clip_id"] = clip_id
            payload["continue_at"] = max(0, int(float(continue_at)))
            payload["task"] = "extend"

        return payload, mv

    def _query(self, api_key, task_id):
        url = f"{DEFAULT_BASE_URL}/suno/fetch/{task_id}"
        resp = requests.get(url, headers={"Accept": "application/json", "Authorization": f"Bearer {api_key}"}, timeout=30)
        if resp.status_code != 200:
            print(f"[RelayAPI] Suno query -> {resp.status_code}: {resp.text[:300]}")
            return None
        try:
            return resp.json()
        except Exception as e:
            print(f"[RelayAPI] Suno query JSON parse error: {e}")
            return None

    def _poll(self, api_key, task_id, poll_timeout, pbar):
        start = time.time()
        while time.time() - start <= poll_timeout:
            time.sleep(5)
            try:
                result = self._query(api_key, task_id)
                if not result:
                    continue

                status = self._status_from(result).lower()
                progress = self._progress_from(result)
                if status or progress is not None:
                    print(f"[RelayAPI] Suno poll | status={status or '<empty>'} | progress={progress}")

                audio_url = self._extract_audio_url(result)
                if audio_url:
                    clip_id = self._extract_clip_id(result)
                    return {"clip_id": clip_id, "audio_url": audio_url, "result": result}

                failure_reason = self._extract_failure_reason(result)
                if failure_reason:
                    self._err(f"Suno task failed: {failure_reason}")

                if any(flag in status for flag in ("fail", "error", "cancel")):
                    data = result.get("data") or {}
                    if not isinstance(data, dict):
                        data = {}
                    reason = data.get("fail_reason") or result.get("message") or status
                    self._err(f"Suno task failed: {reason}")

                if isinstance(progress, str) and progress.endswith("%"):
                    try:
                        pbar.update_absolute(min(90, 40 + int(progress[:-1]) // 2))
                    except ValueError:
                        pass
                elif isinstance(progress, (int, float)):
                    pbar.update_absolute(min(90, 40 + int(progress) // 2))

                if any(flag in status for flag in ("finished", "success", "succeed", "complete", "completed", "done")):
                    self._err(f"Suno task completed without audio URL: {json.dumps(result, ensure_ascii=False)[:500]}")
            except requests.exceptions.Timeout:
                continue
            except RuntimeError:
                raise
            except Exception as e:
                print(f"[RelayAPI] Suno poll exception: {e}")
                continue

        self._err(f"Suno polling timeout after {round(time.time() - start, 1)}s")

    def _download_audio(self, url):
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.content

    def generate_sound(
        self,
        api_key,
        generation_mode,
        prompt,
        title,
        tags,
        make_instrumental,
        version,
        model=DEFAULT_MODEL,
        seed=0,
        negative_tags="",
        extend_mode=False,
        continue_clip_id="",
        continue_at=0.0,
        poll_timeout=3600,
    ):
        clip_id = ""
        task_id = ""
        audio_url = ""

        try:
            api_key = (api_key or "").strip()
            if not api_key:
                self._err("API key is required.")

            if generation_mode == SOUND_GENERATION_MODES[0]:
                if not (prompt or "").strip():
                    self._err("Song description cannot be empty.")
            else:
                if not (title or "").strip():
                    self._err("Title is required in custom lyrics mode.")
                if not (tags or "").strip():
                    self._err("Tags are required in custom lyrics mode.")
                if not make_instrumental and not (prompt or "").strip():
                    self._err("Lyrics or composition prompt is required in custom lyrics mode.")

            pbar = comfy.utils.ProgressBar(100)
            pbar.update_absolute(10)

            payload, mv = self._build_payload(
                generation_mode=generation_mode,
                title=title,
                tags=tags,
                prompt=prompt,
                make_instrumental=make_instrumental,
                version=version,
                model=model,
                negative_tags=negative_tags,
                extend_mode=extend_mode,
                continue_clip_id=continue_clip_id,
                continue_at=continue_at,
            )
            submit_url = f"{DEFAULT_BASE_URL}/suno/submit/music"
            print(f"[RelayAPI] POST {submit_url} (Suno direct, model={payload.get('model')}, mv={mv})")
            resp = self._post_json(submit_url, api_key, payload)
            print(f"[RelayAPI] -> {resp.status_code}")
            if resp.status_code != 200:
                self._err(f"Suno create error: {resp.status_code} - {resp.text[:500]}")

            submit_result = resp.json()
            task_id = self._task_id_from(submit_result)
            if not task_id:
                self._err(f"No task ID returned: {json.dumps(submit_result, ensure_ascii=False)[:500]}")
            print(f"[RelayAPI] Suno task: {task_id}")

            pbar.update_absolute(40)
            poll_result = self._poll(api_key, task_id, int(poll_timeout), pbar)
            clip_id = str(poll_result.get("clip_id") or "")
            audio_url = str(poll_result.get("audio_url") or "")

            if not audio_url:
                self._err("Suno task completed without audio_url.")

            print(f"[RelayAPI] Downloading audio: {audio_url}")
            audio_bytes = self._download_audio(audio_url)
            audio_input = audio_bytes_to_audio_input(audio_bytes)
            pbar.update_absolute(100)

            response_payload = {
                "code": "success",
                "submit": submit_result,
                "query": poll_result.get("result"),
                "model": (model or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
                "mv": mv,
                "seed": int(seed),
                "seed_note": "ComfyUI rerun control only; seed is not sent to Suno API.",
                "api_base": DEFAULT_BASE_URL,
            }
            return (
                audio_input,
                clip_id,
                task_id,
                json.dumps(response_payload, ensure_ascii=False),
                audio_url,
            )

        except Exception as e:
            response_payload = json.dumps({"code": "error", "message": str(e)}, ensure_ascii=False)
            return (ExecutionBlocker(None), clip_id, task_id, response_payload, audio_url)


class RelaySunoDirectPlayer(RelaySunoDirectGenerator):
    RETURN_TYPES = (IO.AUDIO, "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio", "clip_id", "task_id", "response", "audio_url")
    FUNCTION = "generate_sound"
    CATEGORY = "RelayAPI"
    OUTPUT_NODE = True

    def generate_sound(self, *args, **kwargs):
        result = super().generate_sound(*args, **kwargs)
        audio = result[0]
        if isinstance(audio, ExecutionBlocker):
            return result

        ui = comfy_ui.AudioSaveHelper.get_save_audio_ui(
            audio,
            filename_prefix="audio/RelaySunoDirect",
            cls=None,
            format="mp3",
            quality="128k",
        ).as_dict()
        return comfy_io.NodeOutput(*result, ui=ui)
