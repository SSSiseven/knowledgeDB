"""元数据获取 — 综合 arXiv API、Semantic Scholar API 和 Claude 推断"""

import json
import re
from utils.logger import logger
from .arxiv_downloader import fetch_arxiv_metadata


def extract_arxiv_id_from_text(text: str) -> str | None:
    """从论文文本中尝试提取 arXiv ID"""
    patterns = [
        r"arXiv:(\d{4}\.\d{4,5})",
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


def fetch_metadata(arxiv_id: str = None, doi: str = None, first_page_text: str = "") -> dict:
    """综合获取论文元数据。优先级:
    1. arXiv API（有 arxiv_id 时）
    2. Semantic Scholar API（有 DOI 时）
    3. Claude 从文本推断（fallback）
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

    # 优先用 arXiv API
    if arxiv_id:
        arxiv_data = fetch_arxiv_metadata(arxiv_id)
        if arxiv_data:
            metadata.update({
                "title": arxiv_data.get("title", metadata["title"]),
                "authors": arxiv_data.get("authors", metadata["authors"]),
                "year": arxiv_data.get("year", metadata["year"]),
                "abstract": arxiv_data.get("abstract", metadata["abstract"]),
                "arxiv_id": arxiv_id,
            })
            logger.info(f"arXiv API 元数据获取成功: {metadata['title'][:60]}...")
            return metadata

    # TODO: Semantic Scholar API fallback (Phase 4)
    # if doi:
    #     ...

    # 如果 API 都不可用，至少标记一下
    if not metadata["title"]:
        metadata["venue_type"] = "preprint"
        logger.warning("所有 API 都无法获取元数据，标题缺失")

    return metadata


def infer_metadata_with_claude(first_page_text: str, client=None) -> dict:
    """使用 Claude 从论文第一页文本推断元数据（标题、作者等）。
    这是最后的 fallback 方案。
    """
    if client is None:
        logger.warning("Claude 客户端未初始化，无法推断元数据")
        return {"title": "", "authors": [], "year": None, "abstract": ""}

    prompt = f"""You are a paper metadata extractor. Given the first page text of an academic paper, extract the following information in JSON format:

{{
    "title": "full paper title",
    "authors": ["Author Name 1", "Author Name 2"],
    "year": 2024,
    "abstract": "the abstract text"
}}

If you cannot determine something, use empty string or null for year.

Here is the paper text (first page):

{first_page_text[:4000]}

Return ONLY the JSON object, no other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        # 提取 JSON
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        logger.error(f"Claude 元数据推断失败: {e}")

    return {"title": "", "authors": [], "year": None, "abstract": ""}
