"""混合检索器 — 向量检索 + 关键词检索 + RRF 融合"""

from typing import Optional
from database.repository import PaperRepository
from embeddings.embedder import get_embedder
from embeddings.vector_store import get_vector_store
from utils.logger import logger


def hybrid_search(
    query: str,
    top_k: int = 10,
    paper_ids: list[int] | None = None,
    vector_weight: float = 0.7,
) -> list[dict]:
    """混合检索：向量语义检索 + SQLite 关键词检索 → RRF 融合排序。
    返回 [{"paper_id": int, "chunk_text": str, "score": float, "title": str}, ...]
    """
    embedder = get_embedder()
    vector_store = get_vector_store()

    # 1. 向量检索
    query_embedding = embedder.embed_query(query)
    vector_results = vector_store.search_chunks(
        query_embedding, n_results=top_k * 2, paper_ids=paper_ids
    )

    # 2. 关键词检索 (SQLite FTS-like)
    keyword_results = _keyword_search(query, top_k * 2, paper_ids)

    # 3. RRF 融合
    fused = _rrf_fusion(vector_results, keyword_results, vector_weight, top_k)

    # 4. 补充论文标题信息
    return _enrich_results(fused)


def _keyword_search(query: str, limit: int, paper_ids: list[int] | None) -> list[dict]:
    """SQLite 关键词搜索（使用 LIKE 近似全文搜索）"""
    with PaperRepository() as repo:
        papers = repo.list_papers(keyword=query, limit=limit)

    results = []
    for paper in papers:
        if paper_ids and paper.id not in paper_ids:
            continue
        results.append({
            "paper_id": paper.id,
            "chunk_text": paper.abstract or paper.title,
            "title": paper.title,
            "_source": "keyword",
        })
    return results


def _rrf_fusion(
    vector_results: dict,
    keyword_results: list[dict],
    vector_weight: float,
    top_k: int,
) -> list[dict]:
    """Reciprocal Rank Fusion 融合向量和关键词检索结果"""
    scores = {}  # key -> accumulated score
    docs = {}    # key -> doc info

    k = 60  # RRF 常数

    # 向量检索结果
    if vector_results and vector_results.get("ids"):
        ids0 = vector_results["ids"][0]
        docs0 = vector_results.get("documents", [[]])[0]
        metas0 = vector_results.get("metadatas", [[]])[0]
        for rank, (chunk_id, doc, meta) in enumerate(zip(ids0, docs0, metas0)):
            paper_id = meta.get("paper_id", 0)
            key = f"vec_{chunk_id}"
            scores[key] = scores.get(key, 0) + vector_weight / (k + rank + 1)
            docs[key] = {
                "paper_id": paper_id,
                "chunk_text": doc,
                "chunk_index": meta.get("chunk_index", 0),
            }

    # 关键词检索结果
    for rank, kw in enumerate(keyword_results):
        key = f"kw_{kw['paper_id']}"
        scores[key] = scores.get(key, 0) + (1 - vector_weight) / (k + rank + 1)
        docs[key] = {
            "paper_id": kw["paper_id"],
            "chunk_text": kw["chunk_text"],
            "title": kw.get("title", ""),
        }

    # 排序
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    results = []
    for key, score in sorted_items:
        if key in docs:
            doc = docs[key]
            doc["score"] = round(score, 4)
            results.append(doc)

    return results


def _enrich_results(results: list[dict]) -> list[dict]:
    """补充论文标题、作者等信息"""
    if not results:
        return results

    paper_ids = list(set(r["paper_id"] for r in results if r.get("paper_id")))
    if not paper_ids:
        return results

    with PaperRepository() as repo:
        papers = {p.id: p for p in [repo.get_paper(pid) for pid in paper_ids] if p}

    for r in results:
        pid = r.get("paper_id")
        if pid and pid in papers:
            r["title"] = r.get("title") or papers[pid].title
            r["arxiv_id"] = papers[pid].arxiv_id
            r["year"] = papers[pid].year

    return results


def search_papers_by_topic(query: str, top_k: int = 5) -> list[dict]:
    """按主题搜索论文（使用摘要向量检索）"""
    embedder = get_embedder()
    vector_store = get_vector_store()
    query_embedding = embedder.embed_query(query)

    results = vector_store.search_summaries(query_embedding, n_results=top_k)
    output = []
    if results and results.get("metadatas"):
        for meta_list, dist_list in zip(results["metadatas"], results["distances"]):
            for meta, dist in zip(meta_list, dist_list):
                pid = meta.get("paper_id")
                if pid:
                    with PaperRepository() as repo:
                        paper = repo.get_paper(pid)
                    if paper:
                        output.append({
                            "paper_id": pid,
                            "title": paper.title,
                            "similarity": round(1 - dist, 4),
                            "year": paper.year,
                        })
    return output
