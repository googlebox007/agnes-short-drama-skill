#!/usr/bin/env python3
"""
Agnes AI 短剧创作全流程 - Pavo Harness 完整版
实现官方Pavo平台完整工作流：
- 角色资产：主视图+侧面+全身+Character Sheet
- 场景资产：四视图+概念图
- 导演级分镜脚本（用光/情绪/音效/音乐等）
- 分镜关键帧图生成
- Reference模式视频生成（角色一致性）
"""

import os
import json
import urllib.request
import urllib.parse
import ssl
import time
import argparse
import base64
from io import BytesIO
from pathlib import Path

# ============ 配置 ============
BASE_URL = "https://apihub.agnes-ai.cn/v1"
API_KEY = os.environ.get("AGNES_API_KEY", "sk-kcnPnHEcbukoLM1niz4cXl6z5rl0r9J5SmRpYtuLN35bxUQK")
MODEL_TEXT = "agnes-2.5-flash"
MODEL_IMAGE = "agnes-image-2.5-flash"
MODEL_VIDEO = "agnes-video-2.5-flash"

# 限制
VIDEO_MAX_WAIT = 600
RPM_DELAY = 15  # 速率限制间隔（秒）
MAX_RETRIES = 3


# ============ SSL与代理处理 ============
def clear_proxy():
    """清除代理环境变量，避免SSL握手失败"""
    for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
        os.environ.pop(key, None)


def get_ssl_context():
    """创建不验证hostname的SSL上下文"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


# ============ API调用 ============
def api_request(endpoint, payload, timeout=120):
    """API请求封装"""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        ctx = get_ssl_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"  HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  请求错误: {e}")
        return None


def api_get(url_path, params=None):
    """GET请求"""
    url = f"{BASE_URL}/{url_path.lstrip('/')}"
    if params:
        query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {API_KEY}'})
    try:
        ctx = get_ssl_context()
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"  GET错误: {e}")
        return None


def download_file(url, path):
    """下载文件"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        ctx = get_ssl_context()
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            with open(path, 'wb') as f:
                f.write(resp.read())
            return True
    except Exception as e:
        print(f"  下载失败: {e}")
        return False


def compress_image_for_api(image_path, max_kb=150):
    """压缩图片为base64，控制大小"""
    try:
        from PIL import Image
        img = Image.open(image_path)
        
        # 转换为RGB（去除alpha通道）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 压缩到目标大小
        quality = 85
        while quality > 30:
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            size_kb = len(buffer.getvalue()) / 1024
            
            if size_kb <= max_kb:
                break
            quality -= 5
        
        # 缩放（如果需要）
        if size_kb > max_kb:
            ratio = (max_kb / size_kb) ** 0.5
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except ImportError:
        # 无PIL，使用简单缩放
        img = Image.open(image_path)
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=50)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"  图片压缩失败: {e}")
        return None


# ============ Step 1: 制作需求卡片 ============
def generate_production_card(concept):
    """生成制作需求卡片"""
    print("\n" + "="*60)
    print("📋 Step 1: 生成制作需求卡片")
    print("="*60)

    prompt = f"""你是专业的短剧制作人。根据概念生成制作需求卡片。

概念："{concept}"

要求：
- 标题简短有力（不超过8字）
- 梗概100字以内，包含核心冲突
- 时长60-90秒
- 画幅16:9
- 风格：写实/剧情/警示教育

只输出JSON，格式：
{{"title":"剧名","synopsis":"梗概","duration":75,"aspect_ratio":"16:9","visual_style":"写实剧情","genre":"警示教育"}}"""

    payload = {
        "model": MODEL_TEXT,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500
    }

    result = api_request("chat/completions", payload)
    if not result:
        return None

    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    # 提取JSON
    import re
    match = re.search(r'\{[\s\S]*\}', content)
    if match:
        try:
            card = json.loads(match.group())
            print(f"  剧名: {card.get('title')}")
            print(f"  梗概: {card.get('synopsis', '')[:50]}...")
            print(f"  时长: {card.get('duration')}秒")
            return card
        except:
            pass
    
    print(f"  解析失败: {content[:100]}")
    return {"title": "未命名", "synopsis": concept, "duration": 75}


# ============ Step 2: 剧本生成（导演级） ============
def generate_script(card, concept):
    """生成导演级剧本 - 包含角色、场景、详细分镜"""
    print("\n" + "="*60)
    print("📝 Step 2: 生成导演级剧本")
    print("="*60)

    # 2a: 生成角色
    char_prompt = f"""生成4个角色JSON对象。

概念：{concept}
剧名：{card.get('title', '未命名')}

要求：
- 每个角色需要详细的外貌、性格、服装描述
- 包含年龄、身高体型、面部特征
- 服装要有时代感和身份特征
- 角色要有辨识度和记忆点

只输出JSON，格式：
{{"角色名":{{"name":"名字","age":31,"description":"详细描述","costume":"服装描述","personality":"性格特征"}}}}"""

    char_payload = {"model": MODEL_TEXT, "messages": [{"role": "user", "content": char_prompt}], "max_tokens": 1200}
    char_result = api_request("chat/completions", char_payload)
    time.sleep(RPM_DELAY)

    characters = {}
    if char_result:
        content = char_result.get("choices", [{}])[0].get("message", {}).get("content", "")
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                characters = json.loads(match.group())
            except:
                pass
    print(f"  角色: {list(characters.keys())}")

    # 2b: 生成场景
    scene_prompt = f"""生成8个关键场景JSON对象。

概念：{concept}
剧名：{card.get('title', '未命名')}

要求：
- 每个场景要详细的环境、光线、氛围描述
- 包含时间（白天/夜晚）、天气、季节
- 关键道具和细节
- 场景要符合剧情发展逻辑

只输出JSON，格式：
{{"场景名":{{"name":"场景名","description":"详细描述","time":"白天/夜晚","lighting":"光线描述","atmosphere":"氛围"}}}}"""

    scene_payload = {"model": MODEL_TEXT, "messages": [{"role": "user", "content": scene_prompt}], "max_tokens": 1500}
    scene_result = api_request("chat/completions", scene_payload)
    time.sleep(RPM_DELAY)

    scenes = {}
    if scene_result:
        content = scene_result.get("choices", [{}])[0].get("message", {}).get("content", "")
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                scenes = json.loads(match.group())
            except:
                pass
    print(f"  场景: {list(scenes.keys())}")

    # 2c: 生成导演级分镜脚本
    sb_prompt = f"""生成16个导镜头分镜脚本JSON数组。

概念：{concept}
剧名：{card.get('title', '未命名')}
角色：{list(characters.keys())}
场景：{list(scenes.keys())}

每个镜头必须包含以下导演级元数据：

{{
  "shot": 1,
  "description": "画面内容详细描述",
  "time_range": "00:00-00:05",
  "characters": ["角色名"],
  "scene": "场景名",
  "camera": "推轨/横移/固定/跟拍/远景/中景/特写",
  "lighting": "用光描述（如：柔和侧光、逆光剪影）",
  "emotion": "情绪氛围（如：紧张、压抑、温馨）",
  "dialogue": "角色台词",
  "narration": "旁白内容",
  "sound_effects": "音效描述（如：脚步声、雨声）",
  "music": "音乐风格（如：紧张弦乐、悲伤钢琴）",
  "duration": 5
}}

要求：
- 镜头总时长60-90秒
- 每个镜头5-7秒
- 画面描述要具体到人物动作、表情、位置
- 用光要专业（顺光/侧光/逆光/顶光/底光）
- 情绪要贯穿全片
- 音效和音乐要配合画面节奏
"""

    sb_payload = {"model": MODEL_TEXT, "messages": [{"role": "user", "content": sb_prompt}], "max_tokens": 3000}
    sb_result = api_request("chat/completions", sb_payload)
    time.sleep(RPM_DELAY)

    storyboard = []
    if sb_result:
        content = sb_result.get("choices", [{}])[0].get("message", {}).get("content", "")
        match = re.search(r'\[[\s\S]*\]', content)
        if match:
            try:
                storyboard = json.loads(match.group())
            except:
                pass
        
        # 确保每个镜头有基本字段
        for shot in storyboard:
            if not shot.get("description"):
                shot["description"] = "空镜头"
            if not shot.get("duration"):
                shot["duration"] = 5
            if not shot.get("camera"):
                shot["camera"] = "固定镜头"
            if not shot.get("lighting"):
                shot["lighting"] = "自然光"
            if not shot.get("emotion"):
                shot["emotion"] = "中性"
    
    print(f"  分镜数: {len(storyboard)}")
    if storyboard:
        for i, s in enumerate(storyboard[:3]):
            print(f"    镜头{i+1}: {s.get('description', '')[:30]}...")

    # 构建剧本
    script = {
        "title": card.get("title", "未命名"),
        "genre": card.get("visual_style", "剧情"),
        "synopsis": card.get("synopsis", ""),
        "characters": characters,
        "scenes": scenes,
        "storyboard": storyboard
    }

    return script


# ============ Step 3: 角色资产生成 ============
def generate_character_assets(script, output_dir):
    """生成角色资产：主视图+侧面+全身+Character Sheet"""
    print("\n" + "="*60)
    print("🎨 Step 3: 生成角色资产")
    print("="*60)

    characters = script.get("characters", {})
    assets = {}
    output_dir = os.path.join(output_dir, "characters")
    os.makedirs(output_dir, exist_ok=True)

    for name, char_info in characters.items():
        print(f"\n  生成角色: {name}...")
        
        # 基础描述
        base_desc = char_info.get("description", "")
        costume = char_info.get("costume", "")
        
        # 3.1 正面半身像
        front_prompt = f"{base_desc}, 正面半身像, 标准照, 简洁纯色背景, 电影级打光, 写实风格, 人物特写, 高清细节"
        front_path = os.path.join(output_dir, f"{name}_正面.jpg")
        if not os.path.exists(front_path):
            generate_image(front_prompt, front_path, "1024x1024")
        
        # 3.2 侧面像
        side_prompt = f"{base_desc}, 侧面肖像, 轮廓清晰, 简洁背景, 专业人像摄影, 侧光照明"
        side_path = os.path.join(output_dir, f"{name}_侧面.jpg")
        if not os.path.exists(side_path):
            generate_image(side_prompt, side_path, "1024x1024")
        
        # 3.3 全身立绘图
        full_prompt = f"{base_desc}, {costume}, 全身立绘图, 站姿标准, 简洁背景, 设计稿风格, 多角度参照"
        full_path = os.path.join(output_dir, f"{name}_全身.jpg")
        if not os.path.exists(full_path):
            generate_image(full_prompt, full_path, "768x1024")
        
        # 3.4 Character Sheet（角色设定板）
        sheet_prompt = f"""{base_desc}, {costume}
角色设定板, Character Sheet, 包含多个表情和角度, 正面侧面特写, 
白色背景, 设计稿风格, 专业角色设计图, 清晰的服装细节和配饰"""
        sheet_path = os.path.join(output_dir, f"{name}_设定板.jpg")
        if not os.path.exists(sheet_path):
            generate_image(sheet_prompt, sheet_path, "1024x1024")
        
        assets[name] = {
            "front": front_path,
            "side": side_path,
            "full": full_path,
            "sheet": sheet_path
        }
        print(f"    ✅ {name} 资产已生成")

    return assets


def generate_image(prompt, output_path, size="1024x1024"):
    """生成单张图片"""
    payload = {
        "model": MODEL_IMAGE,
        "prompt": prompt,
        "size": size,
        "n": 1
    }
    
    result = api_request("images/generations", payload)
    if result and result.get("data"):
        url = result["data"][0].get("url")
        if url:
            return download_file(url, output_path)
    
    return False


# ============ Step 4: 场景资产生成 ============
def generate_scene_assets(script, output_dir):
    """生成场景资产：概念图+四视图"""
    print("\n" + "="*60)
    print("🏞️  Step 4: 生成场景资产")
    print("="*60)

    scenes = script.get("scenes", {})
    assets = {}
    output_dir = os.path.join(output_dir, "scenes")
    os.makedirs(output_dir, exist_ok=True)

    for name, scene_info in scenes.items():
        print(f"  生成场景: {name}...")
        
        base_desc = scene_info.get("description", "")
        time_of_day = scene_info.get("time", "白天")
        lighting = scene_info.get("lighting", "自然光")
        
        # 4.1 概念图
        concept_prompt = f"{base_desc}, {time_of_day}, {lighting}, 电影概念图, 广角镜头, 氛围感, 专业摄影"
        concept_path = os.path.join(output_dir, f"{name}.jpg")
        if not os.path.exists(concept_path):
            generate_image(concept_prompt, concept_path, "1024x768")
        
        # 4.2 四视图（俯视图、正视图、侧视图、透视图）
        views_prompt = f"""{base_desc}, {time_of_day}, 场景四视图, 建筑效果图风格,
俯视图+正视图+侧视图+透视图, 详细标注, 设计图风格, 清晰的空间关系"""
        views_path = os.path.join(output_dir, f"{name}_四视图.jpg")
        if not os.path.exists(views_path):
            generate_image(views_prompt, views_path, "1024x768")
        
        assets[name] = {
            "concept": concept_path,
            "views": views_path
        }
        print(f"    ✅ {name} 资产已生成")

    return assets


# ============ Step 5: 分镜关键帧生成 ============
def generate_storyboard_keyframes(script, char_assets, scene_assets, output_dir):
    """生成分镜关键帧图"""
    print("\n" + "="*60)
    print("🎬 Step 5: 生成分镜关键帧")
    print("="*60)

    storyboard = script.get("storyboard", [])
    assets = {}
    output_dir = os.path.join(output_dir, "keyframes")
    os.makedirs(output_dir, exist_ok=True)

    for shot in storyboard:
        shot_num = shot.get("shot", 1)
        desc = shot.get("description", "")
        camera = shot.get("camera", "固定镜头")
        lighting = shot.get("lighting", "自然光")
        emotion = shot.get("emotion", "中性")
        
        # 构建关键帧提示词
        keyframe_prompt = f"""{desc}, {camera}, {lighting}, {emotion}氛围, 
电影级构图, 专业摄影, 高质量渲染, 16:9画幅"""
        
        keyframe_path = os.path.join(output_dir, f"shot_{shot_num:02d}.jpg")
        if not os.path.exists(keyframe_path):
            print(f"  生成镜头{shot_num}关键帧...")
            generate_image(keyframe_prompt, keyframe_path, "1280x720")
        
        assets[shot_num] = keyframe_path
        print(f"    ✅ 镜头{shot_num}关键帧已生成")

    return assets


# ============ Step 6: 视频生成（Reference模式） ============
def generate_storyboard_videos(script, char_assets, scene_assets, keyframes, output_dir):
    """生成分镜视频，使用Reference模式确保角色一致性"""
    print("\n" + "="*60)
    print("🎥 Step 6: 生成分镜视频")
    print("="*60)

    storyboard = script.get("storyboard", [])
    videos = []
    os.makedirs(output_dir, exist_ok=True)

    for shot in storyboard:
        shot_num = shot.get("shot", 1)
        desc = shot.get("description", "")
        camera = shot.get("camera", "固定镜头")
        characters = shot.get("characters", [])
        scene = shot.get("scene", "")
        duration = min(shot.get("duration", 5), 12)  # 最长12秒
        
        shot_path = os.path.join(output_dir, f"shot_{shot_num:02d}.mp4")
        
        # 检查是否已完成
        if os.path.exists(shot_path) and os.path.getsize(shot_path) > 100000:
            print(f"  镜头{shot_num}已完成，跳过")
            videos.append(shot_path)
            continue
        
        print(f"\n  生成镜头{shot_num}: {desc[:40]}...")
        
        # 构建详细提示词（导演级）
        lighting = shot.get("lighting", "自然光")
        emotion = shot.get("emotion", "中性")
        sound = shot.get("sound_effects", "")
        music = shot.get("music", "")
        
        detailed_prompt = f"""{desc}

运镜：{camera}
用光：{lighting}
情绪：{emotion}
"""
        
        if sound:
            detailed_prompt += f"\n音效：{sound}"
        if music:
            detailed_prompt += f"\n音乐：{music}"
        
        # 收集参考图URL
        reference_urls = []
        
        # 添加角色参考图
        for char_name in characters:
            if char_name in char_assets:
                char_info = char_assets[char_name]
                # 使用正面图作为主要参考
                if char_info.get("front") and os.path.exists(char_info["front"]):
                    reference_urls.append(char_info["front"])
        
        # 添加场景参考图
        if scene and scene in scene_assets:
            scene_info = scene_assets[scene]
            if scene_info.get("concept") and os.path.exists(scene_info["concept"]):
                reference_urls.append(scene_info["concept"])
        
        # 添加关键帧
        if shot_num in keyframes:
            kf_path = keyframes[shot_num]
            if os.path.exists(kf_path):
                reference_urls.append(kf_path)
        
        # 提交视频生成任务
        payload = {
            "model": MODEL_VIDEO,
            "mode": "reference" if reference_urls else "text",
            "prompt": detailed_prompt,
            "seconds": str(duration),
            "size": "720P",
            "aspect_ratio": "16:9"
        }
        
        # 添加参考图
        if reference_urls:
            payload["images"] = reference_urls[:5]  # 最多5张
        
        result = api_request("videos", payload)
        time.sleep(RPM_DELAY)
        
        if not result:
            print(f"    ❌ 提交失败")
            continue
        
        video_id = result.get("id") or result.get("video_id")
        print(f"    任务ID: {video_id}")
        
        # 轮询等待
        print(f"    等待生成...", end="", flush=True)
        for attempt in range(60):
            time.sleep(10)
            poll_result = api_get("agnesapi", {"video_id": video_id, "model_name": MODEL_VIDEO})
            
            if poll_result:
                status = poll_result.get("status", "")
                if status in ("completed", "success", "done"):
                    elapsed = (attempt+1) * 10
                    print(f" 完成 ({elapsed}s)")
                    url = poll_result.get("url")
                    if url:
                        if download_file(url, shot_path):
                            videos.append(shot_path)
                            print(f"    ✅ {shot_path}")
                        break
                elif status in ("failed", "error"):
                    print(f" 失败: {poll_result.get('error', 'unknown')}")
                    break
            else:
                print(f" .", end="", flush=True)
        
        time.sleep(5)  # 速率限制

    return videos


# ============ Step 7: 成片拼接 ============
def concatenate_videos(videos, output_path):
    """拼接视频"""
    print("\n" + "="*60)
    print("✂️  Step 7: 拼接成片")
    print("="*60)

    if len(videos) == 0:
        print("  没有视频片段")
        return None
    
    if len(videos) == 1:
        import shutil
        shutil.copy(videos[0], output_path)
        print(f"  ✅ 直接复制: {output_path}")
        return output_path

    # 创建concat列表
    list_path = output_path + ".list"
    with open(list_path, "w", encoding="utf-8") as f:
        for v in videos:
            f.write(f"file '{v}'\n")
    
    # 使用ffmpeg拼接
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]
    
    print(f"  正在拼接 {len(videos)} 个片段...")
    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  ✅ 成片已生成: {output_path} ({size_mb:.1f}MB)")
        return output_path
    else:
        print(f"  ❌ 拼接失败: {result.stderr[-300:]}")
        return None


# ============ 主流程 ============
def create_full_drama(concept, script_path=None, output_dir=None):
    """完整 Pavo 短剧创作流程"""
    import time as time_module
    timestamp = int(time_module.time())
    
    if not output_dir:
        output_dir = f"./output/pavo_{timestamp}"
    
    # 如果提供了剧本路径，直接加载
    if script_path and os.path.exists(script_path):
        print(f"\n加载已有剧本: {script_path}")
        with open(script_path, 'r', encoding='utf-8') as f:
            script = json.load(f)
        card = {"title": script.get("title"), "synopsis": script.get("synopsis")}
    else:
        # Step 1: 制作卡片
        clear_proxy()
        card = generate_production_card(concept)
        if not card:
            print("❌ 制作卡片生成失败")
            return None
    
    # Step 2: 剧本生成
    script = generate_script(card, concept)
    if not script:
        print("❌ 剧本生成失败")
        return None
    
    # 保存剧本
    script_path = os.path.join(output_dir, "script.json")
    with open(script_path, 'w', encoding='utf-8') as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 剧本已保存: {script_path}")
    
    # Step 3: 角色资产
    char_assets = generate_character_assets(script, output_dir)
    
    # Step 4: 场景资产
    scene_assets = generate_scene_assets(script, output_dir)
    
    # Step 5: 分镜关键帧
    keyframes = generate_storyboard_keyframes(script, char_assets, scene_assets, output_dir)
    
    # Step 6: 视频生成
    storyboard_dir = os.path.join(output_dir, "storyboard")
    videos = generate_storyboard_videos(script, char_assets, scene_assets, keyframes, storyboard_dir)
    
    # Step 7: 成片
    final_path = os.path.join(output_dir, "final.mp4")
    final = concatenate_videos(videos, final_path)
    
    print("\n" + "="*60)
    print("🎉 短剧创作完成！")
    print(f"📁 输出目录: {output_dir}")
    print(f"📊 统计: {len(char_assets)}角色, {len(scene_assets)}场景, {len(videos)}分镜")
    if final:
        print(f"🎬 成片: {final}")
    print("="*60)
    
    return final


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(
        description="Agnes AI Pavo 短剧创作全流程（完整版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python pavo_complete.py "年轻厨师在米其林餐厅逆袭的故事"
  python pavo_complete.py --script ./script.json
        """
    )
    parser.add_argument("concept", nargs='?', help="短剧创意概念")
    parser.add_argument("--script", default=None, help="已有剧本路径（跳过剧本生成）")
    parser.add_argument("--output", default=None, help="输出目录")
    
    args = parser.parse_args()
    
    if args.script:
        clear_proxy()
        final = create_full_drama(args.script, script_path=args.script, output_dir=args.output)
    elif args.concept:
        clear_proxy()
        final = create_full_drama(args.concept, output_dir=args.output)
    else:
        parser.print_help()
        return
    
    import sys
    sys.exit(0 if final else 1)


if __name__ == "__main__":
    main()
