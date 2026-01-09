# Docker 快速参考卡片

## 🚀 快速开始

```bash
# 1. 构建镜像
docker build -t apprise:latest .

# 2. 发送测试消息（Webhook 模式）
docker run --rm apprise:latest \
  --title="Hello from Docker" \
  --body="Test message" \
  "feishu://YOUR_WEBHOOK_TOKEN"

# 3. 发送测试消息（App 模式）
docker run --rm apprise:latest \
  --title="Hello from Docker" \
  --body="Test message" \
  "feishu://app/cli_APP_ID/APP_SECRET/user@example.com"
```

## 📋 Feishu URL 格式

| 模式 | URL 格式 | 示例 |
|------|----------|------|
| Webhook | `feishu://{token}/` | `feishu://abc123-def456/` |
| App | `feishu://app/{AppID}/{Secret}/{emails}/` | `feishu://app/cli_xyz/secret/user@ex.com/` |

## 🐳 Docker 常用命令

```bash
# 查看镜像
docker images | grep apprise

# 运行一次性命令
docker run --rm apprise:latest --version

# 启动 API 服务器
docker run -d --name apprise-api -p 8000:8000 caronc/apprise-api:latest

# 查看日志
docker logs apprise-api

# 停止容器
docker stop apprise-api

# 删除容器
docker rm apprise-api

# 进入容器
docker exec -it apprise-api /bin/bash
```

## 📝 配置文件示例

`config/apprise.conf`:
```
# Webhook 模式
feishu://your_webhook_token

# App 模式
feishu://app/cli_app_id/app_secret/user1@example.com/user2@example.com
```

## 🌐 API 使用

```bash
# 启动 API 服务器
docker run -d --name apprise-api -p 8000:8000 \
  -v "$(pwd)/config:/config" \
  caronc/apprise-api:latest

# 发送通知
curl -X POST http://localhost:8000/notify \
  -d "urls=feishu://YOUR_TOKEN" \
  -d "title=Alert" \
  -d "body=CPU usage 80%"
```

## 🛠️ 管理脚本

```bash
# Linux/Mac
./run-apprise.sh server    # 启动服务器
./run-apprise.sh test --help  # 测试命令
./run-apprise.sh logs      # 查看日志
./run-apprise.sh stop      # 停止服务

# Windows
run-apprise.bat server
run-apprise.bat test --help
run-apprise.bat logs
run-apprise.bat stop
```

## ✅ 验证安装

```bash
# 检查版本
docker run --rm apprise:latest --version

# 检查插件
docker run --rm apprise:latest \
  ls /usr/local/lib/python3.12/site-packages/apprise/plugins/ | grep feishu

# 运行测试
./test-feishu-docker.sh
```

## 🔧 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| APPRISE_LOG_LEVEL | 日志级别 | info |
| APPRISE_CONFIG | 配置文件路径 | - |
| APPRISE_ATTACHMENT_ALLOW_URL | 允许附件 | false |

## 📦 文件位置

| 文件 | 说明 |
|------|------|
| Dockerfile | 镜像构建文件 |
| .dockerignore | 构建排除文件 |
| docker-compose.prod.yml | Compose 配置 |
| config/apprise.conf | 通知配置 |
| run-apprise.sh | Linux/Mac 脚本 |
| run-apprise.bat | Windows 脚本 |
| test-feishu-docker.sh | 测试脚本 |

## 💡 提示

- 使用 `--dry-run` 参数测试 URL 格式而不发送消息
- 配置文件支持多行注释（# 开头）
- App 模式需要配置飞书应用权限
- 容器内工作目录为 `/app`
- 配置文件挂载到 `/config`
