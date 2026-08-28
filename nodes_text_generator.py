import base64
import json
import time
from io import BytesIO

import comfy.utils  # type: ignore[reportMissingImports]
import requests

from comfy_api.latest import Types
from comfy_api_nodes.util import audio_to_base64_string
from comfy_api_nodes.util import video_to_base64_string

from .config import (
    FORMAT_MODELS,
    API_PATHS,
    get_api_base_list,
    get_config,
    get_current_base_url,
    get_node_api_key,
    save_node_settings,
)
from .utils import tensor2pil


TEXT_MAX_IMAGES = 8
class RelayTextGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            "info": ("STRING", {"default": "", "forceInput": True}),
        }
        for i in range(1, TEXT_MAX_IMAGES + 1):
            optional[f"image{i}"] = ("IMAGE",)
        optional["video"] = ("VIDEO",)
        optional["audio"] = ("AUDIO",)

        return {
            "required": {
                "prompt_template": ("STRING", {"default": "", "multiline": True}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "response")
    FUNCTION = "generate_text"
    CATEGORY = "ComfyUI_LLAI_API"

    def __init__(self):
        self.timeout = 300

    def _err(self, msg):
        full_msg = f"[RelayAPI] {msg}"
        print(full_msg)
        raise RuntimeError(full_msg)

    def _format_http_error(self, status_code, response_text, model):
        message = (response_text or "").strip() or "Unknown upstream error"
        error_code = ""
        try:
            payload = json.loads(response_text)
            error = payload.get("error", payload) if isinstance(payload, dict) else {}
            if isinstance(error, dict):
                message = str(error.get("message") or message).strip()
                error_code = str(error.get("code") or "").strip()
        except (TypeError, ValueError):
            pass

        lines = [f"HTTP {status_code}", message]
        if error_code:
            lines.append(f"code: {error_code}")
        lines.append(f"model: {model}")
        return "\n".join(lines)

    def _get_api_key(self, api_key):
        if api_key and api_key.strip():
            return api_key.strip()
        return get_config().get("api_key", "")

    def _image_to_base64(self, image_tensor):
        pil_image = tensor2pil(image_tensor)[0]
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def _video_to_base64(self, video_input):
        return video_to_base64_string(
            video_input,
            container_format=Types.VideoContainer.MP4,
            codec=Types.VideoCodec.H264,
        )

    def _audio_to_base64(self, audio_input):
        return audio_to_base64_string(
            audio_input,
            container_format="mp3",
            codec_name="libmp3lame",
        )

    def _extract_text(self, result):
        if not isinstance(result, dict):
            return ""

        direct_text = result.get("text") or result.get("output_text") or result.get("response")
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text.strip()

        choices = result.get("choices", [])
        if isinstance(choices, list):
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message", {})
                if not isinstance(message, dict):
                    continue
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
                if isinstance(content, list):
                    texts = []
                    for part in content:
                        if not isinstance(part, dict):
                            continue
                        text = part.get("text")
                        if isinstance(text, str) and text.strip():
                            texts.append(text.strip())
                    if texts:
                        return "\n".join(texts)

        candidates = result.get("candidates", [])
        if isinstance(candidates, list):
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                content = candidate.get("content", {})
                if not isinstance(content, dict):
                    continue
                parts = content.get("parts", [])
                texts = []
                if isinstance(parts, list):
                    for part in parts:
                        if not isinstance(part, dict):
                            continue
                        text = part.get("text")
                        if isinstance(text, str) and text.strip():
                            texts.append(text.strip())
                if texts:
                    return "\n".join(texts)

        return ""

    def _extract_finish_reason(self, result):
        if not isinstance(result, dict):
            return ""

        choices = result.get("choices", [])
        if isinstance(choices, list):
            for choice in choices:
                if isinstance(choice, dict):
                    reason = choice.get("finish_reason")
                    if isinstance(reason, str) and reason.strip():
                        return reason.strip()

        candidates = result.get("candidates", [])
        if isinstance(candidates, list):
            for candidate in candidates:
                if isinstance(candidate, dict):
                    reason = candidate.get("finishReason") or candidate.get("finish_reason")
                    if isinstance(reason, str) and reason.strip():
                        return reason.strip()

        return ""

    def _extract_usage(self, result):
        if not isinstance(result, dict):
            return {}

        for key in ("usage", "usageMetadata", "usage_metadata"):
            usage = result.get(key)
            if isinstance(usage, dict):
                return usage
        return {}

    def _build_response(self, result, text, platform, api_format, model, elapsed):
        payload = {
            "code": "success",
            "text": text,
            "platform": platform,
            "api_format": api_format,
            "model": model,
            "elapsed": round(elapsed, 2),
        }

        finish_reason = self._extract_finish_reason(result)
        if finish_reason:
            payload["finish_reason"] = finish_reason

        usage = self._extract_usage(result)
        if usage:
            payload["usage"] = usage

        return payload

    def _gemini_text_generate(self, base_url, api_key, model, prompt, images, video, audio, pbar):
        paths = API_PATHS.get("text_v1beta/models", {})
        path_tpl = paths.get("generate", "/v1beta/models/{model}:generateContent")
        url = f"{base_url}{path_tpl.format(model=model)}"

        parts = [{"text": prompt}]
        for i, img in enumerate(images):
            pbar.update_absolute(min(15 + i * 3, 55))
            parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": self._image_to_base64(img),
                }
            })
        if video is not None:
            pbar.update_absolute(min(15 + len(images) * 3 + 10, 55))
            parts.append({
                "inline_data": {
                    "mime_type": "video/mp4",
                    "data": self._video_to_base64(video),
                }
            })
        if audio is not None:
            pbar.update_absolute(min(15 + len(images) * 3 + 10, 55))
            parts.append({
                "inline_data": {
                    "mime_type": "audio/mpeg",
                    "data": self._audio_to_base64(audio),
                }
            })

        payload = {
            "contents": [{"role": "user", "parts": parts}],
        }

        pbar.update_absolute(60)
        print(f"[RelayAPI] POST {url} (Gemini text, {len(images)} images, timeout={self.timeout}s)")
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=self.timeout,
        )
        pbar.update_absolute(85)
        print(f"[RelayAPI] -> {resp.status_code}")
        if resp.status_code != 200:
            self._err(self._format_http_error(resp.status_code, resp.text[:500], model))
        return resp.json()

    def _openai_chat_generate(self, base_url, api_key, model, prompt, images, video, audio, pbar):
        paths = API_PATHS.get("text_v1/chat/completions", {})
        url = f"{base_url}{paths.get('chat', '/v1/chat/completions')}"

        if images or video is not None or audio is not None:
            content = [{"type": "text", "text": prompt}]
            for i, img in enumerate(images):
                pbar.update_absolute(min(15 + i * 3, 55))
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{self._image_to_base64(img)}",
                    },
                })
            if video is not None:
                content.append({
                    "type": "video_url",
                    "video_url": {
                        "url": f"data:video/mp4;base64,{self._video_to_base64(video)}",
                    },
                })
            if audio is not None:
                content.append({
                    "type": "input_audio",
                    "input_audio": {
                        "data": self._audio_to_base64(audio),
                        "format": "mp3",
                    },
                })
        else:
            content = prompt

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
        }

        pbar.update_absolute(60)
        print(f"[RelayAPI] POST {url} (OpenAI chat text, {len(images)} images, timeout={self.timeout}s)")
        resp = requests.post(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        pbar.update_absolute(85)
        print(f"[RelayAPI] -> {resp.status_code}")
        if resp.status_code != 200:
            self._err(self._format_http_error(resp.status_code, resp.text[:500], model))
        return resp.json()

    def generate_text(self, prompt, seed, info="", video=None, audio=None, prompt_template="", **kwargs):
        parsed = {}
        if info and info.strip():
            try:
                parsed = json.loads(info)
            except Exception:
                pass

        try:
            _ = seed
            api_key = self._get_api_key(parsed.get("apikey", ""))
            if not api_key:
                self._err("API key not found. Please set via Relay API Settings node.")

            raw_base = parsed.get("api_base", "")
            base_url = raw_base.strip().rstrip("/") if raw_base.strip() else get_current_base_url()
            model = (parsed.get("model", "") or "").strip()
            api_format = (parsed.get("api_format", "v1beta/models") or "").strip()
            platform = (parsed.get("platform", "GeminiText") or "").strip()
            task_type = (parsed.get("task_type", "text") or "").strip()

            if task_type != "text":
                self._err("Relay API Settings task_type must be text.")
            if platform not in {"GeminiText", "xAI", "OpenAI", "Anthropic", "智谱", "通义千问", "DeepSeek", "豆包", "OpenaiText"}:
                self._err(f"Unsupported text platform: {platform}")
            if api_format not in {"v1beta/models", "v1/chat/completions", "runninghub-/v1"}:
                self._err(f"Unsupported text api_format: {api_format}")
            if platform in {"xAI", "OpenAI", "Anthropic", "智谱", "通义千问", "DeepSeek", "豆包", "OpenaiText"} and api_format not in {"v1/chat/completions", "runninghub-/v1"}:
                self._err(f"{platform} only supports v1/chat/completions or runninghub-/v1.")
            doubao_omni_model = "doubao-seed-2-0-lite-260428"
            if audio is not None and platform != "GeminiText" and not (
                platform == "豆包" and model == doubao_omni_model
            ):
                self._err(f"{model} does not support audio input.")
            if video is not None:
                qwen_video_models = {"qwen3.5-flash", "qwen3-vl-8b-instruct"}
                if platform != "GeminiText" and not (
                    platform == "通义千问" and model in qwen_video_models
                ) and not (
                    platform == "豆包" and model == doubao_omni_model
                ):
                    self._err(f"{model} does not support video input.")
            if (video is not None or audio is not None) and platform == "GeminiText":
                if api_format != "v1beta/models":
                    print(
                        f"[RelayAPI] multimodal input detected, forcing Gemini route from {api_format} to v1beta/models"
                    )
                    api_format = "v1beta/models"

            if api_format == "runninghub-/v1":
                base_url = "https://llm.runninghub.ai"
            if not model:
                self._err("Model not found. Please set via Relay API Settings node.")

            final_prompt = prompt
            if isinstance(prompt_template, str):
                template = prompt_template.strip()
                if template and template != "prompt_template":
                    if "{prompt}" in template:
                        final_prompt = template.replace("{prompt}", prompt)
                    elif prompt.strip():
                        final_prompt = template + "\n\n" + prompt
                    else:
                        final_prompt = template

            images = []
            for i in range(1, TEXT_MAX_IMAGES + 1):
                img = kwargs.get(f"image{i}")
                if img is not None:
                    images.append(img)
            if platform == "xAI" and model == "grok-4-1-fast-reasoning" and images:
                self._err("grok-4-1-fast-reasoning does not support image input.")
            if platform == "智谱" and images:
                self._err(f"{model} does not support image input.")
            if platform == "通义千问" and model == "qwen3.7-max" and images:
                self._err("qwen3.7-max does not support image input.")
            if platform == "DeepSeek" and images:
                self._err(f"{model} does not support image input.")

            pbar = comfy.utils.ProgressBar(100)
            pbar.update_absolute(10)
            t0 = time.time()
            print(f"[RelayAPI] text | {platform} | {api_format} | {base_url} | {model}")

            if api_format == "v1beta/models":
                result = self._gemini_text_generate(base_url, api_key, model, final_prompt, images, video, audio, pbar)
            else:
                result = self._openai_chat_generate(
                    base_url, api_key, model, final_prompt, images, video, audio, pbar
                )
            text = self._extract_text(result)
            if not text:
                self._err("No text returned in text response.")

            pbar.update_absolute(100)
            elapsed = time.time() - t0
            response = json.dumps(
                self._build_response(result, text, platform, api_format, model, elapsed),
                ensure_ascii=False,
            )
            print(f"[RelayAPI] TIMING total={elapsed:.1f}s")
            return (text, response)
        except Exception as e:
            error_resp = json.dumps({"code": "error", "message": str(e)}, ensure_ascii=False)
            return ("", error_resp)


def _plain_api_key(apikey):
    key = (apikey or "").strip()
    if key and key.isascii() and "*" not in key and "\u2022" not in key:
        return key
    return ""


class RelayLLMText(RelayTextGenerator):
    PLATFORM = "GeminiText"
    API_FORMAT = "v1beta/models"
    MODEL_DEFAULT = "gemini-3-flash-preview"
    MODEL_LIST = FORMAT_MODELS.get(PLATFORM, {}).get(API_FORMAT, [MODEL_DEFAULT])

    @classmethod
    def INPUT_TYPES(cls):
        api_base_list = get_api_base_list()
        model_list = cls.MODEL_LIST if cls.MODEL_LIST else [cls.MODEL_DEFAULT]
        optional = {}
        for i in range(1, TEXT_MAX_IMAGES + 1):
            optional[f"image{i}"] = ("IMAGE",)
        optional["video"] = ("VIDEO",)
        optional["audio"] = ("AUDIO",)

        return {
            "required": {
                "task_type": (["text"], {"default": "text"}),
                "platform": ([cls.PLATFORM], {"default": cls.PLATFORM}),
                "api_format": ([cls.API_FORMAT], {"default": cls.API_FORMAT}),
                "api_base": (api_base_list, {"default": api_base_list[0]}),
                "model": (model_list, {"default": cls.MODEL_DEFAULT}),
                "apikey": ("STRING", {"default": ""}),
                "prompt_template": ("STRING", {"default": "", "multiline": True}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            },
            "optional": optional,
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "response")
    FUNCTION = "generate_llm_text"
    CATEGORY = "ComfyUI_LLAI_API"

    def _build_info(self, api_base, model, apikey, unique_id, platform=None, api_format=None):
        base_url = (api_base or "").strip().rstrip("/") or get_current_base_url()
        plain_key = _plain_api_key(apikey)

        if plain_key:
            save_node_settings(unique_id, api_key=plain_key, base_url=base_url)
            real_key = plain_key
        else:
            save_node_settings(unique_id, base_url=base_url)
            real_key = get_node_api_key(unique_id) or get_config().get("api_key", "")

        return json.dumps({
            "apikey": real_key,
            "api_base": base_url,
            "model": model or self.MODEL_DEFAULT,
            "platform": platform or self.PLATFORM,
            "api_format": api_format or self.API_FORMAT,
            "task_type": "text",
        })

    def generate_llm_text(self, task_type, platform, api_format, api_base, model,
                          apikey, prompt_template, prompt, seed,
                          unique_id=None, video=None, audio=None, **kwargs):
        info = self._build_info(api_base, model, apikey, unique_id)
        if not json.loads(info).get("apikey"):
            self._err("API key not found. Please set apikey on Relay LLM Text.")
        return self.generate_text(
            prompt=prompt,
            seed=seed,
            info=info,
            video=video,
            audio=audio,
            prompt_template=prompt_template,
            **kwargs,
        )


class RelayLLMTextBatch(RelayLLMText):
    """Batch variant: run the existing LLM text request once per prompt item."""

    API_BASE = "https://api.llaiapi.host"
    PLATFORM_CONFIG = {
        "GeminiText": {
            "api_format": "v1beta/models",
            "models": ["gemini-3-flash-preview", "gemini-3.5-flash", "gemini-3.6-flash"],
        },
        "xAI": {
            "api_format": "v1/chat/completions",
            "models": ["grok-4.5", "grok-4-1-fast-reasoning"],
        },
        "OpenAI": {
            "api_format": "v1/chat/completions",
            "models": ["gpt-5.6-sol", "gpt-5-pro", "gpt-4o-mini"],
        },
        "Anthropic": {
            "api_format": "v1/chat/completions",
            "models": ["claude-fable-5", "claude-opus-4-8", "claude-opus-4-1-20250805"],
        },
        "智谱": {
            "api_format": "v1/chat/completions",
            "models": ["glm-5", "glm-4-flash"],
        },
        "通义千问": {
            "api_format": "v1/chat/completions",
            "models": ["qwen3.7-max", "qwen3.5-flash", "qwen3-vl-8b-instruct"],
        },
        "DeepSeek": {
            "api_format": "v1/chat/completions",
            "models": ["deepseek-v4-flash", "deepseek-v3"],
        },
        "豆包": {
            "api_format": "v1/chat/completions",
            "models": [
                "doubao-seed-2-1-pro-260628",
                "doubao-seed-2-0-lite-260428",
                "doubao-seed-1-8-251228",
                "doubao-seed-1-6-vision-250815",
            ],
        },
    }
    MODEL_LIST = [
        model
        for platform_config in PLATFORM_CONFIG.values()
        for model in platform_config["models"]
    ]

    @classmethod
    def INPUT_TYPES(cls):
        schema = super().INPUT_TYPES()
        schema["required"].pop("prompt", None)
        schema["required"]["platform"] = (
            list(cls.PLATFORM_CONFIG),
            {"default": cls.PLATFORM},
        )
        schema["required"]["api_format"] = (
            list(dict.fromkeys(config["api_format"] for config in cls.PLATFORM_CONFIG.values())),
            {"default": cls.API_FORMAT},
        )
        schema["required"]["api_base"] = ("STRING", {
            "default": cls.API_BASE,
            "tooltip": "固定使用 LLAI API 中转站",
        })
        # Keep the template as an explicit multiline widget for batch prompts.
        # Use a placeholder so the hint is not submitted as prompt content.
        schema["required"]["prompt_template"] = ("STRING", {
            "default": "",
            "multiline": True,
            "placeholder": "You are a assistant...",
            "tooltip": "可选：使用 {prompt} 插入每条列表内容；留空则直接发送原列表项",
        })
        schema["required"]["prompt_context"] = ("STRING", {
            "default": "",
            "multiline": True,
            "placeholder": "输入提示词...",
            "tooltip": "未连接提示词列表时作为单条提示词；连接后追加到每条列表提示词",
        })
        schema["optional"]["prompt_list"] = ("LIST", {"forceInput": True})
        return schema

    @classmethod
    def INPUT_LABELS(cls):
        labels = dict(super().INPUT_LABELS()) if hasattr(super(), "INPUT_LABELS") else {}
        labels["prompt_template"] = "提示词模板（可选）"
        labels["prompt_context"] = "单条/附加提示词"
        labels["prompt_list"] = "提示词列表"
        return labels

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "response")
    OUTPUT_IS_LIST = (True, True)
    FUNCTION = "generate_llm_text_batch"

    def generate_llm_text_batch(self, task_type, platform, api_format, api_base, model,
                                apikey, prompt_template, prompt_context, prompt_list=None, seed=0,
                                unique_id=None, video=None, audio=None, **kwargs):
        if isinstance(prompt_list, str):
            prompts = [prompt_list] if prompt_list.strip() else []
        elif isinstance(prompt_list, (list, tuple)):
            prompts = [str(item) for item in prompt_list if str(item).strip()]
        elif prompt_list is None:
            prompts = []
        else:
            raise ValueError("prompt_list 必须是字符串列表")

        platform_config = self.PLATFORM_CONFIG.get(platform)
        if not platform_config:
            raise ValueError(f"不支持的语言模型平台: {platform}")
        if model not in platform_config["models"]:
            raise ValueError(f"模型 {model} 不属于 {platform} 平台")
        api_format = platform_config["api_format"]

        prompt_context = (prompt_context or "").strip()
        use_context_as_prompt = not prompts
        if use_context_as_prompt:
            if not prompt_context:
                raise ValueError("请连接提示词列表，或输入一条单条提示词")
            prompts = [prompt_context]

        info = self._build_info(
            self.API_BASE,
            model,
            apikey,
            unique_id,
            platform=platform,
            api_format=api_format,
        )
        if not json.loads(info).get("apikey"):
            self._err("API key not found. Please set apikey on Relay LLM Text Batch.")

        texts, responses = [], []
        for index, item in enumerate(prompts, start=1):
            print(f"[LLAI] LLM batch item {index}/{len(prompts)}")
            batch_prompt = item
            if prompt_context and not use_context_as_prompt:
                batch_prompt = f"{item}\n\n{prompt_context}"
            text, response = self.generate_text(
                prompt=batch_prompt,
                seed=seed,
                info=info,
                video=video,
                audio=audio,
                prompt_template=prompt_template,
                **kwargs,
            )
            try:
                response_payload = json.loads(response)
            except (TypeError, ValueError):
                response_payload = {}
            if isinstance(response_payload, dict) and response_payload.get("code") == "error":
                message = str(response_payload.get("message") or "语言模型请求失败").strip()
                if "model:" not in message:
                    message = f"{message}\nmodel: {model}"
                raise RuntimeError(message)
            texts.append(text)
            responses.append(response)
        return (texts, responses)
