from fastapi import APIRouter, HTTPException
import sentry_sdk

router = APIRouter()

@router.get("/test-error")
async def test_error():
    """测试错误监控端点"""
    try:
        raise ValueError("This is a test error for Sentry monitoring")
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(status_code=500, detail="Test error captured by Sentry")

@router.get("/test-manual-error")
async def test_manual_error():
    """手动触发错误"""
    sentry_sdk.capture_message("Manual test message", level="error")
    return {"message": "Manual error message sent to Sentry"}