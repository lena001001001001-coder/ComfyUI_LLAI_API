import importlib
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DummyProgressBar:
    def __init__(self, _steps=100):
        pass

    def update_absolute(self, _value):
        pass


comfy = types.ModuleType("comfy")
comfy.utils = types.SimpleNamespace(ProgressBar=DummyProgressBar)
sys.modules.setdefault("comfy", comfy)
sys.modules.setdefault("comfy.utils", comfy.utils)

comfy_api = types.ModuleType("comfy_api")
comfy_api_latest = types.ModuleType("comfy_api.latest")
comfy_api_latest.Types = types.SimpleNamespace(
    VideoContainer=types.SimpleNamespace(MP4="mp4"),
    VideoCodec=types.SimpleNamespace(H264="h264"),
)
sys.modules.setdefault("comfy_api", comfy_api)
sys.modules.setdefault("comfy_api.latest", comfy_api_latest)

comfy_api_nodes = types.ModuleType("comfy_api_nodes")
comfy_api_nodes_util = types.ModuleType("comfy_api_nodes.util")
comfy_api_nodes_util.audio_to_base64_string = lambda *_args, **_kwargs: ""
comfy_api_nodes_util.video_to_base64_string = lambda *_args, **_kwargs: ""
sys.modules.setdefault("comfy_api_nodes", comfy_api_nodes)
sys.modules.setdefault("comfy_api_nodes.util", comfy_api_nodes_util)

package = types.ModuleType("llai_text_batch_test")
package.__path__ = [str(ROOT)]
sys.modules.setdefault("llai_text_batch_test", package)

utils = types.ModuleType("llai_text_batch_test.utils")
utils.tensor2pil = lambda _image: []
sys.modules.setdefault("llai_text_batch_test.utils", utils)

text_generator_module = importlib.import_module("llai_text_batch_test.nodes_text_generator")
RelayLLMTextBatch = text_generator_module.RelayLLMTextBatch


def test_llm_text_batch_offers_separate_model_platforms():
    input_types = RelayLLMTextBatch.INPUT_TYPES()
    model_input = input_types["required"]["model"]

    assert input_types["required"]["platform"][0] == [
        "GeminiText",
        "xAI",
        "OpenAI",
        "Anthropic",
        "智谱",
        "通义千问",
        "DeepSeek",
        "豆包",
    ]
    assert input_types["required"]["api_format"][0] == [
        "v1beta/models",
        "v1/chat/completions",
    ]
    assert model_input[0] == [
        "gemini-3-flash-preview",
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "grok-4.5",
        "grok-4-1-fast-reasoning",
        "gpt-5.6-sol",
        "gpt-5-pro",
        "gpt-4o-mini",
        "claude-fable-5",
        "claude-opus-4-8",
        "claude-opus-4-1-20250805",
        "glm-5",
        "glm-4-flash",
        "qwen3.7-max",
        "qwen3.5-flash",
        "qwen3-vl-8b-instruct",
        "deepseek-v4-flash",
        "deepseek-v3",
        "doubao-seed-2-1-pro-260628",
        "doubao-seed-2-0-lite-260428",
        "doubao-seed-1-8-251228",
        "doubao-seed-1-6-vision-250815",
    ]
    assert model_input[1]["default"] == "gemini-3-flash-preview"
    assert input_types["required"]["api_base"] == (
        "STRING",
        {
            "default": "https://api.llaiapi.host",
            "tooltip": "固定使用 LLAI API 中转站",
        },
    )
    assert input_types["required"]["prompt_template"][1]["default"] == ""
    assert input_types["required"]["prompt_template"][1]["placeholder"] == "You are a assistant..."
    assert "prompt_list" not in input_types["required"]
    assert input_types["optional"]["prompt_list"][1]["forceInput"] is True


def _make_batch_node():
    node = RelayLLMTextBatch()
    node.built_info = []

    def build_info(api_base, model, _apikey, _unique_id, platform=None, api_format=None):
        node.built_info.append((api_base, platform, api_format, model))
        return json.dumps({"apikey": "test-key"})

    node._build_info = build_info
    node.generate_text = lambda **kwargs: (kwargs["prompt"], "{}")
    return node


def test_llm_text_batch_uses_single_prompt_without_list_input():
    node = _make_batch_node()

    texts, _responses = node.generate_llm_text_batch(
        "text", "GeminiText", "v1beta/models", "https://api.llaiapi.host",
        "gemini-3-flash-preview", "test-key", "", "单条提示词", seed=1,
    )

    assert texts == ["单条提示词"]
    assert node.built_info == [(
        "https://api.llaiapi.host",
        "GeminiText",
        "v1beta/models",
        "gemini-3-flash-preview",
    )]


def test_llm_text_batch_routes_xai_to_openai_chat_format():
    node = _make_batch_node()

    texts, _responses = node.generate_llm_text_batch(
        "text", "xAI", "v1beta/models", "https://wrong.example",
        "grok-4.5", "test-key", "", "介绍一下你自己", seed=1,
    )

    assert texts == ["介绍一下你自己"]
    assert node.built_info == [(
        "https://api.llaiapi.host",
        "xAI",
        "v1/chat/completions",
        "grok-4.5",
    )]


def test_llm_text_batch_routes_openai_to_chat_completions():
    node = _make_batch_node()

    texts, _responses = node.generate_llm_text_batch(
        "text", "OpenAI", "v1beta/models", "https://wrong.example",
        "gpt-5.6-sol", "test-key", "", "分析这段内容", seed=1,
    )

    assert texts == ["分析这段内容"]
    assert node.built_info == [(
        "https://api.llaiapi.host",
        "OpenAI",
        "v1/chat/completions",
        "gpt-5.6-sol",
    )]


def test_llm_text_batch_routes_anthropic_to_chat_completions():
    node = _make_batch_node()

    texts, _responses = node.generate_llm_text_batch(
        "text", "Anthropic", "v1beta/models", "https://wrong.example",
        "claude-fable-5", "test-key", "", "总结输入内容", seed=1,
    )

    assert texts == ["总结输入内容"]
    assert node.built_info == [(
        "https://api.llaiapi.host",
        "Anthropic",
        "v1/chat/completions",
        "claude-fable-5",
    )]


def test_llm_text_batch_routes_zhipu_to_chat_completions():
    node = _make_batch_node()

    texts, _responses = node.generate_llm_text_batch(
        "text", "智谱", "v1beta/models", "https://wrong.example",
        "glm-5", "test-key", "", "编写摘要", seed=1,
    )

    assert texts == ["编写摘要"]
    assert node.built_info == [(
        "https://api.llaiapi.host",
        "智谱",
        "v1/chat/completions",
        "glm-5",
    )]


def test_llm_text_batch_routes_qwen_to_chat_completions():
    node = _make_batch_node()

    texts, _responses = node.generate_llm_text_batch(
        "text", "通义千问", "v1beta/models", "https://wrong.example",
        "qwen3.5-flash", "test-key", "", "分析视频", seed=1,
    )

    assert texts == ["分析视频"]
    assert node.built_info == [(
        "https://api.llaiapi.host",
        "通义千问",
        "v1/chat/completions",
        "qwen3.5-flash",
    )]


def test_llm_text_batch_routes_deepseek_to_chat_completions():
    node = _make_batch_node()

    texts, _responses = node.generate_llm_text_batch(
        "text", "DeepSeek", "v1beta/models", "https://wrong.example",
        "deepseek-v4-flash", "test-key", "", "分析文本", seed=1,
    )

    assert texts == ["分析文本"]
    assert node.built_info == [(
        "https://api.llaiapi.host",
        "DeepSeek",
        "v1/chat/completions",
        "deepseek-v4-flash",
    )]


def test_llm_text_batch_routes_doubao_to_chat_completions():
    node = _make_batch_node()

    texts, _responses = node.generate_llm_text_batch(
        "text", "豆包", "v1beta/models", "https://wrong.example",
        "doubao-seed-2-0-lite-260428", "test-key", "", "分析内容", seed=1,
    )

    assert texts == ["分析内容"]
    assert node.built_info == [(
        "https://api.llaiapi.host",
        "豆包",
        "v1/chat/completions",
        "doubao-seed-2-0-lite-260428",
    )]


def test_openai_chat_payload_includes_qwen_video_data_uri():
    node = RelayLLMTextBatch()
    node._video_to_base64 = lambda _video: "encoded-video"
    captured = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "视频说明"}}]}

    original_post = text_generator_module.requests.post

    def fake_post(_url, **kwargs):
        captured["payload"] = kwargs["json"]
        return FakeResponse()

    text_generator_module.requests.post = fake_post
    try:
        node._openai_chat_generate(
            "https://api.llaiapi.host",
            "test-key",
            "qwen3.5-flash",
            "描述视频",
            [],
            object(),
            None,
            DummyProgressBar(),
        )
    finally:
        text_generator_module.requests.post = original_post

    assert captured["payload"]["messages"][0]["content"] == [
        {"type": "text", "text": "描述视频"},
        {
            "type": "video_url",
            "video_url": {"url": "data:video/mp4;base64,encoded-video"},
        },
    ]


def test_openai_chat_payload_includes_doubao_audio():
    node = RelayLLMTextBatch()
    node._audio_to_base64 = lambda _audio: "encoded-audio"
    captured = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "音频说明"}}]}

    original_post = text_generator_module.requests.post

    def fake_post(_url, **kwargs):
        captured["payload"] = kwargs["json"]
        return FakeResponse()

    text_generator_module.requests.post = fake_post
    try:
        node._openai_chat_generate(
            "https://api.llaiapi.host",
            "test-key",
            "doubao-seed-2-0-lite-260428",
            "转写音频",
            [],
            None,
            object(),
            DummyProgressBar(),
        )
    finally:
        text_generator_module.requests.post = original_post

    assert captured["payload"]["messages"][0]["content"] == [
        {"type": "text", "text": "转写音频"},
        {
            "type": "input_audio",
            "input_audio": {"data": "encoded-audio", "format": "mp3"},
        },
    ]


def test_grok_fast_reasoning_rejects_image_input():
    node = RelayLLMTextBatch()
    info = json.dumps({
        "apikey": "test-key",
        "api_base": "https://api.llaiapi.host",
        "model": "grok-4-1-fast-reasoning",
        "platform": "xAI",
        "api_format": "v1/chat/completions",
        "task_type": "text",
    })

    text, response = node.generate_text("测试", 1, info=info, image1=object())

    assert text == ""
    assert "does not support image input" in json.loads(response)["message"]


def test_zhipu_models_reject_image_input():
    node = RelayLLMTextBatch()
    info = json.dumps({
        "apikey": "test-key",
        "api_base": "https://api.llaiapi.host",
        "model": "glm-5",
        "platform": "智谱",
        "api_format": "v1/chat/completions",
        "task_type": "text",
    })

    text, response = node.generate_text("测试", 1, info=info, image1=object())

    assert text == ""
    assert "does not support image input" in json.loads(response)["message"]


def test_qwen_37_max_rejects_media_input():
    node = RelayLLMTextBatch()
    info = json.dumps({
        "apikey": "test-key",
        "api_base": "https://api.llaiapi.host",
        "model": "qwen3.7-max",
        "platform": "通义千问",
        "api_format": "v1/chat/completions",
        "task_type": "text",
    })

    image_text, image_response = node.generate_text("测试", 1, info=info, image1=object())
    video_text, video_response = node.generate_text("测试", 1, info=info, video=object())

    assert image_text == ""
    assert "does not support image input" in json.loads(image_response)["message"]
    assert video_text == ""
    assert "does not support video input" in json.loads(video_response)["message"]


def test_deepseek_models_reject_image_input():
    node = RelayLLMTextBatch()
    info = json.dumps({
        "apikey": "test-key",
        "api_base": "https://api.llaiapi.host",
        "model": "deepseek-v4-flash",
        "platform": "DeepSeek",
        "api_format": "v1/chat/completions",
        "task_type": "text",
    })

    text, response = node.generate_text("测试", 1, info=info, image1=object())

    assert text == ""
    assert "does not support image input" in json.loads(response)["message"]


def test_doubao_non_omni_models_reject_audio_and_video():
    node = RelayLLMTextBatch()
    info = json.dumps({
        "apikey": "test-key",
        "api_base": "https://api.llaiapi.host",
        "model": "doubao-seed-2-1-pro-260628",
        "platform": "豆包",
        "api_format": "v1/chat/completions",
        "task_type": "text",
    })

    audio_text, audio_response = node.generate_text("测试", 1, info=info, audio=object())
    video_text, video_response = node.generate_text("测试", 1, info=info, video=object())

    assert audio_text == ""
    assert "does not support audio input" in json.loads(audio_response)["message"]
    assert video_text == ""
    assert "does not support video input" in json.loads(video_response)["message"]


def test_llm_text_batch_appends_context_when_list_is_connected():
    node = _make_batch_node()

    texts, _responses = node.generate_llm_text_batch(
        "text", "GeminiText", "v1beta/models", "https://api.llaiapi.host",
        "gemini-3-flash-preview", "test-key", "", "公共说明",
        prompt_list=["提示词一", "提示词二"], seed=1,
    )

    assert texts == ["提示词一\n\n公共说明", "提示词二\n\n公共说明"]


def test_openai_chat_formats_upstream_error_for_comfyui():
    node = RelayLLMTextBatch()

    class FakeResponse:
        status_code = 429
        text = json.dumps({
            "error": {
                "message": "当前分组上游负载已饱和，请稍后再试",
                "code": "model_not_found",
            },
        }, ensure_ascii=False)

    original_post = text_generator_module.requests.post
    text_generator_module.requests.post = lambda *_args, **_kwargs: FakeResponse()
    try:
        try:
            node._openai_chat_generate(
                "https://api.llaiapi.host", "test-key",
                "doubao-seed-2-1-pro-260628", "测试", [], None, None,
                DummyProgressBar(),
            )
            raise AssertionError("Expected the upstream error to be raised")
        except RuntimeError as exc:
            message = str(exc)
    finally:
        text_generator_module.requests.post = original_post

    assert "HTTP 429" in message
    assert "当前分组上游负载已饱和，请稍后再试" in message
    assert "code: model_not_found" in message
    assert "model: doubao-seed-2-1-pro-260628" in message


def test_llm_text_batch_raises_item_error_instead_of_returning_empty_text():
    node = _make_batch_node()
    node.generate_text = lambda **_kwargs: (
        "",
        json.dumps({
            "code": "error",
            "message": "[RelayAPI] HTTP 429\n当前分组上游负载已饱和，请稍后再试\ncode: model_not_found",
        }, ensure_ascii=False),
    )

    try:
        node.generate_llm_text_batch(
            "text", "豆包", "v1/chat/completions", "https://api.llaiapi.host",
            "doubao-seed-2-1-pro-260628", "test-key", "", "测试", seed=1,
        )
        raise AssertionError("Expected the batch node to raise the item error")
    except RuntimeError as exc:
        message = str(exc)

    assert "HTTP 429" in message
    assert "code: model_not_found" in message
    assert "model: doubao-seed-2-1-pro-260628" in message


if __name__ == "__main__":
    test_llm_text_batch_offers_separate_model_platforms()
    test_llm_text_batch_uses_single_prompt_without_list_input()
    test_llm_text_batch_routes_xai_to_openai_chat_format()
    test_llm_text_batch_routes_openai_to_chat_completions()
    test_llm_text_batch_routes_anthropic_to_chat_completions()
    test_llm_text_batch_routes_zhipu_to_chat_completions()
    test_llm_text_batch_routes_qwen_to_chat_completions()
    test_llm_text_batch_routes_deepseek_to_chat_completions()
    test_llm_text_batch_routes_doubao_to_chat_completions()
    test_openai_chat_payload_includes_qwen_video_data_uri()
    test_openai_chat_payload_includes_doubao_audio()
    test_grok_fast_reasoning_rejects_image_input()
    test_zhipu_models_reject_image_input()
    test_qwen_37_max_rejects_media_input()
    test_deepseek_models_reject_image_input()
    test_doubao_non_omni_models_reject_audio_and_video()
    test_llm_text_batch_appends_context_when_list_is_connected()
    test_openai_chat_formats_upstream_error_for_comfyui()
    test_llm_text_batch_raises_item_error_instead_of_returning_empty_text()
    print("LLM text batch inputs: OK")
