# Sora2 批量处理 CSV 使用指南

## 概述

Sora2 批量处理器支持通过 CSV 文件批量生成视频，可以同时处理文生视频和图生视频任务。

## CSV 格式

### 必需列

- **prompt** - 视频生成提示词

### 可选列

| 列名 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| `images` | 参考图片URL（留空为文生视频） | 空 | 图片URL，逗号分隔 |
| `model` | 模型名称 | `sora-2` | `sora-2`, `sora-2-pro` |
| `duration_sora2` | sora-2时长（秒） | `10` | `10`, `15` |
| `duration_sora2pro` | sora-2-pro时长（秒） | `15` | `15`, `25` |
| `orientation` | 视频方向 | `portrait` | `portrait`, `landscape` |
| `size` | 视频尺寸 | `large` | `small`, `large` |
| `watermark` | 是否添加水印 | `false` | `true`, `false` |
| `output_prefix` | 输出文件前缀 | `video_N` | 任意字符串 |

### CSV 示例

#### 基础示例（sora2_batch_basic.csv）

```csv
prompt,images,model,orientation,size,watermark,output_prefix
"A cat playing with a ball",,sora-2,portrait,large,false,cat_video
"A dog running in park",https://example.com/dog.jpg,sora-2,landscape,large,false,dog_video
"A bird flying in sky",,sora-2-pro,landscape,large,false,bird_video
```

#### 高级示例（sora2_batch_advanced.csv）

```csv
prompt,images,model,duration_sora2,duration_sora2pro,orientation,size,watermark,output_prefix
"Futuristic city at night",,sora-2,15,,landscape,large,false,cyberpunk_city
"Chef preparing dish",https://example.com/chef.jpg,sora-2,10,,portrait,large,false,chef_cooking
"Astronaut in space",,sora-2-pro,,25,landscape,large,false,astronaut_space
```

## 使用步骤

### 步骤 1: 准备 CSV 文件

```bash
# 使用示范文件
cp examples/sora2_batch_basic.csv my_videos.csv

# 或编辑自己的 CSV
nano my_videos.csv
```

**注意事项**：
- 使用 UTF-8 编码保存
- 提示词包含逗号时用双引号包裹
- 图片URL留空表示文生视频

### 步骤 2: 在 ComfyUI 中设置工作流

```
CSVBatchReader → Sora2BatchProcessor
├─ csv_path: my_videos.csv
└─ ...
```

### 步骤 3: 配置批量处理器参数

**必需参数**：
- `batch_tasks` - 来自 CSVBatchReader 的数据（自动连接）
- `api_key` - API 密钥（或使用环境变量）
- `output_dir` - 输出目录（例如：`./output/sora2_batch`）
- `delay_between_tasks` - 任务间延迟（推荐：2.0 秒）

**可选参数**：
- `api_base` - API 地址（默认：`https://api.kuai.host`）
- `wait_for_completion` - 是否等待完成（默认：`false`）
- `max_wait_time` - 最大等待时间（默认：1200 秒）
- `poll_interval` - 轮询间隔（默认：15 秒）

### 步骤 4: 执行批量处理

1. 点击 **Queue Prompt**
2. 查看 ComfyUI 控制台日志
3. 等待所有任务提交完成

### 步骤 5: 查看结果

**输出文件**：
```
output_dir/
├── tasks.json          # 所有任务信息汇总
├── cat_video.json      # 单个任务信息
├── dog_video.json
└── bird_video.json
```

**tasks.json 格式**：
```json
[
  {
    "task_id": "sora-2:task_xxx",
    "prompt": "A cat playing with a ball",
    "model": "sora-2",
    "orientation": "portrait",
    "size": "large",
    "has_images": false,
    "status": "pending",
    "output_prefix": "cat_video",
    "created_at": "2025-12-14 10:30:00"
  }
]
```

## 示范文件说明

### 1. sora2_batch_basic.csv

**内容**：5 个基础视频生成任务
- 混合文生视频和图生视频
- 使用 sora-2 和 sora-2-pro 模型
- 不同方向和尺寸

**适用场景**：
- 快速测试批量功能
- 学习 CSV 格式
- 小规模批量生成

### 2. sora2_batch_advanced.csv

**内容**：6 个高级视频生成任务
- 包含所有可配置参数
- 自定义时长设置
- 不同模型和尺寸组合

**适用场景**：
- 精细控制视频参数
- 大规模批量生成
- 专业视频制作

### 3. sora2_batch_template.csv

**内容**：6 个中文提示词模板
- 全中文提示词示例
- 涵盖常见视频类型
- 可直接复制修改

**适用场景**：
- 中文用户快速上手
- 提示词参考
- 模板复用

## 两种处理模式

### 模式 1: 快速提交（推荐）

**配置**：
```
wait_for_completion = false
```

**特点**：
- ⚡ 快速提交所有任务（每个任务 2-3 秒）
- 📝 保存任务ID到 JSON 文件
- 🔄 稍后使用 SoraQueryTask 查询状态

**适用场景**：
- 大批量任务（10+ 个）
- 不需要立即获取视频
- 自动化工作流

**工作流**：
```
CSVBatchReader → Sora2BatchProcessor → (保存任务ID)
                                    ↓
                            稍后使用 SoraQueryTask 查询
```

### 模式 2: 等待完成

**配置**：
```
wait_for_completion = true
max_wait_time = 1200
poll_interval = 15
```

**特点**：
- ⏳ 等待每个任务完成（每个任务 5-15 分钟）
- ✅ 自动获取视频URL
- 📦 完整的任务信息

**适用场景**：
- 少量任务（1-5 个）
- 需要立即获取视频
- 有充足的等待时间

**工作流**：
```
CSVBatchReader → Sora2BatchProcessor → (自动等待) → 获取视频URL
```

## 高级用法

### 1. 混合文生视频和图生视频

```csv
prompt,images,model,output_prefix
"Text-only video",,sora-2,text_video
"Image-based video",https://example.com/img.jpg,sora-2,image_video
```

### 2. 使用不同模型

```csv
prompt,model,duration_sora2,duration_sora2pro,output_prefix
"Quick video",sora-2,10,,quick_video
"Long video",sora-2-pro,,25,long_video
```

### 3. 自定义输出前缀

```csv
prompt,output_prefix
"Product A showcase",product_a_v1
"Product A variant",product_a_v2
```

### 4. 批量查询任务状态

生成 `tasks.json` 后，可以使用脚本批量查询：

```python
import json
from nodes.Sora2 import SoraQueryTask

# 读取任务列表
with open('output/sora2_batch/tasks.json', 'r') as f:
    tasks = json.load(f)

# 批量查询
querier = SoraQueryTask()
for task in tasks:
    status, video_url, _, _, _ = querier.query(
        task_id=task['task_id'],
        api_key='your_key',
        wait=False
    )
    print(f"{task['task_id']}: {status}")
    if video_url:
        print(f"  Video: {video_url}")
```

## 性能优化

### 1. 任务间延迟

**推荐设置**：
- 小批量（<10个）：1.0-2.0 秒
- 中批量（10-50个）：2.0-3.0 秒
- 大批量（>50个）：3.0-5.0 秒

**原因**：避免 API 限流

### 2. 分辨率选择

| 用途 | 推荐设置 | 说明 |
|------|---------|------|
| 测试 | `size=small` | 生成快，成本低 |
| 预览 | `size=small` | 快速查看效果 |
| 正式 | `size=large` | 高质量输出 |

### 3. 模型选择

| 模型 | 时长 | 特点 | 适用场景 |
|------|------|------|---------|
| sora-2 | 10-15秒 | 快速，经济 | 短视频，测试 |
| sora-2-pro | 15-25秒 | 高质量，长时长 | 专业视频 |

### 4. 批量大小建议

- **首次测试**：2-3 个任务
- **小规模**：5-10 个任务
- **中规模**：10-30 个任务
- **大规模**：30+ 个任务（分批处理）

## 常见问题

### Q1: CSV 文件编码问题？

**A**: 确保使用 UTF-8 编码保存，特别是包含中文时。

```bash
# 检查编码
file -i my_videos.csv

# 转换编码（如果需要）
iconv -f GBK -t UTF-8 my_videos.csv > my_videos_utf8.csv
```

### Q2: 提示词包含逗号怎么办？

**A**: 用双引号包裹整个提示词。

```csv
prompt,model
"A cat, a dog, and a bird playing together",sora-2
```

### Q3: 如何查看批量处理进度？

**A**: 查看 ComfyUI 控制台日志。

```
[Sora2Batch] 开始批量生成 5 个视频
[1/5] 处理任务 (行 2)
  提示词: A cat playing...
  任务ID: sora-2:task_xxx
✓ 任务 1 完成
```

### Q4: 任务失败怎么办？

**A**: 检查以下内容：
1. CSV 格式是否正确
2. API Key 是否有效
3. 参数值是否合法
4. 网络连接是否正常

查看 `tasks.json` 中的错误信息。

### Q5: 可以暂停和恢复批量处理吗？

**A**: 当前不支持暂停。建议：
- 分批处理大量任务
- 使用快速提交模式
- 保存 `tasks.json` 以便后续查询

### Q6: 图片URL从哪里获取？

**A**: 可以使用以下方式：
1. 使用 `UploadToImageHost` 节点上传本地图片
2. 使用已有的图床URL
3. 使用 kuai.host 图片上传 API

### Q7: 如何估算批量处理时间？

**A**:
- **快速提交模式**：任务数 × (2-3秒 + 延迟)
- **等待完成模式**：任务数 × (5-15分钟 + 延迟)

示例：
- 10个任务，快速提交：约 30-50 秒
- 10个任务，等待完成：约 50-150 分钟

### Q8: 批量处理失败率高怎么办？

**A**:
1. 增加任务间延迟
2. 检查 API Key 额度
3. 验证 CSV 格式
4. 分批处理
5. 使用快速提交模式

## 最佳实践

### 1. CSV 文件组织

```
my_project/
├── videos_batch_1.csv    # 第一批任务
├── videos_batch_2.csv    # 第二批任务
└── videos_template.csv   # 模板文件
```

### 2. 输出目录组织

```
output/
├── batch_20251214_001/   # 按日期和批次命名
│   ├── tasks.json
│   ├── video_1.json
│   └── video_2.json
└── batch_20251214_002/
    └── ...
```

### 3. 提示词编写

**好的提示词**：
```
"A professional chef preparing a gourmet dish in a modern kitchen,
close-up of hands, dramatic lighting, cinematic camera movement,
high-end restaurant atmosphere"
```

**差的提示词**：
```
"chef cooking"
```

### 4. 测试流程

1. 创建 2-3 个任务的测试 CSV
2. 使用 `size=small` 快速测试
3. 验证结果满意后
4. 使用 `size=large` 正式批量生成

### 5. 成本控制

- 先用 `sora-2` + `small` 测试
- 确认效果后再用 `sora-2-pro` + `large`
- 合理设置任务间延迟
- 分批处理大量任务

## 示例工作流

### 完整批量生成流程

```
步骤 1: 准备 CSV 文件
├─ 编辑 sora2_batch_basic.csv
└─ 确保 UTF-8 编码

步骤 2: 设置 ComfyUI 工作流
├─ CSVBatchReader
│   └─ csv_path: sora2_batch_basic.csv
└─ Sora2BatchProcessor
    ├─ api_key: your_key
    ├─ output_dir: ./output/batch_001
    ├─ delay_between_tasks: 2.0
    └─ wait_for_completion: false

步骤 3: 执行批量处理
├─ Queue Prompt
└─ 查看控制台日志

步骤 4: 查询任务状态
├─ 读取 output/batch_001/tasks.json
└─ 使用 SoraQueryTask 查询每个任务

步骤 5: 下载视频
└─ 从查询结果获取 video_url
```

## 技术支持

- **API 文档**：https://api.kuai.host/docs
- **注册账号**：https://api.kuai.host/register?aff=z2C8
- **问题反馈**：https://github.com/anthropics/claude-code/issues

## 更新日志

### 2025-12-14
- ✅ 初始版本发布
- ✅ 支持文生视频和图生视频批量处理
- ✅ 支持 sora-2 和 sora-2-pro 模型
- ✅ 两种处理模式（快速提交/等待完成）
- ✅ 完整的示范文件和文档

---

祝你批量创作愉快！🎬
