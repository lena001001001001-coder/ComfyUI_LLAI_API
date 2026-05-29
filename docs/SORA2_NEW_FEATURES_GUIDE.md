# Sora2 新功能使用指南

## 概述

Sora2 新增了两个重要功能：
1. **角色创建** - 从视频中提取角色，用于后续视频生成
2. **视频编辑（Remix）** - 基于已生成的视频进行二次编辑

## 新增节点

### 1. 👤 创建角色 (SoraCreateCharacter)

从视频中提取角色，生成可在提示词中使用的角色标识。

**适用场景**：
- 从现有视频中提取角色
- 创建可复用的角色库
- 在多个视频中使用相同角色

#### 参数说明

##### 必需参数

- **timestamps** (时间范围)
  - **类型**：字符串
  - **格式**：`"开始秒,结束秒"`（例如：`"1,3"`）
  - **说明**：指定视频中包含角色的时间段
  - **限制**：
    - 时间范围差值最小 1 秒
    - 时间范围差值最大 3 秒
  - **示例**：
    - `"1,3"` - 提取视频 1-3 秒的角色
    - `"2,4"` - 提取视频 2-4 秒的角色

##### 可选参数（二选一）

- **url** (视频URL)
  - **类型**：字符串
  - **说明**：视频的完整URL地址
  - **示例**：`"https://example.com/video.mp4"`
  - **注意**：url 和 from_task 只能提供一个

- **from_task** (任务ID)
  - **类型**：字符串
  - **说明**：已生成视频的任务ID
  - **示例**：`"video_abc123"`
  - **注意**：url 和 from_task 只能提供一个

##### 其他可选参数

- **api_base** (API地址)
  - **默认值**：`https://api.kuai.host`

- **api_key** (API密钥)
  - **说明**：留空使用环境变量 `KUAI_API_KEY`

- **timeout** (超时时间)
  - **默认值**：60 秒
  - **范围**：5-300 秒

#### 返回值

1. **角色ID** (STRING) - 角色的唯一标识符
2. **角色名称** (STRING) - 角色的用户名（用于提示词中 `@{username}`）
3. **角色主页** (STRING) - 角色在 OpenAI 的主页链接
4. **角色头像URL** (STRING) - 角色头像图片地址

#### 使用示例

##### 示例 1：从视频URL创建角色

```
工作流:
SoraCreateCharacter
├─ timestamps: "1,3"
├─ url: "https://example.com/my_video.mp4"
└─ api_key: (使用环境变量)

返回:
├─ 角色ID: ch_6918d62178e48191a0b1ae49be428a13
├─ 角色名称: hfspncadz.mooflapand
├─ 角色主页: https://sora.chatgpt.com/profile/hfspncadz.mooflapand
└─ 角色头像URL: https://...
```

##### 示例 2：从任务ID创建角色

```
工作流:
SoraCreateAndWait → SoraCreateCharacter
├─ (生成视频)    ├─ timestamps: "2,4"
└─ 任务ID输出 ──→ └─ from_task: (从前一节点获取)

结果:
创建基于刚生成视频的角色
```

##### 示例 3：在新视频中使用角色

创建角色后，可以在提示词中使用 `@{角色名称}` 来引用该角色：

```
SoraCreateCharacter → SoraText2Video
├─ 返回角色名称    ├─ prompt: "A video of @hfspncadz.mooflapand walking in the park"
└─ hfspncadz...  ──→ └─ ...
```

### 2. 🎬 编辑视频 (SoraRemixVideo)

基于已完成的视频进行二次编辑，生成新的视频变体。

**适用场景**：
- 修改视频背景
- 调整视频风格
- 添加新元素到现有视频
- 基于原视频创建变体

#### 参数说明

##### 必需参数

- **video_id** (视频ID)
  - **类型**：字符串
  - **说明**：已完成视频的ID（格式：`video_xxx`）
  - **示例**：`"video_099c5197-abfd-4e16-88ff-1e162f2a5c77"`
  - **获取方式**：从 SoraQueryTask 或 SoraCreateAndWait 的返回值中获取

- **prompt** (编辑提示词)
  - **类型**：多行文本
  - **说明**：描述要对视频进行的编辑
  - **示例**：
    - `"让这个视频背景变成紫色"`
    - `"将视频风格改为水彩画风格"`
    - `"在视频中添加飘落的雪花"`

##### 可选参数

- **api_base** (API地址)
  - **默认值**：`https://api.kuai.host`

- **api_key** (API密钥)
  - **说明**：留空使用环境变量 `KUAI_API_KEY`

- **timeout** (超时时间)
  - **默认值**：120 秒
  - **范围**：5-600 秒

#### 返回值

1. **新任务ID** (STRING) - 编辑后视频的任务ID
2. **状态** (STRING) - 任务初始状态（通常为 `queued`）
3. **原始视频ID** (STRING) - 被编辑的原视频ID

#### 使用示例

##### 示例 1：基础视频编辑

```
工作流:
SoraRemixVideo
├─ video_id: "video_099c5197-abfd-4e16-88ff-1e162f2a5c77"
├─ prompt: "让这个视频背景变成紫色"
└─ api_key: (使用环境变量)

返回:
├─ 新任务ID: video_ffd746b3-3f44-4b48-8d4a-dd5a10261287
├─ 状态: queued
└─ 原始视频ID: video_099c5197-abfd-4e16-88ff-1e162f2a5c77
```

##### 示例 2：完整编辑工作流

```
工作流:
SoraCreateAndWait → SoraRemixVideo → SoraQueryTask
├─ 生成原视频    ├─ 编辑视频    ├─ 查询编辑结果
└─ 任务ID输出 ──→ └─ 新任务ID ──→ └─ 获取编辑后视频
```

##### 示例 3：多次编辑

可以对同一视频进行多次编辑，创建不同变体：

```
原视频 (video_abc)
  ├─ 编辑1: "背景变紫色" → video_def
  ├─ 编辑2: "添加雪花" → video_ghi
  └─ 编辑3: "水彩画风格" → video_jkl
```

## 工作流示例

### 完整角色创建和使用流程

```
步骤 1: 生成包含角色的视频
SoraText2Video
├─ prompt: "A person walking in a garden"
└─ 输出: task_id_1

步骤 2: 查询视频完成
SoraQueryTask
├─ task_id: task_id_1
└─ 输出: video_id_1

步骤 3: 从视频创建角色
SoraCreateCharacter
├─ from_task: video_id_1
├─ timestamps: "1,3"
└─ 输出: character_name

步骤 4: 在新视频中使用角色
SoraText2Video
├─ prompt: "A video of @{character_name} playing basketball"
└─ 输出: 包含相同角色的新视频
```

### 完整视频编辑流程

```
步骤 1: 生成原始视频
SoraCreateAndWait
├─ prompt: "A cat playing with a ball"
└─ 输出: video_id_1, video_url_1

步骤 2: 编辑视频（变体1）
SoraRemixVideo
├─ video_id: video_id_1
├─ prompt: "让背景变成海滩"
└─ 输出: task_id_2

步骤 3: 查询编辑结果
SoraQueryTask
├─ task_id: task_id_2
└─ 输出: video_url_2

步骤 4: 再次编辑（变体2）
SoraRemixVideo
├─ video_id: video_id_1
├─ prompt: "添加下雨效果"
└─ 输出: task_id_3
```

## API 说明

### 创建角色端点

- **URL**：`POST https://api.kuai.host/sora/v1/characters`
- **请求体**：
  ```json
  {
    "timestamps": "1,3",
    "url": "https://example.com/video.mp4",
    // 或
    "from_task": "video_abc123"
  }
  ```
- **响应**：
  ```json
  {
    "id": "ch_xxx",
    "username": "username.suffix",
    "permalink": "https://sora.chatgpt.com/profile/username.suffix",
    "profile_picture_url": "https://..."
  }
  ```

### 编辑视频端点

- **URL**：`POST https://api.kuai.host/v1/videos/{video_id}/remix`
- **请求体**：
  ```json
  {
    "prompt": "让这个视频背景变成紫色"
  }
  ```
- **响应**：
  ```json
  {
    "id": "video_xxx",
    "object": "video",
    "model": "sora-2",
    "status": "queued",
    "remixed_from_video_id": "video_yyy"
  }
  ```

## 最佳实践

### 角色创建

1. **选择合适的时间范围**
   - 选择角色清晰可见的片段
   - 确保时间范围在 1-3 秒之间
   - 避免选择角色被遮挡的片段

2. **角色命名**
   - 系统自动生成角色名称
   - 记录角色名称以便在提示词中使用
   - 可以创建角色库文档记录所有角色

3. **角色复用**
   - 在提示词中使用 `@{username}` 引用角色
   - 可以在多个视频中使用同一角色
   - 角色会保持一致的外观特征

### 视频编辑

1. **编辑提示词技巧**
   - 明确描述要修改的内容
   - 使用具体的视觉描述
   - 可以组合多个编辑要求

2. **编辑类型**
   - **背景修改**：`"将背景改为海滩/森林/城市"`
   - **风格转换**：`"改为水彩画/油画/动漫风格"`
   - **添加元素**：`"添加飘落的雪花/飞舞的蝴蝶"`
   - **光照调整**：`"改为黄昏光照/夜晚场景"`

3. **迭代编辑**
   - 可以对编辑结果再次编辑
   - 每次编辑都会生成新的视频ID
   - 保留原视频ID以便回溯

## 常见问题

### Q1: 角色创建需要多长时间？
A: 通常 10-30 秒，取决于视频大小和服务器负载。

### Q2: 可以从任何视频创建角色吗？
A: 可以从以下来源创建角色：
- 通过 URL 提供的任何视频
- 通过 Sora 生成的视频（使用 from_task）

### Q3: 角色名称可以自定义吗？
A: 角色名称由系统自动生成，无法自定义。但可以记录角色ID和名称的对应关系。

### Q4: 视频编辑会保留原视频吗？
A: 是的，编辑会创建新的视频，原视频保持不变。

### Q5: 可以编辑多少次？
A: 没有次数限制，可以对同一视频进行多次编辑，每次都会生成新的视频。

### Q6: 编辑后的视频质量会下降吗？
A: 不会，每次编辑都是基于原视频重新生成，质量保持一致。

### Q7: 如何获取视频ID？
A: 视频ID可以从以下节点获取：
- SoraQueryTask 的返回值
- SoraCreateAndWait 的返回值
- 查看任务详情中的 video_id 字段

### Q8: 编辑提示词有字数限制吗？
A: 建议保持在 200 字符以内，过长的提示词可能影响编辑效果。

## 技术细节

### 节点实现

- **位置**：`/workspaces/ComfyUI_LLAI_API/nodes/Sora2/sora2.py`
- **依赖**：`requests`、`kuai_utils`
- **分类**：`KuAi/Sora2`

### 错误处理

所有 API 错误都会转换为用户友好的中文错误消息：
- 参数验证错误
- 网络连接错误
- API 调用错误
- 超时错误

### 日志输出

节点会输出详细的日志信息：
```
[SoraCreateCharacter] 角色创建成功: ch_xxx (@username)
[SoraRemixVideo] 视频编辑任务创建成功: video_xxx (基于 video_yyy)
```

## 更新日志

### 2025-12-14
- ✅ 新增 SoraCreateCharacter 节点
- ✅ 新增 SoraRemixVideo 节点
- ✅ 完整的中文标签和错误提示
- ✅ 集成到 KuAi Power 快捷面板
- ✅ 完整的测试套件

## 相关资源

- **API 文档**：https://api.kuai.host/docs
- **注册账号**：https://api.kuai.host/register?aff=z2C8
- **问题反馈**：https://github.com/anthropics/claude-code/issues
- **主文档**：`README.md`

## 许可证

本节点遵循 ComfyUI_LLAI_API 插件的许可证。
