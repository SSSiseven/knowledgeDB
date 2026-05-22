"""Embedding 模型封装 — 本地 sentence-transformers 模型"""

import os
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, EMBEDDING_DEVICE
from utils.logger import logger


class Embedder:
    def __init__(self, model_name: str | None = None, device: str | None = None):
        self.model_name = model_name or EMBEDDING_MODEL
        self.device = device or EMBEDDING_DEVICE
        self._model: SentenceTransformer | None = None
        self._load_error: str | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None and self._load_error is None:
            try:
                logger.info(f"加载 embedding 模型: {self.model_name}")
                # 优先使用 HF 镜像（国内用户）
                if os.getenv("HF_ENDPOINT"):
                    logger.info(f"使用 HF 镜像: {os.getenv('HF_ENDPOINT')}")
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                    trust_remote_code=True,
                )
                logger.info("Embedding 模型加载完成")
            except Exception as e:
                self._load_error = str(e)
                raise RuntimeError(
                    f"无法加载 embedding 模型。请设置 HF 镜像后重试：\n"
                    f"  set HF_ENDPOINT=https://hf-mirror.com\n"
                    f"  原因: {e}"
                )
        if self._model is None:
            raise RuntimeError(f"Embedding 模型未加载: {self._load_error}")
        return self._model

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """生成文本 embedding"""
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 10,
            batch_size=32,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """生成查询 embedding（单条）"""
        return self.embed([text])[0]


# 全局单例（延迟加载）
_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
