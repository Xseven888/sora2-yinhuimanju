# Sora2 视频生成工具

项目使用的API地址：https://api.sora2.email/register?aff=J0Aw

一个支持全系列Sora 2模型的视频生成工具，具备以下核心功能：

## ✨ 核心功能

- 🎬 支持标准版、高清版、横屏版、竖屏版等所有Sora-2模型
- 🎨 可自定义视频方向、尺寸、时长等参数
- 🖼️ 支持带图/无图视频生成
- 📥 自动轮询任务状态并下载结果视频
- 🖥️ 提供GUI图形界面与命令行双模式
- 📚 具备历史记录、设置保存、日志查看等完整用户功能
- 📖 支持小说分析和项目管理系统
- 🎭 角色库管理和角色图片生成
- 🎤 音色库管理

## 🏗️ 系统架构

通过`sora_client.py`调用固定API代理服务完成视频生成。

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

## 🚀 运行程序

```bash
python main.py
```

## 📦 打包成可执行文件

### Windows
```bash
python build_exe_new.py
```

### macOS
```bash
bash build_mac.sh
```

打包后的可执行文件将生成在 `dist` 目录中。

## 🎯 功能模块

### 1. 项目管理
- 创建和管理视频生成项目
- 支持小说文件导入和分析
- 自动生成项目简介和角色信息
- 分集管理和分镜管理

### 2. 任务列表
- 查看所有视频生成任务
- 支持批量下载已完成的视频
- 右键菜单操作（查看详情、下载视频、复制链接、删除任务）

### 3. 角色库
- 角色信息管理
- 自动生成角色图片（支持批量生成）
- 角色描述和特征管理

### 4. *****

### 5. 音色库
- 音色文件管理
- 支持音频播放和预览

### 6. 设置
- API密钥配置
- ComfyUI服务器地址设置
- 视频保存路径配置
- 数据管理（日志查看、数据库管理）

## 🛠️ 技术栈

- **Python 3.7+**: 编程语言
- **PyQt5**: 构建GUI图形界面
- **PyQt-Fluent-Widgets**: 提供现代化UI组件
- **requests**: 调用Sora 2 API接口
- **loguru**: 日志记录管理
- **SQLite**: 本地数据存储
- **PyInstaller**: 打包成可执行文件

## 📁 目录结构

```
├── components/          UI组件封装
├── models/              数据模型定义
├── threads/             多线程操作
├── ui/                  各个界面实现
├── utils/               工具类函数
├── APIDocs/             API文档
├── main.py              主程序入口
├── main_window.py       主窗口
├── database_manager.py  数据库管理
├── sora_client.py       API客户端
├── constants.py         常量定义
├── version.py           版本信息
└── requirements.txt     依赖列表
```

## ⚙️ 配置说明

首次运行前，需要在设置中配置：
- **API Key**: Sora 2 API密钥（必需）
- **视频保存路径**: 生成视频的保存位置（可选，默认使用系统临时目录）
- **ComfyUI服务器**: 高清放大功能需要（可选）

## 📝 许可证

本项目采用开源许可证，详情请查看 LICENSE 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！


