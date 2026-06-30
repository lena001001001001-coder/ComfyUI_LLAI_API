"""Save generated text batches to CSV files."""

import csv
import io
import json
import os
import re
from typing import Any

try:
    import folder_paths
except Exception:  # Allows local tests outside ComfyUI.
    folder_paths = None


class LLAIBatchTextToCSV:
    """Convert one or more text outputs into CSV files."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "暗底上分布着白、蓝、橙色花卉与枝叶，呈现优雅复古的插画印花风格。",
                    },
                ),
                "filename_prefix": ("STRING", {"default": ""}),
                "output_mode": (
                    [
                        "单个保存",
                        "批量合并保存",
                    ],
                    {"default": "单个保存"},
                ),
                "include_header": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "output_file_path": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "placeholder": "可填输出文件夹或 .csv 文件路径",
                    },
                ),
                "custom_header": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "hidden": True,
                        "placeholder": "用英文逗号分隔，例如 text",
                    },
                ),
            },
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "text": "文本",
            "filename_prefix": "文件名前缀",
            "output_mode": "输出模式",
            "include_header": "包含表头",
            "output_file_path": "输出路径",
            "custom_header": "自定义表头",
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("CSV路径", "CSV预览")
    FUNCTION = "write_csv"
    OUTPUT_NODE = True
    CATEGORY = "ComfyUI_LLAI_API"
    DESCRIPTION = (
        "将输入文本保存为 CSV 文件。\n\n"
        "右侧 2 个输出接口：\n"
        "- CSV路径：输出刚刚保存出来的 CSV 文件完整路径，可给后续节点继续读取，或用于确认文件保存位置。\n"
        "- CSV预览：输出本次写入的 CSV 文本内容，可接到 Show Text 等文本显示节点直接预览。\n\n"
        "如果只是想把文本保存成 CSV 文件，这两个接口都可以不连接，节点执行后会直接保存文件。"
    )

    def write_csv(
        self,
        text: Any,
        filename_prefix: str,
        output_mode: str,
        include_header: bool,
        output_file_path: str = "",
        custom_header: str = "",
    ):
        effective_mode = MODE_ALIASES.get(output_mode, output_mode)
        rows = parse_batch_text_rows(text)
        header = parse_custom_header(custom_header)

        if include_header and not header:
            header = ["text"]

        if effective_mode == "批量合并保存":
            return append_csv_rows(rows, filename_prefix, output_file_path, header)

        if header:
            rows = [header] + rows

        csv_text = rows_to_csv(rows)
        csv_path = save_csv(csv_text, filename_prefix, output_file_path)
        return (csv_path, csv_text)


MODE_ALIASES = {
    "鍗曚釜淇濆瓨": "单个保存",
    "鎵归噺鍚堝苟淇濆瓨": "批量合并保存",
    "single_text_single_csv": "单个保存",
    "batch_text_single_csv": "批量合并保存",
    "batch_single_outputs": "单个保存",
    "batch_single_csv": "批量合并保存",
}


def parse_custom_header(header: str) -> list[str]:
    if not header.strip():
        return []
    return [part.strip() for part in header.split(",") if part.strip()]


def parse_batch_text_rows(text: Any) -> list[list[str]]:
    if isinstance(text, (list, tuple)):
        return [[stringify_cell(item).strip()] for item in text if stringify_cell(item).strip()]

    value = stringify_cell(text).strip()
    return [[value]] if value else []


def stringify_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def rows_to_csv(rows: list[list[Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    return output.getvalue()


def save_csv(csv_text: str, filename_prefix: str, output_file_path: str = "") -> str:
    path = get_csv_output_path(filename_prefix, output_file_path)
    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        file.write(csv_text)
    return path


def append_csv_rows(
    rows: list[list[Any]],
    filename_prefix: str,
    output_file_path: str = "",
    header: list[str] | None = None,
) -> tuple[str, str]:
    path = get_csv_output_path(filename_prefix, output_file_path, overwrite=True)
    file_exists = os.path.exists(path)
    should_write_header = bool(header) and (not file_exists or os.path.getsize(path) == 0)
    encoding = "utf-8" if file_exists else "utf-8-sig"

    with open(path, "a", encoding=encoding, newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        if should_write_header:
            writer.writerow(header)
        writer.writerows(rows)

    preview_rows = ([header] if should_write_header else []) + rows
    return path, rows_to_csv(preview_rows)


def get_csv_output_path(filename_prefix: str, output_file_path: str = "", overwrite: bool = False) -> str:
    custom_path = normalize_custom_output_path(output_file_path)

    if custom_path:
        root, extension = os.path.splitext(custom_path)
        if extension.lower() == ".csv":
            directory = os.path.dirname(custom_path) or get_output_dir()
            os.makedirs(directory, exist_ok=True)
            if overwrite:
                return custom_path
            return next_available_file_path(custom_path)

        os.makedirs(custom_path, exist_ok=True)
        if overwrite:
            return os.path.join(custom_path, f"{format_csv_stem(filename_prefix)}.csv")
        return next_available_path(custom_path, filename_prefix)

    output_dir = get_output_dir()
    csv_dir = os.path.join(output_dir, "csv_exports")
    os.makedirs(csv_dir, exist_ok=True)
    if overwrite:
        return os.path.join(csv_dir, f"{format_csv_stem(filename_prefix)}.csv")
    return next_available_path(csv_dir, filename_prefix)


def normalize_custom_output_path(output_file_path: str) -> str:
    custom_path = (output_file_path or "").strip().strip('"').strip("'")
    if not custom_path:
        return ""

    custom_path = os.path.expandvars(os.path.expanduser(custom_path))
    if not os.path.isabs(custom_path):
        custom_path = os.path.join(get_output_dir(), custom_path)
    return os.path.abspath(custom_path)


def get_output_dir() -> str:
    if folder_paths is not None:
        return folder_paths.get_output_directory()
    return os.path.join(os.getcwd(), "output")


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name.strip())
    cleaned = cleaned.strip(" .")
    return cleaned[:120]


def next_available_path(directory: str, prefix: str) -> str:
    stem = format_csv_stem(prefix)
    candidate = os.path.join(directory, f"{stem}.csv")
    if not os.path.exists(candidate):
        return candidate

    index = 2
    while True:
        candidate = os.path.join(directory, f"{stem}_{index:02d}.csv")
        if not os.path.exists(candidate):
            return candidate
        index += 1


def next_available_file_path(file_path: str) -> str:
    if not os.path.exists(file_path):
        return file_path

    root, extension = os.path.splitext(file_path)
    index = 2
    while True:
        candidate = f"{root}_{index:02d}{extension}"
        if not os.path.exists(candidate):
            return candidate
        index += 1


def format_csv_stem(filename_prefix: str) -> str:
    safe_prefix = sanitize_filename(filename_prefix)
    return safe_prefix or "01"


NODE_CLASS_MAPPINGS = {
    "LLAIBatchTextToCSV": LLAIBatchTextToCSV,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLAIBatchTextToCSV": "LL-Batch Text To CSV",
}

