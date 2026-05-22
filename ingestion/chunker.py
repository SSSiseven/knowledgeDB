"""语义分块 — 基于句子相似度的自适应文档分割

策略：
1. 先按 section 标题粗切（利用 pdf_parser 的章节检测结果）
2. 每节内做语义分块：
   a. 按句子初步分段
   b. 对每个句子向量化 (embedding)
   c. 滑动窗口计算相邻句子的余弦相似度
   d. 相似度显著低于滑动均值 → 断开，之前的句子合并为一个 chunk
   e. 最小 chunk 大小兜底，防止碎片化
"""

import re
import numpy as np
from config import CHUNK_SIZE, CHUNK_OVERLAP
from utils.logger import logger

# 语义分块参数
SEMANTIC_MIN_CHUNK_CHARS = 300     # 最小块大小（字符），低于此不单独成块
SEMANTIC_MAX_CHUNK_CHARS = 3000    # 最大块大小，超过强制断开
SIMILARITY_THRESHOLD_RATIO = 0.75  # 低于滑动均值 75% 视为断裂点
SMOOTHING_WINDOW = 5               # 相似度平滑窗口大小


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list[str] | None = None,
    use_semantic: bool = True,
) -> list[dict]:
    """分块入口。use_semantic=True 时使用语义分块，否则回退到递归字符分割。"""
    if not use_semantic:
        return _legacy_chunk(text, chunk_size, chunk_overlap, separators)
    return _semantic_chunk(text)


def _semantic_chunk(text: str) -> list[dict]:
    """语义分块主流程"""
    sentences = _split_sentences(text)
    if len(sentences) <= 5:
        # 太短不分，直接整块
        return [{"text": text.strip(), "index": 0, "char_start": 0, "char_end": len(text)}]

    # 向量化所有句子
    embeddings = _embed_sentences(sentences)
    if embeddings is None:
        logger.warning("语义分块失败，回退到固定大小分块")
        return _force_split(text, SEMANTIC_MAX_CHUNK_CHARS, CHUNK_OVERLAP, 0, [])

    # 计算相邻句子相似度
    similarities = _compute_similarities(embeddings)
    breakpoints = _detect_breakpoints(similarities, sentences)

    # 按断裂点合并句子为块
    chunks = _merge_sentences(sentences, breakpoints)

    # 后处理：最小块兜底 + 最大块截断
    chunks = _post_process(chunks)

    # 添加位置元数据
    return _add_position_metadata(chunks, text)


def _split_sentences(text: str) -> list[str]:
    """句子分割：处理中英文混排"""
    # 按常见句子边界切分
    pattern = re.compile(
        r'(?<=[.!?。！？\n])\s+(?=[A-Z一-鿿])|'  # 标点后的空白
        r'(?<=[.!?。！？])(?=[A-Z一-鿿])|'        # 标点直接跟大写/中文
        r'(?<=\w)(?=\n\n)|'                                # 段落边界
        r'(?<=\n)(?=[A-Z一-鿿])'                   # 换行后新句
    )
    parts = re.split(pattern, text)
    sentences = [s.strip() for s in parts if s.strip() and len(s.strip()) > 5]
    return sentences


def _embed_sentences(sentences: list[str]) -> list[list[float]] | None:
    """向量化所有句子"""
    try:
        from embeddings.embedder import get_embedder
        embedder = get_embedder()
        # 批量向量化
        return embedder.embed(sentences)
    except Exception as e:
        logger.error(f"句子向量化失败: {e}")
        return None


def _compute_similarities(embeddings: list[list[float]]) -> list[float]:
    """计算相邻句子的余弦相似度"""
    sims = []
    for i in range(len(embeddings) - 1):
        a = np.array(embeddings[i])
        b = np.array(embeddings[i + 1])
        # 余弦相似度（向量已归一化，直接点积即可）
        sim = float(np.dot(a, b))
        sims.append(max(0.0, sim))
    return sims


def _detect_breakpoints(similarities: list[float], sentences: list[str]) -> list[int]:
    """基于相似度滑动均值检测语义断裂点。
    返回断裂点索引列表（断裂点 i 表示 sentence[i] 和 sentence[i+1] 之间断开）
    """
    if not similarities:
        return []

    n = len(similarities)
    breakpoints = []
    # 滑动均值
    smoothed = []
    for i in range(n):
        start = max(0, i - SMOOTHING_WINDOW // 2)
        end = min(n, i + SMOOTHING_WINDOW // 2 + 1)
        smoothed.append(sum(similarities[start:end]) / (end - start))

    for i, sim in enumerate(similarities):
        mean = smoothed[i]
        if mean > 0 and sim < mean * SIMILARITY_THRESHOLD_RATIO:
            breakpoints.append(i)

    return breakpoints


def _merge_sentences(sentences: list[str], breakpoints: list[int]) -> list[str]:
    """按断裂点合并句子为块"""
    chunks = []
    start = 0
    for bp in sorted(breakpoints):
        chunk_text = " ".join(sentences[start:bp + 1])
        if chunk_text.strip():
            chunks.append(chunk_text.strip())
        start = bp + 1
    # 最后一块
    remaining = " ".join(sentences[start:])
    if remaining.strip():
        chunks.append(remaining.strip())
    return chunks


def _post_process(chunks: list[str]) -> list[str]:
    """后处理：最小块合并 + 最大块截断"""
    if not chunks:
        return chunks

    result = []
    buffer = ""

    for chunk in chunks:
        # 如果 buffer + 当前块 < 最小大小，继续合并
        if len(buffer) + len(chunk) < SEMANTIC_MIN_CHUNK_CHARS:
            buffer = (buffer + " " + chunk).strip() if buffer else chunk
            continue

        # buffer 够大了，输出
        if buffer:
            result.append(buffer)
            buffer = ""

        # 大块截断
        if len(chunk) > SEMANTIC_MAX_CHUNK_CHARS:
            sub_chunks = _force_split(
                chunk, SEMANTIC_MAX_CHUNK_CHARS,
                CHUNK_OVERLAP, 0, []
            )
            for sc in sub_chunks:
                result.append(sc["text"] if isinstance(sc, dict) else sc)
        else:
            buffer = chunk

    if buffer:
        result.append(buffer)

    # 最后检查：如果只有一个很小的块，不管了
    return [c for c in result if len(c) >= 10]


def _add_position_metadata(chunks: list[str], full_text: str) -> list[dict]:
    """为每个块添加在原文中的位置信息"""
    result = []
    pos = 0
    for i, chunk in enumerate(chunks):
        idx = full_text.find(chunk, pos)
        if idx < 0:
            idx = pos
        result.append({
            "text": chunk,
            "index": i,
            "char_start": idx,
            "char_end": idx + len(chunk),
        })
        pos = idx + len(chunk)
    return result


# ─── 回退方案：递归字符分割 ───

def _legacy_chunk(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str] | None,
) -> list[dict]:
    """递归字符分割（语义分块不可用时的 fallback）"""
    if separators is None:
        separators = ["\n\n", "\n", ". ", "。", " ", ""]
    chunks = []
    _recursive_split(text, separators, 0, chunk_size, chunk_overlap, 0, chunks)
    return chunks


def _recursive_split(
    text: str, separators: list[str], sep_index: int,
    chunk_size: int, chunk_overlap: int, char_offset: int, result: list[dict],
):
    if len(text) <= chunk_size:
        if text.strip():
            result.append({
                "text": text.strip(), "index": len(result),
                "char_start": char_offset, "char_end": char_offset + len(text),
            })
        return
    if sep_index >= len(separators):
        _force_split(text, chunk_size, chunk_overlap, char_offset, result)
        return
    separator = separators[sep_index]
    if separator == "":
        _force_split(text, chunk_size, chunk_overlap, char_offset, result)
        return
    splits = text.split(separator)
    current_chunk = ""
    current_start = char_offset
    for part in splits:
        candidate = current_chunk + (separator if current_chunk else "") + part
        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk.strip():
                result.append({
                    "text": current_chunk.strip(), "index": len(result),
                    "char_start": current_start,
                    "char_end": current_start + len(current_chunk),
                })
            if len(part) > chunk_size:
                _recursive_split(part, separators, sep_index + 1,
                                 chunk_size, chunk_overlap,
                                 char_offset + len(text.split(part)[0]), result)
            else:
                current_chunk = part
                current_start = char_offset + len(text) - len(part)
    if current_chunk.strip():
        result.append({
            "text": current_chunk.strip(), "index": len(result),
            "char_start": current_start,
            "char_end": current_start + len(current_chunk),
        })


def _force_split(text: str, chunk_size: int, overlap: int,
                 char_offset: int, result: list[dict]):
    step = max(chunk_size - overlap, 1)
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size]
        if chunk.strip():
            result.append({
                "text": chunk.strip(), "index": len(result),
                "char_start": char_offset + i,
                "char_end": char_offset + min(i + chunk_size, len(text)),
            })
    return result
