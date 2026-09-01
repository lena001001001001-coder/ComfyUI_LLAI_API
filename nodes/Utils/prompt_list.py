"""提示词列表节点。"""


class LLAIPromptList:
    """将多个多行提示词输入整理为列表。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_1": ("STRING", {"multiline": True, "default": ""}),
                "prompt_2": ("STRING", {"multiline": True, "default": ""}),
                "prompt_3": ("STRING", {"multiline": True, "default": ""}),
                "prompt_4": ("STRING", {"multiline": True, "default": ""}),
                "prompt_5": ("STRING", {"multiline": True, "default": ""}),
                "prompt_6": ("STRING", {"multiline": True, "default": ""}),
                "prompt_7": ("STRING", {"multiline": True, "default": ""}),
                "prompt_8": ("STRING", {"multiline": True, "default": ""}),
                "prompt_9": ("STRING", {"multiline": True, "default": ""}),
                "prompt_10": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                **{
                    f"prompt_{index}": ("STRING", {"multiline": True, "default": ""})
                    for index in range(11, 51)
                },
            },
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt_1": "提示词 1",
            "prompt_2": "提示词 2",
            "prompt_3": "提示词 3",
            "prompt_4": "提示词 4",
            "prompt_5": "提示词 5",
            "prompt_6": "提示词 6",
            "prompt_7": "提示词 7",
            "prompt_8": "提示词 8",
            "prompt_9": "提示词 9",
            "prompt_10": "提示词 10",
            **{f"prompt_{index}": f"提示词 {index}" for index in range(11, 51)},
        }

    RETURN_TYPES = ("LIST", "STRING")
    RETURN_NAMES = ("prompt_list", "prompt_strings")
    OUTPUT_IS_LIST = (False, True)
    FUNCTION = "build_prompt_list"
    CATEGORY = "LLAI/Utils"

    def build_prompt_list(
        self,
        prompt_1="",
        prompt_2="",
        prompt_3="",
        prompt_4="",
        prompt_5="",
        prompt_6="",
        prompt_7="",
        prompt_8="",
        prompt_9="",
        prompt_10="",
        **kwargs,
    ):
        prompts = []
        prompts.extend(
            (prompt_1, prompt_2, prompt_3, prompt_4, prompt_5,
             prompt_6, prompt_7, prompt_8, prompt_9, prompt_10,
             *(kwargs.get(f"prompt_{index}", "") for index in range(11, 51)))
        )
        prompts = [item for item in prompts if isinstance(item, str) and item.strip()]
        return (prompts, prompts)


NODE_CLASS_MAPPINGS = {
    "LLAIPromptList": LLAIPromptList,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLAIPromptList": "LL-提示词列表",
}
