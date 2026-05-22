import streamlit as st


def render_ideas():
    st.title("💡 灵感板")
    st.info("🚧 该功能将在第四阶段上线")
    st.caption("基于已读论文的研究空白分析和灵感生成，支持：")
    st.markdown("""
    - 研究空白分析：孤立概念、矛盾结论、方法断裂
    - 灵感发散生成：具体的研究问题 + 解决思路
    - 可行性评估：低/中/高
    - 定期自动推送：每周一早上 9:00
    """)
