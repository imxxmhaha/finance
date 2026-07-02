# CI/CD 自动部署文档

## 📋 概述

本文档介绍如何通过 GitHub Actions 实现代码推送到 GitHub 后，自动部署到云服务器。

**架构流程：**
```
本地 Windows 开发 → git push → GitHub Actions → SSH 到云服务器 → 执行 deploy.sh → 部署完成
```

**服务器信息：**
- 云服务器 IP：`156.238.249.180`
- SSH 端口：`22`
- 登录用户：`root`
- 登录密码：`C7cCL~|2`
- 项目路径：`/xxm/app/docker-app/finance`
- 部署脚本：`/xxm/app/docker-app/finance/deploy.sh`

---

## 🔧 步骤一：在云服务器上配置 SSH 免密登录

> **🖥️ 操作环境：云服务器 (156.238.249.180)**

### 1.1 登录云服务器

```bash
ssh root@156.238.249.180
# 输入密码：C7cCL~|2
```

### 1.2 确保项目目录存在并克隆代码

```bash
# 创建目录
mkdir -p /xxm/app/docker-app

# 进入目录
cd /xxm/app/docker-app

# 克隆代码（如果还没有）
git clone https://github.com/你的用户名/你的仓库名.git finance

# 进入项目目录
cd finance

# 确保 deploy.sh 有执行权限
chmod +x deploy.sh
```

### 1.3 验证 Docker 环境

```bash
# 检查 Docker 是否安装
docker --version

# 检查 Docker Compose 是否安装
docker compose version

# 如果没有安装，执行以下命令安装 Docker
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker
```

---

## 🔧 步骤二：在 Windows 上生成 SSH 密钥对

> **🖥️ 操作环境：Windows 本地机器**

### 2.1 打开 PowerShell 或 Git Bash

```bash
# 生成 SSH 密钥对（用于 GitHub Actions 连接服务器）
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy
```

执行后会提示：
```
Generating public/private ed25519 key pair.
Enter file in which to save the key (C:/Users/你的用户名/.ssh/github_deploy):  # 直接回车
Enter passphrase (empty for no passphrase):  # 直接回车，不设密码
Enter same passphrase again:  # 直接回车
```

### 2.2 查看生成的密钥

```bash
# 查看私钥（用于 GitHub Secrets）
cat ~/.ssh/github_deploy

# 查看公钥（用于服务器）
cat ~/.ssh/github_deploy.pub
```

### 2.3 将公钥上传到云服务器

```bash
# 方法一：使用 ssh-copy-id（推荐）
ssh-copy-id -i ~/.ssh/github_deploy.pub root@156.238.249.180

# 方法二：手动复制（如果 ssh-copy-id 不可用）
# 先复制公钥内容
cat ~/.ssh/github_deploy.pub
# 然后登录服务器，将公钥追加到 authorized_keys
ssh root@156.238.249.180
mkdir -p ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ2YkMoYBuqT3nmTdP5lmXRv7s6TNOf1rdeMQP3S5ToI github-deploy" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
exit
```

### 2.4 测试免密登录

```bash
ssh -i ~/.ssh/github_deploy root@156.238.249.180
# 如果能直接登录成功，说明配置成功
```

---

## 🔧 步骤三：在 GitHub 上配置 Secrets

> **🖥️ 操作环境：Windows 本地机器（浏览器操作）**

### 3.1 进入 GitHub 仓库设置

1. 打开浏览器，进入你的 GitHub 仓库页面
2. 点击 **Settings**（设置）
3. 左侧菜单找到 **Secrets and variables** → **Actions**

### 3.2 添加 Secrets

点击 **New repository secret** 按钮，依次添加以下 4 个 Secret：

| Secret 名称 | 值 | 说明 |
|-------------|-----|------|
| `SERVER_HOST` | `156.238.249.180` | 云服务器 IP |
| `SERVER_USER` | `root` | SSH 登录用户名 |
| `SERVER_SSH_KEY` | 见下方 | SSH 私钥完整内容 |
| `SERVER_PORT` | `22` | SSH 端口（可选） |

**获取 SERVER_SSH_KEY 的值：**

在 Windows PowerShell 中执行：
```bash
cat ~/.ssh/github_deploy
```

输出内容类似：
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
...
-----END OPENSSH PRIVATE KEY-----
```

**复制完整内容**（包括 `-----BEGIN` 和 `END-----`），粘贴到 GitHub Secret `SERVER_SSH_KEY` 中。

---

## 🔧 步骤四：在 Windows 上创建 GitHub Actions 工作流

> **🖥️ 操作环境：Windows 本地机器**

工作流文件已创建在 `.github/workflows/deploy.yml`，内容如下：

```yaml
name: Deploy to Server

on:
  push:
    branches: [master]
  workflow_dispatch:  # 支持手动触发

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          port: ${{ secrets.SERVER_PORT || 22 }}
          script: |
            cd /xxm/app/docker-app/finance
            git pull
            chmod +x deploy.sh
            ./deploy.sh --all
```

---

## 🔧 步骤五：提交并推送代码

> **🖥️ 操作环境：Windows 本地机器**

### 5.1 在 Windows 上打开终端，进入项目目录

```bash
cd E:\doc\exercise\finance
```

### 5.2 提交 CI/CD 配置文件

```bash
# 添加 GitHub Actions 工作流文件
git add .github/

# 提交
git commit -m "ci: 添加 GitHub Actions 自动部署配置"

# 推送到 GitHub
git push origin master
```

### 5.3 验证部署

1. 打开浏览器，进入 GitHub 仓库页面
2. 点击 **Actions** 标签
3. 应该能看到一个正在运行或已完成的 workflow
4. 点击进入查看详细日志

---

## 📝 部署脚本说明

`deploy.sh` 支持以下参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| 无参数 | 只部署客服服务 | `./deploy.sh` |
| `--frontend` 或 `-f` | 部署客服服务 + 前端 | `./deploy.sh -f` |
| `--middleware` 或 `-m` | 部署客服服务 + 中台 | `./deploy.sh -m` |
| `--all` 或 `-a` | 部署所有服务 | `./deploy.sh --all` |

GitHub Actions 默认使用 `--all` 部署所有服务。如需修改，编辑 `.github/workflows/deploy.yml` 中的 `./deploy.sh --all` 部分。

---

## 🔄 完整操作流程汇总

| 步骤 | 操作环境 | 操作内容 |
|------|---------|---------|
| 1 | 云服务器 | 登录服务器，克隆代码，验证 Docker 环境 |
| 2 | Windows | 生成 SSH 密钥对 |
| 3 | Windows → 云服务器 | 将公钥上传到服务器 |
| 4 | Windows (浏览器) | 在 GitHub 仓库添加 Secrets |
| 5 | Windows | 提交并推送 CI/CD 配置文件 |
| 6 | 自动 | 代码推送到 master 后自动触发部署 |

---

## 🚀 日常使用

配置完成后，日常开发流程：

```bash
# 1. 在 Windows 上修改代码
# 2. 提交代码
git add .
git commit -m "feat: 新功能"

# 3. 推送到 GitHub（自动触发部署）
git push origin master

# 4. 在 GitHub Actions 页面查看部署状态
```

---

## ❓ 常见问题

### Q1: 部署失败，查看日志显示 "Permission denied"

**原因：** SSH 密钥配置错误或服务器未正确配置公钥

**解决：**
1. 检查 GitHub Secrets 中的 `SERVER_SSH_KEY` 是否完整（包括 BEGIN 和 END 行）
2. 检查服务器 `~/.ssh/authorized_keys` 是否包含公钥
3. 检查服务器 SSH 配置文件 `/etc/ssh/sshd_config` 中 `PubkeyAuthentication yes` 是否启用

### Q2: 部署失败，显示 "docker: command not found"

**原因：** 服务器未安装 Docker

**解决：** 登录服务器执行：
```bash
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker
```

### Q3: 如何手动触发部署？

1. 进入 GitHub 仓库 → **Actions** 标签
2. 选择 **Deploy to Server** workflow
3. 点击 **Run workflow** 按钮
4. 选择分支，点击 **Run workflow**

### Q4: 如何只部署部分服务？

修改 `.github/workflows/deploy.yml` 中的脚本：
```yaml
script: |
  cd /xxm/app/docker-app/finance
  git pull
  chmod +x deploy.sh
  ./deploy.sh -f  # 只部署客服服务和前端
```

### Q5: 如何查看部署日志？

1. 进入 GitHub 仓库 → **Actions** 标签
2. 点击最近一次 workflow 运行记录
3. 点击 **deploy** 任务查看详细日志

---

## 🔐 安全提示

- GitHub Secrets 是加密存储的，即使是仓库管理员也无法查看完整内容
- SSH 私钥只在 GitHub Actions 运行时使用，不会暴露在日志中
- 建议定期更换 SSH 密钥和服务器密码
- 生产环境建议使用非 root 用户部署，并配置 sudo 权限
