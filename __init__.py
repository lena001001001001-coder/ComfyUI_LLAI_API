from .nodes_api_settings import RelayAPISettings
from .nodes_video_generator import RelayGrokVideo, RelayVideoGenerator
from .nodes_image_generator import RelayBanana2ImageGenerator, RelayGPTImage2Generator, RelayImageGenerator
from .nodes_notice import RelayAPINotice
from .nodes_sound_generator import RelaySoundGenerator
from .nodes_suno_direct import RelaySunoDirectGenerator, RelaySunoDirectPlayer
from .nodes_text_generator import RelayLLMText, RelayLLMTextBatch
from .nodes_grok_imagine_video import RelayGrokImagineVideo
from .nodes.GPTImage import GPTImage2CLowCost4K
from .nodes.Doubao import (
    LLDoubaoSeedream40BatchTextToImage,
    LLDoubaoSeedream40TextToImage,
    LLDoubaoSeedream45TextToImage,
    LLDoubaoSeedream50ProTextToImage,
    LLDoubaoSeedream40ImageToImage,
    LLDoubaoSeedream45ImageToImage,
    LLDoubaoSeedream50ProImageToImage,
)
from .nodes.Utils.excel_csv_lord import LLExcelCSVLord

try:
    import importlib.util
    import os

    _text_to_csv_path = os.path.join(os.path.dirname(__file__), "nodes", "Utils", "text_to_csv.py")
    _text_to_csv_spec = importlib.util.spec_from_file_location(
        "comfyui_llai_api_text_to_csv",
        _text_to_csv_path,
    )
    _text_to_csv_module = importlib.util.module_from_spec(_text_to_csv_spec)
    _text_to_csv_spec.loader.exec_module(_text_to_csv_module)
    TEXT_TO_CSV_NODE_CLASS_MAPPINGS = _text_to_csv_module.NODE_CLASS_MAPPINGS
    TEXT_TO_CSV_NODE_DISPLAY_NAME_MAPPINGS = _text_to_csv_module.NODE_DISPLAY_NAME_MAPPINGS
except Exception as exc:
    print(f"[ComfyUI_LLAI_API] Batch Text To CSV 节点加载失败: {exc}")
    TEXT_TO_CSV_NODE_CLASS_MAPPINGS = {}
    TEXT_TO_CSV_NODE_DISPLAY_NAME_MAPPINGS = {}

try:
    from .config import register_routes
    register_routes()
except Exception:
    pass

NODE_CLASS_MAPPINGS = {
    "RelayVideoGenerator": RelayGrokVideo,
    "RelayGPTImage2Generator": RelayGPTImage2Generator,
    "RelayBanana2ImageGenerator": RelayBanana2ImageGenerator,
    "RelayAPINotice": RelayAPINotice,
    "RelaySunoDirectPlayer": RelaySunoDirectPlayer,
    "RelayLLMText": RelayLLMText,
    "RelayLLMTextBatch": RelayLLMTextBatch,
    "RelayGrokImagineVideo": RelayGrokImagineVideo,
    "GPTImage2CLowCost4K": GPTImage2CLowCost4K,
    "LLDoubaoSeedream45TextToImage": LLDoubaoSeedream45TextToImage,
    "LLDoubaoSeedream40TextToImage": LLDoubaoSeedream40TextToImage,
    "LLDoubaoSeedream40BatchTextToImage": LLDoubaoSeedream40BatchTextToImage,
    "LLDoubaoSeedream50ProTextToImage": LLDoubaoSeedream50ProTextToImage,
    "LLDoubaoSeedream40ImageToImage": LLDoubaoSeedream40ImageToImage,
    "LLDoubaoSeedream45ImageToImage": LLDoubaoSeedream45ImageToImage,
    "LLDoubaoSeedream50ProImageToImage": LLDoubaoSeedream50ProImageToImage,
    "LL-Excel-CSV-Lord": LLExcelCSVLord,
}
NODE_CLASS_MAPPINGS.update(TEXT_TO_CSV_NODE_CLASS_MAPPINGS)

NODE_DISPLAY_NAME_MAPPINGS = {
    "RelayVideoGenerator": "LL-Grok Video",
    "RelayGPTImage2Generator": "LL-GPT-Image2 Generator",
    "RelayBanana2ImageGenerator": "LL-Banana-image",
    "RelayAPINotice": "LL-API Notice",
    "RelaySunoDirectPlayer": "LL-Suno Direct Player",
    "RelayLLMText": "LL-LLM Text",
    "RelayLLMTextBatch": "LL-LLM Text Batch",
    "RelayGrokImagineVideo": "LL-grok-imagine-video",
    "GPTImage2CLowCost4K": "LL-gpt-image-2-c-低价4k",
    "LLDoubaoSeedream45TextToImage": "LL-doubao-seedream-4.5-文生图",
    "LLDoubaoSeedream40TextToImage": "LL-doubao-seedream-4.0-文生图",
    "LLDoubaoSeedream40BatchTextToImage": "LL-doubao-seedream-4.0-文生图-批量",
    "LLDoubaoSeedream50ProTextToImage": "LL-doubao-seedream-5.0pro-文生图",
    "LLDoubaoSeedream40ImageToImage": "LL-doubao-seedream-4.0-图生图",
    "LLDoubaoSeedream45ImageToImage": "LL-doubao-seedream-4.5-图生图(慢)",
    "LLDoubaoSeedream50ProImageToImage": "LL-doubao-seedream-5.0pro-图生图",
    "LL-Excel-CSV-Lord": "LL-Excel-CSV-Lord",
}
NODE_DISPLAY_NAME_MAPPINGS.update(TEXT_TO_CSV_NODE_DISPLAY_NAME_MAPPINGS)

WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']







