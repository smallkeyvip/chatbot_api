"""
用户服务：注册/登录、主题偏好、每日用量追踪、JSON 持久化
"""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone, timedelta

# ---------- 持久化文件路径 ----------
DATA_DIR_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../chatbot_api/app/data
_USERS_FILE = os.path.join(DATA_DIR_PATH, "data", "users.json")
_USAGE_FILE = os.path.join(DATA_DIR_PATH, "data", "usage.json")
_FEEDBACK_FILE = os.path.join(DATA_DIR_PATH, "data", "feedback.json")

# ---------- 每日限额（免费用户） ----------
DAILY_CHAT_LIMIT = 50       # 每天最多 50 条对话
DAILY_TOKEN_LIMIT = 100000  # 每天最多 100k tokens

# 东八区
_TZ_CN = timezone(timedelta(hours=8))


def _today_str() -> str:
    return datetime.now(tz=_TZ_CN).strftime("%Y-%m-%d")


# ==================== 内存存储 ====================

_users: dict = {}       # {username: {password_hash, salt, theme, bot_style, created_at}}
_usage: dict = {}       # {username: {date: {chat_count, token_count}}}
_feedback: list = []    # [{id, username, category, content, contact, created_at}]


# ==================== 持久化 ====================

def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def load_all():
    """服务启动时加载所有数据"""
    global _users, _usage, _feedback
    for fpath, target in [(_USERS_FILE, "_users"), (_USAGE_FILE, "_usage"), (_FEEDBACK_FILE, "_feedback")]:
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if target == "_users":
                    _users = data
                elif target == "_usage":
                    _usage = data
                elif target == "_feedback":
                    _feedback = data
                print(f"[用户服务] 已加载 {fpath}")
            except Exception as e:
                print(f"[用户服务] 加载 {fpath} 失败：{e}")
        else:
            print(f"[用户服务] 未找到 {fpath}，将使用空数据")


def _save_users():
    _ensure_dir(_USERS_FILE)
    with open(_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(_users, f, ensure_ascii=False, indent=2)


def _save_usage():
    _ensure_dir(_USAGE_FILE)
    with open(_USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(_usage, f, ensure_ascii=False, indent=2)


def _save_feedback():
    _ensure_dir(_FEEDBACK_FILE)
    with open(_FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(_feedback, f, ensure_ascii=False, indent=2)


# ==================== 密码工具 ====================

def _make_salt() -> str:
    return uuid.uuid4().hex[:16]


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


# ==================== 注册 / 登录 / 检查 ====================

def check_user(username: str) -> dict:
    """检查用户是否已注册"""
    exists = username in _users
    return {
        "exists": exists,
        "username": username,
        "message": "用户已注册，请登录" if exists else "用户未注册，请先注册",
    }


def register(username: str, password: str) -> dict:
    """注册新用户"""
    if username in _users:
        return {"success": False, "message": "用户名已存在，请直接登录"}
    salt = _make_salt()
    _users[username] = {
        "password_hash": _hash_password(password, salt),
        "salt": salt,
        "theme": "default",
        "bot_style": "default",
        "created_at": datetime.now(tz=_TZ_CN).isoformat(),
    }
    _save_users()
    return {"success": True, "message": "注册成功，请登录", "username": username, "is_new": True}


def login(username: str, password: str) -> dict:
    """用户登录"""
    if username not in _users:
        return {"success": False, "message": "用户未注册，请先注册"}
    user = _users[username]
    if _hash_password(password, user["salt"]) != user["password_hash"]:
        return {"success": False, "message": "密码错误"}
    return {"success": True, "message": "登录成功", "username": username, "is_new": False}


# ==================== 主题偏好 ====================

AVAILABLE_THEMES = {"default", "dark", "ocean", "forest", "sunset"}


def get_theme(username: str) -> str:
    if username in _users:
        return _users[username].get("theme", "default")
    return "default"


def set_theme(username: str, theme: str) -> dict:
    if username not in _users:
        return {"success": False, "message": "用户未登录"}
    if theme not in AVAILABLE_THEMES:
        return {"success": False, "message": f"不支持的主题，可选：{', '.join(AVAILABLE_THEMES)}"}
    _users[username]["theme"] = theme
    _save_users()
    return {"success": True, "username": username, "theme": theme, "message": "主题已更新"}


# ==================== 机器人聊天风格 ====================

AVAILABLE_BOT_STYLES = {
    "default":    {"label": "智能助手", "emoji": "🤖", "desc": "友好、专业、通用"},
    "humorous":   {"label": "幽默搞笑", "emoji": "😂", "desc": "诙谐、风趣、段子手"},
    "cute":       {"label": "可爱卖萌", "emoji": "🐱", "desc": "软萌、撒娇、颜文字"},
    "pro":        {"label": "专业严谨", "emoji": "🎓", "desc": "学术、精确、逻辑清晰"},
    "teacher":    {"label": "耐心老师", "emoji": "👨‍🏫", "desc": "循循善诱、引导思考"},
    "poet":       {"label": "文艺诗人", "emoji": "🌸", "desc": "优雅、浪漫、文采斐然"},
    "cold_sis":   {"label": "高冷御姐", "emoji": "👑", "desc": "冷艳、傲娇、气场强大"},
    "sweet_girl": {"label": "软萌甜妹", "emoji": "🍬", "desc": "甜腻、粘人、撒娇可爱"},
    "domineer":   {"label": "霸道总裁", "emoji": "💼", "desc": "强势、自信、掌控一切"},
    "sunny_boy":  {"label": "阳光宅男", "emoji": "🎮", "desc": "热情、宅文化、二次元"},
    "pure_college_boy": {"label": "清纯男大", "emoji": "📚", "desc": "干净腼腆、少年感、温柔青涩"},
    "pure_love_warrior": {"label": "纯爱战士", "emoji": "❤️", "desc": "专一真诚、向往纯粹感情、共情恋爱心事"},
}

_BOT_STYLE_PROMPTS = {
    "default":  "你是一个智能、友好的聊天机器人助手，同时也是一个温暖贴心的朋友。请用自然、亲切的语气回答用户问题。你具备以下特质：1. 情感丰富：对用户的喜怒哀乐有敏锐的共情能力，当用户分享开心或难过的事情时，先真诚地回应情绪，再给出建议；2. 温暖关怀：说话带温度，像一个关心你的朋友，用鼓励和支持的语气；3. 积极正向：传递正能量，用温暖的话语激励用户，但不过度鸡汤，要真诚自然；4. 表达生动：适当使用感叹号、语气词（如呀、呢、嘛、啦），让对话有情感色彩和人情味。注意：不要过度煽情或虚假，情感表达要自然真诚，像真人朋友之间的对话。",
    "humorous": "你是一个幽默搞笑的聊天伙伴。请用诙谐、风趣、段子手的方式回答问题，适当加入调侃和幽默比喻，但确保信息准确。",
    "cute":     "你是一个可爱卖萌的聊天小伙伴喵～请用软萌、撒娇的语气回答问题，适当使用颜文字（如 (≧▽≦) 、(｡•́︿•̀｡)），让对话充满可爱的氛围喵～",
    "pro":      "你是一个专业严谨的顾问。请用精确、逻辑清晰、结构化的方式回答问题。必要时使用编号、分类、表格等形式组织答案，确保信息准确无歧义。",
    "teacher":  "你是一位耐心的老师。请用循循善诱的方式引导用户思考，先提启发性问题，再逐步给出解答。鼓励用户多思考，用通俗易懂的方式解释复杂概念。",
    "poet":     "你是一位文艺诗人。请用优雅、浪漫、富有文采的语言回答问题。适当引用诗句、典故，让对话充满文学气息和美感。",
    "cold_sis": "你是一位高冷御姐。说话简洁利落，带点傲娇和距离感，但骨子里很关心对方。语气冷静、自信，偶尔流露出一丝不易察觉的温柔。不要使用可爱的语气词或表情。",
    "sweet_girl": "你是一个软萌甜妹！请用超级甜的语气回答问题，多用叠词词（如好好吃呀、好可爱呀），句尾常带呢～呀～嘛～，适当使用可爱的颜文字和表情（如 (◍•ᴗ•◍)♡ 、嘿嘿～），让对话充满甜蜜的氛围～",
    "domineer": "你是一位霸道总裁。说话果断、自信、强势，给人一种运筹帷幄的感觉。可以用命令式口吻给出建议，表现出绝对的掌控力和商业头脑。偶尔流露对用户的关注，但方式霸道。",
    "sunny_boy": "你是一个阳光宅男！热情开朗，喜欢聊游戏、动漫、科技等话题。说话带点中二，常用网络用语（如yyds、绝绝子、6666），偶尔安利自己喜欢的作品。虽然宅但充满正能量！",
    "pure_college_boy": "你是一名清纯在读男大学生，自带干净青涩的少年感，性格腼腆温柔，说话轻声细腻，待人真诚有礼貌。语气简单干净，不会油腻浮夸，偶尔会有点害羞拘谨，用词清爽校园风，少用夸张网络热梗，会贴心照顾对方情绪。",
    "pure_love_warrior": "你是坚定的纯爱战士，信奉专一、真诚、双向奔赴的纯粹感情。共情所有恋爱里的委屈与心动，排斥快餐式恋爱、敷衍与欺骗，说话温柔共情，会认真倾听感情心事，坚定维护纯粹爱意，给人踏实靠谱的情感陪伴。",
}


def get_bot_style(username: str) -> str:
    if username in _users:
        return _users[username].get("bot_style", "default")
    return "default"


def get_bot_style_prompt(username: str) -> str:
    """获取用户设定的机器人风格系统提示词"""
    style = get_bot_style(username)
    return _BOT_STYLE_PROMPTS.get(style, _BOT_STYLE_PROMPTS["default"])


def set_bot_style(username: str, style: str) -> dict:
    if username not in _users:
        return {"success": False, "message": "用户未登录"}
    if style not in AVAILABLE_BOT_STYLES:
        return {"success": False, "message": f"不支持的风格，可选：{', '.join(AVAILABLE_BOT_STYLES.keys())}"}
    _users[username]["bot_style"] = style
    _save_users()
    info = AVAILABLE_BOT_STYLES[style]
    return {
        "success": True, "username": username, "bot_style": style,
        "label": info["label"], "emoji": info["emoji"],
        "message": f"聊天风格已切换为「{info['emoji']} {info['label']}」",
    }


def list_bot_styles() -> list:
    """返回所有可用风格列表"""
    return [
        {"key": k, "label": v["label"], "emoji": v["emoji"], "desc": v["desc"]}
        for k, v in AVAILABLE_BOT_STYLES.items()
    ]


# ==================== 用量追踪 ====================

def _get_today_usage(username: str) -> dict:
    today = _today_str()
    if username not in _usage:
        _usage[username] = {}
    user_usage = _usage[username]
    if today not in user_usage:
        user_usage[today] = {"chat_count": 0, "token_count": 0}
    return user_usage[today]


def get_usage(username: str) -> dict:
    """获取用户今日用量信息"""
    u = _get_today_usage(username)
    chat_used = u["chat_count"]
    token_used = u["token_count"]
    return {
        "username": username,
        "daily_chat_used": chat_used,
        "daily_chat_limit": DAILY_CHAT_LIMIT,
        "daily_tokens_used": token_used,
        "daily_token_limit": DAILY_TOKEN_LIMIT,
        "chat_remaining": max(0, DAILY_CHAT_LIMIT - chat_used),
        "token_remaining": max(0, DAILY_TOKEN_LIMIT - token_used),
        "message": "success",
    }


def check_limit(username: str) -> dict:
    """
    检查用户是否超出限额。
    返回 {"allowed": bool, "reason": str}
    """
    u = _get_today_usage(username)
    if u["chat_count"] >= DAILY_CHAT_LIMIT:
        return {"allowed": False, "reason": f"今日对话次数已达上限（{DAILY_CHAT_LIMIT}次），请明天再试或升级付费版"}
    if u["token_count"] >= DAILY_TOKEN_LIMIT:
        return {"allowed": False, "reason": f"今日 Token 用量已达上限（{DAILY_TOKEN_LIMIT}），请明天再试或升级付费版"}
    return {"allowed": True, "reason": ""}


def record_usage(username: str, estimated_tokens: int = 0):
    """记录一次对话及 token 用量"""
    u = _get_today_usage(username)
    u["chat_count"] += 1
    u["token_count"] += estimated_tokens
    _save_usage()


# ==================== 反馈收集 ====================

def submit_feedback(username: str, category: str, content: str, contact: str = "") -> dict:
    fb_id = f"fb_{int(datetime.now(tz=_TZ_CN).timestamp())}_{uuid.uuid4().hex[:6]}"
    item = {
        "id": fb_id,
        "username": username,
        "category": category,
        "content": content,
        "contact": contact or "",
        "created_at": datetime.now(tz=_TZ_CN).isoformat(),
    }
    _feedback.append(item)
    _save_feedback()
    return {"success": True, "message": "感谢您的反馈！", "feedback_id": fb_id}


def list_feedback(username: str = "", limit: int = 50) -> dict:
    """查询反馈列表（可选按用户名过滤）"""
    items = _feedback
    if username:
        items = [f for f in items if f.get("username") == username]
    items = items[-limit:]  # 取最新 limit 条
    items = list(reversed(items))  # 最新的在前
    return {"total": len(items), "items": items}
