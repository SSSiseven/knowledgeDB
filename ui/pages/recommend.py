import streamlit as st
from database.connection import init_db
from database.repository import PaperRepository
from recommender.arxiv_fetcher import search_by_keywords, search_top_venues
from recommender.semantic_scholar import get_hot_papers, get_recent_high_impact
from recommender.ranker import rank_by_interest, generate_recommendation_reason
from ingestion.pipeline import ingest_from_arxiv


def render_recommend():
    st.title("🔍 论文推荐")

    init_db()

    # ─── 推荐策略选择 ───
    strategy = st.radio(
        "推荐策略",
        ["📖 基于阅读兴趣", "🔥 热点高引论文", "🏆 顶会最新", "🔑 关键词搜索"],
        horizontal=True,
        key="rec_strategy",
    )

    st.divider()

    if st.button("🚀 开始推荐", use_container_width=True, type="primary"):
        with st.spinner("正在搜索论文..."):
            if strategy == "📖 基于阅读兴趣":
                papers = _recommend_by_interest()
            elif strategy == "🔥 热点高引论文":
                papers = _recommend_hot()
            elif strategy == "🏆 顶会最新":
                papers = _recommend_top_venues()
            else:
                papers = _recommend_by_keywords()

            if papers:
                st.session_state.recommendations = papers
                st.success(f"找到 {len(papers)} 篇推荐论文")
            else:
                st.warning("未找到相关论文")
        st.rerun()

    # ─── 推荐结果 ───
    recs = st.session_state.get("recommendations", [])
    if not recs:
        # 从缓存加载
        with PaperRepository() as repo:
            cached = repo.list_recommendations(unread_only=True, limit=30)
        if cached:
            st.caption(f"之前的推荐（共 {len(cached)} 篇）")
            _render_rec_list(cached, cached_mode=True)
        else:
            st.info("🔍 选择一个推荐策略并点击「开始推荐」")
            st.caption("推荐策略说明：")
            st.markdown("""
            - **基于阅读兴趣**：根据你已读论文的概念和关键词推荐相似工作
            - **热点高引论文**：Semantic Scholar 高引用论文
            - **顶会最新**：NeurIPS/ICML/ICLR/AAAI/IJCAI/AAMAS 最新论文
            - **关键词搜索**：multi-agent RL, MARL, cooperation 等
            """)
    else:
        st.caption(f"搜索结果（共 {len(recs)} 篇）")
        _render_rec_list(recs, cached_mode=False)


def _render_rec_list(papers: list, cached_mode: bool):
    for i, p in enumerate(papers):
        if isinstance(p, dict):
            title = p.get("title", "")
            abstract = p.get("abstract", "")
            authors = p.get("authors", [])
            if isinstance(authors, str):
                authors = authors.split(", ")
            arxiv_id = p.get("arxiv_id", "")
            year = p.get("year", "")
            venue = p.get("venue", "")
            reason = p.get("reason", "")
            citations = p.get("citations", 0)
            score = p.get("relevance_score", 0)
        else:
            title = p.title
            abstract = p.abstract or ""
            authors = p.authors or ""
            arxiv_id = p.arxiv_id or ""
            year = p.year or ""
            venue = p.venue or ""
            reason = p.reason or ""
            citations = 0
            score = 0

        with st.container(border=True):
            st.markdown(f"**{i + 1}. {title[:120]}**")

            meta_parts = []
            if authors:
                if isinstance(authors, list):
                    meta_parts.append(", ".join(authors[:3]))
                else:
                    meta_parts.append(str(authors)[:60])
            if year:
                meta_parts.append(str(year))
            if venue:
                meta_parts.append(venue)
            if citations:
                meta_parts.append(f"引用: {citations}")
            if score:
                meta_parts.append(f"相关度: {score}")
            st.caption(" · ".join(str(m) for m in meta_parts))

            if reason:
                st.caption(f"💡 {reason}")

            with st.expander("摘要"):
                st.text(abstract[:500] if abstract else "无摘要")

            # 一键导入
            if arxiv_id:
                if st.button(f"📥 导入此论文", key=f"import_{arxiv_id}_{i}",
                             use_container_width=True):
                    with st.spinner(f"正在下载并导入 {arxiv_id}..."):
                        paper_id = ingest_from_arxiv(arxiv_id)
                    if paper_id:
                        st.success(f"已导入! (ID: {paper_id})")
                        if cached_mode:
                            with PaperRepository() as repo:
                                repo.mark_recommendation_read(p.id)
                        st.rerun()
                    else:
                        st.error("导入失败")


def _recommend_by_interest() -> list[dict]:
    from recommender.ranker import _get_user_concepts, _get_user_keywords
    concepts = _get_user_concepts()
    if not concepts:
        st.warning("知识库中还没有论文概念，请先导入论文并提取概念")
        return []
    top_concept = max(concepts, key=concepts.get)
    papers = search_by_keywords(
        keywords=list(concepts.keys())[:5] + _get_user_keywords(),
        max_per_keyword=5,
    )
    return rank_by_interest(papers, top_k=20)


def _recommend_hot() -> list[dict]:
    return get_hot_papers("multi-agent reinforcement learning", limit=20)


def _recommend_top_venues() -> list[dict]:
    papers = search_top_venues()
    return rank_by_interest(papers, top_k=20)


def _recommend_by_keywords() -> list[dict]:
    papers = search_by_keywords(max_per_keyword=5)
    return rank_by_interest(papers, top_k=20)
