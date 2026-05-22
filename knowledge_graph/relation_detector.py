"""论文关系检测 — 用 LLM 分析论文之间的关联"""

import json
from database.repository import PaperRepository
from llm.factory import get_llm
from utils.logger import logger

RELATION_PROMPT = """你是一位计算机科学研究助理。请分析以下两篇论文之间的关系。

论文A：
标题：{title_a}
摘要：{abstract_a}
关键概念：{concepts_a}

论文B：
标题：{title_b}
摘要：{abstract_b}
关键概念：{concepts_b}

请判断它们的关系类型（选一个最合适的）：
- cites: A引用了B（或B引用了A）
- extends: A是B的后续/延伸工作
- compares: A和B有直接对比关系
- similar: 研究问题或方法相似但不直接引用
- unrelated: 无明显关系

直接返回 JSON，不要其他文字：
{{"relation": "<类型>", "direction": "A->B" 或 "B->A" 或 "bidirectional" 或 "", "reason": "一句话中文理由"}}"""


def detect_relation(paper_id_a: int, paper_id_b: int, force: bool = False) -> dict | None:
    """检测两篇论文之间的关系。返回关系信息或 None。"""
    if paper_id_a == paper_id_b:
        return None

    with PaperRepository() as repo:
        paper_a = repo.get_paper(paper_id_a)
        paper_b = repo.get_paper(paper_id_b)
        if not paper_a or not paper_b:
            return None

        if not force:
            relations = repo.get_paper_relations(paper_id_a)
            for r in relations:
                if (r.source_id == paper_id_b or r.target_id == paper_id_b):
                    return None  # 已有关系，跳过

        concepts_a = _get_concept_names(repo, paper_id_a)
        concepts_b = _get_concept_names(repo, paper_id_b)

    prompt = RELATION_PROMPT.format(
        title_a=paper_a.title or "",
        abstract_a=(paper_a.abstract or "")[:500],
        concepts_a=", ".join(concepts_a[:8]),
        title_b=paper_b.title or "",
        abstract_b=(paper_b.abstract or "")[:500],
        concepts_b=", ".join(concepts_b[:8]),
    )

    llm = get_llm()
    try:
        resp = llm.chat([{"role": "user", "content": prompt}], max_tokens=512)
        json_match = _find_json(resp)
        if not json_match:
            return None
        result = json.loads(json_match)
    except Exception as e:
        logger.error(f"关系检测异常: {e}")
        return None

    relation_type = result.get("relation", "unrelated")
    if relation_type == "unrelated":
        return None

    direction = result.get("direction", "")
    reason = result.get("reason", "")

    # 存入数据库
    with PaperRepository() as repo:
        if direction == "B->A" or direction == "bidirectional":
            repo.add_relation(paper_id_b, paper_id_a, relation_type)
        else:
            repo.add_relation(paper_id_a, paper_id_b, relation_type)
        repo.commit()

    logger.info(f"检测到关系: {paper_id_a} <-> {paper_id_b}: {relation_type} ({reason[:40]})")
    return {"relation": relation_type, "direction": direction, "reason": reason}


def detect_all_relations(limit: int | None = None):
    """对所有论文对进行批量关系检测（仅检测已有概念的论文）"""
    with PaperRepository() as repo:
        from database.connection import get_session
        from database.models import PaperConcept, Paper
        s = get_session()
        try:
            # 获取有概念的论文
            paper_ids = [row[0] for row in
                         s.query(PaperConcept.paper_id).distinct().all()]
        finally:
            s.close()

    count = 0
    for i, pid_a in enumerate(paper_ids):
        for pid_b in paper_ids[i + 1:]:
            if limit and count >= limit:
                return count
            result = detect_relation(pid_a, pid_b)
            if result:
                count += 1

    return count


def _get_concept_names(repo: PaperRepository, paper_id: int) -> list[str]:
    concepts = repo.get_paper_concepts(paper_id)
    return [c.concept.name for c in concepts if c.concept]


def _find_json(text: str) -> str | None:
    import re
    match = re.search(r"\{[\s\S]*\}", text)
    return match.group(0) if match else None
