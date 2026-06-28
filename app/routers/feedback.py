"""
反馈与建议路由：提交反馈、查询反馈列表
"""
from fastapi import APIRouter, HTTPException

from chatbot_api.app.models.schemas import (
    FeedbackRequest, FeedbackResponse, FeedbackListResponse,
)
from chatbot_api.app.services import user_service

router = APIRouter(prefix="/feedback", tags=["反馈"])


@router.post("/submit", response_model=FeedbackResponse, summary="提交反馈")
async def submit_feedback(req: FeedbackRequest):
    """
    提交一条建议或反馈。
    - category: suggestion（建议）/ bug（Bug 报告）/ feedback（一般反馈）
    - contact: 可选联系方式，便于后续跟进
    """
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="反馈内容不能为空")
    result = user_service.submit_feedback(
        username=username,
        category=req.category.strip(),
        content=content,
        contact=(req.contact or "").strip(),
    )
    return FeedbackResponse(**result)


@router.get("/list", response_model=FeedbackListResponse, summary="查询反馈列表")
async def list_feedback(username: str = "", limit: int = 50):
    """
    查询反馈列表。
    - 传 username 则只返回该用户的反馈
    - 不传则返回所有反馈（管理员视角）
    """
    result = user_service.list_feedback(username=username.strip(), limit=limit)
    return FeedbackListResponse(**result)
