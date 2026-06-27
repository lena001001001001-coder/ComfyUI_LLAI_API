from .veo3 import (
    VeoCreateVideo,
    VeoQueryVideo,
    VeoCreateAndWait,
    VeoImage2Video,
    VeoImage2VideoAndWait,
)

NODE_CLASS_MAPPINGS = {
    "VeoCreateVideo": VeoCreateVideo,
    "VeoQueryVideo": VeoQueryVideo,
    "VeoCreateAndWait": VeoCreateAndWait,
    "VeoImage2Video": VeoImage2Video,
    "VeoImage2VideoAndWait": VeoImage2VideoAndWait,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VeoCreateVideo": "LL Veo 创建视频",
    "VeoQueryVideo": "LL Veo 查询视频",
    "VeoCreateAndWait": "LL Veo 一键生成视频",
    "VeoImage2Video": "LL Veo 图生视频",
    "VeoImage2VideoAndWait": "LL Veo 图生视频（一键）",
}
