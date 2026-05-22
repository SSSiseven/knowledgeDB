"""元数据获取 — 综合 arXiv API、Semantic Scholar API 和 LLM 推断"""

import json
import re
from utils.logger import logger


def extract_arxiv_id_from_text(text: str) -> str | None:
    """从论文文本中尝试提取 arXiv ID"""
    patterns = [
        r"arXiv:\s*(\d{4}\.\d{4,5})",
        r"arxiv\.org/abs/(\d{4}\.\d{4,5})",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_doi_from_text(text: str) -> str | None:
    """从论文文本中尝试提取 DOI"""
    match = re.search(r"10\.\d{4,}/[^\s\"]+", text)
    return match.group(0).rstrip(".") if match else None


def extract_title_from_text(text: str) -> str:
    """从 PDF 第一页文本中通过模式匹配提取标题。
    论文标题通常是第一页最上方的大字体文本，位于作者之前。
    """
    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 5]
    # 跳过明显的元数据行
    skip_patterns = [
        r"^arXiv:", r"^http", r"^DOI:", r"^\d+$", r"^Submitted",
        r"^©", r"^Copyright", r"^Published", r"^\d{1,2}\s+\w+\s+\d{4}",
        r"^[A-Z][a-z]+ \d{1,2}, \d{4}$",
    ]
    candidates = []
    for line in lines[:30]:
        if any(re.match(p, line) for p in skip_patterns):
            continue
        # 标题：较长的英文/中文行，不大写全句
        if 15 < len(line) < 300:
            candidates.append(line)

    if candidates:
        return candidates[0]
    return ""


def fetch_metadata(arxiv_id: str = None, doi: str = None,
                   first_page_text: str = "", use_llm: bool = True) -> dict:
    """综合获取论文元数据。优先级:
    1. arXiv API（有 arxiv_id 时）
    2. PDF 文本正则提取标题（零 API 调用，不受限流影响）
    3. LLM 从文本推断（fallback）
    """
    metadata = {
        "title": "",
        "authors": [],
        "year": None,
        "venue": "",
        "venue_type": "unknown",
        "doi": doi or "",
        "arxiv_id": arxiv_id or "",
        "abstract": "",
    }

    # 优先用 arXiv API（可能因限流失败）
    if arxiv_id:
        from .arxiv_downloader import fetch_arxiv_metadata
        arxiv_data = fetch_arxiv_metadata(arxiv_id)
        if arxiv_data:
            metadata.update({
                "title": arxiv_data.get("title", ""),
                "authors": arxiv_data.get("authors", []),
                "year": arxiv_data.get("year"),
                "abstract": arxiv_data.get("abstract", ""),
                "arxiv_id": arxiv_id,
            })
            logger.info(f"arXiv API 元数据获取成功: {metadata['title'][:60]}")
            return metadata
        logger.warning("arXiv API 失败，尝试从 PDF 文本提取标题...")

    # Fallback: 从 PDF 第一页文本用正则提取标题
    if first_page_text and not metadata["title"]:
        extracted_title = extract_title_from_text(first_page_text)
        if extracted_title:
            metadata["title"] = extracted_title
            logger.info(f"从 PDF 文本提取标题: {extracted_title[:60]}")

    # 最后的 fallback: LLM 推断（需要 API Key）
    if not metadata["title"] and first_page_text and use_llm:
        try:
            inferred = infer_metadata_with_llm(first_page_text)
            if inferred.get("title"):
                metadata.update(inferred)
                logger.info(f"LLM 推断标题: {inferred['title'][:60]}")
        except Exception as e:
            logger.warning(f"LLM 推断失败: {e}")

    if not metadata["title"]:
        metadata["venue_type"] = "preprint"
        logger.warning("所有方式均无法获取标题")

    return metadata


def infer_metadata_with_llm(first_page_text: str) -> dict:
    """使用 LLM 从论文第一页文本推断元数据"""
    from llm.factory import get_llm

    llm = get_llm()
    prompt = f"""Extract the paper metadata from this first page text. Return ONLY a JSON object:

{{
    "title": "full paper title",
    "authors": ["Author Name 1", "Author Name 2"],
    "year": 2024,
    "abstract": "the abstract if present"
}}

Text:
{first_page_text[:3000]}"""

    try:
        resp = llm.chat([{"role": "user", "content": prompt}], max_tokens=1024)
        json_match = re.search(r"\{[\s\S]*\}", resp)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        logger.error(f"LLM 元数据推断失败: {e}")

    return {"title": "", "authors": [], "year": None, "abstract": ""}
