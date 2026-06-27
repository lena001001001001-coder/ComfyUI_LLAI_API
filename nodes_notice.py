class RelayAPINotice:
    MESSAGE = (
        "[低价api地址](https://api.llaiapi.host/register?aff=SXcB)\n"
        "[低价模型调用方法](https://my.feishu.cn/wiki/PjYZw0u8Pi0HzYkY0UgcjpjAn2b?from=from_copylink)\n"
        "[PS/ComfyUI/插件/工作流资源免费领取](https://my.feishu.cn/wiki/WdnewJesfiwxRikq9yCcd5WcnZd?from=from_copylink)\n"
        "[AI工具服务案例与价格](https://my.feishu.cn/wiki/OoA2wpuuyirRtTkAjw4cdNV6ntg?from=from_copylink)\n"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "message": ("STRING", {
                    "default": cls.MESSAGE,
                    "multiline": True,
                }),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "show"
    CATEGORY = "ComfyUI_LLAI_API"

    def show(self, message):
        return ()
