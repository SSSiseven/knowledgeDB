"""研究空白分析 — 从已读论文中找研究机会"""

from database.repository import PaperRepository
from llm.factory import get_llm
from .prompts import GAP_ANALYSIS
from utils.logger import logger


def analyze_gaps() -> str:
    """分析当前知识库中的研究空白。返回分析文本。"""
    # 收集所有论文和概念
    papers_info = []
    with PaperRepository() as repo:
        papers = repo.list_papers(limit=200)

    if not papers:
        return "知识库中还没有论文，无法进行分析。请先导入论文。"

    for p in papers:
        concepts_str = ""
        try:
            with PaperRepository() as repo:
                pcs = repo.get_paper_concepts(p.id)
                concepts_str = ", ".join(
                    [pc.concept.name for pc in pcs if pc.concept][:5]
                )
        except Exception:
            pass

        papers_info.append(
            f"[{p.id}] {p.title}\n"
            f"  摘要: {(p.abstract or '')[:200]}\n"
            f"  概念: {concepts_str or '未提取'}"
        )

    papers_text = "\n\n".join(papers_info[:20])  # 最多 20 篇
    prompt = GAP_ANALYSIS.format(papers_summary=papers_text)

    llm = get_llm()
    result = llm.chat([{"role": "user", "content": prompt}], max_tokens=4096)
    logger.info("研究空白分析完成")
    return result


def get_papers_summary() -> str:
    """获取知识库概览（用于发给 LLM 的上下文）"""
    with PaperRepository() as repo:
        papers = repo.list_papers(limit=100)

    if not papers:
        return "知识库为空"

    lines = []
    for p in papers[:30]:
        try:
            with PaperRepository() as repo:
                pcs = repo.get_paper_concepts(p.id)
                concepts_str = ", ".join(
                    [pc.concept.name for pc in pcs if pc.concept][:5]
                )
        except Exception:
            concepts_str = ""

        lines.append(
            f"[{p.id}] {p.title} ({p.year or '?'})\n"
            f"  concepts: {concepts_str or 'N/A'}"
        )

    return "\n".join(lines)
