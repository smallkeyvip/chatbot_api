"""
知识树服务：负责知识树的 CRUD 操作及 JSON 持久化
"""
import json
import os
from langchain_core.messages import BaseMessage

# 知识树内存存储（按 session_id 隔离）
session_knowledge_trees: dict[str, dict] = {}

# 持久化文件路径

DATA_DIR_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../chatbot_api/app/data
KNOWLEDGE_FILE = os.path.join(DATA_DIR_PATH, "data", "knowledge_data.json")
KNOWLEDGE_FILE = os.path.normpath(KNOWLEDGE_FILE)

# 退出时自动保存的基础路径
KNOWLEDGE_BASE_PATH = "knowledge-tree/"


# ---------- 知识树基础操作 ----------

def get_knowledge_tree(session_id: str) -> dict:
    if session_id not in session_knowledge_trees:
        session_knowledge_trees[session_id] = {}
    return session_knowledge_trees[session_id]


def _navigate_tree(tree: dict, path_parts: list[str]) -> dict:
    """沿路径导航，不存在则自动创建"""
    node = tree
    for part in path_parts:
        if part not in node:
            node[part] = {}
        node = node[part]
    return node


def save_knowledge(session_id: str, path: str, content: str):
    """保存知识到指定路径"""
    tree = get_knowledge_tree(session_id)
    parts = [p.strip() for p in path.split("/") if p.strip()]
    node = _navigate_tree(tree, parts)
    node["__content__"] = content
    save_knowledge_to_file()


def get_knowledge_content(session_id: str, path: str) -> str | None:
    """获取指定路径的知识内容"""
    tree = get_knowledge_tree(session_id)
    parts = [p.strip() for p in path.split("/") if p.strip()]
    node = tree
    for part in parts:
        if part not in node:
            return None
        node = node[part]
    return node.get("__content__")


def delete_knowledge(session_id: str, path: str) -> bool:
    """删除指定路径的知识节点"""
    tree = get_knowledge_tree(session_id)
    parts = [p.strip() for p in path.split("/") if p.strip()]
    if not parts:
        return False
    parent = tree
    for part in parts[:-1]:
        if part not in parent:
            return False
        parent = parent[part]
    target = parts[-1]
    if target in parent:
        del parent[target]
        save_knowledge_to_file()
        return True
    return False


def append_summary_to_path(session_id: str, path: str, summary: str) -> str:
    """将总结追加到指定路径下，自动编号"""
    tree = get_knowledge_tree(session_id)
    parts = [p.strip() for p in path.split("/") if p.strip()]
    node = _navigate_tree(tree, parts)
    existing = [k for k in node if k.startswith("总结")]
    key = f"总结{len(existing) + 1}"
    node[key] = {"__content__": summary}
    save_knowledge_to_file()
    return key


def flatten_knowledge_tree(tree: dict, path_prefix: str = "") -> list[str]:
    """将知识树展平为文本列表，用于注入提示词"""
    results = []
    for key, node in tree.items():
        current_path = f"{path_prefix}/{key}" if path_prefix else key
        if "__content__" in node:
            results.append(f"【{current_path}】\n{node['__content__']}")
        children = {k: v for k, v in node.items() if k != "__content__"}
        if children:
            results.extend(flatten_knowledge_tree(children, current_path))
    return results


def count_knowledge_nodes(tree: dict) -> int:
    """统计有内容的节点数"""
    count = 0
    for key, node in tree.items():
        if "__content__" in node:
            count += 1
        children = {k: v for k, v in node.items() if k != "__content__"}
        if children:
            count += count_knowledge_nodes(children)
    return count


def collect_knowledge_paths(tree: dict, path_prefix: str = "") -> list[str]:
    """收集所有节点路径"""
    paths = []
    for key, node in tree.items():
        current_path = f"{path_prefix}/{key}" if path_prefix else key
        if "__content__" in node:
            paths.append(current_path)
        if current_path not in paths:
            paths.append(current_path)
        children = {k: v for k, v in node.items() if k != "__content__"}
        if children:
            paths.extend(collect_knowledge_paths(children, current_path))
    return paths


# ---------- 持久化 ----------

def load_knowledge_from_file():
    """程序启动时从 JSON 文件加载知识树"""
    global session_knowledge_trees
    if os.path.exists(KNOWLEDGE_FILE):
        try:
            with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
                session_knowledge_trees = json.load(f)
            total = sum(count_knowledge_nodes(t) for t in session_knowledge_trees.values())
            print(f"[知识库] 已加载 {len(session_knowledge_trees)} 个会话、{total} 条知识。文件: {KNOWLEDGE_FILE}")
        except Exception as e:
            print(f"[知识库] 加载失败，使用空知识树：{e}")
            session_knowledge_trees = {}
    else:
        print(f"[知识库] 未找到知识文件，使用空知识树。将保存到: {KNOWLEDGE_FILE}")


def save_knowledge_to_file():
    """将知识树持久化到 JSON 文件"""
    try:
        os.makedirs(os.path.dirname(KNOWLEDGE_FILE), exist_ok=True)
        with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
            json.dump(session_knowledge_trees, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[知识库] 保存失败：{e}")
