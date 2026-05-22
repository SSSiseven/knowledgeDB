"""智能知识库问答系统 - 主入口"""

import streamlit as st

st.set_page_config(
    page_title="KnowledgeDB",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 注入学术期刊风格
from ui.style import inject_styles
inject_styles()

# 初始化 session state
if "current_page" not in st.session_state:
    st.session_state.current_page = "📖 论文库"
if "selected_paper_id" not in st.session_state:
    st.session_state.selected_paper_id = None
if "search_params" not in st.session_state:
    st.session_state.search_params = {
        "keyword": None, "status": None, "sort_by": "created_at", "sort_desc": True,
    }

from ui.components.sidebar import render_sidebar
from ui.pages.library import render_library
from ui.pages.reader import render_reader
from ui.pages.qa import render_qa
from ui.pages.graph import render_graph
from ui.pages.ideas import render_ideas
from ui.pages.recommend import render_recommend

# 侧边栏（内部会同步 session_state.current_page ↔ radio 状态）
page = render_sidebar()

# 路由到对应页面
page_routes = {
    "📖 论文库": render_library,
    "📄 阅读器": render_reader,
    "💬 智能问答": render_qa,
    "🕸️ 知识图谱": render_graph,
    "💡 灵感板": render_ideas,
    "🔍 论文推荐": render_recommend,
}

render_func = page_routes.get(st.session_state.current_page, render_library)
render_func()
