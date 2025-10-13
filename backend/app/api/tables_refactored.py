"""
重构后的表管理API主路由
将原来的超大文件拆分为多个模块，提高可维护性
"""

from fastapi import APIRouter

from app.api import table_management, table_scanning, tables_archive, tables_cold_data

# 创建主路由器
router = APIRouter()

# 包含各个子模块的路由
router.include_router(table_management.router, tags=["Table Management"], prefix="")

router.include_router(table_scanning.router, tags=["Table Scanning"], prefix="")

router.include_router(tables_cold_data.router, tags=["Cold Data"], prefix="")

router.include_router(tables_archive.router, tags=["Table Archiving"], prefix="")

# 兼容性路由重定向（如果需要的话）
# 这里可以添加一些向后兼容的路由映射
