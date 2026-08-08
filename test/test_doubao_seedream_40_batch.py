"""Offline checks for the Doubao Seedream 4.0 sequential batch node."""

import json

import pytest
import torch


def test_seedream_40_batch_registration_and_interface():
    from nodes.Doubao import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    key = "LLDoubaoSeedream40BatchTextToImage"
    node_class = NODE_CLASS_MAPPINGS[key]
    inputs = node_class.INPUT_TYPES()

    assert NODE_DISPLAY_NAME_MAPPINGS[key] == "LL-doubao-seedream-4.0-文生图-批量"
    assert inputs["required"]["batch_count"] == (
        "INT",
        {
            "default": 1,
            "min": 1,
            "max": 2000,
            "step": 1,
            "tooltip": "按相同参数依次生成的批量数量（1-2000）",
        },
    )
    assert node_class.INPUT_LABELS()["batch_count"] == "批量"


def test_seedream_40_batch_calls_original_sequentially(monkeypatch):
    from nodes.Doubao import doubao_seedream_40_batch as module

    calls = []

    def fake_generate(self, **kwargs):
        calls.append(kwargs)
        index = len(calls)
        return (
            torch.full((1, 2, 2, 3), index, dtype=torch.float32),
            f"https://example.com/{index}.jpeg",
            json.dumps({"request": index}),
        )

    monkeypatch.setattr(module.LLDoubaoSeedream40TextToImage, "generate", fake_generate)
    monkeypatch.setattr(
        module.LLDoubaoSeedream40BatchTextToImage,
        "_create_progress_bar",
        staticmethod(lambda total: None),
    )

    image, refs, summary = module.LLDoubaoSeedream40BatchTextToImage().generate(
        prompt="星际列车",
        size="2K",
        watermark=False,
        response_format="url",
        api_key="sk-test",
        seed=123,
        batch_count=3,
        timeout=60,
        ratio="2048x2048（1:1 方图）",
    )

    assert len(calls) == 3
    assert tuple(image.shape) == (3, 2, 2, 3)
    assert refs.splitlines() == [
        "https://example.com/1.jpeg",
        "https://example.com/2.jpeg",
        "https://example.com/3.jpeg",
    ]
    parsed_summary = json.loads(summary)
    assert parsed_summary["requested_batches"] == 3
    assert parsed_summary["completed_batches"] == 3
    assert parsed_summary["image_count"] == 3
    assert parsed_summary["responses"] == [{"request": 1}, {"request": 2}, {"request": 3}]


@pytest.mark.parametrize("batch_count", [0, 2001])
def test_seedream_40_batch_rejects_out_of_range(batch_count):
    from nodes.Doubao.doubao_seedream_40_batch import LLDoubaoSeedream40BatchTextToImage

    with pytest.raises(ValueError, match="1 到 2000"):
        LLDoubaoSeedream40BatchTextToImage().generate(
            prompt="cat",
            size="2K",
            watermark=False,
            response_format="url",
            api_key="sk-test",
            seed=0,
            batch_count=batch_count,
            ratio="2048x2048（1:1 方图）",
        )
