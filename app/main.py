"""
FastAPI 应用入口
"""
import sys
import os

# 兼容 PyCharm 直接运行脚本的场景：确保项目根目录在 sys.path 中
# 这样相对导入（from .routers import ...）才能正常工作
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 统一改用绝对导入，兼容直接运行和 uvicorn 模块启动两种方式
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import chat
from .routers import auth
from .routers import feedback
from .services.knowledge_service import load_knowledge_from_file
from .services.user_service import load_all as load_user_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/停止生命周期管理"""
    # 启动时加载知识树和用户数据
    load_knowledge_from_file()
    load_user_data()
    print("[服务] 聊天机器人 API 服务已启动，等待请求...")
    yield
    # 停止时清理（如有需要）
    print("[服务] 服务正在关闭...")


app = FastAPI(
    title="聊天机器人 API",
    description="多用户聊天机器人，支持注册登录、对话历史记忆、知识树持久化、主题风格、反馈建议、每日用量限制。",
    version="2.0.0",
    lifespan=lifespan,
)

# 跨域配置（按需修改允许的域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(feedback.router)

# 挂载静态文件（H5页面）
# 使用 __file__ 绝对路径计算，兼容任何工作目录
_app_dir = os.path.dirname(os.path.abspath(__file__))           # .../chatbot_api/app
_chatbot_dir = os.path.dirname(_app_dir)                        # .../chatbot_api
_static_dir = os.path.join(_chatbot_dir, "static")             # .../chatbot_api/static
_index_html = os.path.join(_static_dir, "index.html")

print(f"[静态文件] static 目录: {_static_dir}")
print(f"[静态文件] index.html 存在: {os.path.exists(_index_html)}")

if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/", summary="H5 聊天页面", include_in_schema=False)
async def root():
    if os.path.exists(_index_html):
        return FileResponse(_index_html)
    return {"status": "ok", "message": "聊天机器人 API 服务运行中（index.html 未找到：" + _index_html + "）"}


@app.get("/health", summary="健康检查")
async def health():
    return {"status": "healthy"}

