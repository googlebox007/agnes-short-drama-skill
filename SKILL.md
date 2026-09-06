---
name: agnes-short-drama
description: |
  Agnes AI 短剧创作全流程工具。基于 Pavo 平台的完整工作流，使用 Agnes AI 免费 API 实现从创意到成片的工业化生产。
  支持：
  - 一句话需求 → 制作卡片（标题/概梗/时长/画幅/风格）
  - 导演级剧本生成（角色设定+场景设计+分镜脚本含用光/情绪/音效/音乐）
  - 角色资产生成：主视图+侧面+全身+Character Sheet（设定板）
  - 场景资产生成：概念图+四视图
  - 分镜关键帧图生成
  - Reference模式视频生成（角色一致性锁定）
  - 成片拼接合成
  API端点：https://apihub.agnes-ai.cn/v1
  自动优先选择免费模型（含 flash 版本）
trigger: agnes短剧, agnes drama, 短剧创作, 分镜生成, 角色设计, Pavo, 剧情短片, 警示教育片
metadata:
  agent_created: true
  source: https://app.pavo-ai.work/
  trigger-words:
    - 短剧
    - 分镜
    - Pavo
    - 剧情短片
    - 角色一致性
    - 警示教育
---

# Agnes AI 短剧创作 Skill（Pavo Harness 完整版）

基于 Agnes AI Pavo 平台的完整短剧创作工作流，实现工业级生产标准。

## Pavo Harness 智能调度系统

```
用户输入一句话需求或上传剧本
    ↓
[Agent 理解层] → 识别内容类型（搞笑/情绪/反转/宣传片/广告/警示教育）
    ↓
[Agent 剧本层] → 生成制作需求卡片 + 导演级剧本（角色/场景/分镜）
    ↓
[Agent 资产层] → 角色立绘图+设定板 + 场景概念图+四视图
    ↓
[Agent 分镜层] → 多镜头分镜脚本 + 关键帧图生成
    ↓
[Agent 生成层] → Reference模式视频生成（角色一致性锁定）
    ↓
[Agent 剪辑层] → 成片合成输出
```

## 完整创作流程（7 步）

### 第 1 步：输入需求

用户提供一句话创意或完整剧本：
- "小猫在厨房做蛋炒饭，治愈风 30 秒"
- "一个实习生被歧视后逆袭成为部门经理的职场故事"
- 或上传剧本文件（docx/md/json）

### 第 2 步：生成制作需求卡片

AI 自动提取并生成结构化方案：

```json
{
  "title": "剧集名称",
  "synopsis": "故事梗概（100字内）",
  "duration": 75,        // 总时长（秒）
  "aspect_ratio": "16:9", // 画幅比例
  "visual_style": "写实剧情/警示教育", // 视觉风格
  "genre": "警示教育"
}
```

### 第 3 步：导演级剧本生成

生成包含以下内容的完整剧本：

**角色设定**（每个角色）：
```json
{
  "雷霆": {
    "name": "雷霆",
    "age": 31,
    "description": "面容方正，眼神锐利而自信，国企经理",
    "costume": "深蓝色西装，标准领带，皮鞋锃亮",
    "personality": "意气风发，后期逐渐憔悴心事重重"
  }
}
```

**场景设定**（每个场景）：
```json
{
  "雷霆办公室": {
    "name": "雷霆办公室",
    "description": "顶层落地窗办公室，俯瞰全城",
    "time": "白天",
    "lighting": "自然光从落地窗射入，明亮整洁",
    "atmosphere": "专业、权威、压抑"
  }
}
```

**分镜脚本**（每个镜头含导演级元数据）：
```json
{
  "shot": 1,
  "description": "清晨薄雾中的合川城区，镜头推进到学子教育公司大门",
  "time_range": "00:00-00:06",
  "characters": [],
  "scene": "合川区城区清晨",
  "camera": "推轨",
  "lighting": "晨雾柔光，侧逆光",
  "emotion": "希望、憧憬",
  "dialogue": "",
  "narration": "2015年的春天，雷霆刚刚满31岁",
  "sound_effects": "鸟鸣、远处车流",
  "music": "轻柔钢琴，充满希望",
  "duration": 6
}
```

### 第 4 步：角色资产生成

为每个角色生成 4 类资产图：

| 资产类型 | 描述 | 用途 |
|---------|------|------|
| 正面半身像 | 标准正面照，简洁背景 | 视频生成参考 |
| 侧面像 | 侧面肖像，轮廓清晰 | 一致性验证 |
| 全身立绘图 | 站姿标准，服装完整 | 角色设定 |
| Character Sheet | 多角度+表情+服装细节 | 资产锁定 |

### 第 5 步：场景资产生成

为每个场景生成 2 类资产图：

| 资产类型 | 描述 | 用途 |
|---------|------|------|
| 概念图 | 广角镜头，氛围感 | 场景参考 |
| 四视图 | 俯视+正视+侧视+透视 | 空间一致性 |

### 第 6 步：分镜关键帧生成

为每个镜头生成关键帧静态图：
- 基于分镜脚本的详细提示词
- 包含用光、构图、情绪描述
- 作为视频生成的参考图

### 第 7 步：视频生成（Reference模式）

使用 Reference 模式确保角色一致性：

```python
{
  "model": "agnes-video-2.5-flash",
  "mode": "reference",
  "prompt": "详细镜头描述+用光+情绪+音效+音乐",
  "seconds": "6",
  "size": "720P",
  "aspect_ratio": "16:9",
  "images": [
    "角色正面图.jpg",      # ≤5张
    "场景概念图.jpg",
    "关键帧图.jpg"
  ]
}
```

**速率限制**：每次请求间隔 15 秒，避免 429 错误。

### 第 8 步：成片合成

自动拼接所有分镜视频：
```bash
ffmpeg -f concat -safe 0 -i list.txt -c:v libx264 -crf 23 final.mp4
```

## API 调用方式

### 文本 API（剧本生成）
```python
POST https://apihub.agnes-ai.cn/v1/chat/completions
{
  "model": "agnes-2.5-flash",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 3000
}
```

### 图片 API（资产生成）
```python
POST https://apihub.agnes-ai.cn/v1/images/generations
{
  "model": "agnes-image-2.5-flash",
  "prompt": "详细描述...",
  "size": "1024x1024"
}
```

### 视频 API（分镜生成）
```python
POST https://apihub.agnes-ai.cn/v1/videos
{
  "model": "agnes-video-2.5-flash",
  "mode": "reference",
  "prompt": "导演级描述...",
  "seconds": "6",
  "size": "720P",
  "aspect_ratio": "16:9",
  "images": ["url1", "url2"]
}
```

### 查询接口
```python
GET https://apihub.agnes-ai.cn/v1/agnesapi?video_id={id}&model_name={model}
```

## 命令行工具

### 完整流程（推荐）
```bash
# 从创意概念开始
python scripts/pavo_complete.py "一句话创意"

# 从已有剧本开始
python scripts/pavo_complete.py --script ./script.json

# 指定输出目录
python scripts/pavo_complete.py "创意" --output ./my_drama
```

### 分步执行
```bash
# 只生成剧本
python scripts/pavo_complete.py "创意" --step script

# 只生成角色资产
python scripts/pavo_complete.py --script ./script.json --step characters
```

## 文件结构

```
project/
├── card.json                  # 制作需求卡片
├── script.json                # 导演级剧本（含完整元数据）
├── assets/
│   ├── characters/            # 角色资产
│   │   ├── 雷霆_正面.jpg
│   │   ├── 雷霆_侧面.jpg
│   │   ├── 雷霆_全身.jpg
│   │   └── 雷霆_设定板.jpg
│   ├── scenes/                # 场景资产
│   │   ├── 雷霆办公室.jpg
│   │   └── 雷霆办公室_四视图.jpg
│   └── keyframes/             # 分镜关键帧
│       ├── shot_01.jpg
│       └── shot_02.jpg
├── storyboard/                # 分镜视频
│   ├── shot_01.mp4
│   └── shot_02.mp4
└── final.mp4                  # 成片
```

## Windows 环境注意事项

### 代理问题
Windows 系统代理会导致 SSL 握手失败：
```
SSL: UNEXPECTED_EOF_WHILE_READING
```

**解决方案**：API 调用前清除代理环境变量
```python
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    os.environ.pop(key, None)
```

### 图片大小限制
- base64 编码图片过大可能导致 `media_download_failed`
- 建议使用图片 URL 直接传递
- 如需本地图片，先压缩至 150KB 以下

### 速率限制
- 视频生成：每次请求间隔 15 秒
- 图片生成：每次请求间隔 5 秒
- 文本生成：几乎无限制

## 角色一致性锁定机制

核心解决方案：
1. 生成高质量角色立绘图（正面+侧面+全身）
2. 将角色图作为 reference 传入视频 API
3. 每个镜头引用同一套角色资产
4. 关键帧图也作为参考，确保构图一致

## 参考资源

- Pavo 平台：https://app.pavo-ai.work/
- Agnes AI 文档：https://wiki.agnes-ai.com/en/docs
- API 端点：https://apihub.agnes-ai.cn/v1
