# 自托管 Runner（Docker）安装与部署说明

> 目标：在 105 机器上以 Docker 方式运行 GitHub Actions 自托管 Runner，并用于执行 `Deploy Staging (Self-hosted)` 工作流完成一键部署。

## 一、前提条件
- 105 机器具备 root/可 sudo 权限，能访问 GitHub 与 GHCR（`ghcr.io`）。
- 已安装 Docker（含 CLI）。若未安装，可按发行版官方文档安装。
- 本仓库具备以下配置：
  - Secrets：`GHCR_PAT`（至少 `read:packages` 权限，用于登录 GHCR 拉取镜像）。
  - 可选 Repository Variable：`IMAGE_OWNER`（不设则使用仓库 owner）。

## 二、建议：配置国内镜像源（可选）
Linux（root）执行：
```bash
tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://mirror.ccs.tencentyun.com",
    "https://hub-mirror.c.163.com",
    "https://reg-mirror.qiniu.com"
  ]
}
EOF
systemctl daemon-reload && systemctl restart docker
docker info | sed -n '/Registry Mirrors/,+3p'
```

## 三、启动自托管 Runner（Docker）
使用 `myoung34/github-runner`（常用 runner 封装，支持挂载宿主机 Docker）：

1) 在 GitHub → 仓库 Settings → Actions → Runners → New self-hosted runner → 选择 Linux，点击生成 Registration Token（有效期较短）。

2) 在 105 机器执行（将占位替换为实际值）：
```bash
export REPO_URL="https://github.com/<org_or_user>/hive-small-file-platform"
export RUNNER_TOKEN="<registration-token>"   # 上一步页面生成
export RUNNER_NAME="cdpmaster1-staging"      # 自定义

docker pull myoung34/github-runner:latest
docker run -d --restart always --name gh-runner \
  -e REPO_URL="$REPO_URL" \
  -e RUNNER_NAME="$RUNNER_NAME" \
  -e RUNNER_TOKEN="$RUNNER_TOKEN" \
  -e RUNNER_LABELS="staging" \
  -e ORG_RUNNER=false \
  -e EPHEMERAL=false \
  -v /var/run/docker.sock:/var/run/docker.sock \
  myoung34/github-runner:latest

# 观察日志（首启会注册 runner）
docker logs -f gh-runner
```

> 说明：工作流中会自动下载 docker compose v2 二进制（如 runner 环境中不存在），因此只需保证容器内可用 `curl` 与 `docker` 客户端；上面镜像已包含。

### 可选：Docker Hub 不通时
如镜像拉取长期失败，可改用官方 Runner 容器（需要同样的 token 与挂载 docker.sock）：`ghcr.io/actions/actions-runner:latest`。参数名称略有不同，按其 README 配置 `--labels "staging"` 即可。

## 四、触发部署（Deploy Staging）
1) 先确保镜像已存在于 GHCR：运行仓库 `Release` workflow（或用已存在的版本 tag）。
2) 打开 `Deploy Staging (Self-hosted)` workflow → 输入版本号（与 GHCR 镜像 tag 一致）→ 运行。
3) 作业会在标签匹配 `[self-hosted, staging]` 的 105 机器运行：
   - 登录 GHCR（用 `GHCR_PAT`）
   - 在 `/opt/hive-platform` 写入 `docker-compose.prod.yml` 和 `.env`（若缺失）
   - `docker compose pull && up -d`
   - 执行 Alembic 迁移（best-effort）

## 五、验证
在 105 机器上：
```bash
curl -s http://127.0.0.1:8000/health   # API
curl -s http://127.0.0.1/health        # 前端
docker ps | grep hive-platform         # 进程状态
```

## 六、常见问题
- Runner 未上线：
  - Token 过期（重新在 GitHub 页面生成，重建容器）。
  - 网络受限：放行到 `github.com` 与 `ghcr.io`。
- 工作流中 `docker compose` 命令不存在：
  - 我们已在 Job 内置“下载 compose v2”步骤；确保容器内有 `curl` 即可。
- GHCR 拉取失败：
  - 仓库 Secrets `GHCR_PAT` 缺少 `read:packages` 权限，或账户与镜像所有者不一致。
- 端口冲突：
  - 编辑 `/opt/hive-platform/docker-compose.prod.yml` 对 `80/8000/5432/6379` 进行调整。

---
本文件与 `.github/workflows/deploy-staging-selfhosted.yml` 搭配使用，可实现“105 机器一键部署”。

