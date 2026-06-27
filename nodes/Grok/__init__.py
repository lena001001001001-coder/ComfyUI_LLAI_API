from .grok import (
    GrokCreateVideo,
    GrokQueryVideo,
    GrokCreateAndWait,
    GrokText2Video,
    GrokText2VideoAndWait,
    GrokExtendVideo,
    GrokExtendVideoAndWait,
)
from .grok_videos import (
    GrokVideosCreateVideo,
    GrokVideosQueryVideo,
    GrokVideosCreateAndWait,
)
from .batch_processor import GrokBatchProcessor
from .concurrent_processor import (
    GrokText2Video10Concurrent,
    GrokImage2Video10Concurrent,
)
from .csv_concurrent_processor import GrokCSVConcurrentProcessor
from .batch_image_to_csv_task import GrokBatchImageToCSVTask
from .dir_batch_image2video import GrokDirBatchImage2Video

NODE_CLASS_MAPPINGS = {
    "GrokCreateVideo": GrokCreateVideo,
    "GrokQueryVideo": GrokQueryVideo,
    "GrokCreateAndWait": GrokCreateAndWait,
    "GrokText2Video": GrokText2Video,
    "GrokText2VideoAndWait": GrokText2VideoAndWait,
    "GrokExtendVideo": GrokExtendVideo,
    "GrokExtendVideoAndWait": GrokExtendVideoAndWait,
    "GrokVideosCreateVideo": GrokVideosCreateVideo,
    "GrokVideosQueryVideo": GrokVideosQueryVideo,
    "GrokVideosCreateAndWait": GrokVideosCreateAndWait,
    "GrokBatchProcessor": GrokBatchProcessor,
    "GrokText2Video10Concurrent": GrokText2Video10Concurrent,
    "GrokImage2Video10Concurrent": GrokImage2Video10Concurrent,
    "GrokCSVConcurrentProcessor": GrokCSVConcurrentProcessor,
    "GrokBatchImageToCSVTask": GrokBatchImageToCSVTask,
    "GrokDirBatchImage2Video": GrokDirBatchImage2Video,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GrokCreateVideo": "LL Grok 创建视频",
    "GrokQueryVideo": "LL Grok 查询视频",
    "GrokCreateAndWait": "LL Grok 一键生成视频",
    "GrokText2Video": "LL Grok 文生视频",
    "GrokText2VideoAndWait": "LL Grok 文生视频（一键）",
    "GrokExtendVideo": "LL Grok 扩展视频",
    "GrokExtendVideoAndWait": "LL Grok 扩展视频（一键）",
    "GrokVideosCreateVideo": "LL Grok-videos 生视频 6-10s",
    "GrokVideosQueryVideo": "LL Grok-videos 查询视频",
    "GrokVideosCreateAndWait": "LL Grok-videos 生视频 6-10s（一键）",
    "GrokBatchProcessor": "LL Grok 批量处理器",
    "GrokText2Video10Concurrent": "LL Grok 文生视频（10路并发）",
    "GrokImage2Video10Concurrent": "LL Grok 图生视频（10路并发）",
    "GrokCSVConcurrentProcessor": "LL Grok CSV 并发批量处理器（legacy）",
    "GrokBatchImageToCSVTask": "LL Grok 批量图片转任务列表（legacy）",
    "GrokDirBatchImage2Video": "LL Grok 目录批量图生视频（一键闭环）",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
