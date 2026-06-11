# GPT Image 2 ComfyUI 多图生图改图节点设计

## 审查结论

现有方案方向正确：保留旧节点、增强文生图、新增一个可接 ComfyUI `IMAGE` 的多图改图节点。但原设计还不够可执行，主要风险集中在四处：

- 响应解析不能只复用当前 `_extract_urls()`。本地改图文档返回示例是 `data.b64_json` 对象结构，当前代码只处理 `data[]` 和 `choices[].message.content`，会漏掉成功响应。
- 输出格式字段存在供应商差异。本地 KuAi 生图文档使用 `format`，本地改图响应字段使用 `output_format`，OpenAI 官方指南也把它描述为 output format。设计必须明确节点 UI、请求字段和响应字段的映射关系。
- 多图 multipart 字段必须固定并可测。OpenAI 官方 curl 示例使用 `image[]`，当前 URL 版编辑节点也使用 `image[]`；本地 OpenAPI schema 写的是 `image` 且说明可为数组。新实现应把字段名集中成常量，默认沿用 `image[]`，并用单测锁定。
- ComfyUI `IMAGE` batch 语义必须明确。不能像 `to_pil_from_comfy()` 默认行为那样静默只取 batch 第 0 张。

## 依据

- 当前代码：
  - `nodes/GPTImage/gpt_image.py` 已有 `GPTImage2Generate`、`GPTImage2Edit`、`FORMATS`、`QUALITY_OPTIONS`、`_extract_urls()`。
  - `nodes/GPTImage/__init__.py` 手动注册 GPT Image 节点。
  - `nodes/Sora2/kuai_utils.py` 已有 `env_or()`、`to_pil_from_comfy()`、`save_image_to_buffer()`、`http_headers_multipart()`、`raise_for_bad_status()`。
- 本地 API 文档：
  - `/workspace/apis/gpt-image-2/生图.md`：`POST /v1/images/generations`，请求字段包含 `model`、`prompt`、`n`、`size`、`format`、`quality`。
  - `/workspace/apis/gpt-image-2/改图.md`：`POST /v1/images/edits`，`image` 支持图片数组，图片小于 16 张且每张 50MB 以内；请求字段包含 `model`、`prompt`、`n`、`size`、`quality`、`background`、`moderation`，响应包含 `data.b64_json`、`output_format`、`quality`、`size`。
- 外部参考：
  - OpenAI `gpt-image-2` 模型页说明它支持图像生成和编辑，并支持图像输入输出。
  - OpenAI 图像生成指南说明 Image API 可生成和编辑图像，编辑端支持一个或多个参考图，官方 curl 多图示例使用 `image[]`。
  - OpenAI 图像生成指南说明 `gpt-image-2` 不允许设置 `input_fidelity`，因为图像输入自动高保真处理。
  - OpenAI 图像生成指南说明输出可调 `size`、`quality`、output format、compression、`background`，且 `gpt-image-2` 当前不支持透明背景。
  - ComfyUI 官方 GPT-Image-2 合作伙伴节点提供文生图和图像编辑工作流。
  - 社区 `gpt-image-2-comfyui` 节点通常拆分 API Key、Text-to-Image、Image-to-Image 节点，图生图节点提供多个参考图输入。

## 目标

- 在不破坏旧工作流的前提下增强 `GPTImage2Generate`。
- 新增 `GPTImage2EditImages`，直接接收 ComfyUI `IMAGE`，最多 15 张参考图。
- 对生图和改图共用可靠的响应解析，兼容 URL、data URL、`b64_json`、`data` 数组、`data` 对象和 provider 的 `choices[].message.content` 回退。
- 把请求构造拆出来做离线单测，不依赖真实 API Key。
- 保持现有 `🍐LLAI/GPTImage` 分类和中文 UI 风格。

## 非目标

- 不删除或替换现有 URL 版 `GPTImage2Edit`。
- 不改 `GPTImage2Generate` 的输出数量和类型。
- 不实现 `mask` 遮罩编辑。
- 不新增 CSV 批处理节点。
- 不新增 API Key 独立节点。本仓库已有节点参数加 `KUAI_API_KEY` 环境变量的模式，本次沿用。
- 不暴露 `input_fidelity`。OpenAI 文档明确 `gpt-image-2` 不允许调整该参数。
- 不暴露 `output_compression`。本地 KuAi 文档没有该字段，先避免未验证参数。

## 推荐架构

采用“兼容旧节点 + 新增 IMAGE 改图节点 + 公共 helper”的方案。

文件组织：

- 修改 `nodes/GPTImage/gpt_image.py`
  - 增强 `GPTImage2Generate`。
  - 保留 `GPTImage2Edit` 的节点名、返回值和现有行为。
  - 新增或替换 `_extract_urls()` 为更通用的 `_extract_image_outputs()`，并保留 `_extract_urls()` 兼容包装，避免旧代码大改。
  - 新增请求构造、图片收集、响应摘要 helper。
- 修改 `nodes/GPTImage/__init__.py`
  - 注册 `GPTImage2EditImages`。
  - display name 使用 `🍐 GPT Image 2 多图改图`。
- 新增 `test/test_gpt_image_nodes.py`
  - 覆盖节点注册、输入接口、请求构造、响应解析和 batch 展开。

不建议新建过多文件。`gpt_image.py` 当前体量可控，相关 helper 和三个节点放在同一文件更容易保持字段常量一致。只有当实现后文件明显过长，再拆 `nodes/GPTImage/gpt_image_utils.py`。

## 节点设计

### `GPTImage2Generate`

保留必需输入：

- `prompt`
- `model`
- `size`
- `n`
- `api_key`

保留可选输入：

- `api_base`
- `timeout`

新增可选输入：

- `format`: `png`、`jpeg`、`webp`，默认 `png`
- `quality`: `auto`、`low`、`medium`、`high`，默认 `auto`

输出保持兼容：

- `IMAGE`
- `STRING`

签名兼容要求：

```python
def generate(
    self,
    prompt,
    model,
    size,
    n,
    api_key,
    api_base="https://api.kuai.host",
    timeout=1800,
    format="png",
    quality="auto",
):
```

新增参数必须放在已有可选参数之后，降低旧 workflow 和直接调用出现参数错位的风险。

请求字段策略：

- 必发：`model`、`prompt`、`n`、`size`。
- `format`：本地 KuAi 生图文档字段名是 `format`，节点 UI 也使用 `format`。默认 `png` 时可以不发送；选择 `jpeg` 或 `webp` 时发送 `format`。
- `quality`：默认 `auto` 时可以不发送；选择 `low`、`medium`、`high` 时发送。
- 不发送 `output_format`。它是 OpenAI 官方常用字段/响应字段，但本仓库默认 `api_base` 是 KuAi，本地文档以 `format` 为准。后续若要支持官方 OpenAI `api_base`，应新增 provider profile，而不是本次混发两个字段。

### `GPTImage2Edit`

旧 URL 版节点保持兼容，不改节点名、输入名、输出类型和 display name。

允许做的内部改进：

- 复用新的 `_extract_image_outputs()`，修复 `data` 对象结构和 `b64_json` 解析。
- 复用响应摘要 helper，避免错误中打印完整 base64。
- 不主动删除现有 `format`、`transparent` 等输入，避免破坏旧 workflow。

### `GPTImage2EditImages`

新增节点，面向 ComfyUI 原生 `IMAGE` 输入。

必需输入：

- `image_1`: `IMAGE`
- `prompt`: `STRING`
- `model`: 默认 `gpt-image-2`
- `size`
- `n`
- `api_key`

可选输入：

- `image_2` 到 `image_15`: `IMAGE`
- `format`: `png`、`jpeg`、`webp`，默认 `png`
- `quality`: `auto`、`low`、`medium`、`high`，默认 `auto`
- `background`: `auto`、`opaque`，默认 `auto`
- `moderation`: `auto`、`low`，默认 `auto`
- `api_base`: 默认 `https://api.kuai.host`
- `timeout`: 默认 `1800`

不在新节点暴露 `transparent`。原因是本地改图文档描述和示例互相矛盾，而 OpenAI 当前文档明确 `gpt-image-2` 不支持透明背景。旧 URL 节点保留 `transparent` 只是兼容历史 workflow。

输出：

- `IMAGE`，生成结果 batch。
- `STRING`，图片引用。可能是 URL，也可能是 `data:image/<format>;base64,...`。节点 UI 名称建议为 `图片URL/DataURL`，避免误导。
- `STRING`，响应 JSON 摘要。为避免 ComfyUI 卡顿和日志膨胀，`b64_json` 字段在该输出中应截断为 `<base64 omitted, N chars>`；如果必须调试完整响应，应通过临时日志或开发开关处理，不默认输出完整 base64。

## 图片输入和 batch 规则

新节点按以下规则收集图片：

1. 遍历 `image_1` 到 `image_15`。
2. 跳过未连接的可选输入。
3. 如果输入是 4D ComfyUI batch tensor 或 numpy array，展开 batch 中每一张图。
4. 如果输入是单张 3D 图，按一张处理。
5. 使用 `to_pil_from_comfy(image, index=i)` 转为 PIL。
6. 总图数必须满足 `1 <= count <= 15`。超过 15 张直接报中文错误，不截断。
7. 每张参考图编码为 PNG，保留 alpha 通道。

这样可以避免用户把一个 batch 接到 `image_1` 时只有第 0 张被静默使用。

## 改图请求构造

使用 `multipart/form-data` 请求：

- endpoint: `/v1/images/edits`
- headers: `http_headers_multipart(api_key)`
- files 字段名常量：`EDIT_IMAGE_FIELD = "image[]"`
- 每张图：

```python
("image[]", ("image_01.png", image_buffer, "image/png"))
```

选择 `image[]` 的理由：

- OpenAI 官方多图 curl 示例使用 `image[]`。
- 现有 URL 版 `GPTImage2Edit` 已使用 `image[]`。
- 本地 OpenAPI schema 虽然字段名写 `image`，但描述和示例表达的是图片数组；multipart 数组用 `image[]` 更符合当前实现和官方示例。

表单字段策略：

- 必发：`model`、`prompt`、`n`、`size`。
- `quality`：默认 `auto` 不发送，非默认才发送。
- `background`：默认 `auto` 不发送，选择 `opaque` 才发送。
- `moderation`：默认 `auto` 不发送，选择 `low` 才发送。
- `format`：默认 `png` 不发送，选择 `jpeg` 或 `webp` 才发送。这样兼顾本地生图文档、旧节点行为和 OpenAI 输出格式能力，同时降低改图端因未列出该字段而拒绝默认请求的风险。

## 响应解析设计

新增 helper：

```python
def _extract_image_outputs(data: dict, fallback_format: str = "png") -> list[dict]:
    ...
```

返回列表元素建议结构：

```python
{
    "source": "url" | "data_url" | "b64_json",
    "value": "...",
    "mime": "image/png",
}
```

必须支持：

- `{"data": [{"url": "..."}]}`
- `{"data": [{"b64_json": "..."}]}`
- `{"data": {"url": "..."}}`
- `{"data": {"b64_json": "..."}}`
- 顶层 `{"b64_json": "..."}`
- `{"choices": [{"message": {"content": "https://..."}}]}`
- `choices[].message.content` 返回 data URL。

`b64_json` 转 data URL 时，mime 由以下顺序决定：

1. 响应里的 `output_format`。
2. 节点请求的 `format`。
3. 默认 `png`。

错误处理：

- 没有可提取图像时，异常中包含响应摘要，不包含完整 base64。
- base64 解码失败时，报“响应图像 base64 解码失败”，并包含截断摘要。
- URL 下载失败时，保留 HTTP 状态和 URL 前 200 字符。

## 错误处理

- API Key 解析沿用 `env_or(api_key, "KUAI_API_KEY")`。
- `prompt.strip()` 为空时报 `提示词不能为空`。
- `GPTImage2EditImages` 没有任何图片时报 `至少需要提供一张图片`。
- 图片总数超过 15 张时报 `参考图数量不能超过 15 张，当前为 X 张`。
- 任一已连接图片转换或编码失败时直接报错，包含输入名和 batch index。
- HTTP 错误继续使用 `raise_for_bad_status()`，但后续可考虑让它复用 `extract_error_message_from_response()` 以减少噪音。
- 响应摘要函数必须截断 `b64_json`、data URL 和过长字符串，避免异常或响应 JSON 摘要输出过大。

## 测试计划

新增 `test/test_gpt_image_nodes.py`，使用离线单测为主。

节点接口：

- `GPTImage2Generate` 注册正常。
- `GPTImage2Generate.INPUT_TYPES()` 包含 `format` 和 `quality`。
- `GPTImage2Generate.RETURN_TYPES == ("IMAGE", "STRING")`。
- `GPTImage2EditImages` 注册到 `🍐LLAI/GPTImage`。
- `GPTImage2EditImages.INPUT_TYPES()` 包含 `image_1` 到 `image_15`。
- `GPTImage2EditImages.RETURN_TYPES == ("IMAGE", "STRING", "STRING")`，第三个 `RETURN_NAMES` 为 `响应JSON摘要`。
- `INPUT_LABELS()` 覆盖所有新增输入。

请求构造：

- 文生图默认参数只发送必要字段。
- 文生图选择 `jpeg/high` 时发送 `format=jpeg`、`quality=high`。
- 多图改图 multipart 使用 `image[]` 字段。
- 多图改图默认不发送 `format`、`quality=auto`、`background=auto`、`moderation=auto`。
- 多图改图选择 `webp/high/opaque/low` 时发送对应字段。

图片处理：

- 单张 `IMAGE` 可转 PNG buffer。
- batch `IMAGE` 会展开多张。
- 多个输入 socket 和 batch 混合时按连接顺序展开。
- 总数 16 张时报错。

响应解析：

- 支持 `data` 数组 URL。
- 支持 `data` 数组 `b64_json`。
- 支持 `data` 对象 `b64_json`。
- 支持顶层 `b64_json`。
- 支持 `choices[].message.content` URL。
- 无图像数据时报错且摘要不包含完整 base64。

集成验证：

- 运行 `python diagnose.py`。
- 运行新增测试文件。
- 如果环境变量存在 `KUAI_API_KEY`，可增加手动真实 API 验证；自动测试默认跳过真实请求。

## 实施顺序

1. 在 `gpt_image.py` 增加 constants 和 helper：响应摘要、输出提取、图片输出转 tensor、ComfyUI batch 展开、edit multipart 构造。
2. 增强 `GPTImage2Generate` 输入、标签、签名和 payload 构造，保持返回类型不变。
3. 让 `GPTImage2Edit` 复用新的响应解析，尽量不动外部接口。
4. 新增 `GPTImage2EditImages`。
5. 在 `nodes/GPTImage/__init__.py` 注册新节点和 display name。
6. 添加离线单测。
7. 运行 `python -m pytest test/test_gpt_image_nodes.py` 和 `python diagnose.py`。

## 取舍说明

- 为什么不新增 API Key 节点：社区插件常这么做，但本仓库已有统一的“节点参数优先，空则读 `KUAI_API_KEY`”模式。本次不引入新的凭证节点，避免增加工作流复杂度。
- 为什么新节点限制 15 张：本地 API 写“小于16张”，设计上用最多 15 张直接对应。
- 为什么输出可能是 DataURL：OpenAI GPT Image 模型默认返回 base64，URL 对 GPT Image 模型并不可靠。保持 STRING 输出可以兼容下游，但 UI 名称和文档必须说明不一定是 CDN URL。
- 为什么默认不发送多数可选字段：减少 provider 对未列出字段或默认值校验失败的概率，同时不影响默认行为。
- 为什么不自动重试不同字段名：图像生成/编辑请求成本高，自动重试容易造成重复请求。字段兼容问题应通过 helper 常量和真实 API 验证修正。
