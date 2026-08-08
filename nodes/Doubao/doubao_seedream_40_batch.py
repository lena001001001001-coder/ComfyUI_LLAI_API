"""LLAI Doubao Seedream 4.0 sequential batch text-to-image node."""

import json

import torch

from .doubao_seedream_40 import LLDoubaoSeedream40TextToImage


class LLDoubaoSeedream40BatchTextToImage(LLDoubaoSeedream40TextToImage):
    """Run the Seedream 4.0 text-to-image request repeatedly in sequence."""

    @classmethod
    def INPUT_TYPES(cls):
        base_inputs = super().INPUT_TYPES()
        required = dict(base_inputs["required"])
        required["batch_count"] = (
            "INT",
            {
                "default": 1,
                "min": 1,
                "max": 2000,
                "step": 1,
                "tooltip": "按相同参数依次生成的批量数量（1-2000）",
            },
        )
        return {
            "required": required,
            "optional": dict(base_inputs.get("optional", {})),
        }

    @classmethod
    def INPUT_LABELS(cls):
        return {
            "prompt": "提示词",
            "size": "尺寸",
            "watermark": "水印",
            "response_format": "返回格式",
            "api_key": "API密钥",
            "seed": "种子值",
            "ratio": "比例",
            "batch_count": "批量",
            "timeout": "超时",
        }

    def generate(
        self,
        prompt,
        size,
        watermark,
        response_format,
        api_key,
        seed,
        batch_count=1,
        timeout=1800,
        ratio=None,
    ):
        batch_count = int(batch_count)
        if not 1 <= batch_count <= 2000:
            raise ValueError("批量数量必须在 1 到 2000 之间")

        images = []
        refs = []
        summaries = []
        progress_bar = self._create_progress_bar(batch_count)

        print(f"[LLAI] Doubao Seedream 4.0 批量任务开始，共 {batch_count} 次")
        for index in range(batch_count):
            print(f"[LLAI] Doubao Seedream 4.0 批量进度 {index + 1}/{batch_count}")
            image, result_ref, summary = super().generate(
                prompt=prompt,
                size=size,
                watermark=watermark,
                response_format=response_format,
                api_key=api_key,
                seed=seed,
                timeout=timeout,
                ratio=ratio,
            )
            images.append(image)
            if result_ref:
                refs.extend(result_ref.splitlines())
            summaries.append(self._decode_summary(summary))
            if progress_bar is not None:
                progress_bar.update_absolute(index + 1, batch_count)

        combined_image = torch.cat(images, dim=0)
        batch_summary = json.dumps(
            {
                "requested_batches": batch_count,
                "completed_batches": batch_count,
                "image_count": int(combined_image.shape[0]),
                "responses": summaries,
            },
            ensure_ascii=False,
        )
        print(
            f"[LLAI] Doubao Seedream 4.0 批量任务完成，"
            f"共生成 {combined_image.shape[0]} 张图像"
        )
        return (combined_image, "\n".join(refs), batch_summary)

    @staticmethod
    def _decode_summary(summary):
        try:
            return json.loads(summary)
        except (TypeError, ValueError):
            return summary

    @staticmethod
    def _create_progress_bar(total):
        try:
            from comfy.utils import ProgressBar
        except ImportError:
            return None
        return ProgressBar(total)
