"""
管理接口：查询注册用户列表等运维数据（需在 .env 配置 ADMIN_KEY）
"""
import os
import secrets

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException

from chatbot_api.app.models.schemas import AdminUserListResponse
from chatbot_api.app.services import user_service

load_dotenv()

router = APIRouter(prefix="/admin", tags=["管理"])


def verify_admin_key(x_admin_key: str = Header(default="", description="管理密钥")):
    """校验请求头 X-Admin-Key 是否与 .env 中的 ADMIN_KEY 一致"""
    admin_key = os.getenv("ADMIN_KEY", "").strip()
    if not admin_key:
        raise HTTPException(status_code=403, detail="管理功能未启用：请在 .env 中配置 ADMIN_KEY 后重启服务")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, admin_key):
        raise HTTPException(status_code=403, detail="管理密钥无效")


@router.get("/users", response_model=AdminUserListResponse, summary="查询注册用户列表")
async def list_users(_: None = Depends(verify_admin_key)):
    """
    查询所有已注册用户，按注册时间升序返回。

    包含字段：用户名、注册时间、主题、聊天风格、今日对话数、今日 Token 数（不含密码信息）。

    请求头需携带：`X-Admin-Key: <ADMIN_KEY>`
    """
    return AdminUserListResponse(**user_service.list_registered_users())
