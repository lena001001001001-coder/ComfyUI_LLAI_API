"""Tests for the LLAI prompt list utility node."""

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "nodes" / "Utils" / "prompt_list.py"
SPEC = importlib.util.spec_from_file_location("llai_prompt_list", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
LLAIPromptList = MODULE.LLAIPromptList


def test_prompt_list_exposes_list_and_string_outputs():
    assert LLAIPromptList.RETURN_TYPES == ("LIST", "STRING")
    assert LLAIPromptList.RETURN_NAMES == ("prompt_list", "prompt_strings")
    assert LLAIPromptList.OUTPUT_IS_LIST == (False, True)


def test_prompt_list_returns_each_prompt_for_both_outputs():
    result = LLAIPromptList().build_prompt_list(
        prompt_1="first prompt",
        prompt_2="   ",
        prompt_3="third prompt",
        prompt_11="eleventh prompt",
    )

    expected = ["first prompt", "third prompt", "eleventh prompt"]
    assert result == (expected, expected)


if __name__ == "__main__":
    test_prompt_list_exposes_list_and_string_outputs()
    test_prompt_list_returns_each_prompt_for_both_outputs()
    print("Prompt list tests passed")
