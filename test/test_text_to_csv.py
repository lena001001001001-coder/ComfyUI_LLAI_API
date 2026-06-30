#!/usr/bin/env python3
"""Tests for text-to-CSV helper node."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_text_to_csv_display_name():
    from nodes.Utils.text_to_csv import NODE_DISPLAY_NAME_MAPPINGS

    assert NODE_DISPLAY_NAME_MAPPINGS["LLAIBatchTextToCSV"] == "LL-Batch Text To CSV"


def test_text_to_csv_chinese_labels_are_readable():
    from nodes.Utils.text_to_csv import LLAIBatchTextToCSV

    input_types = LLAIBatchTextToCSV.INPUT_TYPES()
    labels = LLAIBatchTextToCSV.INPUT_LABELS()

    assert input_types["required"]["text"][1]["default"] == (
        "暗底上分布着白、蓝、橙色花卉与枝叶，呈现优雅复古的插画印花风格。"
    )
    assert labels["text"] == "文本"
    assert labels["output_mode"] == "输出模式"
    assert LLAIBatchTextToCSV.RETURN_NAMES == ("CSV路径", "CSV预览")


def test_text_to_csv_description_explains_outputs():
    from nodes.Utils.text_to_csv import LLAIBatchTextToCSV

    assert "CSV路径" in LLAIBatchTextToCSV.DESCRIPTION
    assert "CSV预览" in LLAIBatchTextToCSV.DESCRIPTION
    assert "这两个接口都可以不连接" in LLAIBatchTextToCSV.DESCRIPTION

