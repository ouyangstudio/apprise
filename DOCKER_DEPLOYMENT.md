# Apprise Docker 部署指南

本项目已成功构建为 Docker 镜像，包含新实现的 Feishu App Mode 插件。

## 快速开始

### 1. 构建镜像

```bash
docker build -t apprise:latest .
```

### 2. 验证安装

```bash
docker run --rm apprise:latest --version
```

输出：
```
Apprise v1.9.6
Copyright (C) 2025 Chris Caron <lead2gold@gmail.com>
This code is licensed under the BSD 2-Clause License.
```

### 3. 验证 Feishu 插件

```bash
docker run --rm apprise:latest \
  ls /usr/local/lib/python3.12/site-packages/apprise/plugins/ | grep feishu
```

应该显示：
```
feishu.py
```

## 使用方式

### 方式一：命令行发送通知

#### Webhook 模式

```bash
docker run --rm \
  -v "$(pwd)/config:/config" \
  apprise:latest \
  --title="Alert" \
  --body="CPU usage 80%" \
  "feishu://YOUR_WEBHOOK_TOKEN"
```

#### App 模式（新功能）

```bash
docker run --rm \
  -v "$(pwd)/config:/config" \
  apprise:latest \
  --title="Alert" \
  --body="Server maintenance in 10 minutes" \
  "feishu://app/cli_your_app_id/your_app_secret/user1@example.com/user2@example.com"
```

### 方式二：使用配置文件

#### 1. 创建配置文件 `config/apprise.conf`

```bash
# Feishu Webhook Mode
feishu://your_webhook_token

# Feishu App Mode
feishu://app/cli_app_id/app_secret/user@example.com
```

#### 2. 使用配置文件发送

```bash
docker run --rm \
  -v "$(pwd)/config:/config" \
  apprise:latest \
  --config="/config/apprise.conf" \
  --title="Test" \
  --body="Message from Docker container"
```

### 方式三：使用 API 服务器

#### 启动 API 服务器

```bash
# 使用官方 API 镜像
docker run -d \
  --name apprise-api \
  --restart unless-stopped \
  -p 8000:8000 \
  -v "$(pwd)/config:/config" \
  -e APPRISE_CONFIG=/config/apprise.conf \
  caronc/apprise-api:latest
```

#### 通过 API 发送通知

```bash
# Webhook 模式
curl -X POST http://localhost:8000/notify \
  -d "urls=feishu://your_webhook_token" \
  -d "title=Alert" \
  -d "body=CPU usage 80%"

# App 模式
curl -X POST http://localhost:8000/notify \
  -d "urls=feishu://app/cli_app_id/app_secret/user@example.com" \
  -d "title=Alert" \
  -d "body=Server restart scheduled"
```

## Docker Compose 部署

### 使用提供的 docker-compose.prod.yml

```bash
# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 停止服务
docker-compose -f docker-compose.prod.yml down
```

## 管理脚本

项目提供了便捷的管理脚本：

### Linux/Mac
```bash
# 运行服务器
./run-apprise.sh server

# 查看 CLI 帮助
./run-apprise.sh test --help

# 进入容器 shell
./run-apprise.sh shell

# 查看日志
./run-apprise.sh logs

# 停止服务
./run-apprise.sh stop

# 清理容器和镜像
./run-apprise.sh clean
```

### Windows
```cmd
REM 运行服务器
run-apprise.bat server

REM 查看 CLI 帮助
run-apprise.bat test --help

REM 进入容器 shell
run-apprise.bat shell

REM 查看日志
run-apprise.bat logs

REM 停止服务
run-apprise.bat stop

REM 清理容器和镜像
run-apprise.bat clean
```

## 测试脚本

运行测试脚本验证 Feishu 插件：

```bash
./test-feishu-docker.sh
```

这会执行以下测试：
1. 检查 Feishu 插件是否安装
2. 验证 Webhook 模式 URL
3. 验证 App 模式 URL
4. 显示实际使用示例

## Feishu URL 格式

### Webhook 模式（原有功能）
```
feishu://{webhook_token}/
```

### App 模式（新功能）
```
feishu://app/{AppID}/{AppSecret}/{email1}/{email2}/...
```

## 环境变量

可以在容器中设置以下环境变量：

- `APPRISE_LOG_LEVEL`: 日志级别（debug, info, warning, error）
- `APPRISE_CONFIG`: 配置文件路径
- `APPRISE_ATTACHMENT_ALLOW_URL`: 是否允许附件 URL（true/false）

## 目录结构

```
apprise/
├── Dockerfile                    # 生产环境 Dockerfile
├── .dockerignore                 # Docker 构建排除文件
├── docker-compose.prod.yml       # Docker Compose 配置
├── run-apprise.sh               # Linux/Mac 管理脚本
├── run-apprise.bat              # Windows 管理脚本
├── test-feishu-docker.sh        # 测试脚本
├── config/                      # 配置文件目录
│   └── apprise.conf            # Apprise 配置文件
└── logs/                        # 日志目录（可选）
```

## 故障排查

### 1. 检查容器是否运行

```bash
docker ps | grep apprise
```

### 2. 查看容器日志

```bash
docker logs apprise-server
```

### 3. 进入容器调试

```bash
docker exec -it apprise-server /bin/bash
```

### 4. 测试 URL 格式

```bash
docker run --rm apprise:latest \
  --dry-run \
  "feishu://your_url_here"
```

## 最佳实践

1. **使用环境变量管理敏感信息**
   ```bash
   docker run -d \
     -e FEISHU_WEBHOOK_TOKEN="xxx" \
     -e FEISHU_APP_ID="cli_xxx" \
     -e FEISHU_APP_SECRET="xxx" \
     apprise:latest
   ```

2. **使用配置文件管理多个 URL**
   - 将所有通知 URL 集中管理
   - 便于维护和更新

3. **设置日志级别**
   - 开发环境使用 `debug`
   - 生产环境使用 `info` 或 `warning`

4. **定期清理旧镜像**
   ```bash
   docker system prune -a
   ```

## 镜像信息

- **基础镜像**: python:3.12-slim
- **镜像大小**: ~307MB
- **Apprise 版本**: v1.9.6
- **包含功能**: 所有 Apprise 插件（包括 Feishu 双模式）

## 相关文档

- [Apprise 官方文档](https://github.com/caronc/apprise)
- [Feishu 插件使用指南](./FEISHU_APP_MODE_USAGE.md)
- [实现总结](./IMPLEMENTATION_SUMMARY.md)

## 支持

如有问题，请检查：
1. Docker 版本是否 >= 20.10
2. 端口 8000 是否被占用
3. 配置文件路径是否正确
4. Feishu 凭证是否有效
