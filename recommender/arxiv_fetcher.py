"""arXiv API 论文搜索与获取"""

import time
import requests
import xml.etree.ElementTree as ET
from config import ARXIV_SEARCH_MAX_RESULTS, DEFAULT_KEYWORDS
from utils.logger import logger

BASE_URL = "https://export.arxiv.org/api/query"


def search_arxiv(
    query: str,
    max_results: int = ARXIV_SEARCH_MAX_RESULTS,
    start: int = 0,
    sort_by: str = "submittedDate",
    sort_order: str = "descending",
) -> list[dict]:
    """搜索 arXiv 论文。返回论文列表 [{"arxiv_id": ..., "title": ..., ...}]"""
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }
    time.sleep(1)  # 礼貌延迟

    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        if resp.status_code != 200:
            logger.error(f"arXiv API 返回 {resp.status_code}")
            return []
        return _parse_xml(resp.text)
    except Exception as e:
        logger.error(f"arXiv 搜索异常: {e}")
        return []


def search_by_keywords(
    keywords: list[str] = None,
    max_per_keyword: int = 5,
    recent_months: int = 3,
) -> list[dict]:
    """按关键词批量搜索，限制近期论文"""
    keywords = keywords or DEFAULT_KEYWORDS
    all_papers = {}
    seen = set()

    for kw in keywords[:6]:
        query = f"all:{kw}"
        papers = search_arxiv(query, max_results=max_per_keyword)
        for p in papers:
            if p["arxiv_id"] not in seen:
                seen.add(p["arxiv_id"])
                all_papers[p["arxiv_id"]] = p
        time.sleep(2)

    return list(all_papers.values())


def search_recent_by_venue(venue: str, year: int = 2025, max_results: int = 10) -> list[dict]:
    """搜索特定期刊/会议的近期论文"""
    query = f'all:"{venue}" AND submittedDate:[{year}0101 TO {year}1231]'
    return search_arxiv(query, max_results=max_results)


def search_top_venues() -> list[dict]:
    """搜索顶会近期论文"""
    from config import TOP_VENUES
    all_papers = {}
    seen = set()

    for venue in TOP_VENUES[:6]:
        papers = search_recent_by_venue(venue, max_results=3)
        for p in papers:
            if p["arxiv_id"] not in seen:
                seen.add(p["arxiv_id"])
                all_papers[p["arxiv_id"]] = p
        time.sleep(2)

    return list(all_papers.values())


def _parse_xml(xml_text: str) -> list[dict]:
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall("atom:entry", ns):
        arxiv_id_url = entry.find("atom:id", ns)
        arxiv_id = ""
        if arxiv_id_url is not None and arxiv_id_url.text:
            arxiv_id = arxiv_id_url.text.split("/abs/")[-1]

        title = entry.find("atom:title", ns)
        title_text = " ".join(title.text.split()) if title is not None and title.text else ""

        summary = entry.find("atom:summary", ns)
        summary_text = " ".join(summary.text.split()) if summary is not None and summary.text else ""

        authors = []
        for author in entry.findall("atom:author", ns):
            name = author.find("atom:name", ns)
            if name is not None and name.text:
                authors.append(name.text.strip())

        published = entry.find("atom:published", ns)
        year = int(published.text[:4]) if published is not None and published.text else None

        papers.append({
            "arxiv_id": arxiv_id,
            "title": title_text,
            "authors": authors,
            "year": year,
            "abstract": summary_text,
        })

    return papers
