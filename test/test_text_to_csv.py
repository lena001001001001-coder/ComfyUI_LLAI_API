#!/usr/bin/env python3
"""Tests for text-to-CSV helper node."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_text_to_csv_display_name():
    from nodes.Utils.text_to_csv import NODE_DISPLAY_NAME_MAPPINGS

    assert NODE_DISPLAY_NAME_MAPPINGS["LLAIBatchTextToCSV"] == "LL-Batch Text To CSV"

