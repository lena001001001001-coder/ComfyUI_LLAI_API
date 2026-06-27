# ComfyUI_LLAI_API

`ComfyUI_LLAI_API` 是一个面向 LLAI 中转站的 ComfyUI 扩展，提供文本、图片、视频、音频、批量处理与辅助工具节点。

当前项目的主品牌是 `LLAI`，默认中转站地址为：

```text
https://api.llaiapi.host/
```

`doc.kuai.host` 只作为接口结构参考，不作为本项目默认运行地址。

## 主要节点

| 节点 | 用途 |
| --- | --- |
| LLAI API Settings | 统一配置任务类型、平台、api_format、base、模型和 API Key |
| LLAI Text Generator | 文本生成、多模态理解 |
| LLAI Image Generator | 文生图、图像编辑 |
| LLAI Video Generator | Grok / Veo 视频生成 |
| LLAI Sound Generator | Suno 音乐生成 |
| LLAI Notice | 通知与状态提示 |

项目里也包含若干分类节点，例如：

```text
LLAI/Grok
LLAI/GrokImage
LLAI/GPTImage
LLAI/NanoBanana
LLAI/Gemini
LLAI/Kling
LLAI/WAN
LLAI/Sora2
LLAI/Utils
```

## 安装

把仓库放到 ComfyUI 的 `custom_nodes` 目录下：

```text
ComfyUI/custom_nodes/ComfyUI_LLAI_API/
```

重启 ComfyUI 后即可在 `LLAI` 分类下使用节点。

## 默认中转站

默认 base 列表以 `https://api.llaiapi.host/` 为首选，其余可用 base 包括：

```text
https://www.runninghub.cn/
https://llm.runninghub.ai/
https://yunwu.ai/
https://ai.t8star.cn/
https://api.bltcy.ai/
```

用户可以在设置节点里添加自定义 base。API Key 会按节点保存，不要把真实 key 提交到仓库。

## 支持的 API 形式

### 视频

| api_format | 说明 |
| --- | --- |
| `v1/video` | `/v1/video/create` + `/v1/video/query?id={task_id}` |
| `v1/videos` | `/v1/videos` + `/v1/videos/{task_id}` |
| `v2/videos` | `/v2/videos/generations` + `/v2/videos/generations/{task_id}` |
| `runninghub-/openapi/v2` | RunningHub 视频格式 |

### 图片

| api_format | 说明 |
| --- | --- |
| `v1beta/models` | Gemini 风格生成接口 |
| `v1/images` | OpenAI Images 风格接口 |
| `v1/chat/completions` | Chat Completions 风格多模态接口 |
| `runninghub-/openapi/v2` | RunningHub 图片格式 |

### 音频

| api_format | 说明 |
| --- | --- |
| `suno/submit` | LLAI Suno 接口 |
| `runninghub-/openapi/v2` | RunningHub Suno 格式 |

### 文本

| api_format | 说明 |
| --- | --- |
| `v1beta/models` | Gemini 风格文本/多模态 |
| `v1/chat/completions` | Chat Completions 风格文本/多模态 |
| `runninghub-/v1` | RunningHub 文本格式 |

## 常用模型

### 视频

- Grok: `grok-video-3-10s`, `grok-video-3`, `grok-videos`
- Veo: `veo3.1`, `veo3.1-fast`, `veo_3_1-lite`, `veo_3_1-lite-4K`, `veo_3_1-fast-4K`

### 图片

- banana-pro: `nano-banana-pro`
- banana-2: `gemini-3.1-flash-image-preview`
- gpt-image2: `gpt-image-2`

### 音频

- Suno: `suno_music_open`, `suno_music`

### 文本

- GeminiText: `gemini-3.1-flash-lite-preview`, `gemini-3-flash-preview`, `gemini-3.1-pro-preview`
- OpenaiText: `claude-opus-4-6`, `grok-4.1`

## 典型工作流

- 文生视频
- 图生视频
- 文生图
- 图像编辑
- 多模态理解
- Suno 歌曲生成
- 批量 CSV 任务

仓库里已经带有一些 `workflows/` 和 `examples/` 示例文件，可以直接参考。

## 配置文件

本地配置保存在：

```text
relay_config.json
```

其中包含：

- 自定义 base
- 自定义模型
- 节点级 API Key

## 测试

常用检查命令：

```powershell
python diagnose.py
python test/test_labels.py
python test/test_csv_nodes.py
python -m py_compile .\config.py .\__init__.py .\nodes_api_settings.py .\nodes_video_generator.py .\nodes_image_generator.py .\nodes_sound_generator.py .\nodes_text_generator.py
node --check .\js\relay_api_settings.js
```

## 说明

- 新增文档、注释和界面文案请使用 `LLAI`、`llaiapi` 或 `llai`
- 旧的 `Relay...` 名称属于兼容标识，尽量不要继续扩展新的旧品牌命名
- 真实 API Key 不要写进仓库文件

## License

MIT
