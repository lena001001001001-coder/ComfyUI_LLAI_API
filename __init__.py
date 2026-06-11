from .nodes_api_settings import RelayAPISettings
from .nodes_video_generator import RelayGrokVideo, RelayVideoGenerator
from .nodes_image_generator import RelayBanana2ImageGenerator, RelayGPTImage2Generator, RelayImageGenerator
from .nodes_notice import RelayAPINotice
from .nodes_sound_generator import RelaySoundGenerator
from .nodes_suno_direct import RelaySunoDirectGenerator, RelaySunoDirectPlayer
from .nodes_text_generator import RelayLLMText, RelayTextGenerator

try:
    from .config import register_routes
    register_routes()
except Exception:
    pass

NODE_CLASS_MAPPINGS = {
    "RelayAPISettings": RelayAPISettings,
    "RelayVideoGenerator": RelayGrokVideo,
    "RelayGrokVideo": RelayGrokVideo,
    "RelayImageGenerator": RelayImageGenerator,
    "RelayGPTImage2Generator": RelayGPTImage2Generator,
    "RelayBanana2ImageGenerator": RelayBanana2ImageGenerator,
    "RelayAPINotice": RelayAPINotice,
    "RelaySoundGenerator": RelaySoundGenerator,
    "RelaySunoDirectGenerator": RelaySunoDirectGenerator,
    "RelaySunoDirectPlayer": RelaySunoDirectPlayer,
    "RelayTextGenerator": RelayTextGenerator,
    "RelayLLMText": RelayLLMText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RelayAPISettings": "🍐 API Settings",
    "RelayVideoGenerator": "🍐 Grok Video",
    "RelayGrokVideo": "🍐 Grok Video",
    "RelayImageGenerator": "🍐 Image Generator",
    "RelayGPTImage2Generator": "🍐 GPT-Image2 Generator",
    "RelayBanana2ImageGenerator": "🍐 Banana-2 Image Generator",
    "RelayAPINotice": "🍐 API Notice",
    "RelaySoundGenerator": "🍐 Sound Generator",
    "RelaySunoDirectGenerator": "🍐 Suno Direct",
    "RelaySunoDirectPlayer": "🍐 Suno Direct Player",
    "RelayTextGenerator": "🍐 Text Generator",
    "RelayLLMText": "🍐 LLM Text",
}

WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
