"""
聊天服务：负责对话历史管理、模型调用、会话退出时自动保存知识
"""
import os
from datetime import datetime, timezone, timedelta
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from chatbot_api.app.services.knowledge_service import (
    get_knowledge_tree,
    flatten_knowledge_tree,
    count_knowledge_nodes,
    append_summary_to_path,
    KNOWLEDGE_BASE_PATH,
    KNOWLEDGE_FILE,
)
from chatbot_api.app.services.user_service import get_bot_style_prompt

load_dotenv()

# ---------- 模型实例 ----------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

chat_model = ChatOpenAI(
    model="deepseek-v4-pro",
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    streaming=False,  # HTTP 接口使用非流式，便于返回完整响应
)

summary_model = ChatOpenAI(
    model="deepseek-v4-pro",
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    streaming=False,
)

# ---------- 对话历史（内存，按 session_id 隔离） ----------
session_histories: dict[str, list[BaseMessage]] = {}


def get_history(session_id: str) -> list[BaseMessage]:
    if session_id not in session_histories:
        session_histories[session_id] = []
    return session_histories[session_id]


def clear_history(session_id: str) -> int:
    """清空指定会话的对话历史，返回清除的消息数"""
    history = get_history(session_id)
    count = len(history)
    history.clear()
    return count


def on_style_change(session_id: str) -> dict:
    """
    风格切换时，将旧对话历史总结为简短摘要替换原始记录。
    保留关键上下文，同时避免旧风格的 AI 回复影响新风格。
    知识树不受影响。
    """
    history = get_history(session_id)
    if not history:
        return {"cleared": 0, "summarized": False}

    old_count = len(history)

    # 总结旧历史为简短摘要
    summary_messages = [
        SystemMessage(content="请用一两句话简洁总结以下对话的关键上下文要点（用户提过什么、讨论过什么主题），不要包含任何语气或风格特征。"),
        *history,
        HumanMessage(content="请总结以上对话的关键上下文。"),
    ]
    response = summary_model.invoke(summary_messages)
    summary_text = response.content.strip()

    # 用摘要替换原始历史
    history.clear()
    history.append(HumanMessage(content=f"（之前的对话摘要：{summary_text}）"))
    history.append(AIMessage(content="好的，我已了解之前的对话内容。"))

    return {"cleared": old_count, "summarized": True}


# ---------- 退出词检测 ----------
EXIT_WORDS = {"quit", "退出", "退下", "再见", "拜拜"}


def is_exit_word(text: str) -> bool:
    """判断用户输入是否为退出触发词"""
    return text.strip().lower() in EXIT_WORDS


# ---------- 日历时间按需注入 ----------
_DATETIME_KEYWORDS = [
    "今天", "明天", "昨天", "后天", "前天",
    "现在", "当前", "日期", "时间", "时刻",
    "星期", "周几", "几号", "几月", "几年", "年份",
    "上午", "下午", "凌晨", "周末", "工作日",
    "节假日", "假日", "小时", "分钟", "日历", "月历",
    "本周", "上周", "下周", "本月", "上月", "下月",
    "今年", "去年", "明年",
    "today", "date", "time", "now", "weekday",
]


def is_datetime_related(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in _DATETIME_KEYWORDS)


def get_current_datetime_str() -> str:
    now = datetime.now(tz=timezone(timedelta(hours=8)))
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return f"{now.strftime('%Y年%m月%d日 %H:%M:%S')}（{weekday_names[now.weekday()]}）"


# ---------- 系统提示词构建 ----------

def build_system_message(session_id: str) -> SystemMessage:
    tree = get_knowledge_tree(session_id)
    knowledge_items = flatten_knowledge_tree(tree)
    base_prompt = get_bot_style_prompt(session_id)
    if knowledge_items:
        base_prompt += "\n\n以下是用户积累的知识库，请在回答时参考："
        for item in knowledge_items:
            base_prompt += f"\n\n{item}"
    return SystemMessage(content=base_prompt)


# ---------- 对话主逻辑 ----------

def chat(session_id: str, user_input: str) -> dict:
    """
    处理用户输入：
    - 若为退出词，自动触发 exit_session，返回 {"exited": True, ...}
    - 否则正常对话，返回 {"exited": False, "reply": "..."}  
    """
    # 退出词检测：自动触发总结+润色+保存+清空
    if is_exit_word(user_input):
        result = exit_session(session_id)
        result["exited"] = True
        result["reply"] = "再见！本次对话已自动总结并保存到知识库，欢迎下次再来。"
        return result

    history = get_history(session_id)

    # 日历相关问题，在用户消息中注入当前时间（不污染历史）
    if is_datetime_related(user_input):
        current_dt = get_current_datetime_str()
        enriched_input = f"（当前时间为：{current_dt}） {user_input}"
        send_msg = HumanMessage(content=enriched_input)
    else:
        send_msg = HumanMessage(content=user_input)

    messages = [build_system_message(session_id), *history, send_msg]
    response = chat_model.invoke(messages)
    full_response = response.content

    # 历史中保存原始输入
    history.append(HumanMessage(content=user_input))
    history.append(AIMessage(content=full_response))

    return {"exited": False, "reply": full_response}


# ---------- 会话退出：自动总结 + 润色 + 保存知识 ----------

def summarize_history(session_id: str) -> str:
    """调用模型总结当前对话历史"""
    history = get_history(session_id)
    summary_messages = [
        SystemMessage(content="你是一个专业的对话总结助手。请将以下对话历史进行简洁、准确的总结，保留关键信息和上下文要点。"),
        *history,
        HumanMessage(content="请总结以上对话内容。"),
    ]
    response = summary_model.invoke(summary_messages)
    return response.content.strip()


def polish_content(content: str) -> str:
    """调用模型对内容进行语法和表达润色"""
    polish_messages = [
        SystemMessage(content="你是一个专业的文本润色助手。请对以下知识内容进行语法修正和表达优化，保持原意不变，使表达更准确、流畅、简洁。请直接输出润色后的内容，不要添加任何额外说明。"),
        HumanMessage(content=content),
    ]
    response = summary_model.invoke(polish_messages)
    return response.content.strip()


def exit_session(session_id: str) -> dict:
    """
    退出会话：自动总结 + AI 润色 + 保存到知识树 + 清空对话历史。
    服务不停止，仅结束本次会话。
    返回保存结果信息。
    """
    history = get_history(session_id)
    if not history:
        return {"saved": False, "message": "当前会话没有对话历史，无需保存。"}

    # 1、总结
    summary = summarize_history(session_id)

    # 2、润色
    polished = polish_content(summary)

    # 3、保存到知识树（路径：基础路径/sessionId/总结N）
    save_path = f"{KNOWLEDGE_BASE_PATH}/{session_id}"
    save_key = append_summary_to_path(session_id, save_path, polished)
    full_path = f"{save_path}/{save_key}"
    knowledge_count = count_knowledge_nodes(get_knowledge_tree(session_id))

    # 4、清空对话历史
    history.clear()

    return {
        "saved": True,
        "save_path": full_path,
        "knowledge_count": knowledge_count,
        "knowledge_file": KNOWLEDGE_FILE,
        "message": f"会话已结束，知识已保存到「{full_path}」（共 {knowledge_count} 条知识）。",
    }
