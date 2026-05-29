# 批量处理工作流使用指南

## 📋 概述

本指南介绍如何使用 ComfyUI_LLAI_API 插件的批量处理工作流，通过 CSV 文件实现视频和图像的批量生成。

**支持的批量处理类型**:
- ✅ Veo3 文生视频批量处理
- ✅ Veo3 图生视频批量处理
- ✅ Grok 文生视频批量处理
- ✅ Grok 图生视频批量处理
- ✅ Kling 批量处理
- ✅ Nano Banana 图像批量生成

---

## 🎯 工作流架构

所有批量处理工作流都遵循相同的两节点架构：

```
┌─────────────────────┐
│  📂 CSV批量读取器    │
│  (CSVBatchReader)   │
└──────────┬──────────┘
           │ JSON任务列表
           ▼
┌─────────────────────┐
│  📦 并发处理器       │
│  (Concurrent        │
│   Processor)        │
└─────────────────────┘
```

**数据流**:
1. CSV批量读取器读取 CSV 文件
2. 解析并转换为 JSON 格式的任务列表
3. 传递给并发处理器
4. 并发处理器逐个执行任务
5. 生成结果保存到输出目录

---

## 📂 可用的工作流文件

### Veo3 批量处理

| 工作流文件 | 说明 | CSV模板 |
|-----------|------|---------|
| `veo3_text2video_batch_workflow.json` | Veo3 文生视频批量处理 | `veo3_text2video_batch.csv` |
| `veo3_image2video_batch_workflow.json` | Veo3 图生视频批量处理 | `veo3_image2video_batch.csv` |
| `veo3_csv_concurrent_workflow.json` | Veo3 CSV并发处理（文生视频） | `veo3_text2video_batch.csv` |
| `veo3_csv_concurrent_image2video_workflow.json` | Veo3 CSV并发处理（图生视频） | `veo3_image2video_batch.csv` |

### Grok 批量处理

| 工作流文件 | 说明 | CSV模板 |
|-----------|------|---------|
| `grok_text2video_batch_workflow.json` | Grok 文生视频批量处理 | `grok_text2video_batch.csv` |
| `grok_image2video_batch_workflow.json` | Grok 图生视频批量处理 | `grok_image2video_batch.csv` |
| `grok_csv_concurrent_workflow.json` | Grok CSV并发处理（文生视频） | `grok_text2video_batch.csv` |
| `grok_csv_concurrent_image2video_workflow.json` | Grok CSV并发处理（图生视频） | `grok_image2video_batch.csv` |

### Kling 批量处理

| 工作流文件 | 说明 |
|-----------|------|
| `kling_batch_processing.json` | Kling 批量处理工作流 |

### Nano Banana 批量处理

| 工作流文件 | 说明 | CSV模板 |
|-----------|------|---------|
| （待补充） | Nano Banana 批量图像生成 | `nanobana_batch_template_text2image.csv` |

---

## 🚀 快速开始

### 步骤1：准备 CSV 文件

选择或创建适合你任务的 CSV 文件。

**方法A：使用示例文件**（推荐新手）
```bash
# 复制示例文件到 ComfyUI/input/ 目录
cp workflows/veo3_text2video_batch.csv /path/to/ComfyUI/input/
```

**方法B：使用模板创建**
1. 打开对应的 CSV 模板文件
2. 根据需求填写任务数据
3. 保存为 UTF-8 编码的 CSV 文件

**CSV 文件位置**:
- 示例文件：`workflows/*.csv`
- 模板文件：`workflows/nanobana_batch_template_*.csv`
- 参考文档：`workflows/CSV_TEMPLATES_README.md`

### 步骤2：加载工作流

1. 打开 ComfyUI
2. 点击"Load"按钮
3. 选择对应的工作流 JSON 文件
4. 工作流会自动加载到画布

### 步骤3：上传 CSV 文件

**方法1：拖放上传**（推荐）⭐
1. 找到"📂 CSV批量读取器"节点
2. 将 CSV 文件从文件管理器**拖放**到"CSV文件"参数框
3. 文件会自动上传并显示在下拉列表中

**方法2：选择已上传的文件**
1. 点击"CSV文件"参数的下拉箭头
2. 从列表中选择之前上传的文件

**方法3：输入文件路径**
1. 在"CSV路径"参数中输入完整路径
2. 支持绝对路径和相对路径

**详细说明**: 参见 [CSV批量读取器使用指南](../docs/CSV_BATCH_READER_GUIDE.md)

### 步骤4：配置处理器参数

在并发处理器节点中配置以下参数：

**必需参数**:
- **API密钥**: 输入你的 kuai.host API Key
  - 或设置环境变量 `KUAI_API_KEY`
  - 留空则使用环境变量

**可选参数**:
- **输出目录**: 生成文件的保存位置（默认：`./output/veo3` 或 `./output/grok`）
- **任务间延迟**: 两个任务之间的等待时间（默认：2.0秒）
- **最大等待时间**: 单个任务的最大等待时间（默认：600秒）
- **轮询间隔**: 查询任务状态的间隔（默认：10秒）

### 步骤5：执行工作流

1. 点击"Queue Prompt"按钮（或按 Ctrl+Enter）
2. 工作流开始执行
3. 在 ComfyUI 控制台查看处理进度

**控制台输出示例**:
```
[CSVBatchReader] 成功读取 5 个任务
[Batch] 开始批量处理 5 个任务
[1/5] 处理任务 (行 2)
✓ 任务 1 完成
[2/5] 处理任务 (行 3)
✓ 任务 2 完成
...
批量处理完成
总任务数: 5
成功: 5
失败: 0
```

### 步骤6：查看结果

生成的文件保存在输出目录中：

**文件结构**:
```
output/
├── veo3/                    # Veo3 输出目录
│   ├── prefix_a1b2c3d4.mp4 # 生成的视频文件
│   ├── prefix_e5f6g7h8.mp4
│   └── tasks.json           # 任务列表（包含任务ID和URL）
└── grok/                    # Grok 输出目录
    ├── prefix_i9j0k1l2.mp4
    └── tasks.json
```

**tasks.json 格式**:
```json
[
  {
    "task_id": "task_xxx",
    "prompt": "一只可爱的小猫",
    "video_url": "https://...",
    "local_path": "output/veo3/prefix_a1b2c3d4.mp4",
    "created_at": "2025-03-11 10:30:00"
  }
]
```

---

## 📊 CSV 文件格式详解

### Veo3 文生视频 CSV

**必需列**:
- `prompt`: 视频生成提示词

**可选列**:
- `model`: 模型名称（默认：`veo3.1`）
- `duration`: 视频时长（10/15/25，默认：10）
- `orientation`: 方向（`portrait`/`landscape`，默认：`landscape`）
- `output_prefix`: 输出文件名前缀（默认：`veo3`）

**示例**:
```csv
prompt,model,duration,orientation,output_prefix
"科技产品展示视频",veo3.1,10,landscape,product_demo
"时尚服装走秀",veo3.1,15,portrait,fashion_show
"美食制作教程",veo3.1,25,landscape,cooking_tutorial
```

### Veo3 图生视频 CSV

**必需列**:
- `prompt`: 视频生成提示词
- `image_1`: 参考图片URL

**可选列**:
- `model`: 模型名称（默认：`veo3.1`）
- `duration`: 视频时长（10/15/25，默认：10）
- `orientation`: 方向（`portrait`/`landscape`，默认：`landscape`）
- `output_prefix`: 输出文件名前缀（默认：`veo3`）

**示例**:
```csv
prompt,image_1,duration,output_prefix
"让这张图片动起来",https://example.com/image1.jpg,10,animated_1
"添加动态效果",https://example.com/image2.jpg,15,animated_2
```

### Grok 文生视频 CSV

**必需列**:
- `prompt`: 视频生成提示词

**可选列**:
- `model`: 模型名称（默认：`grok-video-1.5`）
- `duration`: 视频时长（默认：10）
- `orientation`: 方向（`portrait`/`landscape`，默认：`landscape`）
- `output_prefix`: 输出文件名前缀（默认：`grok`）

**示例**:
```csv
prompt,duration,orientation,output_prefix
"城市夜景延时摄影",10,landscape,city_night
"人物肖像特写",10,portrait,portrait_1
```

### Grok 图生视频 CSV

**必需列**:
- `prompt`: 视频生成提示词
- `image_1`: 第一张参考图片URL

**可选列**:
- `image_2`: 第二张参考图片URL
- `image_3`: 第三张参考图片URL
- `model`: 模型名称（默认：`grok-video-1.5`）
- `duration`: 视频时长（默认：10）
- `orientation`: 方向（`portrait`/`landscape`，默认：`landscape`）
- `output_prefix`: 输出文件名前缀（默认：`grok`）

**示例**:
```csv
prompt,image_1,image_2,image_3,output_prefix
"多角度产品展示",https://example.com/img1.jpg,https://example.com/img2.jpg,https://example.com/img3.jpg,product_multi
```

---

## ⚙️ 高级配置

### 并发处理优化

**任务间延迟**（`delay_between_tasks`）:
- 默认：2.0秒
- 建议：1.0-5.0秒
- 作用：避免 API 请求过于频繁

**最大等待时间**（`max_wait_time`）:
- 默认：600秒（10分钟）
- 建议：根据视频时长调整
  - 10秒视频：300-600秒
  - 15秒视频：600-900秒
  - 25秒视频：900-1200秒

**轮询间隔**（`poll_interval`）:
- 默认：10秒
- 建议：5-15秒
- 作用：查询任务状态的频率

### 错误处理

**失败任务重试**:
- 当前版本不支持自动重试
- 失败的任务会记录在处理报告中
- 可以手动重新提交失败的任务

**部分失败处理**:
- 即使部分任务失败，其他任务仍会继续执行
- 最终报告会显示成功和失败的数量

### 输出管理

**自定义输出目录**:
```python
# 在并发处理器节点中设置
output_dir = "./output/my_project/batch_001"
```

**文件命名规则**:
- 格式：`{output_prefix}_{hash8}.mp4`
- `output_prefix`: CSV 中指定的前缀
- `hash8`: 任务ID的前8位哈希值

---

## 🔍 监控和调试

### 查看处理进度

**方法1：ComfyUI 控制台**
- 实时显示处理进度
- 显示成功/失败状态
- 显示错误信息

**方法2：tasks.json 文件**
- 记录所有已完成任务的信息
- 包含任务ID、URL、本地路径

### 常见错误和解决方法

#### 错误1：API Key 未配置

**错误信息**:
```
API Key 未配置，请在节点参数或环境变量中设置
```

**解决方法**:
```bash
# 方法1：设置环境变量
export KUAI_API_KEY=your_key_here

# 方法2：在节点参数中输入
```

#### 错误2：任务超时

**错误信息**:
```
任务超时: task_xxx
```

**解决方法**:
- 增加 `max_wait_time` 参数
- 检查网络连接
- 检查 API 服务状态

#### 错误3：CSV 格式错误

**错误信息**:
```
CSV 文件中没有有效的任务数据
```

**解决方法**:
- 检查 CSV 文件是否有数据行
- 确认列名正确
- 确认文件编码为 UTF-8

---

## 💡 最佳实践

### 1. 测试小批量

在大规模批量处理前，先用 2-3 行数据测试：
```csv
prompt,output_prefix
"测试视频1",test_1
"测试视频2",test_2
```

### 2. 合理设置任务间延迟

- API 有速率限制，建议设置 2-5 秒延迟
- 避免因请求过快导致失败

### 3. 使用有意义的 output_prefix

```csv
prompt,output_prefix
"产品A展示",product_a_demo
"产品B展示",product_b_demo
```

便于后续管理和识别文件。

### 4. 备份 CSV 文件

在编辑前备份原始 CSV 文件，避免数据丢失。

### 5. 监控输出目录

定期清理输出目录，避免磁盘空间不足。

### 6. 使用版本控制

对于重要的 CSV 文件，使用 Git 等版本控制工具管理。

---

## 📚 相关文档

- [CSV批量读取器使用指南](../docs/CSV_BATCH_READER_GUIDE.md)
- [Veo3 并发处理器文档](../docs/VEO3_CONCURRENT_PROCESSOR_GUIDE.md)
- [Grok 并发处理器文档](../docs/GROK_CONCURRENT_PROCESSOR_GUIDE.md)
- [CSV 模板参考](./CSV_TEMPLATES_README.md)
- [主 README](../README.md)

---

## 🎓 示例场景

### 场景1：电商产品视频批量生成

**需求**: 为 10 个产品生成展示视频

**CSV 文件**:
```csv
prompt,duration,orientation,output_prefix
"产品A 360度旋转展示",10,landscape,product_a
"产品B 功能演示",15,landscape,product_b
"产品C 使用场景",10,landscape,product_c
...
```

**工作流**: `veo3_text2video_batch_workflow.json`

### 场景2：社交媒体内容批量生成

**需求**: 为社交媒体生成竖屏短视频

**CSV 文件**:
```csv
prompt,duration,orientation,output_prefix
"时尚穿搭推荐",10,portrait,fashion_01
"美食制作教程",15,portrait,food_01
"旅行风景展示",10,portrait,travel_01
...
```

**工作流**: `grok_text2video_batch_workflow.json`

### 场景3：图片动画化批量处理

**需求**: 将静态产品图转换为动态视频

**CSV 文件**:
```csv
prompt,image_1,output_prefix
"让产品动起来",https://cdn.example.com/product1.jpg,animated_product_1
"添加动态光效",https://cdn.example.com/product2.jpg,animated_product_2
...
```

**工作流**: `veo3_image2video_batch_workflow.json`

---

## 🔄 更新日志

- **2025-03-11**: 创建批量处理工作流使用指南
- **2025-03-10**: 添加 Grok 和 Veo3 并发处理工作流
- **2025-03-06**: 添加 Kling 批量处理支持

---

## 📞 获取帮助

如果遇到问题：
1. 查看本指南的相关章节
2. 检查 ComfyUI 控制台的日志输出
3. 参考示例 CSV 文件和工作流
4. 查看 [CSV批量读取器使用指南](../docs/CSV_BATCH_READER_GUIDE.md)
5. 在项目 GitHub 提交 Issue

---

**提示**: 批量处理是提高工作效率的利器，合理使用可以大幅节省时间！
