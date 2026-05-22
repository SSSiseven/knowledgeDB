"""个性化推荐排序 — 基于用户阅读历史"""

from database.repository import PaperRepository
from utils.logger import logger


def rank_by_interest(papers: list[dict], top_k: int = 20) -> list[dict]:
    """根据用户已读论文的兴趣偏好排序推荐"""
    # 收集用户已读论文的概念
    user_concepts = _get_user_concepts()
    user_kw = _get_user_keywords()

    scored = []
    for p in papers:
        score = 0
        text = f"{p.get('title', '')} {p.get('abstract', '')}".lower()

        # 概念匹配加分
        for concept, weight in user_concepts.items():
            if concept.lower() in text:
                score += weight * 3

        # 关键词匹配加分
        for kw in user_kw:
            if kw.lower() in text:
                score += 1

        # 引用量加分
        citations = p.get("citations", 0) or 0
        score += min(citations / 100, 5)

        # 年份加分（越新越好）
        year = p.get("year", 0) or 0
        score += max(0, (year - 2020) * 0.5)

        p["relevance_score"] = round(score, 2)
        scored.append(p)

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:top_k]


def generate_recommendation_reason(paper: dict) -> str:
    """生成推荐理由"""
    reasons = []
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")[:300]
    text = f"{title} {abstract}".lower()

    user_concepts = _get_user_concepts()
    matched = [c for c in user_concepts if c.lower() in text]
    if matched:
        reasons.append(f"与你的研究方向 '{matched[0]}' 相关")

    citations = paper.get("citations", 0) or 0
    if citations > 100:
        reasons.append(f"高引用 ({citations} 次)")
    elif citations > 10:
        reasons.append(f"有一定引用 ({citations} 次)")

    year = paper.get("year", 0) or 0
    if year >= 2025:
        reasons.append("最新发表")
    elif year >= 2024:
        reasons.append("较新发表")

    if paper.get("venue"):
        reasons.append(f"发表于 {paper['venue']}")

    return "; ".join(reasons) if reasons else "可能符合你的研究方向"


def _get_user_concepts() -> dict:
    """获取用户知识库中的高频概念及权重"""
    from database.connection import get_session
    from database.models import PaperConcept
    s = get_session()
    try:
        pcs = s.query(PaperConcept).all()
        concept_counts = {}
        for pc in pcs:
            if pc.concept:
                concept_counts[pc.concept.name] = concept_counts.get(pc.concept.name, 0) + 1
        max_count = max(concept_counts.values()) if concept_counts else 1
        return {name: count / max_count for name, count in concept_counts.items()}
    except Exception:
        return {}
    finally:
        s.close()


def _get_user_keywords() -> list[str]:
    from config import DEFAULT_KEYWORDS
    return DEFAULT_KEYWORDS
