import streamlit as st


def render_graph():
    st.title("🕸️ 知识图谱")
    st.info("🚧 该功能将在第三阶段上线")
    st.caption("基于已读论文自动构建的知识网络，支持：")
    st.markdown("""
    - 概念节点：算法、方法、问题的关联关系
    - 论文引用链：追溯思想演进路径
    - 交互式探索：点击节点查看详情，按领域筛选
    - 研究脉络可视化：一目了然的领域全景
    """)
