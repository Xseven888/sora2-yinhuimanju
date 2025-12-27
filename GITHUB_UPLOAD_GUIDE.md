# GitHub 上传指南

本指南将帮助您将项目上传到 GitHub。

## 前置条件

1. 已安装 Git（如果未安装，请访问 https://git-scm.com/downloads）
2. 拥有 GitHub 账号（如果没有，请访问 https://github.com 注册）

## 步骤 1: 在 GitHub 上创建新仓库

1. 登录 GitHub
2. 点击右上角的 "+" 按钮，选择 "New repository"
3. 填写仓库信息：
   - **Repository name**: 例如 `sora2-video-generator` 或 `yh-comic-drama`
   - **Description**: 例如 "Sora2 视频生成工具 - 支持全系列Sora 2模型的视频生成"
   - **Visibility**: 选择 Public（公开）或 Private（私有）
   - **不要**勾选 "Initialize this repository with a README"（因为我们已经有了）
4. 点击 "Create repository"

## 步骤 2: 配置 Git 用户信息（如果还未配置）

```bash
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的GitHub邮箱"
```

## 步骤 3: 添加远程仓库并推送代码

在项目目录下执行以下命令：

```bash
# 添加远程仓库（将 YOUR_USERNAME 和 REPO_NAME 替换为你的实际信息）
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# 或者使用 SSH（如果已配置 SSH 密钥）
# git remote add origin git@github.com:YOUR_USERNAME/REPO_NAME.git

# 推送代码到 GitHub
git branch -M main
git push -u origin main
```

## 步骤 4: 验证上传

1. 访问你的 GitHub 仓库页面
2. 确认所有文件都已成功上传
3. 检查 README.md 是否正确显示

## 常见问题

### 问题 1: 需要输入用户名和密码

**解决方案**: 使用 Personal Access Token（个人访问令牌）

1. 访问 GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
2. 点击 "Generate new token (classic)"
3. 勾选 `repo` 权限
4. 生成并复制 token
5. 推送时使用 token 作为密码

或者使用 SSH 密钥（推荐）：
1. 生成 SSH 密钥：`ssh-keygen -t ed25519 -C "your_email@example.com"`
2. 将公钥添加到 GitHub：Settings > SSH and GPG keys > New SSH key
3. 使用 SSH URL：`git@github.com:USERNAME/REPO.git`

### 问题 2: 推送被拒绝

**解决方案**: 如果远程仓库有内容，先拉取：

```bash
git pull origin main --allow-unrelated-histories
# 解决可能的冲突后
git push -u origin main
```

### 问题 3: 文件太大

如果某些文件超过 100MB，GitHub 会拒绝。检查并移除大文件：

```bash
# 查看大文件
git ls-files | xargs du -h | sort -rh | head -20

# 如果已提交大文件，需要从历史中移除（谨慎操作）
```

## 后续更新

以后更新代码时，使用以下命令：

```bash
# 添加更改的文件
git add .

# 提交更改
git commit -m "描述你的更改"

# 推送到 GitHub
git push
```

## 添加许可证

如果需要添加开源许可证：

1. 在 GitHub 仓库页面点击 "Add file" > "Create new file"
2. 文件名输入 `LICENSE`
3. 点击 "Choose a license template"
4. 选择适合的许可证（如 MIT、Apache 2.0 等）
5. 提交文件

## 添加 GitHub Actions（可选）

可以添加 CI/CD 自动化流程，例如自动测试、自动打包等。

---

**提示**: 如果遇到任何问题，可以查看 Git 日志：
```bash
git log --oneline
git status
```

