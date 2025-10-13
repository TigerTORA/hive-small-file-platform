# 发布指南（Release Guide)

本指南帮助你从当前仓库构建一套“可发布”的生产部署（Docker 方式），并给出版本化、镜像构建、上线与验收的完整步骤。

## 版本与命名

- 版本号文件：`VERSION`（例如：`1.0.0`）
- 镜像命名（默认）：
  - 后端 API：`hive-small-file-api:${VERSION}`
  - 前端 UI：`hive-small-file-frontend:${VERSION}`
  - Celery Worker：与 API 共用镜像（命令不同）
  - Celery Beat：与 API 共用镜像（命令不同）

你可以通过设置环境变量覆盖镜像名称：
```
export IMAGE_API=hive-small-file-api
export IMAGE_FE=hive-small-file-frontend
```

## 生产环境配置模板

- 后端：`backend/.env.production.example`
  - 关键项：`DATABASE_URL`、`REDIS_URL`、`AUTO_CREATE_SCHEMA=false`、`RELOAD=false`、`SENTRY_ENVIRONMENT=production`
- 前端：`frontend/.env.production.example`
  - 关键项：`VITE_API_BASE_URL=/api/v1`（由前端 Nginx 反代到后端）

复制并按需修改：
```
cp backend/.env.production.example backend/.env
cp frontend/.env.production.example frontend/.env
```

## 一键构建与启动（Docker Compose）

确保本机已安装 Docker 与 Docker Compose。然后：

```
# 1) 设置版本（或编辑 VERSION 文件）
echo "1.0.0" > VERSION

# 2) 构建镜像
make build-images

# 3) 以生产编排启动
VERSION=$(cat VERSION) docker compose -f docker-compose.prod.yml up -d

# 4) 验证
curl -s http://localhost:8000/health
curl -s http://localhost/health
```

说明：
- `docker-compose.prod.yml` 使用前端 Nginx 代理 `/api` 到后端 `api:8000`，前端默认监听 `80`。
- 若端口冲突，请调整 compose 暴露端口或使用反向代理。

## 常见运维动作

- 首次初始化数据库（生产推荐 Alembic）：
  - 进入 API 容器并执行 `alembic upgrade head`
```
docker compose -f docker-compose.prod.yml exec api bash -lc "alembic upgrade head"
```

- 滚动升级（以 1.0.1 为例）：
```
echo "1.0.1" > VERSION
make build-images
VERSION=$(cat VERSION) docker compose -f docker-compose.prod.yml up -d api celery-worker celery-beat frontend
```

- 查看日志：
```
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f celery-worker
docker compose -f docker-compose.prod.yml logs -f frontend
```

## 生产发布检查清单（Checklist）

- 配置
  - [ ] `backend/.env` 使用生产数据库与 Redis，`AUTO_CREATE_SCHEMA=false`，`RELOAD=false`
  - [ ] `frontend/.env` 使用 `/api/v1`（由 Nginx 反代）
  - [ ] Sentry DSN（可选）与环境 `SENTRY_ENVIRONMENT=production`
- 安全与网络
  - [ ] HttpFS/WebHDFS 端口可达（14000/9870），HiveServer2 可达（10000）
  - [ ] 仅开放必要端口（80/8000/5432/6379 视需要）
- 数据库
  - [ ] Alembic 迁移到最新版本
  - [ ] 关闭自动建表（仅开发使用）
- 质量与监控
  - [ ] CI 通过、例行冒烟
  - [ ] /health 正常；关键 API 可用
  - [ ] 仪表板加载、扫描任务创建与日志可用

## 可选：生成离线镜像包

```
make release-save
# 产物：
#   dist/hive-small-file-api-<VERSION>.tar
#   dist/hive-small-file-frontend-<VERSION>.tar
```

## 备注

- 若需推送到镜像仓库（如 GHCR/Harbor），请在本地登录并 `docker tag` / `docker push` 即可。
- 若要通过 Tag 触发 CI 发布，可新增一个 `release` workflow（需配置仓库密钥）。

