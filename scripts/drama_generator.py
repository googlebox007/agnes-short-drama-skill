#!/usr/bin/env python3
"""
Agnes AI 短剧创作工具
基于 Pavo 平台的短剧创作工作流
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

# ============ 配置 ============
BASE_URL = "https://apihub.agnes-ai.cn/v1"
API_KEY = os.environ.get("AGNES_API_KEY", "sk-kcnPnHEcbukoLM1niz4cXl6z5rl0r9J5SmRpYtuLN35bxUQK")

# 默认模型
DEFAULT_TEXT_MODEL = "agnes-2.5-flash"
DEFAULT_IMAGE_MODEL = "agnes-image-2.5-flash"
DEFAULT_VIDEO_MODEL = "agnes-video-2.5-flash"

# 视频限制
VIDEO_MAX_WAIT = 600
IMAGE_SIZES = ["1024x1024", "768x1024", "1024x768", "1024x576", "576x1024"]

# 输出目录
OUTPUT_DIR = "./output"


# ============ API 工具函数 ============
def api_request(endpoint, payload, method="POST", timeout=300):
    """统一 API 请求封装"""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP Error {e.code}: {body[:300]}")
        return None
    except Exception as e:
        print(f"  Request Error: {e}")
        return None


def api_get(url_path, params=None):
    """GET 请求封装"""
    url = f"{BASE_URL}/{url_path.lstrip('/')}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP Error {e.code}: {body[:300]}")
        return None
    except Exception as e:
        print(f"  GET Error: {e}")
        return None


def download_file(url, path, headers=None):
    """下载文件"""
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(path, "wb") as f:
                f.write(resp.read())
            return True
    except Exception as e:
        print(f"  下载失败: {e}")
        return False


# ============ 文本生成 ============
def generate_text(prompt, system_prompt=None, model=None, max_tokens=2000):
    """使用文本 API 生成内容"""
    if not model:
        model = DEFAULT_TEXT_MODEL

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    result = api_request("chat/completions", payload)
    if result and "choices" in result and len(result["choices"]) > 0:
        return result["choices"][0]["message"]["content"]
    return None


# ============ 图片生成 ============
def generate_image(prompt, size="1024x1024", model=None):
    """生成图片"""
    if not model:
        model = DEFAULT_IMAGE_MODEL

    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": 1,
    }

    result = api_request("images/generations", payload)
    if result and "data" in result and len(result["data"]) > 0:
        return result["data"][0].get("url")
    return None


def generate_characters(characters, output_dir):
    """批量生成角色图片"""
    results = {}
    for char_name, char_desc in characters.items():
        print(f"  [角色] 生成: {char_name}")
        img_url = generate_image(f"{char_desc}, 正面半身像, 写实风格, 简洁背景")
        if img_url:
            path = os.path.join(output_dir, f"{char_name}.jpg")
            if download_file(img_url, path):
                results[char_name] = path
                print(f"  [角色] ✅ {char_name}: {path}")
            else:
                print(f"  [角色] ❌ 下载失败: {char_name}")
        else:
            print(f"  [角色] ❌ 生成失败: {char_name}")
    return results


def generate_scenes(scenes, output_dir):
    """批量生成场景图片"""
    results = {}
    for scene_name, scene_desc in scenes.items():
        print(f"  [场景] 生成: {scene_name}")
        img_url = generate_image(f"{scene_desc}, 广角镜头, 电影质感")
        if img_url:
            path = os.path.join(output_dir, f"{scene_name}.jpg")
            if download_file(img_url, path):
                results[scene_name] = path
                print(f"  [场景] ✅ {scene_name}: {path}")
            else:
                print(f"  [场景] ❌ 下载失败: {scene_name}")
        else:
            print(f"  [场景] ❌ 生成失败: {scene_name}")
    return results


# ============ 视频生成 ============
def submit_video(prompt, images=None, first_frame=None, last_frame=None, model=None):
    """提交视频生成任务"""
    if not model:
        model = DEFAULT_VIDEO_MODEL

    has_images = images and len(images) > 0
    has_frames = first_frame is not None or last_frame is not None

    if has_frames:
        mode = "keyframe"
        payload = {"model": model, "mode": mode, "prompt": prompt}
        if first_frame:
            payload["first_frame"] = first_frame
        if last_frame:
            payload["last_frame"] = last_frame
    elif has_images:
        mode = "reference"
        payload = {"model": model, "mode": mode, "prompt": prompt, "images": images[:5]}
    else:
        mode = "text"
        payload = {"model": model, "mode": mode, "prompt": prompt}

    print(f"  [视频] 模式: {mode}")
    result = api_request("videos", payload)
    if result and ("id" in result or "video_id" in result):
        return result.get("id") or result.get("video_id")
    return None


def poll_video(video_id, model=None, max_wait=VIDEO_MAX_WAIT):
    """轮询视频生成状态"""
    model_name = model or DEFAULT_VIDEO_MODEL
    start = time.time()

    while time.time() - start < max_wait:
        elapsed = int(time.time() - start)
        if elapsed % 15 == 0 and elapsed > 0:
            print(f"  [视频] 等待... {elapsed}s", end="\r")

        url = f"agnesapi?video_id={video_id}&model_name={model_name}"
        result = api_get(url)

        if result:
            status = result.get("status", "")
            if status in ("completed", "success"):
                print(f"  [视频] ✅ 完成 ({elapsed}s)")
                return result.get("url") or result.get("metadata", {}).get("url")
            elif status in ("failed", "error"):
                print(f"  [视频] ❌ 失败: {result.get('error')}")
                return None
        time.sleep(10)

    print(f"  [视频] ⏱ 超时 ({max_wait}s)")
    return None


def generate_video(prompt, output_path=None, images=None, model=None):
    """完整视频生成流程"""
    video_id = submit_video(prompt, images=images, model=model)
    if not video_id:
        return None

    video_url = poll_video(video_id, model=model)
    if not video_url:
        return None

    if not output_path:
        timestamp = int(time.time())
        output_path = f"{OUTPUT_DIR}/video_{timestamp}.mp4"

    if download_file(video_url, output_path):
        return output_path
    return None


# ============ 视频拼接 ============
def concat_videos(input_files, output_path):
    """使用 ffmpeg 拼接视频"""
    if len(input_files) < 2:
        return input_files[0] if input_files else None

    list_file = output_path + ".list"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in input_files:
            f.write(f"file '{p}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"  [拼接] ✅ 完成: {output_path}")
            return output_path
        else:
            print(f"  [拼接] ❌ 失败: {result.stderr[-200:]}")
            return None
    except Exception as e:
        print(f"  [拼接] ❌ 异常: {e}")
        return None
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)


# ============ 短剧创作 ============
SYSTEM_PROMPT_SCRIPT = """你是专业的短剧编剧和导演，擅长创作短视频剧本。请根据用户输入的概念生成完整的短剧方案，包括：
1. 剧名（简短有力）
2. 类型（如：职场、爱情、悬疑、喜剧等）
3. 主角设定（2-3 个主要角色，包含外貌、性格描述）
4. 剧情大纲（3-5 个关键转折点）
5. 分镜脚本（每个镜头的描述，包含画面、动作、台词）
6. 每段视频的时长建议（4-12 秒）

请以 JSON 格式输出，包含以下字段：
{
  "title": "剧名",
  "genre": "类型",
  "characters": {
    "角色名": "外貌和性格描述"
  },
  "scenes": {
    "场景名": "场景描述"
  },
  "storyboard": [
    {
      "shot": 镜头编号,
      "description": "画面描述",
      "dialogue": "台词（如有）",
      "duration": 时长（秒）
    }
  ]
}"""

SYSTEM_PROMPT_IMAGE = """你是专业的视觉设计师，擅长为短剧生成角色和场景的参考图描述。请根据输入生成适合 AI 图像生成的详细描述，包含：
- 外貌特征（脸型、发型、服装）
- 表情和姿态
- 背景和光线
- 画风（写实/动漫/电影质感）"""


def create_drama(concept, output_dir=None):
    """创建完整短剧"""
    if not output_dir:
        output_dir = f"{OUTPUT_DIR}/drama_{int(time.time())}"

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/characters", exist_ok=True)
    os.makedirs(f"{output_dir}/scenes", exist_ok=True)
    os.makedirs(f"{output_dir}/storyboard", exist_ok=True)

    print("=" * 60)
    print(f"🎬 Agnes AI 短剧创作")
    print(f"📝 概念: {concept}")
    print(f"📁 输出: {output_dir}")
    print("=" * 60)

    # Step 1: 生成剧本
    print("\n📖 Step 1: 生成剧本...")
    script_text = generate_text(
        prompt=f"短剧概念: {concept}",
        system_prompt=SYSTEM_PROMPT_SCRIPT,
        max_tokens=2000
    )
    if not script_text:
        print("❌ 剧本生成失败")
        return None

    # 解析 JSON
    try:
        # 尝试找到 JSON 部分
        start = script_text.find("{")
        end = script_text.rfind("}")
        if start != -1 and end != -1:
            script = json.loads(script_text[start:end+1])
        else:
            print("⚠️ 无法解析剧本 JSON，使用原始文本")
            return None
    except json.JSONDecodeError:
        print("⚠️ 剧本 JSON 解析失败，尝试修复...")
        # 简单修复：提取代码块
        import re
        match = re.search(r'```json\s*(.*?)\s*```', script_text, re.DOTALL)
        if match:
            script = json.loads(match.group(1))
        else:
            print("❌ 剧本解析失败")
            return None

    # 保存剧本
    script_path = f"{output_dir}/script.json"
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 剧本已保存: {script_path}")

    # Step 2: 生成角色图片
    print("\n👤 Step 2: 生成角色图片...")
    characters = script.get("characters", {})
    char_results = generate_characters(characters, f"{output_dir}/characters")

    # Step 3: 生成场景图片
    print("\n🎭 Step 3: 生成场景图片...")
    scenes = script.get("scenes", {})
    scene_results = generate_scenes(scenes, f"{output_dir}/scenes")

    # Step 4: 生成分镜视频
    print("\n🎬 Step 4: 生成分镜视频...")
    storyboard = script.get("storyboard", [])
    video_results = []

    for shot in storyboard:
        shot_num = shot.get("shot", 0)
        desc = shot.get("description", "")
        duration = shot.get("duration", 4)

        print(f"  [镜头 {shot_num}] {desc[:50]}...")
        video_path = generate_video(
            prompt=f"{desc}，{shot.get('dialogue', '')}",
            output_path=f"{output_dir}/storyboard/shot_{shot_num:02d}.mp4",
            model=DEFAULT_VIDEO_MODEL
        )
        if video_path:
            video_results.append(video_path)
        else:
            print(f"  [镜头 {shot_num}] ❌ 生成失败")

    # Step 5: 拼接成片
    print("\n✂️ Step 5: 拼接成片...")
    if video_results:
        final_path = f"{output_dir}/final.mp4"
        concat_videos(video_results, final_path)
        print(f"\n🎉 短剧创作完成!")
        print(f"   📁 剧本: {script_path}")
        print(f"   🖼️ 角色图: {output_dir}/characters/")
        print(f"   🎭 场景图: {output_dir}/scenes/")
        print(f"   🎬 成片: {final_path}")
        return final_path
    else:
        print("❌ 没有生成任何视频片段")
        return None


# ============ CLI ============
def main():
    parser = argparse.ArgumentParser(
        description="Agnes AI 短剧创作工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 创建完整短剧
  python drama_generator.py create --concept "一个关于职场逆袭的短剧"

  # 只生成剧本
  python drama_generator.py script --concept "职场逆袭短剧" --output "./output/script.json"

  # 生成角色图片
  python drama_generator.py character --name "主角" --description "年轻男性，职场精英" --output "./output/characters/"

  # 生成分镜视频
  python drama_generator.py storyboard --script "./output/script.json" --output "./output/storyboard/"

  # 拼接成片
  python drama_generator.py concat --input ./output/storyboard/*.mp4 --output "./output/final.mp4"
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # create 命令
    create_parser = subparsers.add_parser("create", help="创建完整短剧")
    create_parser.add_argument("--concept", required=True, help="短剧概念描述")
    create_parser.add_argument("--output", default=None, help="输出目录")

    # script 命令
    script_parser = subparsers.add_parser("script", help="生成剧本")
    script_parser.add_argument("--concept", required=True, help="短剧概念")
    script_parser.add_argument("--output", default="./output/script.json", help="输出路径")

    # character 命令
    char_parser = subparsers.add_parser("character", help="生成角色图片")
    char_parser.add_argument("--name", required=True, help="角色名")
    char_parser.add_argument("--description", required=True, help="角色描述")
    char_parser.add_argument("--output", default="./output/characters/", help="输出目录")

    # scene 命令
    scene_parser = subparsers.add_parser("scene", help="生成场景图片")
    scene_parser.add_argument("--name", required=True, help="场景名")
    scene_parser.add_argument("--description", required=True, help="场景描述")
    scene_parser.add_argument("--output", default="./output/scenes/", help="输出目录")

    # storyboard 命令
    sb_parser = subparsers.add_parser("storyboard", help="生成分镜视频")
    sb_parser.add_argument("--script", required=True, help="剧本 JSON 文件路径")
    sb_parser.add_argument("--output", default="./output/storyboard/", help="输出目录")

    # concat 命令
    concat_parser = subparsers.add_parser("concat", help="拼接视频")
    concat_parser.add_argument("--input", nargs="+", required=True, help="输入视频文件")
    concat_parser.add_argument("--output", required=True, help="输出路径")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.command == "create":
        result = create_drama(args.concept, args.output)
        sys.exit(0 if result else 1)

    elif args.command == "script":
        print("生成剧本...")
        text = generate_text(f"短剧概念: {args.concept}", SYSTEM_PROMPT_SCRIPT, max_tokens=2000)
        if text:
            # 保存
            output_path = args.output
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"✅ 剧本已保存: {output_path}")
        else:
            print("❌ 生成失败")
            sys.exit(1)

    elif args.command == "character":
        print(f"生成角色图片: {args.name}")
        img_url = generate_image(f"{args.description}, 正面半身像, 写实风格")
        if img_url:
            os.makedirs(args.output, exist_ok=True)
            path = os.path.join(args.output, f"{args.name}.jpg")
            if download_file(img_url, path):
                print(f"✅ 已保存: {path}")
            else:
                print("❌ 下载失败")
        else:
            print("❌ 生成失败")

    elif args.command == "scene":
        print(f"生成场景图片: {args.name}")
        img_url = generate_image(f"{args.description}, 广角镜头, 电影质感")
        if img_url:
            os.makedirs(args.output, exist_ok=True)
            path = os.path.join(args.output, f"{args.name}.jpg")
            if download_file(img_url, path):
                print(f"✅ 已保存: {path}")
            else:
                print("❌ 下载失败")
        else:
            print("❌ 生成失败")

    elif args.command == "storyboard":
        with open(args.script, "r", encoding="utf-8") as f:
            script = json.load(f)
        os.makedirs(args.output, exist_ok=True)
        for shot in script.get("storyboard", []):
            shot_num = shot.get("shot", 0)
            desc = shot.get("description", "")
            dialogue = shot.get("dialogue", "")
            print(f"  [镜头 {shot_num}] {desc[:40]}...")
            generate_video(
                f"{desc}，{dialogue}",
                f"{args.output}/shot_{shot_num:02d}.mp4"
            )

    elif args.command == "concat":
        concat_videos(args.input, args.output)


if __name__ == "__main__":
    main()
