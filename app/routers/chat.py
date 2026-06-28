"""
聊天相关路由：/chat, /chat/clear, /chat/exit, /chat/session-info
"""
from fastapi import APIRouter, HTTPException

from chatbot_api.app.models.schemas import (
    ChatRequest, ChatResponse,
    ClearRequest, ClearResponse,
    ExitRequest, ExitResponse,
    SessionInfoResponse,
)
from chatbot_api.app.services import chat_service
from chatbot_api.app.services import user_service
from chatbot_api.app.services.knowledge_service import count_knowledge_nodes, get_knowledge_tree

router = APIRouter(prefix="/chat", tags=["聊天"])


@router.post("/send", response_model=ChatResponse, summary="发送消息")
async def send_message(req: ChatRequest):
    """
    发送一条消息，返回模型回复。
    - session_id 用于区分不同用户，每个用户的对话历史和知识树相互隔离。
    - 若消息涉及日期/时间，系统自动注入当前东八区时间。
    - 若消息为退出词（退出/退下/再见/拜拜/quit），自动触发总结+润色+保存知识流程。
    - 每日对话次数和 Token 用量有限制，超限返回 429。
    """
    session_id = req.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id 不能为空")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    # 用量检查（session_id 即用户名）
    limit_check = user_service.check_limit(session_id)
    if not limit_check["allowed"]:
        usage = user_service.get_usage(session_id)
        raise HTTPException(
            status_code=429,
            detail={
                "message": limit_check["reason"],
                "daily_chat_used": usage["daily_chat_used"],
                "daily_chat_limit": usage["daily_chat_limit"],
                "daily_tokens_used": usage["daily_tokens_used"],
                "daily_token_limit": usage["daily_token_limit"],
            }
        )

    result = chat_service.chat(session_id, req.message.strip())

    # 记录用量（粗略估算 token：输入+输出字符数 / 2）
    estimated_tokens = (len(req.message) + len(result.get("reply", ""))) // 2
    user_service.record_usage(session_id, estimated_tokens)

    usage = user_service.get_usage(session_id)
    return ChatResponse(
        session_id=req.session_id,
        reply=result["reply"],
        exited=result["exited"],
        saved=result.get("saved"),
        save_path=result.get("save_path"),
        knowledge_count=result.get("knowledge_count"),
        message=result.get("message", "success"),
        daily_chat_used=usage["daily_chat_used"],
        daily_chat_limit=usage["daily_chat_limit"],
        daily_tokens_used=usage["daily_tokens_used"],
        daily_token_limit=usage["daily_token_limit"],
    )


@router.post("/clear", response_model=ClearResponse, summary="清空对话历史")
async def clear_history(req: ClearRequest):
    """
    清空指定会话的对话历史，知识树保留。
    """
    if not req.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id 不能为空")

    count = chat_service.clear_history(req.session_id.strip())
    knowledge_count = count_knowledge_nodes(get_knowledge_tree(req.session_id.strip()))

    if knowledge_count > 0:
        msg = f"已清除 {count} 条对话记录，{knowledge_count} 条知识已保留，后续对话将自动参考。"
    else:
        msg = f"已清除 {count} 条对话记录，让我们重新开始吧！"

    return ClearResponse(session_id=req.session_id, cleared_count=count, message=msg)


@router.post("/exit", response_model=ExitResponse, summary="退出会话（自动总结并保存知识）")
async def exit_session(req: ExitRequest):
    """
    退出当前会话：自动总结对话历史 → AI 润色 → 保存到知识树 → 清空对话历史。
    服务持续运行，不会停止，仅结束本次会话。下次携带同一 session_id 请求时将重新开始。
    """
    if not req.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id 不能为空")

    result = chat_service.exit_session(req.session_id.strip())
    return ExitResponse(
        session_id=req.session_id,
        saved=result["saved"],
        save_path=result.get("save_path"),
        knowledge_count=result.get("knowledge_count"),
        message=result["message"],
    )


@router.get("/session-info", response_model=SessionInfoResponse, summary="查询会话信息")
async def get_session_info(session_id: str):
    """
    查询指定会话的对话历史条数和知识树节点数。
    """
    if not session_id.strip():
        raise HTTPException(status_code=400, detail="session_id 不能为空")

    history = chat_service.get_history(session_id.strip())
    knowledge_count = count_knowledge_nodes(get_knowledge_tree(session_id.strip()))

    return SessionInfoResponse(
        session_id=session_id,
        history_count=len(history),
        knowledge_count=knowledge_count,
        message="success",
    )
