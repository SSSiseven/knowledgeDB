"""图谱持久化 — 图序列化与恢复"""

import pickle
from pathlib import Path
import networkx as nx
from config import GRAPH_DIR
from .graph_builder import build_graph
from utils.logger import logger

GRAPH_FILE = GRAPH_DIR / "knowledge_graph.pkl"


def save_graph(G: nx.Graph = None):
    """保存图谱到磁盘"""
    if G is None:
        G = build_graph()
    GRAPH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_FILE, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info(f"图谱已保存: {GRAPH_FILE} ({G.number_of_nodes()} 节点)")


def load_graph() -> nx.Graph | None:
    """从磁盘加载图谱"""
    if not GRAPH_FILE.exists():
        return None
    try:
        with open(GRAPH_FILE, "rb") as f:
            G = pickle.load(f)
        logger.info(f"图谱已加载: {G.number_of_nodes()} 节点")
        return G
    except Exception as e:
        logger.error(f"图谱加载失败: {e}")
        return None


def get_or_build_graph() -> nx.Graph:
    """获取图谱（优先从磁盘加载，否则重建）"""
    G = load_graph()
    if G is None:
        G = build_graph()
        save_graph(G)
    return G


def rebuild_graph():
    """强制重建图谱"""
    G = build_graph()
    save_graph(G)
    return G
