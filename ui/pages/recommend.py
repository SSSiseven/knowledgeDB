import streamlit as st


def render_recommend():
    st.title("🔍 论文推荐")
    st.info("🚧 该功能将在第四阶段上线")
    st.caption("arXiv + Semantic Scholar 智能论文推荐，支持：")
    st.markdown("""
    - 基于阅读历史：根据你读过的论文推荐相似工作
    - 顶会追踪：NeurIPS, ICML, ICLR, AAAI, IJCAI, AAMAS 最新论文
    - 关键词订阅：multi-agent RL, MARL, cooperation 等
    - 热点排序：按引用量和关注度排序
    """)
