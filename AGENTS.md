# AGENTS.md

This file guides Codex and other AI coding agents when working in this repository.

## Repository Guardrails

- Do not batch-delete files or directories.
- Never use `del /s`, `rd /s`, `rmdir /s`, `Remove-Item -Recurse`, or `rm -rf`.
- If one file must be removed, remove only one explicit path at a time, for example `Remove-Item "C:\path\to\file.txt"`.
- If many files need to be removed, stop and ask the user to delete them manually.

## Project Overview

**ComfyUI_LLAI_API** is a ComfyUI extension for LLAI model relay workflows. It provides video, image, audio, text, upload, batch, and monitoring nodes for Chinese ComfyUI users.

Primary relay base:

```text
https://api.llaiapi.host/
```

Use `doc.kuai.host` only as an interface reference for endpoint paths, request fields, and response shapes. Keep the working relay base on `https://api.llaiapi.host/`.

Branding rule:

- User-facing docs, comments, labels, and new code should use `LLAI`, `llaiapi`, or `llai`.
- Some existing compatibility identifiers still contain the old `Relay...` naming, especially top-level class names, JavaScript filenames, and `/relayapi/...` local ComfyUI routes. Treat those as compatibility IDs unless you are doing a deliberate migration across Python registration, saved workflows, frontend scripts, and route consumers.
- Do not introduce new brand text using the old RelayAPI/Relay wording.

## Development Commands

```powershell
pip install -r requirements.txt
python diagnose.py
python test/test_labels.py
python test/test_csv_nodes.py
python -m py_compile .\config.py .\__init__.py .\nodes_api_settings.py .\nodes_video_generator.py .\nodes_image_generator.py .\nodes_sound_generator.py .\nodes_text_generator.py
node --check .\js\relay_api_settings.js
```

For non-generating connectivity checks, prefer model/list endpoints when available. Avoid running paid generation endpoints unless the user asks for a live API test or provides a test key.

## Configuration

Core configuration lives in `config.py`.

Important structures:

- `DEFAULT_API_BASES`: default base URLs. The first and primary base must be `https://api.llaiapi.host/`.
- `DEFAULT_MODELS`: broad fallback model lists by platform.
- `FORMAT_MODELS`: model lists scoped by platform and `api_format`.
- `TASK_PLATFORMS`: maps task types to supported platforms.
- `VIDEO_API_FORMATS`, `IMAGE_API_FORMATS`, `SOUND_API_FORMATS`, `TEXT_API_FORMATS`: UI/API format options.
- `API_PATHS`: canonical endpoint path map used by generic nodes.
- `relay_config.json`: persisted local settings, custom bases, custom models, and per-node API key storage.

Default base list currently includes:

```text
https://api.llaiapi.host/
https://www.runninghub.cn/
https://llm.runninghub.ai/
https://yunwu.ai/
https://ai.t8star.cn/
https://api.bltcy.ai/
```

API key handling:

- Most nodes accept `api_key` or `apikey` parameters.
- Top-level compatibility nodes can persist masked/real keys per node via `save_node_settings`.
- Several legacy utility helpers still read `KUAI_API_KEY`; keep this for compatibility unless you migrate every caller.
- Never print full API keys.

## Node Registration

There are two node systems in this repository.

Top-level compatibility nodes are registered in root `__init__.py`:

- API settings
- Grok video
- generic image generator
- GPT-Image2 generator
- Banana-2 generator
- sound generator
- Suno direct generator/player
- text generator
- notice node

These classes still use old compatibility names such as `RelayGrokVideo`. Keep those registered names stable unless you also update saved-workflow compatibility and JavaScript frontend logic.

Category nodes are registered by each `nodes/<Category>/__init__.py`:

```text
nodes/Sora2
nodes/Veo3
nodes/Grok
nodes/GrokImage
nodes/GPTImage
nodes/NanoBanana
nodes/Gemini
nodes/Kling
nodes/WAN
nodes/Utils
```

New category nodes should use:

```python
CATEGORY = "LLAI/<Category>"
```

Use Chinese labels in `INPUT_LABELS` and `RETURN_NAMES` where the surrounding node already does.

## Endpoint Matrix

All paths below are relative to the selected `api_base` unless noted otherwise. For LLAI-native nodes, the default full base is `https://api.llaiapi.host/`.

### Generic Video Nodes

Files:

- `nodes_video_generator.py`
- `nodes/Grok/grok.py`
- `nodes/Grok/grok_videos.py`
- `nodes/Veo3/veo3.py`
- `nodes/Sora2/sora2.py`

Supported formats and paths:

```text
video_v1/video:
POST /v1/video/create
GET  /v1/video/query?id={task_id}

video_v1/videos:
POST /v1/videos
GET  /v1/videos/{task_id}
GET  /v1/videos/{task_id}/content

video_v2/videos:
POST /v2/videos/generations
GET  /v2/videos/generations/{task_id}
```

Platform behavior:

- Grok: text-to-video and image-to-video, usually `grok-video-3-10s`, `grok-video-3`, or `grok-videos`.
- Veo: text-to-video and image-to-video, usually `veo3.1`, `veo3.1-fast`, `veo_3_1-lite`, `veo_3_1-lite-4K`, or `veo_3_1-fast-4K`.
- Sora2: direct category nodes use `/v1/video/create` and `/v1/video/query`, plus Sora-specific character/remix endpoints.

Sora-specific paths:

```text
POST /sora/v1/characters
POST /v1/videos/{video_id}/remix
```

RunningHub video format:

```text
POST /openapi/v2/{model}/text-to-video
POST /openapi/v2/{model}/image-to-video
POST /openapi/v2/media/upload/binary
POST /openapi/v2/query
```

Use RunningHub bases (`https://www.runninghub.cn/` or `https://llm.runninghub.ai/` depending on task) only for `runninghub-*` formats. Do not send LLAI-native paths to RunningHub bases or RunningHub paths to LLAI bases.

### Image Nodes

Files:

- `nodes_image_generator.py`
- `nodes/GPTImage/gpt_image.py`
- `nodes/GPTImage/gpt_image_2_all.py`
- `nodes/GrokImage/grok_image.py`
- `nodes/NanoBanana/nano_banana.py`
- `nodes/NanoBanana/batch_processor.py`

Supported formats and paths:

```text
image_v1beta/models:
POST /v1beta/models/{model}:generateContent
POST /v1beta/models/{model}:streamGenerateContent

image_v1/images:
POST /v1/images/generations
POST /v1/images/edits

image_v1/chat/completions:
POST /v1/chat/completions
```

Platform behavior:

- `banana-pro`: Gemini/Nano Banana Pro style generation, commonly `gemini-3-pro-image-preview` or `nano-banana-pro`.
- `banana-2`: Gemini 3.1 Flash image generation, commonly `gemini-3.1-flash-image-preview`.
- `gpt-image2`: OpenAI Images-compatible generation/editing, commonly `gpt-image-2`; supports multi-image editing and strict size/ratio handling.
- `GrokImage`: uses OpenAI Images-compatible `/v1/images/generations` and `/v1/images/edits`.

RunningHub image format:

```text
POST /openapi/v2/{model}/text-to-image
POST /openapi/v2/{model}/image-to-image
POST /openapi/v2/media/upload/binary
POST /openapi/v2/query
```

### Sound and Suno Nodes

Files:

- `nodes_sound_generator.py`
- `nodes_suno_direct.py`
- `nodes/Utils/audio_upload.py`

LLAI Suno format:

```text
POST /suno/submit/music
GET  /suno/fetch/{task_id}
```

Description-mode payload uses fields like:

```json
{
  "model": "suno_music_open",
  "gpt_description_prompt": "song description",
  "mv": "chirp-crow",
  "prompt": "",
  "make_instrumental": true
}
```

Custom-lyrics payload uses fields like:

```json
{
  "model": "suno_music_open",
  "prompt": "lyrics or full creation prompt",
  "mv": "chirp-crow",
  "title": "song title",
  "tags": "pop, electronic"
}
```

Version map:

```text
V3    -> chirp-v3.0
V3.5  -> chirp-v3.5
V4    -> chirp-v4
V4.5  -> chirp-auk
V4.5+ -> chirp-bluejay
V5    -> chirp-crow
V5.5  -> chirp-fenix
```

RunningHub Suno format:

```text
POST /openapi/v2/rhart-audio/suno-v5.5/single
POST /openapi/v2/rhart-audio/suno-v5.5/custom
POST /openapi/v2/query
```

### Text and Multimodal Understanding Nodes

Files:

- `nodes_text_generator.py`
- `nodes/Sora2/script_generator.py`
- `nodes/Gemini/gemini_understanding.py`
- `nodes/Utils/deepseek_ocr.py`

Supported paths:

```text
POST /v1beta/models/{model}:generateContent
POST /v1/chat/completions
```

Platform behavior:

- `GeminiText`: supports text, image, video, and audio inputs through `v1beta/models`.
- `OpenaiText`: supports OpenAI chat-compatible text/image messages through `v1/chat/completions`.
- `runninghub-/v1`: forces base URL to `https://llm.runninghub.ai/` and uses `/v1/chat/completions`.
- DeepSeek OCR and Sora prompt generation use chat-completions style requests.

### WAN and Kling Nodes

Files:

- `nodes/WAN/wan.py`
- `nodes/Kling/kling.py`
- `nodes/Kling/batch_processor.py`

WAN paths:

```text
POST /alibailian/api/v1/services/aigc/video-generation/video-synthesis
GET  /alibailian/api/v1/tasks/{task_id}
```

Kling nodes use the helpers in `nodes/Kling/kling_utils.py`. Before changing Kling behavior, inspect that helper file and the concrete node payloads together.

### Utility and Batch Nodes

Files:

- `nodes/Utils/csv_reader.py`
- `nodes/Utils/batch_state.py`
- `nodes/Utils/batch_logger.py`
- `nodes/Utils/batch_process_logger.py`
- `nodes/Utils/batch_monitor.py`
- `nodes/Utils/realtime_monitor.py`
- `nodes/Utils/image_upload.py`
- `nodes/Utils/audio_upload.py`
- `nodes/Utils/video_download.py`
- `nodes/Utils/image_urls_to_batch.py`
- `nodes/Grok/*batch*.py`
- `nodes/Veo3/*batch*.py`
- `nodes/Sora2/batch_processor.py`
- `nodes/NanoBanana/batch_processor.py`

Batch processors usually parse JSON task lists emitted by CSV/helper nodes, submit tasks one by one or concurrently, optionally poll, optionally download output media, and write task metadata/report files.

Do not change CSV column names casually. Existing workflows depend on names like:

```text
prompt
image_url
image_urls
image_path
model
ratio
size
duration
output_prefix
custom_model
```

## Response Parsing Rules

LLAI and compatible providers may wrap responses differently. Keep parsing flexible.

Task IDs may appear in:

```text
task_id
id
request_id
taskId
data
data.id
data.task_id
data.taskId
```

Status may appear in:

```text
status
state
data.status
data.state
```

Media URLs may appear in:

```text
url
image_url
audio_url
video_url
download_url
output_url
file_url
output
data.url
data.output
results[]
images[]
clips[]
```

Failure reasons may appear in:

```text
fail_reason
failReason
last_error
message
error.message
errorMessage
failedReason
```

When adding a new model integration, prefer helper methods that unwrap nested `data` objects and support these alternate fields.

## Async Task Pattern

For video/audio APIs and other async endpoints, keep submit, query, and poll logic separate:

```python
def _submit_xxx(...):
    # POST create endpoint, return task_id and request payload

def _query_xxx(...):
    # GET/POST query endpoint, return status, media_url, raw payload

def _poll(...):
    # loop until success/fail/timeout, with bounded retry handling
```

Terminal success words commonly include:

```text
success
succeed
completed
complete
done
SUCCESS
COMPLETED
DONE
```

Terminal failure words commonly include:

```text
fail
failed
error
cancel
FAILED
ERROR
CANCELLED
```

## Image and Media Handling

Common conversions:

- ComfyUI image tensors are converted through `utils.tensor2pil` or category-local helpers.
- OpenAI-compatible image edits usually upload multipart `image[]` fields.
- Gemini-compatible image/video/audio understanding usually uses inline base64 in `inline_data`.
- Some video APIs accept `data:image/png;base64,...`; others expect uploaded URLs or multipart files. Match the existing node path before changing payload shape.
- Downloaded images should be converted back to ComfyUI IMAGE tensors.
- Downloaded video/audio should use ComfyUI-compatible video/audio wrappers already used in the repository.

## Frontend Extensions

Frontend files:

```text
js/relay_api_settings.js
js/relay_video_generator.js
js/relay_image_generator.js
js/relay_sound_generator.js
js/relay_text_generator.js
js/relay_api_notice.js
web/kuaipower_panel.js
web/video_preview.js
web/realtime_monitor.js
web/llai_api_badge.js
```

The `js/relay_*.js` filenames and extension IDs are compatibility artifacts. New visible text should say LLAI/llaiapi/llai. If renaming frontend files or ComfyUI class names, update:

- root `__init__.py`
- `NODE_CLASS_MAPPINGS`
- `NODE_DISPLAY_NAME_MAPPINGS`
- JavaScript `node.comfyClass` checks
- local API routes in `config.py`
- saved workflow compatibility expectations

Local settings routes currently use `/relayapi/...` for compatibility. Do not change the route prefix unless you also update every frontend caller and consider migration for users.

## Adding or Removing Features

Before adding a model, platform, or endpoint:

1. Inspect the closest existing node implementation.
2. Add or update config first: `DEFAULT_MODELS`, `FORMAT_MODELS`, `TASK_PLATFORMS`, relevant `*_API_FORMATS`, and `API_PATHS`.
3. Implement node logic in the local style for that task type.
4. Keep API base defaults pointed at `https://api.llaiapi.host/` unless the selected format is explicitly RunningHub.
5. Add flexible parsing for task IDs, statuses, media URLs, and error messages.
6. Preserve saved workflow compatibility when changing node class names, input names, or widget order.
7. Update docs/examples/workflows that mention the changed node or endpoint.
8. Run syntax checks for touched Python and JavaScript files.

Before removing an old feature:

1. Search for the class name, display name, endpoint, model, and CSV columns with `rg`.
2. Check workflows, examples, docs, frontend `node.comfyClass` checks, and batch processors.
3. Remove or deprecate in a coordinated way. Do not leave config dropdowns pointing at removed code paths.
4. If removal breaks saved workflows, prefer leaving a small compatibility wrapper that raises a clear Chinese error or forwards to the new node.

## Testing and Diagnostics

Useful checks:

```powershell
python diagnose.py
python test/test_labels.py
python test/test_csv_nodes.py
python test/test_grok_nodes.py
python test/test_gpt_image_nodes.py
python -m py_compile .\config.py .\__init__.py .\nodes_video_generator.py .\nodes_image_generator.py .\nodes_sound_generator.py .\nodes_text_generator.py
node --check .\js\relay_api_settings.js
node --check .\js\relay_video_generator.js
node --check .\js\relay_image_generator.js
node --check .\js\relay_sound_generator.js
node --check .\js\relay_text_generator.js
```

ComfyUI must be restarted to reload Python node changes. Watch the ComfyUI console and log for this plugin's messages. Existing logs may still use old compatibility prefixes; new user-facing logs should prefer `[LLAI]` or `[ComfyUI_LLAI_API]`.

Common failure interpretation:

- `API key not found`: API settings did not pass a key downstream or the per-node key was masked and not stored.
- `401 Unauthorized`: wrong key, expired key, missing model permission, or wrong base URL.
- `200` with HTML/non-JSON: wrong endpoint path or wrong `api_format` for the selected base.
- task ID exists but no output: query parser does not match returned response shape, or async task failed after submission.
- node missing after restart: import error; run `python -m py_compile` and check ComfyUI logs.

## Documentation Rules

When updating docs:

- Use `https://api.llaiapi.host/` as the primary LLAI base.
- Mention RunningHub bases only for RunningHub-specific formats.
- Avoid new user-facing RelayAPI/Relay brand wording.
- Keep code identifiers exact when documenting compatibility behavior.
- Keep Chinese UI labels and examples accurate for the current node inputs.
- Update README, docs, examples, and workflow notes when changing public node behavior.
