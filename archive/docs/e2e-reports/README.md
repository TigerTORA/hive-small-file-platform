# E2E测试报告

本目录存放E2E(端到端)测试的报告和相关资源文件。

## 📁 目录结构

```
docs/e2e-reports/
├── README.md                    # 本说明文档
├── generate_e2e_report.py       # 报告生成脚本
├── E2E测试报告_YYYYMMDD.docx    # 生成的Word测试报告
└── screenshots/                 # 测试截图目录
    ├── dashboard.png
    ├── tables.png
    ├── tasks.png
    └── table_detail.png
```

## 🚀 如何生成报告

### 前置条件

1. **前端服务运行** - 确保前端开发服务器运行在 `http://localhost:3000`
   ```bash
   cd frontend && npm run dev
   ```

2. **后端服务运行** - 确保后端API服务运行在 `http://localhost:8000`
   ```bash
   cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000
   ```

3. **安装依赖** - 确保安装了Playwright和python-docx
   ```bash
   cd backend && source venv/bin/activate
   pip install playwright python-docx
   playwright install chromium
   ```

### 生成报告

```bash
cd /path/to/hive-small-file-platform/docs/e2e-reports
python generate_e2e_report.py
```

报告将生成为 `E2E测试报告_YYYYMMDD.docx`,同时在 `screenshots/` 目录生成4张截图。

## 📝 报告内容

生成的Word报告包含以下章节:

1. **测试概述** - 测试范围、目标、环境信息
2. **测试场景1-9** - 9个E2E测试场景的详细记录
3. **Bug文档** - 测试过程中发现的Bug和修复记录
4. **测试结论** - 测试结果总结和建议

## 📸 截图说明

- **dashboard.png** - 集群管理/监控中心页面
- **tables.png** - 表列表页面
- **tasks.png** - 任务列表页面
- **table_detail.png** - 表详情页面

## ⚠️ 注意事项

1. **本目录文件不提交到Git仓库** - 截图和Word文档已在`.gitignore`中排除
2. **脚本文件可提交** - `generate_e2e_report.py`和本README可以提交
3. **每次生成会覆盖旧文件** - 注意备份重要的历史报告
4. **截图依赖真实数据** - 确保测试环境有足够的测试数据

## 🐛 已知问题

1. **Dashboard截图** - 由于路由守卫机制,可能显示集群管理页面而不是监控中心
2. **Vue警告覆盖层** - tasks和table_detail截图可能包含Vue开发警告弹窗

## 📚 相关文档

- [E2E测试用例文档](../test-cases/e2e/)
- [测试环境配置](../../README.md#测试环境)
- [Bug追踪](../../CHANGELOG.md)
