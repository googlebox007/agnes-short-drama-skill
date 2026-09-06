#!/usr/bin/env python3
"""
Agnes AI 短剧创作工具 - 修复版
关键改进：
1. 清除代理环境变量避免SSL握手失败
2. 使用优化prompt替代base64 reference（避免media_download_failed）
3. 自动跳过已完成的分镜
"""

import os
import json
import urllib.request
import ssl
import time
import argparse

# ============ 配置 ============
BASE_URL = "https://apihub.agnes-ai.cn/v1"
API_KEY = os.environ.get("AGNES_API_KEY", "sk-kcnPnHEcbukoLM1niz4cXl6z5rl0r9J5SmRpYtuLN35bxUQK")
MODEL_VIDEO = "agnes-video-2.5-flash"

# 输出目录
OUTPUT_DIR = "./output"


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


def api_request(endpoint, payload):
    """API请求封装"""
    url = f"{BASE_URL}/{endpoint}"
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        ctx = get_ssl_context()
        with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f'    API Error: {e}')
        return None


def api_get(url_path, params=None):
    """GET请求封装"""
    url = f"{BASE_URL}/{url_path}"
    if params:
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        url = f'{url}?{query}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {API_KEY}'})
    try:
        ctx = get_ssl_context()
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return None


def download_file(url, path):
    """下载文件"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        ctx = get_ssl_context()
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            with open(path, 'wb') as f:
                f.write(resp.read())
            return True
    except Exception as e:
        print(f'    下载失败: {e}')
        return False


def generate_shot(shot, output_dir, retry_count=0):
    """生成单个分镜视频"""
    shot_num = shot['shot']
    desc = shot['description']
    dialogue = shot.get('dialogue', '')
    duration = shot.get('duration', 5)
    camera = shot.get('camera', '固定镜头')
    
    print(f'\n[镜头 {shot_num}] {desc[:35]}...')
    
    # 构建优化后的prompt（替代base64 reference）
    video_prompt = f'{desc}，{camera}'
    if dialogue and dialogue.strip():
        video_prompt += f'，{dialogue}'
    
    # 添加风格描述
    video_prompt += '，中国题材，写实风格，电影质感'
    
    payload = {
        'model': MODEL_VIDEO,
        'mode': 'text',
        'prompt': video_prompt,
        'seconds': str(min(duration, 12)),
        'size': '720P',
        'aspect_ratio': '16:9'
    }
    
    result = api_request('videos', payload)
    if not result:
        print(f'  ❌ 提交失败')
        if retry_count < 3:
            time.sleep(15)
            return generate_shot(shot, output_dir, retry_count + 1)
        return None
    
    video_id = result.get('id') or result.get('video_id')
    print(f'  任务ID: {video_id}')
    
    print(f'  等待生成...', end='', flush=True)
    for i in range(60):
        time.sleep(10)
        poll_result = api_get('agnesapi', {'video_id': video_id, 'model_name': MODEL_VIDEO})
        
        if poll_result:
            status = poll_result.get('status', '')
            if status in ('completed', 'success', 'done'):
                elapsed = (i+1) * 10
                print(f' 完成 ({elapsed}s)')
                url = poll_result.get('url') or poll_result.get('metadata', {}).get('url')
                if url:
                    path = os.path.join(output_dir, f'shot_{shot_num:02d}.mp4')
                    if download_file(url, path):
                        print(f'  ✅ {path}')
                        return path
                    else:
                        print(f'  ❌ 下载失败')
                break
            elif status in ('failed', 'error'):
                print(f' 失败: {poll_result}')
                return None
        else:
            print(f' .', end='', flush=True)
    
    time.sleep(3)  # 速率限制
    return None


def main():
    parser = argparse.ArgumentParser(description="Agnes AI 短剧生成工具")
    parser.add_argument("--script", required=True, help="剧本JSON文件路径")
    parser.add_argument("--output", default="./output/storyboard/", help="输出目录")
    args = parser.parse_args()
    
    # 清除代理环境变量
    clear_proxy()
    
    # 加载剧本
    with open(args.script, 'r', encoding='utf-8') as f:
        script = json.load(f)
    
    storyboard = script.get('storyboard', [])
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    # 检查已完成的分镜
    completed = set()
    for f in os.listdir(output_dir):
        if f.startswith('shot_') and f.endswith('.mp4'):
            num = int(f.replace('shot_', '').replace('.mp4', ''))
            completed.add(num)
    
    print(f'=== Agnes AI 短剧生成 ===')
    print(f'总镜头数: {len(storyboard)}')
    print(f'已完成: {len(completed)}')
    print(f'待生成: {len(storyboard) - len(completed)}')
    
    videos = []
    for shot in storyboard:
        shot_num = shot['shot']
        if shot_num in completed:
            print(f'\n[镜头 {shot_num}] 已存在，跳过')
            continue
        
        path = generate_shot(shot, output_dir)
        if path:
            videos.append(path)
    
    print(f'\n=== 完成 ===')
    print(f'新生成: {len(videos)} 个分镜')
    print(f'总计: {len(completed) + len(videos)}/{len(storyboard)} 个分镜')
    
    # 返回视频列表用于拼接
    return videos


if __name__ == "__main__":
    videos = main()
