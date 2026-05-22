import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.title("📚 KnowledgeDB")
        st.caption("智能知识库问答系统")

        st.divider()

        # 导航菜单
        pages = ["📖 论文库", "📄 阅读器", "💬 智能问答", "🕸️ 知识图谱", "💡 灵感板", "🔍 论文推荐"]
        current = st.session_state.get("current_page", "📖 论文库")
        if current not in pages:
            current = "📖 论文库"

        page = st.radio(
            "导航",
            pages,
            index=pages.index(current),
            label_visibility="collapsed",
            key="nav_radio",
        )
        # 用户手动切换导航时同步到 session state
        if page != st.session_state.get("current_page"):
            st.session_state.current_page = page

        st.divider()

        # 统计信息（缓存 10 秒，避免每次渲染都查库）
        @st.cache_data(ttl=10, show_spinner=False)
        def get_stats():
            from database.connection import get_session
            from database.models import Paper, Idea, Recommendation
            s = get_session()
            try:
                return {
                    "paper_count": s.query(Paper).count(),
                    "unread": s.query(Paper).filter(Paper.status == "unread").count(),
                    "reading": s.query(Paper).filter(Paper.status == "reading").count(),
                    "read": s.query(Paper).filter(Paper.status == "read").count(),
                    "idea_count": s.query(Idea).count(),
                    "rec_count": s.query(Recommendation).filter(Recommendation.is_read == False).count(),
                }
            finally:
                s.close()

        try:
            stats = get_stats()
            st.metric("论文总数", stats["paper_count"])
            col1, col2, col3 = st.columns(3)
            col1.metric("未读", stats["unread"])
            col2.metric("在读", stats["reading"])
            col3.metric("已读", stats["read"])
            if stats["idea_count"] > 0:
                st.metric("灵感", stats["idea_count"])
            if stats["rec_count"] > 0:
                st.metric("待看推荐", stats["rec_count"])
        except Exception:
            pass

        st.divider()
        st.caption(f"研究方向：多智能体协作 & 强化学习")

    return page
