"""概念实体提取 — 用 LLM 从论文中提取关键概念"""

import json
from database.repository import PaperRepository
from llm.factory import get_llm
from utils.logger import logger

EXTRACT_PROMPT = """你是一位计算机科学研究助理。请从以下论文中提取关键概念实体。

论文标题：{title}
摘要：{abstract}
正文片段：{content}

请提取 5-10 个核心概念，每个概念包含：
1. name: 概念名称（英文，简洁）
2. description: 一句话中文描述
3. category: 类型，从以下选一个
   - algorithm (算法/方法)
   - framework (框架/架构)
   - problem (问题/挑战)
   - metric (评估指标)
   - theory (理论)
   - technique (技术/技巧)

直接返回 JSON 数组，不要其他文字：
[{{"name": "...", "description": "...", "category": "..."}}, ...]"""


def extract_concepts(paper_id: int, force: bool = False) -> list[dict]:
    """提取一篇论文的关键概念，存入 concept 表并建立关联。
    如果 paper 已有概念则不重复提取，除非 force=True。
    """
    with PaperRepository() as repo:
        paper = repo.get_paper(paper_id)
        if not paper:
            logger.error(f"论文不存在: {paper_id}")
            return []

        if not force:
            existing = repo.get_paper_concepts(paper_id)
            if existing:
                return [{"id": c.concept_id, "name": c.concept.name,
                         "category": c.concept.category, "relevance": c.relevance}
                        for c in existing]

    # 获取论文内容
    title = paper.title or ""
    abstract = paper.abstract or ""
    content = ""
    if paper.file_path:
        from pathlib import Path
        if Path(paper.file_path).exists():
            from ingestion.pdf_parser import extract_text_from_first_pages
            content = extract_text_from_first_pages(paper.file_path, num_pages=3)

    full_text = f"{abstract}\n{content}"[:4000]

    llm = get_llm()
    prompt = EXTRACT_PROMPT.format(title=title, abstract=abstract, content=full_text)

    try:
        resp = llm.chat([{"role": "user", "content": prompt}], max_tokens=2048)
        # 提取 JSON 部分
        json_match = _find_json(resp)
        if not json_match:
            logger.error(f"概念提取失败，未找到 JSON: {resp[:200]}")
            return []
        concepts = json.loads(json_match)
    except Exception as e:
        logger.error(f"概念提取异常: {e}")
        return []

    # 存入数据库
    results = []
    with PaperRepository() as repo:
        for c in concepts:
            concept = repo.get_or_create_concept(
                name=c["name"],
                category=c.get("category", "algorithm"),
                description=c.get("description", ""),
            )
            relevance = "core" if concepts.index(c) < 3 else "related"
            repo.link_paper_concept(paper_id, concept.id, relevance)
            results.append({"id": concept.id, "name": concept.name,
                            "category": concept.category, "relevance": relevance})
        repo.commit()

    logger.info(f"论文 {paper_id} 提取出 {len(results)} 个概念")
    return results


def extract_all_concepts() -> dict:
    """对所有未提取概念的论文进行批量提取"""
    from database.connection import get_session
    from database.models import Paper

    s = get_session()
    try:
        papers = s.query(Paper).all()
    finally:
        s.close()

    total = len(papers)
    done = 0
    for paper in papers:
        concepts = extract_concepts(paper.id)
        if concepts:
            done += 1
            logger.info(f"[{done}/{total}] {paper.title[:40]}... -> {len(concepts)} concepts")

    return {"total": total, "processed": done}


def _find_json(text: str) -> str | None:
    """从 LLM 回复中提取 JSON 数组"""
    import re
    match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", text)
    return match.group(0) if match else None
