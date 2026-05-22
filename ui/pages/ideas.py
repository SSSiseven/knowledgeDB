import streamlit as st
from database.connection import init_db
from database.repository import PaperRepository
from idea_generator.gap_analyzer import analyze_gaps
from idea_generator.brainstormer import generate_ideas


def render_ideas():
    st.title("💡 灵感板")

    init_db()

    # ─── 操作区 ───
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔍 研究空白分析", use_container_width=True,
                      help="分析知识库中论文的研究空白、矛盾点、方法断裂"):
            with st.spinner("正在分析研究空白..."):
                gap_result = analyze_gaps()
                st.session_state.gap_result = gap_result
            st.rerun()
    with col2:
        if st.button("💡 生成灵感", use_container_width=True,
                      help="基于空白分析生成具体的研究 idea"):
            with PaperRepository() as repo:
                paper_count = repo.count_papers()
            if paper_count == 0:
                st.warning("请先导入论文")
                return
            with st.spinner("正在生成灵感（可能需要 1-2 分钟）..."):
                ideas = generate_ideas(save=True)
                st.session_state.generated_ideas = ideas
            st.rerun()
    with col3:
        if st.button("🗑️ 清空灵感", use_container_width=True):
            st.session_state.gap_result = None
            st.session_state.generated_ideas = None
            st.rerun()

    st.divider()

    # ─── 空白分析展示 ───
    if st.session_state.get("gap_result"):
        with st.expander("🔍 研究空白分析报告", expanded=True):
            st.markdown(st.session_state.gap_result)

    # ─── 灵感列表 ───
    ideas = st.session_state.get("generated_ideas")
    if not ideas:
        # 从数据库加载已有灵感
        with PaperRepository() as repo:
            db_ideas = repo.list_ideas(limit=30)
        if db_ideas:
            st.caption(f"已保存的灵感（共 {len(db_ideas)} 个）")
            _render_idea_list(db_ideas)
        else:
            st.info("💡 还没有灵感，点击「生成灵感」基于你的论文库发散研究 idea")
            st.caption("灵感生成流程：空白分析 → 头脑风暴 → 生成具体研究问题和方法思路")
    else:
        st.caption(f"本次生成 {len(ideas)} 个灵感")
        _render_idea_list(ideas)


def _render_idea_list(ideas: list):
    for i, idea in enumerate(ideas):
        # 兼容 dict 和 ORM 对象
        if isinstance(idea, dict):
            title = idea.get("title", f"Idea {i+1}")
            desc = idea.get("description", "")
            status = idea.get("status", "draft")
            idea_id = idea.get("id")
        else:
            title = idea.title
            desc = idea.description or ""
            status = idea.status
            idea_id = idea.id

        with st.container(border=True):
            col_title, col_status = st.columns([4, 1])
            with col_title:
                st.markdown(f"**{i + 1}. {title}**")
            with col_status:
                status_labels = {
                    "draft": "📝 草稿", "developing": "🔬 探索中",
                    "abandoned": "❌ 放弃", "implemented": "✅ 已实现"}
                st.caption(status_labels.get(status, status))

            with st.expander("详情", expanded=i < 3):
                st.markdown(desc[:3000])

            if idea_id:
                c1, c2, c3 = st.columns(3)
                new_status = c1.selectbox(
                    "状态", ["draft", "developing", "abandoned", "implemented"],
                    index=["draft", "developing", "abandoned", "implemented"].index(status),
                    key=f"idea_status_{idea_id}",
                    label_visibility="collapsed",
                )
                if new_status != status:
                    with PaperRepository() as repo:
                        repo.update_idea(idea_id, status=new_status)
                    st.rerun()
