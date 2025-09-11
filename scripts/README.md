# 代码质量工具脚本

本目录包含用于代码质量检查和格式化的脚本。

## 脚本说明

### quality_check.py
运行完整的代码质量检查，包括：
- Black 代码格式化检查
- Flake8 代码规范检查 
- isort 导入排序检查
- MyPy 类型检查

### format_code.py
自动格式化代码，包括：
- isort 导入排序
- Black 代码格式化

## 使用方法

### 1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 格式化代码
```bash
python scripts/format_code.py
```

### 3. 检查代码质量
```bash
python scripts/quality_check.py
```

### 4. 使用 Makefile（推荐）
```bash
make install-dev  # 安装开发依赖
make format       # 格式化代码
make check        # 质量检查
make test         # 运行测试
make clean        # 清理缓存
```

## 配置文件

- `backend/pyproject.toml`: Black、isort、Flake8、MyPy 配置
- `.pre-commit-config.yaml`: Pre-commit 钩子配置
- `.vscode/settings.json`: VS Code 编辑器配置

## 质量标准

代码需要通过以下检查：
- ✅ Black 格式化
- ✅ Flake8 代码规范（最大行长度88）
- ✅ isort 导入排序
- ✅ MyPy 类型检查（基础模式）

## 集成到开发流程

1. **开发前**: `make format` 格式化代码
2. **提交前**: `make check` 检查代码质量
3. **可选**: 安装 pre-commit 钩子自动检查