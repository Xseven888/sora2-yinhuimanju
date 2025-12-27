#!/usr/bin/env python3
"""
简单的Sora 2视频生成工具
用户选择模型，API代理固定为 https://lanzhi.fun
"""

import os
import sys
from typing import List, Optional
from sora_client import (
    SoraClient,
    SoraModel,
    VideoOrientation,
    VideoSize,
    VideoDuration
)


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def display_banner():
    """显示横幅"""
    print("=" * 60)
    print("           Sora 2 视频生成工具")
    print("        API代理: https://lanzhi.fun")
    print("=" * 60)
    print()


def get_api_key() -> str:
    """获取API密钥"""
    # 首先尝试从环境变量获取
    api_key = os.getenv('SORA_API_KEY')
    if api_key:
        return api_key

    # 如果环境变量没有，提示用户输入
    while True:
        api_key = input("请输入您的API密钥: ").strip()
        if api_key:
            return api_key
        print("API密钥不能为空，请重新输入。")


def select_model() -> SoraModel:
    """选择模型"""
    models = [
        (SoraModel.SORA_2, "Sora 2 标准版本"),
        (SoraModel.SORA_2_HD, "Sora 2 高清版本"),
        (SoraModel.SORA_2_LANDSCAPE, "Sora 2 横屏版本"),
        (SoraModel.SORA_2_LANDSCAPE_HD, "Sora 2 横屏高清版本"),
        (SoraModel.SORA_2_PORTRAIT, "Sora 2 竖屏版本"),
        (SoraModel.SORA_2_PORTRAIT_HD, "Sora 2 竖屏高清版本")
    ]

    print("请选择Sora模型:")
    for i, (model, description) in enumerate(models, 1):
        print(f"{i}. {description} ({model.value})")

    while True:
        try:
            choice = input("\n请输入选择 (1-6): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(models):
                return models[index][0]
            print("无效选择，请输入1-6之间的数字。")
        except ValueError:
            print("请输入有效的数字。")


def select_orientation() -> VideoOrientation:
    """选择视频方向"""
    orientations = [
        (VideoOrientation.PORTRAIT, "竖屏"),
        (VideoOrientation.LANDSCAPE, "横屏")
    ]

    print("\n请选择视频方向:")
    for i, (orientation, description) in enumerate(orientations, 1):
        print(f"{i}. {description}")

    while True:
        try:
            choice = input("\n请输入选择 (1-2): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(orientations):
                return orientations[index][0]
            print("无效选择，请输入1-2之间的数字。")
        except ValueError:
            print("请输入有效的数字。")


def select_size() -> VideoSize:
    """选择视频尺寸"""
    sizes = [
        (VideoSize.SMALL, "一般质量"),
        (VideoSize.LARGE, "高清质量")
    ]

    print("\n请选择视频尺寸:")
    for i, (size, description) in enumerate(sizes, 1):
        print(f"{i}. {description}")

    while True:
        try:
            choice = input("\n请输入选择 (1-2): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(sizes):
                return sizes[index][0]
            print("无效选择，请输入1-2之间的数字。")
        except ValueError:
            print("请输入有效的数字。")


def select_duration() -> VideoDuration:
    """选择视频时长"""
    durations = [
        (VideoDuration.DURATION_10, "10秒"),
        (VideoDuration.DURATION_15, "15秒")
    ]

    print("\n请选择视频时长:")
    for i, (duration, description) in enumerate(durations, 1):
        print(f"{i}. {description}")

    while True:
        try:
            choice = input("\n请输入选择 (1-2): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(durations):
                return durations[index][0]
            print("无效选择，请输入1-2之间的数字。")
        except ValueError:
            print("请输入有效的数字。")


def get_images() -> Optional[List[str]]:
    """获取图片URL列表"""
    while True:
        choice = input("\n是否添加图片? (y/n): ").strip().lower()
        if choice in ['y', 'yes', '是']:
            images = []
            print("\n请输入图片URL (每行一个，输入空行结束):")
            while True:
                url = input(f"图片{len(images)+1}: ").strip()
                if not url:
                    break
                if url.startswith(('http://', 'https://')):
                    images.append(url)
                else:
                    print("请输入有效的URL地址。")

            return images if images else None
        elif choice in ['n', 'no', '否']:
            return None
        else:
            print("请输入 y/n 或 是/否")


def get_prompt() -> str:
    """获取提示词"""
    while True:
        prompt = input("\n请输入视频生成提示词: ").strip()
        if prompt:
            return prompt
        print("提示词不能为空，请重新输入。")


def display_task_info(task_id: str, prompt: str, model: SoraModel,
                     orientation: VideoOrientation, size: VideoSize,
                     duration: VideoDuration, images: Optional[List[str]]):
    """显示任务信息"""
    print("\n" + "=" * 60)
    print("任务创建成功！")
    print("=" * 60)
    print(f"任务ID: {task_id}")
    print(f"模型: {model.value}")
    print(f"提示词: {prompt}")
    print(f"方向: {orientation.value}")
    print(f"尺寸: {size.value}")
    print(f"时长: {duration.value}秒")
    if images:
        print(f"图片数量: {len(images)}")
    print("=" * 60)


def wait_for_task_completion(client: SoraClient, task_id: str):
    """等待任务完成"""
    print("\n正在生成视频，请稍候...")

    try:
        result = client.wait_for_completion(task_id, max_wait_time=600, poll_interval=15)

        if result.get('status') == 'completed':
            print("\n[SUCCESS] 视频生成完成！")
            video_url = result.get('video_url')
            thumbnail_url = result.get('thumbnail_url')

            if video_url:
                print(f"视频地址: {video_url}")

                # 询问是否下载
                download_choice = input("\n是否下载视频? (y/n): ").strip().lower()
                if download_choice in ['y', 'yes', '是']:
                    filename = f"video_{task_id}.mp4"
                    if client.download_video(video_url, filename):
                        print(f"[OK] 视频已下载到: {filename}")
                    else:
                        print("[ERROR] 视频下载失败")

            if thumbnail_url:
                print(f"缩略图地址: {thumbnail_url}")

                # 询问是否下载缩略图
                thumb_choice = input("\n是否下载缩略图? (y/n): ").strip().lower()
                if thumb_choice in ['y', 'yes', '是']:
                    filename = f"thumb_{task_id}.webp"
                    if client.download_video(thumbnail_url, filename):
                        print(f"[OK] 缩略图已下载到: {filename}")
                    else:
                        print("[ERROR] 缩略图下载失败")
        else:
            print(f"\n[ERROR] 视频生成失败，状态: {result.get('status')}")
            if 'detail' in result:
                print(f"详细信息: {result['detail']}")

    except TimeoutError:
        print("\n[TIMER] 等待任务完成超时，您可以稍后手动查询任务状态")
        print(f"任务ID: {task_id}")
    except Exception as e:
        print(f"\n[ERROR] 查询任务状态时出错: {e}")


def main():
    """主函数"""
    try:
        clear_screen()
        display_banner()

        # 获取API密钥
        api_key = get_api_key()

        # 初始化客户端
        client = SoraClient(base_url="http://lanzhi.fun", api_key=api_key)

        # 获取用户输入
        model = select_model()
        orientation = select_orientation()
        size = select_size()
        duration = select_duration()
        images = get_images()
        prompt = get_prompt()

        # 确认信息
        print("\n" + "=" * 60)
        print("请确认以下信息:")
        print("=" * 60)
        print(f"模型: {model.value}")
        print(f"方向: {orientation.value}")
        print(f"尺寸: {size.value}")
        print(f"时长: {duration.value}秒")
        print(f"提示词: {prompt}")
        if images:
            print(f"图片数量: {len(images)}")
        else:
            print("图片: 无")
        print("=" * 60)

        confirm = input("\n确认创建任务? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes', '是']:
            print("已取消任务创建。")
            return

        # 创建任务
        print("\n正在创建任务...")

        try:
            if images:
                print(f"[LIST] 调用带图片的视频创建API...")
                result = client.create_video_with_images(
                    images=images,
                    prompt=prompt,
                    model=model,
                    orientation=orientation,
                    size=size,
                    duration=duration
                )
            else:
                print(f"[LIST] 调用无图片的视频创建API...")
                result = client.create_video_without_images(
                    prompt=prompt,
                    model=model,
                    orientation=orientation,
                    size=size,
                    duration=duration
                )

            task_id = result.get('id')
            if task_id:
                print(f"[OK] 任务创建成功，获得任务ID: {task_id}")
                display_task_info(task_id, prompt, model, orientation, size, duration, images)
                wait_for_task_completion(client, task_id)
            else:
                print("[ERROR] 任务创建失败，未返回任务ID")
                print(f"   📄 API响应: {result}")

        except Exception as e:
            print(f"[ERROR] 创建任务时出错: {e}")
            print(f"   [SEARCH] 错误类型: {type(e).__name__}")
            import traceback
            print(f"   [LIST] 详细错误信息:")
            traceback.print_exc()

    except KeyboardInterrupt:
        print("\n\n程序已取消。")
    except Exception as e:
        print(f"\n[ERROR] 程序出错: {e}")


if __name__ == "__main__":
    main()