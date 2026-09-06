# Agnes Short Drama Skill

基于 Agnes AI Pavo 平台的完整短剧创作工作流实现，支持从创意概念到成片输出的工业化生产。

## ✨ 功能特性

- **制作需求卡片** — 一句话创意 → 结构化方案
- **导演级剧本** — 角色设定 + 场景设计 + 分镜脚本（含用光/情绪/音效/音乐元数据）
- **角色资产生成** — 主视图 + 侧面 + 全身 + Character Sheet（设定板）
- **场景资产生成** — 概念图 + 四视图
- **分镜关键帧** — 为每个镜头生成参考图
- **Reference模式视频** — 传递参考图确保角色一致性
- **成片拼接** — 自动合并所有分镜

## 📁 项目结构

```
agnes-short-drama-skill/
├── SKILL.md                  # 技能文档
├── README.md                 # 本文件
├── references/
│   └── api-reference.md      # API 参考
└── scripts/
    ├── pavo_complete.py      # 完整版工作流（推荐）
    ├── generate_drama.py     # 修复版脚本
    ├── drama_generator.py    # 原脚本
    └── pavo_workflow.py      # 基础版脚本
```

## 🚀 快速开始

### 安装技能

将 `scripts/` 目录放入 WorkBuddy 技能目录：

```bash
cp -r scripts ~/.workbuddy/skills/agnes-short-drama/
```

### 使用方法

```bash
# 完整流程（从创意概念开始）
python scripts/pavo_complete.py "一句话创意"

# 从已有剧本开始
python scripts/pavo_complete.py --script ./script.json

# 指定输出目录
python scripts/pavo_complete.py "创意" --output ./my_drama
```

## 📋 使用示例

### 从创意概念生成
```bash
python scripts/pavo_complete.py "一个关于反腐的警示教育短片"
```

### 从剧本文件生成
```bash
python scripts/pavo_complete.py --script ./output.docx
```

## 🔧 技术细节

### 依赖

- Python 3.10+
- ffmpeg（视频拼接）
- Agnes AI API Key

### API 端点

| 服务 | 端点 |
|------|------|
| 文本 | `https://apihub.agnes-ai.cn/v1/chat/completions` |
| 图片 | `https://apihub.agnes-ai.cn/v1/images/generations` |
| 视频 | `https://apihub.agnes-ai.cn/v1/videos` |
| 查询 | `GET /v1/agnesapi?video_id={id}&model_name={model}` |

### Windows 环境注意事项

**代理问题**：Windows 系统代理可能导致 SSL 握手失败。解决方案已在脚本中内置：
```python
# 自动清除代理环境变量
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(key, None)
```

## 📚 相关资源

- [Agnes AI 官方文档](https://wiki.agnes-ai.com/en/docs)
- [Pavo 平台](https://app.pavo-ai.work/)
- [API 端点](https://apihub.agnes-ai.cn/v1)

## 📄 License

MIT License
