"""智能问答引擎 — 检索 + LLM 生成（支持 DeepSeek / Claude 可切换）"""

from llm.factory import get_llm
from .retriever import hybrid_search
from .prompts import (
    CHAT_SYSTEM, GENERAL_QA, CONCEPT_EXPLAIN,
    ALGORITHM_COMPARE, LITERATURE_REVIEW, RESEARCH_TREND, PAPER_CRITIQUE,
    PAPER_SUMMARY,
)
from utils.logger import logger


class QAEngine:
    def __init__(self):
        self.llm = get_llm()

    def answer(self, question: str, context_chunks: list[dict] = None,
               chat_history: list[dict] = None) -> str:
        """通用问答"""
        if context_chunks is None:
            context_chunks = hybrid_search(question, top_k=10)

        context = self._format_context(context_chunks)
        prompt = GENERAL_QA.format(context=context, question=question)
        return self.llm.chat([{"role": "user", "content": prompt}], system=CHAT_SYSTEM)

    def chat(self, question: str, chat_history: list[dict] = None) -> dict:
        """聊天接口（检索 + 生成），返回 {answer, sources}"""
        chunks = hybrid_search(question, top_k=8)
        context = self._format_context(chunks) if chunks else "知识库中暂无相关内容。"

        sources = []
        seen = set()
        for c in chunks:
            pid = c.get("paper_id")
            title = c.get("title", "")
            if pid and pid not in seen and title:
                seen.add(pid)
                sources.append({"paper_id": pid, "title": title, "arxiv_id": c.get("arxiv_id", "")})

        messages = list(chat_history) if chat_history else []
        prompt = GENERAL_QA.format(context=context, question=question)
        messages.append({"role": "user", "content": prompt})

        answer = self.llm.chat(messages, system=CHAT_SYSTEM)
        return {"answer": answer, "sources": sources}

    def explain_concept(self, concept: str) -> str:
        chunks = hybrid_search(concept, top_k=10)
        context = self._format_context(chunks)
        prompt = CONCEPT_EXPLAIN.format(concept=concept, context=context)
        return self.llm.chat([{"role": "user", "content": prompt}], system=CHAT_SYSTEM)

    def compare_algorithms(self, algo_a: str, algo_b: str) -> str:
        query = f"{algo_a} vs {algo_b} comparison"
        chunks = hybrid_search(query, top_k=10)
        context = self._format_context(chunks)
        prompt = ALGORITHM_COMPARE.format(algo_a=algo_a, algo_b=algo_b, context=context)
        return self.llm.chat([{"role": "user", "content": prompt}], system=CHAT_SYSTEM)

    def literature_review(self, topic: str) -> str:
        chunks = hybrid_search(topic, top_k=15)
        context = self._format_context(chunks)
        prompt = LITERATURE_REVIEW.format(topic=topic, context=context)
        return self.llm.chat([{"role": "user", "content": prompt}], system=CHAT_SYSTEM)

    def research_trend(self, topic: str) -> str:
        chunks = hybrid_search(topic, top_k=15)
        context = self._format_context(chunks)
        prompt = RESEARCH_TREND.format(topic=topic, context=context)
        return self.llm.chat([{"role": "user", "content": prompt}], system=CHAT_SYSTEM)

    def critique_paper(self, title: str, content: str) -> str:
        prompt = PAPER_CRITIQUE.format(title=title, content=content[:5000])
        return self.llm.chat([{"role": "user", "content": prompt}], system=CHAT_SYSTEM)

    def summarize_paper(self, title: str, abstract: str, content: str) -> str:
        prompt = PAPER_SUMMARY.format(title=title, abstract=abstract, content=content[:3000])
        return self.llm.chat([{"role": "user", "content": prompt}], system=CHAT_SYSTEM)

    def _format_context(self, chunks: list[dict]) -> str:
        if not chunks:
            return "暂无相关论文资料。"
        lines = []
        seen = set()
        for c in chunks:
            pid = c.get("paper_id", "?")
            title = c.get("title", "未知")
            text = c.get("chunk_text", "")[:500]
            key = f"{pid}_{c.get('chunk_index', '')}"
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"[论文 {pid}: {title}]\n{text}\n")
        return "\n".join(lines)


_qa_engine: QAEngine | None = None


def get_qa_engine() -> QAEngine:
    global _qa_engine
    if _qa_engine is None:
        _qa_engine = QAEngine()
    return _qa_engine
