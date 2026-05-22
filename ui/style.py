"""学术期刊风格的全局 CSS"""

ACADEMIC_CSS = """
<style>
/* ============================================================
   KnowledgeDB — Academic Journal Theme
   ============================================================ */

/* ── 基础排版 ── */
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Serif SC', -apple-system, sans-serif;
    color: #2c2c2c;
}

/* 标题使用衬线字体 */
h1, h2, h3, h4, h5 {
    font-family: 'Source Serif 4', 'Noto Serif SC', 'Georgia', 'Times New Roman', serif !important;
    font-weight: 600 !important;
    color: #1a1a2e !important;
    letter-spacing: -0.01em;
}

h1 {
    font-size: 2.0rem !important;
    border-bottom: 2px solid #c4a35a;
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
}

h2 {
    font-size: 1.5rem !important;
    margin-top: 1.5rem;
}

h3 {
    font-size: 1.2rem !important;
    color: #2c3e50 !important;
}

/* ── 主背景 ── */
.main {
    background: linear-gradient(180deg, #fdfaf5 0%, #f8f4eb 100%);
}

.stApp {
    background: #faf8f2;
}

/* ── 侧边栏 ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-right: 3px solid #c4a35a;
}

[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #e8e0d5 !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #c4a35a !important;
    font-family: 'Source Serif 4', 'Georgia', serif !important;
}

[data-testid="stSidebar"] hr {
    border-color: #c4a35a44;
}

/* 侧边栏 metric */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: #ffffff10;
    border-radius: 4px;
    padding: 6px 4px;
    min-width: 55px;
}

[data-testid="stSidebar"] [data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.1rem !important;
    color: #e8e0d5 !important;
}

[data-testid="stSidebar"] [data-testid="stMetric"] label {
    color: #c4a35a !important;
    font-size: 0.82rem;
    letter-spacing: 0.04em;
    white-space: nowrap;
    overflow: visible;
}

/* 侧边栏 radio */
[data-testid="stSidebar"] .stRadio label {
    color: #e8e0d5 !important;
}

/* ── 卡片容器 ── */
[data-testid="stExpander"] {
    border: 1px solid #d4c9b5 !important;
    border-radius: 0 !important;
    background: #fefdf9 !important;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.05);
}

[data-testid="stExpander"] summary {
    font-family: 'Source Serif 4', 'Georgia', serif !important;
    color: #2c3e50 !important;
    border-bottom: 1px dotted #d4c9b5;
}

/* bordered container -> paper card */
[data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] {
    border: 1px solid #d4c9b5;
    border-radius: 2px;
    background: #fefdf9;
    padding: 1rem;
    margin-bottom: 0.8rem;
    box-shadow: 1px 1px 4px rgba(0,0,0,0.04);
    position: relative;
}

/* ── 按钮 ── */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    border-radius: 2px !important;
    border: 1px solid #8b7355 !important;
    background: #fdfaf5 !important;
    color: #4a3728 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em;
    transition: all 0.2s;
}

.stButton > button:hover {
    background: #4a3728 !important;
    color: #fdfaf5 !important;
    border-color: #4a3728 !important;
}

.stButton > button:active {
    background: #2c3e50 !important;
    border-color: #2c3e50 !important;
}

/* 主要按钮 */
.stButton > button[kind="primary"] {
    background: #1a1a2e !important;
    color: #c4a35a !important;
    border: 2px solid #c4a35a !important;
}

.stButton > button[kind="primary"]:hover {
    background: #c4a35a !important;
    color: #1a1a2e !important;
}

/* ── 输入框 ── */
.stTextInput > div > input,
.stTextArea textarea {
    border: 1px solid #c4b99a !important;
    border-radius: 2px !important;
    background: #fefdf9 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Select / MultiSelect ── */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    border-radius: 2px !important;
}

/* ── Metric ── */
[data-testid="stMetric"] {
    background: #fefdf9;
    border: 1px solid #e5ddcc;
    border-radius: 2px;
    padding: 8px 12px;
}

[data-testid="stMetric"] label {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.04em;
    color: #8b7355 !important;
    white-space: nowrap;
    overflow: visible;
}

/* ── Tabs ── */
.stTabs [role="tab"] {
    font-family: 'Source Serif 4', 'Georgia', serif !important;
    color: #8b7355 !important;
}

.stTabs [role="tab"][aria-selected="true"] {
    color: #1a1a2e !important;
    border-bottom: 2px solid #c4a35a !important;
}

/* ── 聊天消息 ── */
[data-testid="stChatMessage"] {
    background: #fefdf9 !important;
    border: 1px solid #e5ddcc !important;
    border-radius: 2px !important;
    padding: 12px 16px !important;
}

/* user message slight tint */
[data-testid="stChatMessage"][data-testid="stChatMessage"] {
    margin-bottom: 0.8rem;
}

/* ── Caption / small text ── */
.caption, small, [data-testid="stCaptionContainer"] {
    color: #8b7355 !important;
    font-size: 0.8rem !important;
}

/* ── Code / keywords ── */
code {
    background: #f0ebe0 !important;
    color: #4a3728 !important;
    border-radius: 2px !important;
    padding: 2px 6px !important;
    font-size: 0.85rem !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] {
    border-color: #c4a35a !important;
}

/* ── Warning / Info / Success ── */
[data-testid="stAlert"] {
    border-radius: 2px !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Radio (horizontal) ── */
.stRadio [role="radiogroup"] {
    gap: 1rem;
}

/* ── Divider ── */
hr {
    border-color: #d4c9b5 !important;
    margin: 1.5rem 0;
}

/* ── 页脚印记 ── */
footer:after {
    content: "KnowledgeDB · Academic Knowledge Base · Est. 2026";
    display: block;
    text-align: center;
    font-family: 'Source Serif 4', 'Georgia', serif;
    font-size: 0.75rem;
    color: #c4b99a;
    padding: 1rem;
}
</style>
"""


def inject_styles():
    """注入学术期刊风格 CSS"""
    import streamlit as st
    st.markdown(ACADEMIC_CSS, unsafe_allow_html=True)
