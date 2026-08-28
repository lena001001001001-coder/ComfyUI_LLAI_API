from .gpt_image import GPTImage2Generate, GPTImage2Edit, GPTImage2EditImages

try:
    from .gpt_image_2_all import GPTImage2AllGenerate, GPTImage2AllEdit
except ImportError:
    GPTImage2AllGenerate = None
    GPTImage2AllEdit = None

from .gpt_image_2_c import GPTImage2CLowCost4K, GPTImage2CFullSize

NODE_CLASS_MAPPINGS = {
    "GPTImage2Generate": GPTImage2Generate,
    "GPTImage2Edit": GPTImage2Edit,
    "GPTImage2EditImages": GPTImage2EditImages,
    "GPTImage2CFullSize": GPTImage2CFullSize,
    **({
        "GPTImage2AllGenerate": GPTImage2AllGenerate,
        "GPTImage2AllEdit": GPTImage2AllEdit,
    } if GPTImage2AllGenerate and GPTImage2AllEdit else {}),
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GPTImage2Generate": "LL GPT Image 2 文生图",
    "GPTImage2Edit": "LL GPT Image 2 图片编辑",
    "GPTImage2EditImages": "LL GPT Image 2 图生图",
    "GPTImage2CFullSize": "LL-gpt-image-2-c低价",
    **({
        "GPTImage2AllGenerate": "LL gpt-image-2-all生图",
        "GPTImage2AllEdit": "LL gpt-image-2-all编辑图",
    } if GPTImage2AllGenerate and GPTImage2AllEdit else {}),
}
