from .doubao_seedream import LLDoubaoSeedream45TextToImage
from .doubao_seedream_40 import LLDoubaoSeedream40TextToImage
from .doubao_seedream_40_batch import LLDoubaoSeedream40BatchTextToImage
from .doubao_seedream_50_pro import LLDoubaoSeedream50ProTextToImage
from .doubao_seedream_40_i2i import LLDoubaoSeedream40ImageToImage
from .doubao_seedream_45_i2i import LLDoubaoSeedream45ImageToImage
from .doubao_seedream_50_pro_i2i import LLDoubaoSeedream50ProImageToImage
from .doubao_seedream_40_combined import LLDoubaoSeedream40
from .doubao_seedream_45_combined import LLDoubaoSeedream45
from .doubao_seedream_50_pro_combined import LLDoubaoSeedream50Pro
from .doubao_seedream_50_lite import LLDoubaoSeedream50Lite


NODE_CLASS_MAPPINGS = {
    "LLDoubaoSeedream40": LLDoubaoSeedream40,
    "LLDoubaoSeedream45": LLDoubaoSeedream45,
    "LLDoubaoSeedream50Pro": LLDoubaoSeedream50Pro,
    "LLDoubaoSeedream50Lite": LLDoubaoSeedream50Lite,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLDoubaoSeedream40": "LL-doubao-seedream-4.0",
    "LLDoubaoSeedream45": "LL-doubao-seedream-4.5",
    "LLDoubaoSeedream50Pro": "LL-doubao-seedream-5.0pro",
    "LLDoubaoSeedream50Lite": "LL-doubao-seedream-5.0lite",
}
