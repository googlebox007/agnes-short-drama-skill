#!/usr/bin/env python3
"""
Agnes AI Pavo 短剧创作全流程复现
修复版：增强JSON解析、添加速率限制、支持场景生成
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
import re

# ============ 配置 ============
BASE_URL = "https://apihub.agnes-ai.cn/v1"
API_KEY = os.environ.get("AGNES_API_KEY", "sk-kcnPnHEcbukoLM1niz4cXl6z5rl0r9J5SmRpYtuLN35bxUQK")

# 模型
MODEL_TEXT = "agnes-2.5-flash"
MODEL_IMAGE = "agnes-image-2.5-flash"
MODEL_VIDEO = "agnes-video-2.5-flash"

# 限制
VIDEO_MAX_WAIT = 600
RPM_DELAY = 12  # 速率限制间隔
MAX_SHOTS = 8   # 最大分镜数


# ============ 工具函数 ============
def api_request(endpoint, payload, method="POST"):
    """API 请求封装"""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  请求错误: {e}")
        return None


def api_get(url_path, params=None):
    """GET 请求"""
    url = f"{BASE_URL}/{url_path.lstrip('/')}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  GET 错误: {e}")
        return None


def download_file(url, path):
    """下载文件"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(path, "wb") as f:
                f.write(resp.read())
            return True
    except Exception as e:
        print(f"  下载失败: {e}")
        return False


def wait_api():
    """速率限制等待"""
    time.sleep(RPM_DELAY)


def parse_json_response(text, expected_type="object"):
    """
    从LLM输出中解析JSON
    expected_type: "object" 或 "array"
    """
    # 先尝试直接解析
    text = text.strip()
    
    # 移除 markdown 代码块
    text = re.sub(r'^\s*```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```\s*$', '', text)
    
    # 清理多余逗号
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*\]', ']', text)
    
    try:
        result = json.loads(text)
        if expected_type == "object" and isinstance(result, dict):
            return result
        if expected_type == "array" and isinstance(result, list):
            return result
        if expected_type == "any":
            return result
    except:
        pass
    
    # 尝试提取第一个JSON对象或数组
    if expected_type == "object" or expected_type == "any":
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, dict):
                    return result
            except:
                pass
    
    if expected_type == "array" or expected_type == "any":
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return result
            except:
                pass
    
    return None


# ============ Step 1: 制作需求卡片 =====
def generate_production_card(concept):
    """生成制作需求卡片"""
    print("\n" + "="*60)
    print("📋 Step 1: 生成制作需求卡片")
    print("="*60)

    prompt = f"""你是一个专业的短剧制作人。根据概念生成制作需求卡片。

概念："{concept}"

要求：
- 标题简短有力（不超过8字）
- 梗概100字以内
- 时长30秒左右
- 画幅16:9
- 风格描述简洁

只输出JSON，格式：
{{"title":"剧名","synopsis":"梗概","duration":30,"aspect_ratio":"16:9","visual_style":"风格"}}"""

    payload = {
        "model": MODEL_TEXT,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500
    }

    result = api_request("chat/completions", payload)
    if not result:
        return None

    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    card = parse_json_response(content, "object")
    
    if not card:
        print(f"  原始输出: {content[:200]}")
        card = {"title": "未命名", "synopsis": concept, "duration": 30}
    else:
        print(f"  剧名: {card.get('title')}")
        print(f"  梗概: {card.get('synopsis', '')[:50]}...")
        print(f"  时长: {card.get('duration')}秒")

    return card


# ============ Step 2: 剧本生成 =====
def generate_script(card, concept, output_dir):
    """生成完整剧本 - 分步生成以确保JSON完整性"""
    print("\n" + "="*60)
    print("📝 Step 2: 生成剧本")
    print("="*60)

    # Step 2a: 生成角色
    char_prompt = f"""生成4个角色JSON对象。

概念：{concept}
剧名：{card.get('title', '未命名')}

要求：
- 包含主角、反派、配角、智者各1个
- 每个角色有名字和详细描述
- 描述包括：年龄、外貌、性格、服装特征
- 角色要有辨识度，适合短视频表现

只输出JSON，格式：
{{"角色名":"详细描述","角色名2":"描述"...}}"""

    char_payload = {"model": MODEL_TEXT, "messages": [{"role": "user", "content": char_prompt}], "max_tokens": 800}
    char_result = api_request("chat/completions", char_payload)
    wait_api()

    characters = {}
    if char_result:
        chars_content = char_result.get("choices", [{}])[0].get("message", {}).get("content", "")
        characters = parse_json_response(chars_content, "object") or {}
    
    print(f"  角色: {list(characters.keys())}")

    # Step 2b: 生成场景
    scene_prompt = f"""生成3个关键场景JSON对象。

概念：{concept}
剧名：{card.get('title', '未命名')}
主要角色：{list(characters.keys())[:2]}

要求：
- 场景要符合剧情发展
- 描述包括：环境、光线、氛围、关键道具
- 场景要有视觉冲击力

只输出JSON，格式：
{{"场景名":"详细描述","场景名2":"描述"...}}"""

    scene_payload = {"model": MODEL_TEXT, "messages": [{"role": "user", "content": scene_prompt}], "max_tokens": 800}
    scene_result = api_request("chat/completions", scene_payload)
    wait_api()

    scenes = {}
    if scene_result:
        scene_content = scene_result.get("choices", [{}])[0].get("message", {}).get("content", "")
        scenes = parse_json_response(scene_content, "object") or {}
    
    print(f"  场景: {list(scenes.keys())}")

    # Step 2c: 生成分镜
    sb_prompt = f"""生成分镜脚本JSON数组。

概念：{concept}
剧名：{card.get('title', '未命名')}
角色：{list(characters.keys())[:3]}
场景：{list(scenes.keys())[:2]}

要求：
- 生成6-8个镜头
- 每镜头5-6秒
- 描述具体画面内容
- 包含运镜方式
- 适当加入台词

只输出JSON数组，格式：
[{{"shot":1,"description":"画面描述","dialogue":"台词","duration":5,"camera":"运镜"}}]"""

    sb_payload = {"model": MODEL_TEXT, "messages": [{"role": "user", "content": sb_prompt}], "max_tokens": 1500}
    sb_result = api_request("chat/completions", sb_payload)
    wait_api()

    storyboard = []
    if sb_result:
        sb_content = sb_result.get("choices", [{}])[0].get("message", {}).get("content", "")
        storyboard = parse_json_response(sb_content, "array") or []
        
        # 确保每个镜头有基本字段
        for shot in storyboard:
            if not shot.get("description"):
                shot["description"] = "空镜头"
            if not shot.get("duration"):
                shot["duration"] = 5
            if not shot.get("camera"):
                shot["camera"] = "固定镜头"
    
    print(f"  分镜数: {len(storyboard)}")
    if storyboard:
        print(f"  镜头: {[s.get('description', '')[:20] for s in storyboard]}")

    # 构建剧本
    script = {
        "title": card.get("title", "未命名"),
        "genre": card.get("visual_style", "剧情"),
        "characters": characters,
        "scenes": scenes,
        "storyboard": storyboard
    }

    script_path = os.path.join(output_dir, "script.json")
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已保存: {script_path}")

    return script


# ============ Step 3: 角色图片生成 =====
def generate_character_images(script, output_dir):
    """生成角色图片"""
    print("\n" + "="*60)
    print("🎨 Step 3: 生成角色图片")
    print("="*60)

    characters = script.get("characters", {})
    assets = {}
    output_dir = os.path.join(output_dir, "characters")
    os.makedirs(output_dir, exist_ok=True)

    for name, desc in characters.items():
        print(f"  生成角色: {name}...")
        prompt = f"{desc}, 正面半身像, 写实风格, 简洁背景, 电影质感 lighting, 人物特写"

        payload = {
            "model": MODEL_IMAGE,
            "prompt": prompt,
            "size": "1024x1024",
            "n": 1
        }

        result = api_request("images/generations", payload)
        wait_api()

        if result and result.get("data"):
            url = result["data"][0].get("url")
            if url:
                path = os.path.join(output_dir, f"{name}.jpg")
                if download_file(url, path):
                    assets[name] = path
                    print(f"  ✅ {name}: {path}")

    return assets


# ============ Step 4: 场景图片生成 =====
def generate_scene_images(script, output_dir):
    """生成场景图片"""
    print("\n" + "="*60)
    print("🏞️  Step 4: 生成场景图片")
    print("="*60)

    scenes = script.get("scenes", {})
    assets = {}
    output_dir = os.path.join(output_dir, "scenes")
    os.makedirs(output_dir, exist_ok=True)

    for name, desc in scenes.items():
        print(f"  生成场景: {name}...")
        prompt = f"{desc}, 广角镜头, 电影质感, 专业摄影, 氛围感"

        payload = {
            "model": MODEL_IMAGE,
            "prompt": prompt,
            "size": "1024x768",
            "n": 1
        }

        result = api_request("images/generations", payload)
        wait_api()

        if result and result.get("data"):
            url = result["data"][0].get("url")
            if url:
                path = os.path.join(output_dir, f"{name}.jpg")
                if download_file(url, path):
                    assets[name] = path
                    print(f"  ✅ {name}: {path}")

    return assets


# ============ Step 5: 分镜视频生成 =====
def generate_storyboard_videos(script, char_assets, scene_assets, output_dir):
    """生成分镜视频"""
    print("\n" + "="*60)
    print("🎬 Step 5: 生成分镜视频")
    print("="*60)

    storyboard = script.get("storyboard", [])
    videos = []
    os.makedirs(output_dir, exist_ok=True)

    for i, shot in enumerate(storyboard[:MAX_SHOTS]):
        shot_num = shot.get("shot", i+1)
        desc = shot.get("description", "")
        dialogue = shot.get("dialogue", "")
        duration = min(shot.get("duration", 5), 12)  # 最长12秒
        camera = shot.get("camera", "固定镜头")

        print(f"  生成镜头 {shot_num}: {desc[:40]}...")

        # 构建 prompt
        video_prompt = f"{desc}，{camera}"
        if dialogue and dialogue.strip():
            video_prompt += f"，角色台词：{dialogue}"

        # 提交任务
        payload = {
            "model": MODEL_VIDEO,
            "mode": "text",
            "prompt": video_prompt,
            "seconds": str(duration),
            "size": "720P",
            "aspect_ratio": "16:9"
        }

        result = api_request("videos", payload)
        wait_api()

        if not result:
            print(f"    ❌ 提交失败")
            continue

        video_id = result.get("id") or result.get("video_id")
        print(f"    任务ID: {video_id}")

        # 轮询
        print(f"    等待生成...", end="", flush=True)
        for j in range(60):
            time.sleep(10)
            poll_result = api_get(f"agnesapi", {"video_id": video_id, "model_name": MODEL_VIDEO})

            if poll_result:
                status = poll_result.get("status", "")
                if status in ("completed", "success", "done"):
                    elapsed = (j+1) * 10
                    print(f" 完成 ({elapsed}s)")
                    url = poll_result.get("url")
                    if url:
                        path = os.path.join(output_dir, f"shot_{shot_num:02d}.mp4")
                        if download_file(url, path):
                            videos.append(path)
                            print(f"    ✅ {path}")
                        else:
                            print(f"    ❌ 下载失败")
                    else:
                        print(f"    ⚠️ 未找到视频 URL")
                    break
                elif status in ("failed", "error"):
                    print(f" 失败: {poll_result.get('error', 'unknown')}")
                    break
            else:
                print(f" .", end="", flush=True)

        time.sleep(5)  # 速率限制

    return videos


# ============ Step 6: 成片拼接 =====
def concatenate_videos(videos, output_path):
    """拼接视频（带交叉淡入淡出）"""
    print("\n" + "="*60)
    print("✂️  Step 6: 拼接成片")
    print("="*60)

    if len(videos) == 0:
        print("  没有视频片段")
        return None
    
    if len(videos) == 1:
        print(f"  只有一个片段，直接复制")
        import shutil
        shutil.copy(videos[0], output_path)
        return output_path

    # 检查 ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except:
        print("  ❌ ffmpeg 未安装，尝试直接拼接...")
        # 简单拼接（无转码）
        list_path = output_path + ".list"
        with open(list_path, "w", encoding="utf-8") as f:
            for v in videos:
                f.write(f"file '{v}'\n")
        
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", output_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"  ✅ 拼接完成: {output_path}")
            return output_path
    
    # 创建带交叉淡入淡出的复杂滤镜
    inputs = " ".join([f"-i {v}" for v in videos])
    filter_parts = []
    for i in range(len(videos) - 1):
        filter_parts.append(f"[{i}:v][{i+1}:v]xfade=transition=fade:duration=0.5:offset={i*5}[v{i}]")
    filter_parts.append(f"[{len(videos)-1}:v] [v0]")  # 最后一段
    
    # 简化处理：直接concat拼接
    list_path = output_path + ".list"
    with open(list_path, "w", encoding="utf-8") as f:
        for v in videos:
            f.write(f"file '{v}'\n")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c:v", "libx264", "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]
    
    print(f"  正在拼接 {len(videos)} 个片段...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  ✅ 成片已生成: {output_path} ({size_mb:.1f}MB)")
        return output_path
    else:
        print(f"  ❌ 拼接失败: {result.stderr[-300:]}")
        return None


# ============ 主流程 =====
def create_pavo_drama(concept, output_dir=None):
    """完整 Pavo 短剧创作流程"""
    import time as time_module
    timestamp = int(time_module.time())
    
    if not output_dir:
        output_dir = f"./output/pavo_{timestamp}"

    # 创建目录结构
    dirs = [
        f"{output_dir}/assets/characters",
        f"{output_dir}/assets/scenes",
        f"{output_dir}/storyboard",
        f"{output_dir}/assets"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    print("\n" + "━"*60)
    print(f"🎬 Agnes AI Pavo 短剧创作全流程")
    print(f"📝 概念: {concept}")
    print(f"📁 输出: {output_dir}")
    print("━"*60)

    # Step 1: 制作卡片
    card = generate_production_card(concept)
    if not card:
        print("❌ 制作卡片生成失败")
        return None

    card_path = os.path.join(output_dir, "card.json")
    with open(card_path, "w", encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已保存: {card_path}")

    # Step 2: 剧本
    script = generate_script(card, concept, output_dir)
    if not script:
        print("❌ 剧本生成失败")
        return None

    # Step 3: 角色图片
    char_assets = generate_character_images(script, output_dir)
    if not char_assets:
        print("⚠️  角色图片生成失败，继续...")

    # Step 4: 场景图片
    scene_assets = generate_scene_images(script, output_dir)
    if not scene_assets:
        print("⚠️  场景图片生成失败，继续...")

    # Step 5: 分镜视频
    storyboard_dir = os.path.join(output_dir, "storyboard")
    videos = generate_storyboard_videos(script, char_assets, scene_assets, storyboard_dir)
    if not videos:
        print("❌ 视频生成失败")
        return None

    # Step 6: 成片
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


# ============ CLI =====
def main():
    parser = argparse.ArgumentParser(
        description="Agnes AI Pavo 短剧创作全流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python pavo_workflow.py "年轻厨师在米其林餐厅逆袭的故事"
  python pavo_workflow.py "霸道总裁和灰姑娘的爱情故事" --output "./my_drama"
        """
    )
    parser.add_argument("concept", help="短剧创意概念")
    parser.add_argument("--output", default=None, help="输出目录")

    args = parser.parse_args()
    result = create_pavo_drama(args.concept, args.output)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
