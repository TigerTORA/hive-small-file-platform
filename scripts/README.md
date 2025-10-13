# 项目脚本工具集

本目录包含项目开发和测试相关的工具脚本。

## 脚本分类

### 📦 演示/数据脚本
- **`scripts/dev/seed_demo_archive.py`**：根据 `backend/demo-data/` 重置缓存数据。
- **`scripts/generate_project_status.py`**：生成 `PROJECT_STATUS.md`。
- **`scripts/update-dashboard.sh`**：刷新前端仪表盘状态文件。

### 🧹 工作区清理
- **`cleanup_workspace.py`**：清理根目录下的 `.tmp_*`、`*_dev.log`、Playwright/Vite 缓存等（默认 dry-run，传 `--apply` 真正删除）。

### 🛠️ 代码质量工具
- **`quality_check.py`**: 完整的代码质量检查
- **`format_code.py`**: 自动代码格式化
- **`quick_test_check.py`** / **`validate_test_coverage.py`**：测试配置辅助脚本

### 🧼 Legacy 脚本

Hive/集群相关脚本、Docker Compose 启动器等已移至 `archive/scripts/legacy/`。如果需要恢复旧流程，可从该目录拷贝并手动维护，默认 demo 模式不会调用它们。
