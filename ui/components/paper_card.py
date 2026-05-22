import streamlit as st
import json


def paper_card(paper, show_actions: bool = True):
    """渲染论文卡片"""
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"**{paper.title}**")

            # 作者
            try:
                authors = json.loads(paper.authors) if paper.authors else []
                author_str = ", ".join(authors[:5])
                if len(authors) > 5:
                    author_str += f" et al. ({len(authors)} authors)"
            except (json.JSONDecodeError, TypeError):
                author_str = paper.authors or ""

            if author_str:
                st.caption(author_str)

            # 元信息行
            meta_parts = []
            if paper.year:
                meta_parts.append(str(paper.year))
            if paper.venue:
                meta_parts.append(paper.venue)
            if paper.arxiv_id:
                meta_parts.append(f"arXiv:{paper.arxiv_id}")
            if meta_parts:
                st.caption(" · ".join(meta_parts))

        with col2:
            status_emoji = {"unread": "⬜", "reading": "📖", "read": "✅"}
            st.caption(f"{status_emoji.get(paper.status, '')} {paper.status}")
            if paper.rating:
                st.caption(f"{'⭐' * paper.rating}")

        # 摘要（折叠）
        if paper.abstract:
            with st.expander("摘要", expanded=False):
                st.text(paper.abstract[:500])

        # 关键词标签
        try:
            keywords = json.loads(paper.keywords) if paper.keywords else []
            if keywords:
                kw_str = " ".join([f"`{kw}`" for kw in keywords[:8]])
                st.caption(kw_str)
        except (json.JSONDecodeError, TypeError):
            pass

        # 操作按钮
        if show_actions:
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("📖 阅读", key=f"read_{paper.id}", use_container_width=True):
                st.session_state.selected_paper_id = paper.id
                st.session_state.current_page = "📄 阅读器"
                st.rerun()
            if c2.button("📝 笔记", key=f"note_{paper.id}", use_container_width=True):
                st.session_state.selected_paper_id = paper.id
                st.session_state.current_page = "📄 阅读器"
                st.session_state.show_note_editor = True
                st.rerun()
            if c3.button("✅ 已读", key=f"mark_read_{paper.id}", use_container_width=True):
                from database.repository import PaperRepository
                with PaperRepository() as repo:
                    repo.update_paper(paper.id, status="read")
                st.rerun()
            if c4.button("🗑️", key=f"del_{paper.id}", use_container_width=True):
                st.session_state[f"confirm_delete_{paper.id}"] = True
                st.rerun()

        # 删除确认
        if st.session_state.get(f"confirm_delete_{paper.id}", False):
            st.warning(f"确认删除「{paper.title[:50]}...」？")
            cy, cn = st.columns(2)
            if cy.button("确认删除", key=f"confirm_yes_{paper.id}"):
                from database.repository import PaperRepository
                from pathlib import Path
                with PaperRepository() as repo:
                    paper_to_del = repo.get_paper(paper.id)
                    if paper_to_del and paper_to_del.file_path:
                        pdf_path = Path(paper_to_del.file_path)
                        if pdf_path.exists():
                            pdf_path.unlink()
                    repo.delete_paper(paper.id)
                st.session_state.pop(f"confirm_delete_{paper.id}", None)
                st.rerun()
            if cn.button("取消", key=f"confirm_no_{paper.id}"):
                st.session_state.pop(f"confirm_delete_{paper.id}", None)
                st.rerun()
