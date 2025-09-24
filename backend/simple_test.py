"""
简单的测试服务器，用于验证基本功能
"""

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Hive Small File Platform - Test")


@app.get("/")
async def root():
    return {"message": "Hive 小文件治理平台测试服务正在运行！", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "hive-small-file-platform"}


if __name__ == "__main__":
    print("🚀 启动测试服务...")
    print("访问地址: http://localhost:8000")
    print("API 文档: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
