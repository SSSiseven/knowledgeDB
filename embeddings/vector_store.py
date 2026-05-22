"""ChromaDB 向量存储 — 管理 paper_chunks 和 paper_summaries 两个集合"""

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from config import CHROMA_DIR
from utils.logger import logger


class VectorStore:
    def __init__(self, persist_dir: str | None = None):
        persist_dir = persist_dir or str(CHROMA_DIR)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._ensure_collections()

    def _ensure_collections(self):
        """确保关键 collection 存在"""
        existing = self._client.list_collections()
        existing_names = [c.name for c in existing]

        if "paper_chunks" not in existing_names:
            self._client.create_collection(
                name="paper_chunks",
                metadata={"description": "论文分块文本，用于 RAG 检索", "hnsw:space": "cosine"},
            )
            logger.info("创建 ChromaDB 集合: paper_chunks")

        if "paper_summaries" not in existing_names:
            self._client.create_collection(
                name="paper_summaries",
                metadata={"description": "论文摘要，用于语义搜索", "hnsw:space": "cosine"},
            )
            logger.info("创建 ChromaDB 集合: paper_summaries")

        if "concepts" not in existing_names:
            self._client.create_collection(
                name="concepts",
                metadata={"description": "概念/知识点描述", "hnsw:space": "cosine"},
            )
            logger.info("创建 ChromaDB 集合: concepts")

    def get_collection(self, name: str):
        return self._client.get_collection(name)

    # ─── paper_chunks ────────────────────────────────

    def add_chunks(self, paper_id: int, chunks: list[dict], embeddings: list[list[float]]):
        """批量添加论文分块及其向量"""
        if not chunks:
            return
        collection = self.get_collection("paper_chunks")
        ids = [f"paper_{paper_id}_chunk_{c['index']}" for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "paper_id": paper_id,
                "chunk_index": c["index"],
                "char_start": c["char_start"],
                "char_end": c["char_end"],
            }
            for c in chunks
        ]
        # 删除已有该论文的分块（避免重复）
        try:
            collection.delete(where={"paper_id": paper_id})
        except Exception:
            pass

        collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        logger.info(f"ChromaDB: 添加 paper_{paper_id} 的 {len(chunks)} 个分块")

    def search_chunks(self, query_embedding: list[float], n_results: int = 10,
                      paper_ids: list[int] | None = None) -> dict:
        """向量检索最相关的分块"""
        collection = self.get_collection("paper_chunks")
        where_filter = None
        if paper_ids:
            where_filter = {"paper_id": {"$in": paper_ids}}

        return collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

    # ─── paper_summaries ──────────────────────────────

    def add_summary(self, paper_id: int, summary: str, embedding: list[float]):
        """添加论文摘要向量"""
        collection = self.get_collection("paper_summaries")
        try:
            collection.delete(where={"paper_id": paper_id})
        except Exception:
            pass
        collection.add(
            ids=[f"paper_{paper_id}_summary"],
            documents=[summary],
            embeddings=[embedding],
            metadatas=[{"paper_id": paper_id}],
        )

    def search_summaries(self, query_embedding: list[float], n_results: int = 5) -> dict:
        collection = self.get_collection("paper_summaries")
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    # ─── concepts ─────────────────────────────────────

    def add_concept(self, concept_id: int, name: str, description: str, embedding: list[float]):
        collection = self.get_collection("concepts")
        try:
            collection.delete(where={"concept_id": concept_id})
        except Exception:
            pass
        collection.add(
            ids=[f"concept_{concept_id}"],
            documents=[f"{name}: {description}"],
            embeddings=[embedding],
            metadatas=[{"concept_id": concept_id, "name": name}],
        )

    def search_concepts(self, query_embedding: list[float], n_results: int = 10) -> dict:
        collection = self.get_collection("concepts")
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    # ─── 管理 ─────────────────────────────────────────

    def delete_paper(self, paper_id: int):
        """删除论文相关的所有向量"""
        for coll_name in ["paper_chunks", "paper_summaries"]:
            try:
                collection = self.get_collection(coll_name)
                collection.delete(where={"paper_id": paper_id})
            except Exception as e:
                logger.warning(f"删除向量失败 [{coll_name}]: {e}")

    def count(self, collection_name: str = "paper_chunks") -> int:
        try:
            return self.get_collection(collection_name).count()
        except Exception:
            return 0


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
