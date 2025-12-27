#!/usr/bin/env python3
"""
自动创建 GitHub 仓库并上传代码
"""

import requests
import subprocess
import sys
import json
from pathlib import Path

def check_git_repo():
    """检查是否已初始化 Git 仓库"""
    result = subprocess.run(['git', 'rev-parse', '--git-dir'], 
                          capture_output=True, text=True)
    return result.returncode == 0

def get_remote_url():
    """检查是否已配置远程仓库"""
    result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None

def create_github_repo(token, repo_name, description="", is_private=False):
    """使用 GitHub API 创建仓库"""
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "description": description,
        "private": is_private,
        "auto_init": False  # 不初始化，因为我们已经有了代码
    }
    
    print(f"正在创建 GitHub 仓库: {repo_name}...")
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 201:
        repo_info = response.json()
        print(f"✅ 仓库创建成功！")
        print(f"   仓库地址: {repo_info['html_url']}")
        return repo_info['clone_url'], repo_info['html_url']
    elif response.status_code == 422:
        error_data = response.json()
        if 'errors' in error_data and any('name' in str(err) for err in error_data['errors']):
            print(f"❌ 错误: 仓库名称 '{repo_name}' 已存在或无效")
        else:
            print(f"❌ 错误: {error_data.get('message', '未知错误')}")
        return None, None
    elif response.status_code == 401:
        print("❌ 错误: 认证失败，请检查 Personal Access Token 是否正确")
        return None, None
    else:
        print(f"❌ 错误: 创建仓库失败 (状态码: {response.status_code})")
        try:
            error_data = response.json()
            print(f"   错误信息: {error_data.get('message', '未知错误')}")
        except:
            print(f"   响应内容: {response.text[:200]}")
        return None, None

def get_github_username(token):
    """获取 GitHub 用户名"""
    url = "https://api.github.com/user"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('login')
    return None

def setup_remote_and_push(repo_url, branch='main'):
    """配置远程仓库并推送代码"""
    # 检查是否已有远程仓库
    existing_remote = get_remote_url()
    if existing_remote:
        print(f"⚠️  检测到已存在的远程仓库: {existing_remote}")
        choice = input("是否要替换为新的远程仓库？(y/n): ").strip().lower()
        if choice == 'y':
            subprocess.run(['git', 'remote', 'remove', 'origin'], check=False)
        else:
            print("取消操作")
            return False
    
    # 添加远程仓库
    print(f"正在添加远程仓库...")
    result = subprocess.run(['git', 'remote', 'add', 'origin', repo_url], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 添加远程仓库失败: {result.stderr}")
        return False
    
    # 确保分支名称是 main
    print(f"正在切换到 main 分支...")
    subprocess.run(['git', 'branch', '-M', branch], check=False)
    
    # 推送代码
    print(f"正在推送代码到 GitHub...")
    result = subprocess.run(['git', 'push', '-u', 'origin', branch], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 代码推送成功！")
        return True
    else:
        print(f"❌ 推送失败: {result.stderr}")
        print("\n提示: 如果遇到认证问题，请使用 Personal Access Token 作为密码")
        return False

def main():
    print("=" * 60)
    print("GitHub 仓库自动创建和上传工具")
    print("=" * 60)
    print()
    
    # 检查 Git 仓库
    if not check_git_repo():
        print("❌ 错误: 当前目录不是 Git 仓库")
        print("   请先运行: git init")
        return
    
    # 检查是否有提交
    result = subprocess.run(['git', 'log', '--oneline'], 
                          capture_output=True, text=True)
    if not result.stdout.strip():
        print("❌ 错误: 没有找到任何提交")
        print("   请先提交代码: git add . && git commit -m 'Initial commit'")
        return
    
    print("✅ Git 仓库检查通过")
    print()
    
    # 获取用户输入
    print("请提供以下信息：")
    print()
    
    # GitHub Personal Access Token
    print("1. GitHub Personal Access Token")
    print("   (如果还没有，请访问: https://github.com/settings/tokens)")
    print("   创建新 token，勾选 'repo' 权限")
    print()
    token = input("请输入 Personal Access Token: ").strip()
    if not token:
        print("❌ Token 不能为空")
        return
    
    # 验证 Token 并获取用户名
    print("\n正在验证 Token...")
    username = get_github_username(token)
    if not username:
        print("❌ Token 验证失败，请检查 Token 是否正确")
        return
    print(f"✅ Token 验证成功，用户名: {username}")
    print()
    
    # 仓库名称
    default_repo_name = "sora2-video-generator"
    repo_name = input(f"2. 仓库名称 (默认: {default_repo_name}): ").strip()
    if not repo_name:
        repo_name = default_repo_name
    
    # 仓库描述
    default_description = "Sora2 视频生成工具 - 支持全系列Sora 2模型的视频生成"
    description = input(f"3. 仓库描述 (默认: {default_description}): ").strip()
    if not description:
        description = default_description
    
    # 是否私有
    is_private_input = input("4. 是否创建为私有仓库？(y/n, 默认: n): ").strip().lower()
    is_private = is_private_input == 'y'
    
    print()
    print("=" * 60)
    print("确认信息：")
    print(f"  仓库名称: {repo_name}")
    print(f"  仓库描述: {description}")
    print(f"  是否私有: {'是' if is_private else '否'}")
    print("=" * 60)
    print()
    
    confirm = input("确认创建并上传？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消操作")
        return
    
    print()
    
    # 创建仓库
    clone_url, html_url = create_github_repo(token, repo_name, description, is_private)
    if not clone_url:
        return
    
    print()
    
    # 配置远程仓库并推送
    if setup_remote_and_push(clone_url):
        print()
        print("=" * 60)
        print("🎉 完成！")
        print("=" * 60)
        print(f"仓库地址: {html_url}")
        print(f"克隆地址: {clone_url}")
        print()
        print("你现在可以在浏览器中访问仓库查看代码了！")
    else:
        print()
        print("⚠️  仓库已创建，但推送代码失败")
        print(f"   你可以手动运行以下命令：")
        print(f"   git remote add origin {clone_url}")
        print(f"   git branch -M main")
        print(f"   git push -u origin main")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
