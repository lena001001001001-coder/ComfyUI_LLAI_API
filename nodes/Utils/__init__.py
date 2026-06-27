"""配套能力节点模块"""

import importlib


NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
_EXPORTED_CLASS_NAMES = []


def _merge_node_module(module_name):
    try:
        module = importlib.import_module(f"{__name__}.{module_name}")
    except Exception as exc:
        print(f"[ComfyUI_LLAI_API] 跳过 Utils 节点模块 {module_name}: {exc}")
        return

    NODE_CLASS_MAPPINGS.update(getattr(module, "NODE_CLASS_MAPPINGS", {}))
    NODE_DISPLAY_NAME_MAPPINGS.update(getattr(module, "NODE_DISPLAY_NAME_MAPPINGS", {}))
    for class_name in getattr(module, "NODE_CLASS_MAPPINGS", {}).values():
        globals()[class_name.__name__] = class_name
        _EXPORTED_CLASS_NAMES.append(class_name.__name__)


for _module_name in (
    "image_upload",
    "batch_image_uploader",
    "image_urls_to_batch",
    "audio_upload",
    "deepseek_ocr",
    "video_download",
    "csv_reader",
    "show_text",
    "text_to_csv",
    "batch_process_logger",
    "batch_monitor",
    "realtime_monitor",
):
    _merge_node_module(_module_name)

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
] + _EXPORTED_CLASS_NAMES
