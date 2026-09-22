"""
认证相关路由：注册、登录、检查用户、主题设置、用量查询
"""
from fastapi import APIRouter, HTTPException

from chatbot_api.app.models.schemas import (
    RegisterRequest, LoginRequest, CheckUserRequest,
    AuthResponse, CheckUserResponse,
    AutoLoginRequest, LogoutRequest, AutoLoginResponse,
    UpdateThemeRequest, UserSettingsResponse,
    UpdateBotStyleRequest, BotStyleResponse, BotStyleListResponse,
    UsageResponse,
)
from chatbot_api.app.services import user_service
from chatbot_api.app.services import chat_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/check", response_model=CheckUserResponse, summary="检查用户是否已注册")
async def check_user(req: CheckUserRequest):
    """
    输入用户名，返回该用户是否已注册。
    前端据此决定展示注册还是登录表单。
    """
    if not req.username.strip():
        raise HTTPException(status_code=400, detail="用户名不能为空")
    result = user_service.check_user(req.username.strip())
    return CheckUserResponse(**result)


@router.post("/register", response_model=AuthResponse, summary="注册")
async def register(req: RegisterRequest):
    """注册新账号"""
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    result = user_service.register(username, req.password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return AuthResponse(**result)


@router.post("/login", response_model=AuthResponse, summary="登录")
async def login(req: LoginRequest):
    """用户登录"""
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    result = user_service.login(username, req.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    return AuthResponse(**result)


@router.post("/auto-login", response_model=AutoLoginResponse, summary="自动登录（5分钟内免密）")
async def auto_login(req: AutoLoginRequest):
    """
    使用登录/注册时颁发的免密凭证自动登录。
    滑动窗口：每次校验通过后凭证自动续期 5 分钟。
    """
    if not req.token.strip():
        raise HTTPException(status_code=400, detail="token 不能为空")
    result = user_service.auto_login(req.token.strip())
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    return AutoLoginResponse(**result)


@router.post("/logout", response_model=AutoLoginResponse, summary="退出登录（注销免密凭证）")
async def logout(req: LogoutRequest):
    """注销免密登录凭证，之后需重新输入密码登录。"""
    if req.token and req.token.strip():
        user_service.logout(req.token.strip())
    return AutoLoginResponse(success=True, message="已退出登录")


@router.post("/theme", response_model=UserSettingsResponse, summary="更新主题风格")
async def update_theme(req: UpdateThemeRequest):
    """更新用户聊天界面主题"""
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    result = user_service.set_theme(username, req.theme.strip())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "操作失败"))
    return UserSettingsResponse(
        username=result["username"],
        theme=result["theme"],
        message=result["message"],
    )


@router.get("/theme", response_model=UserSettingsResponse, summary="获取当前主题")
async def get_theme(username: str):
    """获取用户当前主题"""
    username = username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    theme = user_service.get_theme(username)
    return UserSettingsResponse(username=username, theme=theme, message="success")


@router.get("/usage", response_model=UsageResponse, summary="查询今日用量")
async def get_usage(username: str):
    """查询用户今日对话次数和 Token 用量"""
    username = username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    result = user_service.get_usage(username)
    return UsageResponse(**result)


@router.post("/bot-style", response_model=BotStyleResponse, summary="设置机器人聊天风格")
async def update_bot_style(req: UpdateBotStyleRequest):
    """更新机器人聊天风格（幽默、可爱、专业等）"""
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    result = user_service.set_bot_style(username, req.bot_style.strip())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "操作失败"))
    # 风格切换后，将旧历史总结为摘要，确保新风格不受旧回复影响
    chat_service.on_style_change(username)
    return BotStyleResponse(
        username=result["username"],
        bot_style=result["bot_style"],
        label=result.get("label"),
        emoji=result.get("emoji"),
        message=result["message"],
    )


@router.get("/bot-style", response_model=BotStyleListResponse, summary="获取机器人风格列表及当前选择")
async def get_bot_style(username: str):
    """获取所有可用的机器人聊天风格及用户当前选择"""
    username = username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    current = user_service.get_bot_style(username)
    items = user_service.list_bot_styles()
    return BotStyleListResponse(current=current, items=items)
