# 阿里云 OSS 配置说明

## 概述

本项目已集成阿里云 OSS 存储功能，可以将图片和视频上传到阿里云 OSS，而不是使用默认的文件服务接口。功能保持完全一致，只是存储位置改变。

## 功能特点

- ✅ 支持图片上传到 OSS
- ✅ 支持视频上传到 OSS
- ✅ 自动按日期组织文件目录
- ✅ 支持自定义域名
- ✅ 自动回退：如果 OSS 配置不完整或上传失败，自动使用原有接口
- ✅ 完全兼容现有功能

## 配置步骤

### 1. 安装依赖

首先安装阿里云 OSS SDK：

```bash
pip install oss2
```

或者使用项目的 requirements.txt：

```bash
pip install -r requirements.txt
```

### 2. 获取阿里云 OSS 配置信息

在阿里云控制台获取以下信息：

1. **AccessKey ID** 和 **AccessKey Secret**
   - 登录阿里云控制台
   - 进入「访问控制 RAM」->「用户」-> 创建或选择用户
   - 在「安全信息」中创建 AccessKey

2. **Endpoint（地域节点）**
   - 在 OSS 控制台查看，例如：
     - 华东1（杭州）：`https://oss-cn-hangzhou.aliyuncs.com`
     - 华东2（上海）：`https://oss-cn-shanghai.aliyuncs.com`
     - 华北2（北京）：`https://oss-cn-beijing.aliyuncs.com`
     - 更多地域请查看 [阿里云文档](https://help.aliyun.com/document_detail/31837.html)

3. **Bucket 名称**
   - 在 OSS 控制台创建或选择一个 Bucket
   - 记录 Bucket 名称

4. **自定义域名（可选）**
   - 如果已绑定自定义域名，填写完整域名，例如：`https://cdn.example.com`
   - 如果不填写，将使用 OSS 默认域名

### 3. 在程序中配置

1. 打开程序，进入「设置」界面
2. 找到「阿里云 OSS 配置（可选）」部分
3. 勾选「启用阿里云 OSS 存储」
4. 填写以下信息：
   - **AccessKey ID**：你的 AccessKey ID
   - **AccessKey Secret**：你的 AccessKey Secret
   - **Endpoint**：OSS 地域节点，例如 `https://oss-cn-hangzhou.aliyuncs.com`
   - **Bucket 名称**：你的 Bucket 名称
   - **自定义域名（可选）**：如果已绑定自定义域名，填写完整域名
5. 点击「保存」

### 4. 验证配置

配置完成后，尝试上传一张图片或视频，如果成功上传到 OSS，说明配置正确。

## 文件存储结构

上传到 OSS 的文件会按以下结构组织：

```
images/
  └── 2024/
      └── 01/
          └── 15/
              └── abc12345-image.jpg

videos/
  └── 2024/
      └── 01/
          └── 15/
              └── def67890-video.mp4
```

- 图片存储在 `images/` 目录下
- 视频存储在 `videos/` 目录下
- 按年/月/日自动组织目录
- 文件名格式：`{8位随机ID}-{原文件名}`

## 注意事项

1. **权限配置**：确保 AccessKey 有对应 Bucket 的读写权限
2. **Bucket 设置**：
   - 建议设置为「公共读」或配置跨域规则（如果需要）
   - 如果使用自定义域名，需要在 OSS 控制台绑定域名
3. **费用**：OSS 按使用量计费，请注意存储和流量费用
4. **回退机制**：如果 OSS 配置不完整或上传失败，程序会自动使用原有的文件服务接口，不影响正常使用

## 故障排查

### 问题：上传失败，提示 "OSS 配置不完整"

**解决方案**：
- 检查是否勾选了「启用阿里云 OSS 存储」
- 检查是否填写了所有必填项（AccessKey ID、Secret、Endpoint、Bucket 名称）

### 问题：上传失败，提示权限错误

**解决方案**：
- 检查 AccessKey 是否有对应 Bucket 的读写权限
- 在 RAM 控制台为用户添加 OSS 相关权限策略

### 问题：上传成功但无法访问

**解决方案**：
- 检查 Bucket 的读写权限设置
- 如果使用自定义域名，检查域名是否正确绑定
- 检查文件 URL 是否正确生成

## 技术实现

- 使用 `oss2` Python SDK 进行文件上传
- 支持图片和视频的自动 Content-Type 识别
- 自动生成唯一文件名，避免冲突
- 完整的错误处理和日志记录
- 自动回退到原有接口，保证可用性

## 相关文件

- `utils/oss_uploader.py` - OSS 上传工具类
- `threads/image_upload_thread.py` - 图片上传线程（已集成 OSS）
- `threads/video_analysis_thread.py` - 视频上传方法（已集成 OSS）
- `components/settings_dialog.py` - 设置界面（已添加 OSS 配置）

