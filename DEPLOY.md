# 金融智能客服系统 - 部署指南

## 一、系统架构

```
浏览器
  │
  ├─ :5174 ──→ Nginx (前端)
  │               ├─ /api/*      → customer-service:7000
  │               └─ /finance/*  → finance-data:8000
  │
  ├─ :7000 ──→ 客服服务 (FastAPI + LangChain + LLM)
  │               └─ 调用 finance-data:8000
  │
  └─ :8000 ──→ 中台服务 (FastAPI)
                  └─ 读写 mysql:3306
```

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| MySQL | finance-mysql | 3306 | 数据库 |
| 中台服务 | finance-data | 8000 | 金融业务 API |
| 客服服务 | finance-customer-service | 7000 | LangChain 智能客服 |
| 前端 | finance-frontend | 5174 | Vue3 + Nginx |

---

## 二、虚拟机环境准备

### 2.1 系统要求

| 项目 | 最低要求 |
|------|---------|
| 操作系统 | Ubuntu 20.04+ / CentOS 7+ / Debian 11+ |
| CPU | 2 核 |
| 内存 | 4 GB |
| 磁盘 | 20 GB |
| 网络 | 能访问外网（拉取 Docker 镜像） |

### 2.2 安装 Docker

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录终端使 docker 组生效

# CentOS
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin



sudo systemctl start docker
sudo systemctl list-unit-files | grep docker
sudo systemctl enable docker
```

### 2.3 验证安装

```bash
docker --version
# Docker version 24.x.x

docker compose version
# Docker Compose version v2.x.x
```

---

## 三、上传项目到虚拟机

### 方式一：scp 直接上传

```bash
# Windows PowerShell / Git Bash
scp -r D:\ws\py_ws\20260316\project\06\finance user@192.168.1.100:/home/user/
```

### 方式二：先压缩再上传（推荐）

```bash
# Windows 端：压缩
tar -czf finance.tar.gz -C D:\ws\py_ws\20260316\project\06 finance

# 上传
scp finance.tar.gz user@192.168.1.100:/home/user/

# 虚拟机端：解压
cd /home/user
tar -xzf finance.tar.gz
```

### 方式三：Git（如果已托管）

```bash
cd /home/user
git clone <仓库地址> finance
```

---

## 四、配置环境变量

### 4.1 修改 LLM API Key

编辑 `finance/docker-compose.yml`，找到 `LLM_API_KEY` 替换为你的真实 Key：

```yaml
LLM_API_KEY: "sk-你的真实key"
```

或通过环境变量注入（不修改文件）：

```bash
export LLM_API_KEY=sk-你的真实key
docker compose up -d --build
```

### 4.2 修改 MySQL 密码（可选）

默认密码为 `root`，生产环境建议修改 `docker-compose.yml` 中的：

```yaml
MYSQL_ROOT_PASSWORD: your_strong_password
DB_PASSWORD: your_strong_password
```

---

## 五、启动服务

```bash
cd /home/user/finance

# 构建镜像并后台启动所有服务
docker compose up -d --build
```

首次启动需要拉取镜像和构建，耗时约 5-15 分钟。

启动顺序（自动）：MySQL → finance-data → customer-service → frontend

---

## 六、验证服务

### 6.1 检查容器状态

```bash
docker compose ps
```

正常输出应显示 4 个容器均为 `Up` 状态：

```
NAME                        STATUS
finance-mysql               Up (healthy)
finance-data                Up
finance-customer-service    Up
finance-frontend            Up
```

### 6.2 验证各服务接口

```bash
# 中台服务 - 健康检查
curl http://localhost:8000/health
# 返回 {"code":0,"message":"ok",...}

# 中台服务 - 查询渠道（验证数据库连接）
curl http://localhost:8000/api/v1/channels \
  -H "Authorization: Bearer EMP000006" \
  -H "X-Channel-Code: OPEN_API" \
  -H "X-Operator-No: EMP000006"

# 客服服务 - 数据库测试
curl http://localhost:7000/db-test

# 导入中台数据
docker exec -it finance-data uv run -m generate.main --profile full

# 前端页面
curl http://localhost:5174
```

### 6.3 浏览器访问

```
前端页面：http://虚拟机IP:5174
中台文档：http://虚拟机IP:8000/docs
```

---

## 七、查看日志

```bash
# 查看所有服务日志（实时）
docker compose logs -f

# 查看单个服务日志
docker compose logs -f customer-service
docker compose logs -f finance-data
docker compose logs -f mysql
docker compose logs -f frontend

# 查看最近 100 行
docker compose logs --tail 100 customer-service
```

---

## 八、防火墙配置

如果虚拟机开启了防火墙，需要放行端口：

### Ubuntu (ufw)

```bash
sudo ufw allow 5174/tcp   # 前端
sudo ufw allow 7000/tcp   # 客服服务
sudo ufw allow 8000/tcp   # 中台服务
sudo ufw reload
```

### CentOS (firewalld)

```bash
sudo firewall-cmd --add-port=5174/tcp --permanent
sudo firewall-cmd --add-port=7000/tcp --permanent
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

### 云服务器（阿里云/腾讯云）

在安全组中添加入站规则，放行 5174、7000、8000 端口。

---

## 九、常用运维命令

```bash
# ====== 生命周期 ======

# 启动
docker compose up -d

# 停止
docker compose down

# 重启所有服务
docker compose restart

# 重启单个服务
docker compose restart customer-service

# 代码更新后重新构建并启动
docker compose up -d --build

# ====== 调试 ======

# 进入容器
docker exec -it finance-customer-service bash
docker exec -it finance-data bash
docker exec -it finance-mysql bash

# 查看 MySQL 数据
docker exec -it finance-mysql mysql -uroot -proot -e "SHOW DATABASES;"
docker exec -it finance-mysql mysql -uroot -proot finance -e "SHOW TABLES;"

# ====== 清理 ======

# 停止并删除容器、网络
docker compose down

# 停止并删除容器、网络、数据卷（会清空数据库！）
docker compose down -v

# 清理无用镜像
docker image prune -f
```

---

## 十、常见问题

### Q1: 中台服务启动失败，日志报 `Connection refused`

MySQL 还没就绪。`docker-compose.yml` 已配置 `healthcheck` + `depends_on`，会自动等待。如果仍然失败：

```bash
docker compose restart finance-data
```

### Q2: 客服服务调用中台返回 `CHANNEL_NOT_AVAILABLE`

检查 `.env` 或 `docker-compose.yml` 中的 `API_CHANNEL_CODE` 是否为 `OPEN_API`（中台 dim_channel 表中存在的渠道编码）。

### Q3: 拉取 Docker 镜像太慢

配置国内镜像加速：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://registry.docker-cn.com"
  ]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### Q4: 前端页面白屏

检查 nginx 配置中代理目标是否正确：

```bash
docker exec -it finance-frontend cat /etc/nginx/conf.d/default.conf
```

确认 `proxy_pass` 指向的是容器名（`customer-service`、`finance-data`），不是 `127.0.0.1`。

### Q5: 如何查看数据库初始化是否成功

```bash
docker exec -it finance-mysql mysql -uroot -proot finance -e "SHOW TABLES;"
```

应看到中台的业务表（customer、account、transaction 等）。如果没有表，检查 SQL 文件是否正确挂载：

```bash
docker exec -it finance-mysql ls /docker-entrypoint-initdb.d/
```
