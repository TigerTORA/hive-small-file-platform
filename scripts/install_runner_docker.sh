#!/usr/bin/env bash
set -euo pipefail

# 一键安装/重装 GitHub 自托管 Runner（Docker）
# 依赖：105 机器已安装 Docker；可访问 github.com / ghcr.io

# 可通过环境变量覆盖；也可使用参数：
#   ./install_runner_docker.sh <REPO_URL> <RUNNER_TOKEN> [RUNNER_NAME] [RUNNER_LABELS]

REPO_URL_DEFAULT="https://github.com/TigerTORA/hive-small-file-platform"
RUNNER_NAME_DEFAULT="cdpmaster1-staging"
RUNNER_LABELS_DEFAULT="staging"

REPO_URL=${1:-${REPO_URL:-$REPO_URL_DEFAULT}}
RUNNER_TOKEN=${2:-${RUNNER_TOKEN:-}}
RUNNER_NAME=${3:-${RUNNER_NAME:-$RUNNER_NAME_DEFAULT}}
RUNNER_LABELS=${4:-${RUNNER_LABELS:-$RUNNER_LABELS_DEFAULT}}

if [[ -z "${RUNNER_TOKEN}" ]]; then
  echo "[ERROR] 缺少 RUNNER_TOKEN。请在 GitHub 仓库 Settings → Actions → Runners → New runner 页面生成 registration token。" >&2
  echo "用法: $0 <REPO_URL> <RUNNER_TOKEN> [RUNNER_NAME] [RUNNER_LABELS]" >&2
  exit 2
fi

IMAGE=${IMAGE:-myoung34/github-runner:latest}
CONTAINER=${CONTAINER:-gh-runner}

echo "[INFO] Repo URL       : ${REPO_URL}"
echo "[INFO] Runner Name    : ${RUNNER_NAME}"
echo "[INFO] Runner Labels  : ${RUNNER_LABELS}"
echo "[INFO] Docker Image   : ${IMAGE}"
echo "[INFO] Container name : ${CONTAINER}"

echo "[STEP] 清理旧容器（如存在）"
docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true

echo "[STEP] 拉取镜像 ${IMAGE}"
docker pull "${IMAGE}"

echo "[STEP] 启动 Runner 容器并注册"
docker run -d --restart always --name "${CONTAINER}" \
  -e REPO_URL="${REPO_URL}" \
  -e RUNNER_NAME="${RUNNER_NAME}" \
  -e RUNNER_TOKEN="${RUNNER_TOKEN}" \
  -e RUNNER_LABELS="${RUNNER_LABELS}" \
  -e ORG_RUNNER=false \
  -e EPHEMERAL=false \
  -v /var/run/docker.sock:/var/run/docker.sock \
  "${IMAGE}"

echo "[STEP] 等待初始化日志（Ctrl+C 可退出跟随）"
docker logs -f "${CONTAINER}" || true

cat <<'TIP'

[DONE] Runner 容器已启动。接下来：
1) 打开 GitHub 仓库 → Settings → Actions → Runners，确认 runner 在线并带有 label: staging。
2) 触发工作流：Deploy Staging (Self-hosted)，传入版本号（与 GHCR 镜像 tag 一致）。
3) 若需要重新注册，重新生成 RUNNER_TOKEN 后再次执行本脚本即可。

常用排查：
- 查看日志：  docker logs -f gh-runner
- 删除容器：  docker rm -f gh-runner
- 查看 compose 部署：cd /opt/hive-platform && docker compose -f docker-compose.prod.yml ps
- 健康检查：  curl -s http://127.0.0.1:8000/health; curl -s http://127.0.0.1/health

TIP

