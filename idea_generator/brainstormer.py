"""灵感发散生成 — 基于空白分析生成具体研究 idea"""

import json
from database.repository import PaperRepository
from llm.factory import get_llm
from .prompts import BRAINSTORM
from .gap_analyzer import analyze_gaps, get_papers_summary
from utils.logger import logger


def generate_ideas(save: bool = True) -> list[dict]:
    """生成研究灵感。返回 idea 列表。"""
    # Step 1: 空白分析
    logger.info("步骤1: 研究空白分析...")
    gap_result = analyze_gaps()

    if gap_result.startswith("知识库中还没有论文"):
        return [{"title": "无法生成", "description": gap_result}]

    # Step 2: 获取论文摘要
    papers_summary = get_papers_summary()

    # Step 3: 头脑风暴
    logger.info("步骤2: 头脑风暴生成 idea...")
    prompt = BRAINSTORM.format(gap_analysis=gap_result, papers_summary=papers_summary)

    llm = get_llm()
    result = llm.chat([{"role": "user", "content": prompt}], max_tokens=4096)
    logger.info("灵感生成完成")

    # Step 4: 解析 idea 并保存
    ideas = _parse_ideas(result)
    if save and ideas:
        _save_ideas(ideas)

    return ideas


def _parse_ideas(text: str) -> list[dict]:
    """解析 LLM 生成的 idea 文本"""
    parts = text.split("---")
    ideas = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # 提取标题
        lines = part.strip().split("\n")
        title = ""
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("**") or stripped.startswith("#"):
                title = stripped.lstrip("#* ").strip()
            elif "标题" in stripped and ":" in stripped:
                title = stripped.split(":", 1)[1].strip().lstrip("* ")
            if title and len(title) > 5:
                break
        if not title:
            title = lines[0][:80] if lines else "未命名灵感"

        ideas.append({
            "title": title[:200],
            "description": part.strip()[:3000],
            "motivation": "",
        })
    return ideas


def _save_ideas(ideas: list[dict]):
    """保存灵感到数据库"""
    with PaperRepository() as repo:
        for idea in ideas:
            repo.add_idea(
                title=idea["title"],
                description=idea.get("description", ""),
                motivation=idea.get("motivation", ""),
            )
        repo.commit()
    logger.info(f"已保存 {len(ideas)} 个灵感")
