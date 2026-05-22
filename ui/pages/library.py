import json
import streamlit as st
from database.repository import PaperRepository
from database.connection import init_db
from ingestion.pipeline import ingest_pdf, ingest_from_arxiv
from ui.components.paper_card import paper_card


def render_library():
    st.title("📖 论文库")

    # 初始化数据库
    init_db()

    # ─── 顶部操作栏 ───
    tab_upload, tab_arxiv, tab_search = st.tabs(["📤 上传PDF", "🔗 arXiv链接", "🔍 搜索筛选"])

    with tab_upload:
        _render_upload()

    with tab_arxiv:
        _render_arxiv_import()

    with tab_search:
        _render_search()

    st.divider()

    # ─── 论文列表 ───
    _render_paper_list()


def _render_upload():
    uploaded_file = st.file_uploader(
        "选择 PDF 文件",
        type=["pdf"],
        accept_multiple_files=False,
        key="pdf_uploader",
        help="支持本地上传 PDF 论文，自动提取文本和元数据",
    )

    if uploaded_file:
        # 防止 Streamlit rerun 时重复处理同一个文件
        file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("last_uploaded") == file_key:
            st.success("✅ 论文摄入成功！")
            return

        import tempfile
        from pathlib import Path
        from config import PAPER_DIR

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=str(PAPER_DIR)) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        final_path = PAPER_DIR / uploaded_file.name
        if final_path.exists():
            final_path.unlink()
        Path(tmp_path).replace(final_path)

        with st.spinner(f"正在处理 {uploaded_file.name}..."):
            paper_id = ingest_pdf(str(final_path))

        if paper_id:
            st.session_state.last_uploaded = file_key
            st.success(f"✅ 论文摄入成功！ (ID: {paper_id})")
            st.rerun()
        else:
            st.error("摄入失败，请检查文件是否为有效 PDF")


def _render_arxiv_import():
    col1, col2 = st.columns([4, 1])
    with col1:
        arxiv_input = st.text_input(
            "输入 arXiv 链接或 ID",
            placeholder="https://arxiv.org/abs/2301.12345 或 2301.12345",
            key="arxiv_input",
        )
    with col2:
        import_btn = st.button("下载并导入", use_container_width=True, key="import_arxiv_btn")

    if import_btn and arxiv_input.strip():
        with st.spinner(f"正在下载并处理 {arxiv_input.strip()}..."):
            paper_id = ingest_from_arxiv(arxiv_input.strip())

        if paper_id:
            st.success(f"✅ 论文导入成功！ (ID: {paper_id})")
            st.rerun()
        else:
            st.error("导入失败，请检查 arXiv 链接是否正确")


def _render_search():
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        keyword = st.text_input("关键词搜索", placeholder="标题、作者、摘要...", key="search_keyword")

    with col2:
        status_filter = st.selectbox(
            "阅读状态",
            ["全部", "unread", "reading", "read"],
            format_func=lambda x: {"unread": "未读", "reading": "在读", "read": "已读"}.get(x, x),
            key="search_status",
        )

    with col3:
        sort_by = st.selectbox(
            "排序",
            ["created_at", "year", "title", "rating"],
            format_func=lambda x: {"created_at": "导入时间", "year": "年份", "title": "标题", "rating": "评分"}.get(x, x),
            key="search_sort",
        )

    with col4:
        sort_order = st.selectbox(
            "顺序",
            ["desc", "asc"],
            format_func=lambda x: "降序" if x == "desc" else "升序",
            key="search_order",
        )

    # 保存搜索条件
    st.session_state.search_params = {
        "keyword": keyword if keyword else None,
        "status": status_filter if status_filter != "全部" else None,
        "sort_by": sort_by,
        "sort_desc": sort_order == "desc",
    }


def _render_paper_list():
    # 获取搜索参数
    params = st.session_state.get("search_params", {
        "keyword": None, "status": None, "sort_by": "created_at", "sort_desc": True,
    })

    with PaperRepository() as repo:
        papers = repo.list_papers(
            status=params["status"],
            keyword=params["keyword"],
            sort_by=params["sort_by"],
            sort_desc=params["sort_desc"],
        )

    if not papers:
        st.info("📭 论文库是空的，上传你的第一篇论文吧！")
        st.caption("支持本地上传 PDF 或输入 arXiv 链接自动下载")
        return

    st.caption(f"共 {len(papers)} 篇论文")

    for paper in papers:
        paper_card(paper)
