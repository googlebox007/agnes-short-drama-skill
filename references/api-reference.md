# Agnes AI API 参考

## 文本生成

### 端点
`POST /v1/chat/completions`

### 请求参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | ✅ | 模型 ID，如 `agnes-2.5-flash` |
| messages | array | ✅ | 消息列表，格式 `[{"role": "system/user/assistant", "content": "..."}]` |
| max_tokens | int | ❌ | 最大生成 token 数，默认 2000 |
| temperature | float | ❌ | 温度参数，0-2，默认 0.7 |

### 响应示例
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "choices": [{
    "message": {"role": "assistant", "content": "生成的文本内容"},
    "finish_reason": "stop"
  }]
}
```

## 图片生成

### 端点
`POST /v1/images/generations`

### 请求参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | ✅ | 模型 ID，如 `agnes-image-2.5-flash` |
| prompt | string | ✅ | 图片描述 |
| size | string | ❌ | 尺寸，如 `1024x1024` |
| n | int | ❌ | 生成数量，默认 1 |

### 响应示例
```json
{
  "data": [{
    "url": "https://...",
    "revised_prompt": "..."
  }]
}
```

## 视频生成

### 端点
`POST /v1/videos`

### 请求参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | ✅ | 模型 ID |
| mode | string | ✅ | `text`/`keyframe`/`reference` |
| prompt | string | ✅ | 视频描述 |
| seconds | string | ❌ | 时长 4-12 秒 |
| size | string | ❌ | 分辨率，固定 `720P` |
| aspect_ratio | string | ❌ | 画幅，默认 `16:9` |
| first_frame | string | keyframe | 首帧图片 URL |
| last_frame | string | keyframe | 尾帧图片 URL |
| images | array | reference | 参考图片 URL 列表（最多 5 张） |
| audios | array | reference | 参考音频 URL 列表（最多 3 段） |

### 查询端点
`GET /v1/agnesapi?video_id={id}&model_name={model}`

## 模型列表

### 端点
`GET /v1/models`

### 可用模型
- `agnes-2.0-flash` - 文本模型（免费）
- `agnes-2.5-flash` - 文本模型（免费，推荐）
- `agnes-image-2.0-flash` - 图片模型（免费）
- `agnes-image-2.1-flash` - 图片模型（免费）
- `agnes-image-2.5-flash` - 图片模型（免费，推荐）
- `agnes-video-2.5-flash` - 视频模型（限时免费）
- `agnes-video-2.5` - 视频模型（付费）
