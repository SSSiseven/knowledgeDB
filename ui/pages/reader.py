import json
import streamlit as st
from pathlib import Path
from database.repository import PaperRepository
from database.connection import init_db


def render_reader():
    st.title("📄 论文阅读器")

    init_db()

    # 选择论文
    paper_id = st.session_state.get("selected_paper_id")

    if not paper_id:
        # 让用户选择一篇论文
        with PaperRepository() as repo:
            papers = repo.list_papers(limit=200)
        if not papers:
            st.info("论文库为空，请先去论文库导入论文")
            return

        paper_options = {f"[{p.id}] {p.title[:80]}": p.id for p in papers}
        selected = st.selectbox("选择论文", list(paper_options.keys()))
        if selected:
            paper_id = paper_options[selected]
            st.session_state.selected_paper_id = paper_id

    if not paper_id:
        return

    # 获取论文详情
    with PaperRepository() as repo:
        paper = repo.get_paper(paper_id)

    if not paper:
        st.error("论文不存在")
        st.session_state.selected_paper_id = None
        return

    # ─── 论文信息头部 ───
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"## {paper.title}")

        try:
            authors = json.loads(paper.authors) if paper.authors else []
            st.caption(", ".join(authors))
        except (json.JSONDecodeError, TypeError):
            st.caption(paper.authors or "")

        meta = []
        if paper.year:
            meta.append(str(paper.year))
        if paper.venue:
            meta.append(paper.venue)
        if paper.arxiv_id:
            meta.append(f"[arXiv:{paper.arxiv_id}](https://arxiv.org/abs/{paper.arxiv_id})")
        if paper.doi:
            meta.append(f"[DOI:{paper.doi}](https://doi.org/{paper.doi})")
        st.caption(" · ".join(meta))

    with col2:
        # 状态管理
        new_status = st.selectbox(
            "阅读状态",
            ["unread", "reading", "read"],
            index=["unread", "reading", "read"].index(paper.status),
            format_func=lambda x: {"unread": "⬜ 未读", "reading": "📖 在读", "read": "✅ 已读"}.get(x, x),
            key=f"status_{paper_id}",
        )

        if new_status != paper.status:
            with PaperRepository() as repo:
                repo.update_paper(paper_id, status=new_status)
            st.rerun()

        new_rating = st.slider(
            "评分", 0, 5, paper.rating or 0,
            key=f"rating_{paper_id}",
            help="1-5 星评分",
        )
        if new_rating != paper.rating:
            with PaperRepository() as repo:
                repo.update_paper(paper_id, rating=new_rating)
            st.rerun()

        # 阅读进度
        new_progress = st.slider(
            "阅读进度", 0.0, 1.0, paper.reading_progress or 0.0, 0.05,
            key=f"progress_{paper_id}",
        )
        if new_progress != paper.reading_progress:
            with PaperRepository() as repo:
                repo.update_paper(paper_id, reading_progress=new_progress)
            st.rerun()

    st.divider()

    # ─── Tab 页：摘要 / PDF / 笔记 ───
    tab_abstract, tab_pdf, tab_notes = st.tabs(["📋 摘要", "📄 PDF 预览", "📝 笔记"])

    with tab_abstract:
        if paper.abstract:
            st.markdown("### 摘要")
            st.write(paper.abstract)
        else:
            st.info("无摘要信息")

        if paper.summary:
            st.markdown("### AI 生成总结")
            st.write(paper.summary)
        else:
            if st.button("🤖 生成 AI 总结", use_container_width=True):
                with st.spinner("正在调用 AI 生成总结..."):
                    _generate_summary(paper)
                st.rerun()

        # 关键词
        try:
            keywords = json.loads(paper.keywords) if paper.keywords else []
            if keywords:
                st.markdown("### 关键词")
                st.write(" ".join([f"`{kw}`" for kw in keywords]))
        except (json.JSONDecodeError, TypeError):
            pass

    with tab_pdf:
        if paper.file_path:
            pdf_path = Path(paper.file_path)
            if pdf_path.exists():
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                col_dl, col_open = st.columns([1, 1])
                with col_dl:
                    st.download_button(
                        "📥 下载 PDF",
                        data=pdf_bytes,
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        use_container_width=True,
                    )
                with col_open:
                    if st.button("📂 系统查看器打开", use_container_width=True):
                        import os
                        os.startfile(str(pdf_path))

                # 文本预览（缓存避免重复提取）
                st.divider()
                st.caption("文本预览")

                @st.cache_data(show_spinner=False)
                def get_preview_text(file_path):
                    from ingestion.pdf_parser import extract_text
                    text, _ = extract_text(file_path)
                    return text

                preview_text = get_preview_text(str(pdf_path))
                st.text_area(
                    "全文内容",
                    value=preview_text,
                    height=600,
                    disabled=True,
                    label_visibility="collapsed",
                )
            else:
                st.warning("PDF 文件不存在于本地")
        else:
            st.info("无 PDF 文件")

    with tab_notes:
        _render_notes(paper_id)

    # ─── 返回按钮 ───
    if st.button("⬅ 返回论文库", use_container_width=True):
        st.session_state.selected_paper_id = None
        st.session_state.current_page = "📖 论文库"
        st.rerun()


def _render_notes(paper_id: int):
    """渲染笔记区域"""
    st.markdown("### 阅读笔记")

    # 显示已有笔记
    with PaperRepository() as repo:
        logs = repo.get_reading_logs(paper_id)

    if logs:
        for log in logs:
            with st.container(border=True):
                st.caption(f"{log.date.strftime('%Y-%m-%d %H:%M') if log.date else ''}")
                if log.key_points:
                    st.markdown(f"**要点:** {log.key_points}")
                if log.notes:
                    st.text(log.notes)

    st.divider()

    # 添加新笔记
    with st.form("add_note_form", clear_on_submit=True):
        key_points = st.text_input("核心要点（一句话总结）", key="note_key_points")
        notes = st.text_area("详细笔记", height=150, key="note_text")
        submitted = st.form_submit_button("💾 保存笔记", use_container_width=True)

        if submitted:
            with PaperRepository() as repo:
                repo.add_reading_log(paper_id, notes=notes, key_points=key_points)
            st.success("笔记已保存")
            st.rerun()


def _generate_summary(paper):
    """用 LLM 生成论文总结"""
    from llm.factory import get_llm
    from rag.prompts import PAPER_SUMMARY, CHAT_SYSTEM
    from ingestion.pdf_parser import extract_text_from_first_pages
    from pathlib import Path

    if paper.file_path and Path(paper.file_path).exists():
        text = extract_text_from_first_pages(paper.file_path, num_pages=5)
    elif paper.abstract:
        text = paper.abstract
    else:
        with PaperRepository() as repo:
            repo.update_paper(paper.id, summary="无法提取文本内容")
        return

    llm = get_llm()
    prompt = PAPER_SUMMARY.format(
        title=paper.title,
        abstract=paper.abstract or "",
        content=text[:3000],
    )
    try:
        summary = llm.chat([{"role": "user", "content": prompt}], system=CHAT_SYSTEM)
        with PaperRepository() as repo:
            repo.update_paper(paper.id, summary=summary)
    except Exception as e:
        with PaperRepository() as repo:
            repo.update_paper(paper.id, summary=f"生成失败: {e}")
