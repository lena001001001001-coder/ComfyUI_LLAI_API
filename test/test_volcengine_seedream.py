import io
import base64

import pytest
import torch
from PIL import Image


def test_registration_and_inputs():
    from nodes.Volcengine import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    from nodes.Volcengine.volcengine_seedream import ENDPOINT, IMAGE_INPUT_NAMES, LLVolcengineSeedream

    assert NODE_CLASS_MAPPINGS["LLVolcengineSeedream"] is LLVolcengineSeedream
    assert NODE_DISPLAY_NAME_MAPPINGS["LLVolcengineSeedream"] == "LL-火山方舟"
    assert ENDPOINT == "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    inputs = LLVolcengineSeedream.INPUT_TYPES()
    assert inputs["optional"]["image"][0] == "IMAGE"
    assert len(IMAGE_INPUT_NAMES) == 14
    assert all(inputs["optional"][name][0] == "IMAGE" for name in IMAGE_INPUT_NAMES)
    assert list(inputs["required"])[0] == "api_key"
    assert inputs["required"]["api_key"][1]["default"] == ""
    assert inputs["required"]["api_key"][1]["placeholder"] == "ark-..."
    assert inputs["required"]["model"][1]["default"] == "Doubao-Seedream-4.5"


def test_official_model_size_mappings():
    from nodes.Volcengine.volcengine_seedream import resolve_size

    assert resolve_size("Doubao-Seedream-4.0", "1K", "16:9") == "1280x720"
    assert resolve_size("Doubao-Seedream-4.5", "4K", "9:16") == "3040x5504"
    assert resolve_size("Doubao-Seedream-5.0-lite", "3K", "4:3") == "3456x2592"
    assert resolve_size("Doubao-Seedream-5.0-lite 260128", "3K", "4:3") == "3456x2592"
    assert resolve_size("Doubao-Seedream-5.0-pro", "1.5K", "21:9") == "2352x1008"
    with pytest.raises(ValueError, match="不支持"):
        resolve_size("Doubao-Seedream-4.5", "1K", "1:1")


def test_payload_model_differences_and_modes():
    from nodes.Volcengine.volcengine_seedream import build_payload

    normal = build_payload("Doubao-Seedream-4.0", "测试", "2K", "1:1")
    assert normal["model"] == "doubao-seedream-4-0-250828"
    assert normal["sequential_image_generation"] == "disabled"
    assert normal["stream"] is False
    assert "image" not in normal

    pro = build_payload("Doubao-Seedream-5.0-pro", "编辑", "2K", "16:9", ["data:image/png;base64,abc"])
    assert pro["image"] == "data:image/png;base64,abc"
    assert "sequential_image_generation" not in pro
    assert "stream" not in pro
    assert "seed" not in pro


def test_sensitive_image_error_is_translated_to_chinese():
    from nodes.Volcengine.volcengine_seedream import _raise_for_volcengine_error

    class Response:
        status_code = 400
        text = ""
        @staticmethod
        def json():
            return {"error": {
                "code": "InputImageSensitiveContentDetected",
                "message": "The input image may contain sensitive information. Request id: 021787900163499b566464da517b102b4cb09cdfd60e7ee971153",
            }}

    with pytest.raises(RuntimeError) as error:
        _raise_for_volcengine_error(Response())
    message = str(error.value)
    assert "触发火山方舟内容审核" in message
    assert "输入参考图可能包含敏感内容" in message
    assert "InputImageSensitiveContentDetected" in message
    assert "021787900163499b566464da517b102b4cb09cdfd60e7ee971153" in message


def test_unknown_volcengine_error_keeps_official_details():
    from nodes.Volcengine.volcengine_seedream import _raise_for_volcengine_error

    class Response:
        status_code = 429
        text = ""
        @staticmethod
        def json():
            return {"error": {"code": "RateLimitExceeded", "message": "Too many requests"}}

    with pytest.raises(RuntimeError, match="HTTP 429.*RateLimitExceeded.*Too many requests"):
        _raise_for_volcengine_error(Response())


def test_image_size_limit_stops_before_request(monkeypatch):
    from nodes.Volcengine import volcengine_seedream as module

    class OversizeBuffer(io.BytesIO):
        def tell(self):
            return module.MAX_IMAGE_BYTES + 1

    monkeypatch.setattr(module, "to_pil_from_comfy", lambda *_args, **_kwargs: Image.new("RGB", (16, 16)))
    monkeypatch.setattr(module.io, "BytesIO", OversizeBuffer)
    called = False

    class Session:
        trust_env = True

        def post(self, *_args, **_kwargs):
            nonlocal called
            called = True

    monkeypatch.setattr(module.requests, "Session", Session)
    with pytest.raises(ValueError, match="火山限制单图不超过 30MB"):
        module.LLVolcengineSeedream().generate(
            api_key="test", model="Doubao-Seedream-4.0", resolution="1K", ratio="1:1",
            prompt="测试", seed=1, image=torch.zeros((1, 16, 16, 3)), timeout=30,
        )
    assert called is False


def test_reference_image_long_edge_is_scaled_to_6000(monkeypatch):
    from nodes.Volcengine import volcengine_seedream as module

    monkeypatch.setattr(module, "to_pil_from_comfy", lambda *_args, **_kwargs: Image.new("RGB", (7000, 1000)))
    data_url = module._image_data_url(None, 0)
    image_bytes = base64.b64decode(data_url.split(",", 1)[1])
    with Image.open(io.BytesIO(image_bytes)) as image:
        assert image.size == (6000, 857)


def test_direct_request_and_batch_images(monkeypatch):
    from nodes.Volcengine import volcengine_seedream as module

    captured = {}

    class Response:
        status_code = 200
        text = ""
        def json(self):
            return {"data": [{"b64_json": "YWJj"}]}
        def raise_for_status(self):
            return None

    class Session:
        trust_env = True
        def post(self, url, json, headers, timeout):
            captured.update(url=url, payload=json, headers=headers, timeout=timeout, trust_env=self.trust_env)
            return Response()

    monkeypatch.setattr(module.requests, "Session", Session)
    monkeypatch.setattr(module, "_image_data_url", lambda _image, index: f"data:image/png;base64,{index}")
    monkeypatch.setattr(module, "_outputs_to_tensor_and_refs", lambda *_args: ("tensor", ""))
    result = module.LLVolcengineSeedream().generate(
        api_key="volc-key", model="Doubao-Seedream-5.0-lite", resolution="2K", ratio="1:1",
        prompt="测试", seed=9, image=torch.zeros((2, 2, 2, 3)), timeout=60,
    )
    assert result[0] == "tensor"
    assert captured["url"] == module.ENDPOINT
    assert captured["headers"]["Authorization"] == "Bearer volc-key"
    assert captured["trust_env"] is False
    assert captured["payload"]["image"] == ["data:image/png;base64,0", "data:image/png;base64,1"]
    assert "api.llaiapi.host" not in captured["url"]


def test_multiple_ports_and_batches_are_flattened(monkeypatch):
    from nodes.Volcengine import volcengine_seedream as module

    captured = {}

    class Response:
        status_code = 200
        text = ""
        def json(self):
            return {"data": [{"b64_json": "YWJj"}]}
        def raise_for_status(self):
            return None

    class Session:
        trust_env = True
        def post(self, _url, json, **_kwargs):
            captured["payload"] = json
            return Response()

    monkeypatch.setattr(module.requests, "Session", Session)
    monkeypatch.setattr(module, "_image_data_url", lambda image, index: f"ref-{int(image[0, 0, 0, 0])}-{index}")
    monkeypatch.setattr(module, "_outputs_to_tensor_and_refs", lambda *_args: ("tensor", ""))
    module.LLVolcengineSeedream().generate(
        api_key="key", model="Doubao-Seedream-4.5", resolution="2K", ratio="1:1",
        prompt="测试", seed=1, image=torch.ones((2, 2, 2, 3)),
        image_2=torch.full((1, 2, 2, 3), 2.0), timeout=60,
    )
    assert captured["payload"]["image"] == ["ref-1-0", "ref-1-1", "ref-2-0"]


def test_pro_rejects_more_than_ten_images_before_encoding(monkeypatch):
    from nodes.Volcengine import volcengine_seedream as module

    called = False
    def encode(*_args):
        nonlocal called
        called = True

    monkeypatch.setattr(module, "_image_data_url", encode)
    with pytest.raises(ValueError, match="最多支持 10 张参考图，当前为 11 张"):
        module.LLVolcengineSeedream().generate(
            api_key="key", model="Doubao-Seedream-5.0-pro", resolution="2K", ratio="1:1",
            prompt="测试", seed=1, image=torch.zeros((10, 2, 2, 3)),
            image_2=torch.zeros((1, 2, 2, 3)), timeout=60,
        )
    assert called is False
