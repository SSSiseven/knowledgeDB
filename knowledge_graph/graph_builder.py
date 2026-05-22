"""知识图谱构建 — 将 papers + concepts + relations 组装为 NetworkX 图"""

import networkx as nx
from database.connection import get_session
from database.models import Paper, Concept, PaperConcept, PaperRelation
from utils.logger import logger


def build_graph() -> nx.Graph:
    """从数据库构建完整知识图谱。
    节点：论文 + 概念
    边：论文-概念关联 + 论文间关系 + 论文间共享概念
    """
    G = nx.Graph()
    s = get_session()
    try:
        papers = s.query(Paper).all()
        concepts = s.query(Concept).all()
        paper_concepts = s.query(PaperConcept).all()
        relations = s.query(PaperRelation).all()
    finally:
        s.close()

    # 添加论文节点
    for p in papers:
        G.add_node(
            f"paper_{p.id}",
            type="paper",
            label=p.title[:80] if p.title else f"Paper {p.id}",
            title=p.title or "",
            year=p.year or 0,
            venue=p.venue or "",
            arxiv_id=p.arxiv_id or "",
            paper_id=p.id,
            status=p.status or "unread",
        )

    # 添加概念节点
    for c in concepts:
        G.add_node(
            f"concept_{c.id}",
            type="concept",
            label=c.name,
            name=c.name,
            category=c.category or "",
            description=c.description or "",
            concept_id=c.id,
        )

    # 论文-概念边
    for pc in paper_concepts:
        G.add_edge(
            f"paper_{pc.paper_id}",
            f"concept_{pc.concept_id}",
            type="has_concept",
            relevance=pc.relevance or "related",
        )

    # 论文间关系边
    for r in relations:
        G.add_edge(
            f"paper_{r.source_id}",
            f"paper_{r.target_id}",
            type="paper_relation",
            relation=r.relation_type,
        )

    # 共享概念的论文之间加弱连接（至少共享2个概念）
    concept_to_papers = {}
    for pc in paper_concepts:
        concept_to_papers.setdefault(pc.concept_id, []).append(pc.paper_id)

    for concept_id, paper_list in concept_to_papers.items():
        if len(paper_list) >= 2:
            for i, pid_a in enumerate(paper_list):
                for pid_b in paper_list[i + 1:]:
                    # 只有两者之间的共享概念数达到阈值才加边
                    shared = len(set(concept_to_papers.get(cid, []))
                                 & {pid_a, pid_b}
                                 for cid in concept_to_papers
                                 if pid_a in concept_to_papers.get(cid, [])
                                 and pid_b in concept_to_papers.get(cid, []))
                    if _count_shared_concepts(paper_concepts, pid_a, pid_b) >= 2:
                        if not G.has_edge(f"paper_{pid_a}", f"paper_{pid_b}"):
                            G.add_edge(
                                f"paper_{pid_a}",
                                f"paper_{pid_b}",
                                type="shared_concepts",
                                weight=0.5,
                            )

    logger.info(f"知识图谱构建完成: {G.number_of_nodes()} 节点, {G.number_of_edges()} 边")
    return G


def _count_shared_concepts(pc_list: list[PaperConcept], pid_a: int, pid_b: int) -> int:
    concepts_a = {pc.concept_id for pc in pc_list if pc.paper_id == pid_a}
    concepts_b = {pc.concept_id for pc in pc_list if pc.paper_id == pid_b}
    return len(concepts_a & concepts_b)


def get_subgraph(G: nx.Graph, concept_ids: list[int] = None,
                 paper_ids: list[int] = None, max_depth: int = 2) -> nx.Graph:
    """提取子图：以指定节点为中心，向外扩展指定深度"""
    seed_nodes = []
    if paper_ids:
        seed_nodes.extend([f"paper_{pid}" for pid in paper_ids if f"paper_{pid}" in G])
    if concept_ids:
        seed_nodes.extend([f"concept_{cid}" for cid in concept_ids if f"concept_{cid}" in G])

    if not seed_nodes:
        return G

    nodes = set(seed_nodes)
    for seed in seed_nodes:
        for neighbor in G.neighbors(seed):
            nodes.add(neighbor)
            if max_depth >= 2:
                for n2 in G.neighbors(neighbor):
                    nodes.add(n2)

    return G.subgraph(nodes).copy()
