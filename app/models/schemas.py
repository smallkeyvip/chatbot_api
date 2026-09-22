"""
Pydantic 请求/响应数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional


# ==================== 聊天相关 ====================

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="用户会话 ID，用于隔离不同用户的对话历史和知识树")
    message: str = Field(..., description="用户发送的消息内容")


class ClearRequest(BaseModel):
    session_id: str = Field(..., description="用户会话 ID")


class ExitRequest(BaseModel):
    session_id: str = Field(..., description="用户会话 ID")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    exited: bool = False
    saved: Optional[bool] = None
    save_path: Optional[str] = None
    knowledge_count: Optional[int] = None
    message: str = "success"
    # 用量信息
    daily_chat_used: Optional[int] = None
    daily_chat_limit: Optional[int] = None
    daily_tokens_used: Optional[int] = None
    daily_token_limit: Optional[int] = None


class ClearResponse(BaseModel):
    session_id: str
    cleared_count: int
    message: str


class ExitResponse(BaseModel):
    session_id: str
    saved: bool
    save_path: Optional[str] = None
    knowledge_count: Optional[int] = None
    message: str


class SessionInfoResponse(BaseModel):
    session_id: str
    history_count: int
    knowledge_count: int
    message: str


# ==================== 认证相关 ====================

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32, description="用户名（2-32字符）")
    password: str = Field(..., min_length=6, max_length=64, description="密码（至少6位）")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class CheckUserRequest(BaseModel):
    username: str = Field(..., description="用户名")


class AuthResponse(BaseModel):
    success: bool
    message: str
    username: Optional[str] = None
    is_new: Optional[bool] = None  # True=新注册 False=已存在
    # 5 分钟免密自动登录凭证
    auto_login_token: Optional[str] = None
    auto_login_expires_in: Optional[int] = Field(None, description="凭证有效期（秒）")


class AutoLoginRequest(BaseModel):
    token: str = Field(..., description="登录/注册时颁发的免密凭证")


class LogoutRequest(BaseModel):
    token: Optional[str] = Field(None, description="免密凭证（可选）")


class AutoLoginResponse(BaseModel):
    success: bool
    message: str
    username: Optional[str] = None


class CheckUserResponse(BaseModel):
    exists: bool
    username: str
    message: str  # "用户已注册，请登录" 或 "用户未注册，请注册"


# ==================== 猜你喜欢（推荐问题） ====================

class RecommendItem(BaseModel):
    question: str


class RecommendResponse(BaseModel):
    session_id: str
    items: list[RecommendItem]
    source: str = "default"  # history=基于历史生成 default=默认推荐池
    message: str = "success"


# ==================== 用户设置/风格 ====================

class UpdateThemeRequest(BaseModel):
    username: str = Field(..., description="用户名")
    theme: str = Field(..., description="主题名称：default / dark / ocean / forest / sunset")


class UserSettingsResponse(BaseModel):
    username: str
    theme: str
    message: str


# ==================== 机器人聊天风格 ====================

class UpdateBotStyleRequest(BaseModel):
    username: str = Field(..., description="用户名")
    bot_style: str = Field(..., description="风格：default / humorous / cute / pro / teacher / poet")


class BotStyleResponse(BaseModel):
    username: str
    bot_style: str
    label: Optional[str] = None
    emoji: Optional[str] = None
    message: str


class BotStyleListResponse(BaseModel):
    current: str
    items: list


# ==================== 反馈相关 ====================

class FeedbackRequest(BaseModel):
    username: str = Field(..., description="用户名")
    category: str = Field("suggestion", description="类别：suggestion / bug / feedback")
    content: str = Field(..., min_length=1, max_length=2000, description="反馈内容")
    contact: Optional[str] = Field(None, max_length=100, description="联系方式（可选）")


class FeedbackResponse(BaseModel):
    success: bool
    message: str
    feedback_id: Optional[str] = None


class FeedbackListResponse(BaseModel):
    total: int
    items: list


# ==================== 用量相关 ====================

class UsageResponse(BaseModel):
    username: str
    daily_chat_used: int
    daily_chat_limit: int
    daily_tokens_used: int
    daily_token_limit: int
    chat_remaining: int
    token_remaining: int
    message: str


# ==================== 管理相关 ====================

class AdminUserItem(BaseModel):
    username: str
    created_at: str = ""
    theme: str = "default"
    bot_style: str = "default"
    today_chat_count: int = 0
    today_token_count: int = 0


class AdminUserListResponse(BaseModel):
    total: int
    items: list[AdminUserItem]
