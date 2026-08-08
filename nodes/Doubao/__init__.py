from .doubao_seedream import LLDoubaoSeedream45TextToImage
from .doubao_seedream_40 import LLDoubaoSeedream40TextToImage
from .doubao_seedream_40_batch import LLDoubaoSeedream40BatchTextToImage
from .doubao_seedream_50_pro import LLDoubaoSeedream50ProTextToImage
from .doubao_seedream_40_i2i import LLDoubaoSeedream40ImageToImage
from .doubao_seedream_45_i2i import LLDoubaoSeedream45ImageToImage
from .doubao_seedream_50_pro_i2i import LLDoubaoSeedream50ProImageToImage


NODE_CLASS_MAPPINGS = {
    "LLDoubaoSeedream45TextToImage": LLDoubaoSeedream45TextToImage,
    "LLDoubaoSeedream40TextToImage": LLDoubaoSeedream40TextToImage,
    "LLDoubaoSeedream40BatchTextToImage": LLDoubaoSeedream40BatchTextToImage,
    "LLDoubaoSeedream50ProTextToImage": LLDoubaoSeedream50ProTextToImage,
    "LLDoubaoSeedream40ImageToImage": LLDoubaoSeedream40ImageToImage,
    "LLDoubaoSeedream45ImageToImage": LLDoubaoSeedream45ImageToImage,
    "LLDoubaoSeedream50ProImageToImage": LLDoubaoSeedream50ProImageToImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLDoubaoSeedream45TextToImage": "LL-doubao-seedream-4.5-文生图",
    "LLDoubaoSeedream40TextToImage": "LL-doubao-seedream-4.0-文生图",
    "LLDoubaoSeedream40BatchTextToImage": "LL-doubao-seedream-4.0-文生图-批量",
    "LLDoubaoSeedream50ProTextToImage": "LL-doubao-seedream-5.0pro-文生图",
    "LLDoubaoSeedream40ImageToImage": "LL-doubao-seedream-4.0-图生图",
    "LLDoubaoSeedream45ImageToImage": "LL-doubao-seedream-4.5-图生图(慢)",
    "LLDoubaoSeedream50ProImageToImage": "LL-doubao-seedream-5.0pro-图生图",
}
