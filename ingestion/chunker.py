"""文本分块 — 递归字符分割，适配 embedding 和 RAG 场景"""

import re
from config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list[str] | None = None,
) -> list[dict]:
    """递归字符分割文本。
    返回 [{"text": str, "index": int, "char_start": int, "char_end": int}, ...]
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", "。", " ", ""]

    chunks = []
    _recursive_split(text, separators, 0, chunk_size, chunk_overlap, 0, chunks)
    return chunks


def _recursive_split(
    text: str,
    separators: list[str],
    sep_index: int,
    chunk_size: int,
    chunk_overlap: int,
    char_offset: int,
    result: list[dict],
):
    if len(text) <= chunk_size:
        if text.strip():
            result.append({
                "text": text.strip(),
                "index": len(result),
                "char_start": char_offset,
                "char_end": char_offset + len(text),
            })
        return

    if sep_index >= len(separators):
        # 无法分割，强制按字符数切分
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
            # 保存当前块
            if current_chunk.strip():
                result.append({
                    "text": current_chunk.strip(),
                    "index": len(result),
                    "char_start": current_start,
                    "char_end": current_start + len(current_chunk),
                })
            # 处理剩余部分
            if len(part) > chunk_size:
                _recursive_split(
                    part,
                    separators,
                    sep_index + 1,
                    chunk_size,
                    chunk_overlap,
                    char_offset + len(text.split(part)[0]),
                    result,
                )
            else:
                current_chunk = part
                current_start = char_offset + len(text) - len(part)

    # 处理最后一块
    if current_chunk.strip():
        result.append({
            "text": current_chunk.strip(),
            "index": len(result),
            "char_start": current_start,
            "char_end": current_start + len(current_chunk),
        })


def _force_split(text: str, chunk_size: int, overlap: int, char_offset: int, result: list[dict]):
    """按固定字符数强制切分"""
    step = chunk_size - overlap
    if step <= 0:
        step = chunk_size

    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size]
        if chunk.strip():
            result.append({
                "text": chunk.strip(),
                "index": len(result),
                "char_start": char_offset + i,
                "char_end": char_offset + min(i + chunk_size, len(text)),
            })
