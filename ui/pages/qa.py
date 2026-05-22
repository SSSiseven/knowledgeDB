import streamlit as st
from database.connection import init_db
from rag.qa_engine import get_qa_engine
from utils.logger import logger


def render_qa():
    st.title("💬 智能问答")

    init_db()

    # 初始化聊天历史
    if "qa_messages" not in st.session_state:
        st.session_state.qa_messages = []

    # ─── 快捷提问 ───
    st.caption("💡 快捷提问")
    quick_cols = st.columns(4)
    quick_questions = [
        "什么是 CTDE（集中训练分布执行）？",
        "QMIX 和 VDN 的区别是什么？",
        "MARL 中通信机制的发展脉络",
        "多智能体协作方向的未来趋势",
    ]
    for col, q in zip(quick_cols, quick_questions):
        if col.button(q, key=f"quick_{q[:15]}", use_container_width=True):
            st.session_state.qa_messages.append({"role": "user", "content": q})
            _generate_response(q)
            st.rerun()

    # ─── 功能按钮行 ───
    feat_col1, feat_col2, feat_col3, feat_col4 = st.columns(4)
    with feat_col1:
        if st.button("📖 概念解释", use_container_width=True):
            concept = st.session_state.get("concept_input", "")
            if concept:
                _handle_concept_explain(concept)
                st.rerun()
    with feat_col2:
        if st.button("⚖️ 算法对比", use_container_width=True):
            algo_input = st.session_state.get("algo_compare_input", "")
            if algo_input:
                _handle_algo_compare(algo_input)
                st.rerun()
    with feat_col3:
        if st.button("📝 文献综述", use_container_width=True):
            topic = st.session_state.get("review_topic_input", "")
            if topic:
                _handle_literature_review(topic)
                st.rerun()
    with feat_col4:
        if st.button("🔮 研究趋势", use_container_width=True):
            topic = st.session_state.get("trend_topic_input", "")
            if topic:
                _handle_trend(topic)
                st.rerun()

    st.divider()

    # ─── 聊天消息展示 ───
    for msg in st.session_state.qa_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("sources"):
                with st.expander("📚 参考来源", expanded=False):
                    for src in msg["sources"]:
                        arxiv_link = f"https://arxiv.org/abs/{src['arxiv_id']}" if src.get("arxiv_id") else ""
                        st.caption(f"📄 [{src['title'][:80]}]({arxiv_link})")

    # ─── 输入区域 ───
    if prompt := st.chat_input("输入你的问题，基于知识库回答...", key="qa_chat_input"):
        st.session_state.qa_messages.append({"role": "user", "content": prompt})
        _generate_response(prompt)
        st.rerun()

    # ─── 清空按钮 ───
    if st.session_state.qa_messages and st.sidebar.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.qa_messages = []
        st.rerun()


def _generate_response(prompt: str):
    try:
        qa = get_qa_engine()
        with st.spinner("正在检索知识库并生成回答..."):
            # 构建聊天历史（最近10轮）
            history = []
            for msg in st.session_state.qa_messages[-20:-1]:  # 排除当前消息
                history.append({"role": msg["role"], "content": msg["content"]})

            result = qa.chat(prompt, chat_history=history if history else None)

        st.session_state.qa_messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("sources", []),
        })
    except Exception as e:
        logger.error(f"问答失败: {e}")
        st.session_state.qa_messages.append({
            "role": "assistant",
            "content": f"抱歉，问答生成失败: {str(e)}",
            "sources": [],
        })


def _handle_concept_explain(concept: str):
    try:
        qa = get_qa_engine()
        with st.spinner(f"正在解释概念: {concept}..."):
            answer = qa.explain_concept(concept)
        st.session_state.qa_messages.append({"role": "user", "content": f"请解释概念: {concept}"})
        st.session_state.qa_messages.append({"role": "assistant", "content": answer, "sources": []})
    except Exception as e:
        st.error(f"生成失败: {e}")


def _handle_algo_compare(input_str: str):
    parts = [p.strip() for p in input_str.split("vs")]
    if len(parts) < 2:
        st.warning("请输入两个算法，用 'vs' 分隔，如 'QMIX vs VDN'")
        return
    try:
        qa = get_qa_engine()
        with st.spinner(f"正在对比 {parts[0]} 和 {parts[1]}..."):
            answer = qa.compare_algorithms(parts[0], parts[1])
        st.session_state.qa_messages.append({"role": "user", "content": f"对比 {parts[0]} 和 {parts[1]}"})
        st.session_state.qa_messages.append({"role": "assistant", "content": answer, "sources": []})
    except Exception as e:
        st.error(f"生成失败: {e}")


def _handle_literature_review(topic: str):
    try:
        qa = get_qa_engine()
        with st.spinner(f"正在综述: {topic}..."):
            answer = qa.literature_review(topic)
        st.session_state.qa_messages.append({"role": "user", "content": f"请综述「{topic}」方向的研究现状"})
        st.session_state.qa_messages.append({"role": "assistant", "content": answer, "sources": []})
    except Exception as e:
        st.error(f"生成失败: {e}")


def _handle_trend(topic: str):
    try:
        qa = get_qa_engine()
        with st.spinner(f"正在分析趋势: {topic}..."):
            answer = qa.research_trend(topic)
        st.session_state.qa_messages.append({"role": "user", "content": f"请分析「{topic}」的研究趋势"})
        st.session_state.qa_messages.append({"role": "assistant", "content": answer, "sources": []})
    except Exception as e:
        st.error(f"生成失败: {e}")
