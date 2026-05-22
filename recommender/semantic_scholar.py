"""Semantic Scholar API — 获取引用量、热门论文"""

import time
import requests
from utils.logger import logger

BASE_URL = "https://api.semanticscholar.org/graph/v1"


def search_s2(query: str, limit: int = 10) -> list[dict]:
    """搜索 Semantic Scholar"""
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,externalIds,citationCount,venue",
    }
    try:
        resp = requests.get(f"{BASE_URL}/paper/search", params=params, timeout=30)
        if resp.status_code != 200:
            logger.error(f"S2 API 返回 {resp.status_code}")
            return []
        data = resp.json().get("data", [])
        return [_format_s2_result(p) for p in data]
    except Exception as e:
        logger.error(f"S2 搜索异常: {e}")
        return []


def get_paper_details(s2_id: str) -> dict | None:
    """获取单篇论文详情（含引用量）"""
    params = {"fields": "title,authors,year,abstract,externalIds,citationCount,venue"}
    try:
        resp = requests.get(f"{BASE_URL}/paper/{s2_id}", params=params, timeout=30)
        if resp.status_code == 200:
            return _format_s2_result(resp.json())
    except Exception as e:
        logger.error(f"S2 详情异常: {e}")
    return None


def get_hot_papers(topic: str = "multi-agent reinforcement learning", limit: int = 15) -> list[dict]:
    """获取热门高引论文"""
    papers = search_s2(topic, limit=limit * 2)
    # 按引用量排序
    papers.sort(key=lambda p: p.get("citations", 0), reverse=True)
    return papers[:limit]


def get_recent_high_impact(year_from: int = 2024, limit: int = 15) -> list[dict]:
    """获取近期高影响力论文"""
    params = {
        "query": "multi-agent reinforcement learning",
        "limit": limit * 2,
        "year": f"{year_from}-",
        "fields": "title,authors,year,abstract,externalIds,citationCount,venue",
        "sort": "citationCount:desc",
    }
    try:
        resp = requests.get(f"{BASE_URL}/paper/search", params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return [_format_s2_result(p) for p in data[:limit]]
    except Exception as e:
        logger.error(f"S2 高引异常: {e}")
    return []


def _format_s2_result(p: dict) -> dict:
    ext = p.get("externalIds", {}) or {}
    return {
        "s2_id": p.get("paperId", ""),
        "title": p.get("title", ""),
        "authors": [a.get("name", "") for a in (p.get("authors", []) or [])],
        "year": p.get("year"),
        "abstract": p.get("abstract", "") or "",
        "citations": p.get("citationCount", 0),
        "venue": (p.get("venue", {}) or {}).get("name", ""),
        "arxiv_id": ext.get("ArXiv", ""),
        "doi": ext.get("DOI", ""),
    }
