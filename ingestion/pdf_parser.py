import fitz  # PyMuPDF
from pathlib import Path
from utils.logger import logger


def extract_text(file_path: str, preserve_structure: bool = True) -> tuple[str, dict]:
    """从 PDF 提取文本。
    返回 (full_text, metadata) — metadata 包含页数、章节信息等。
    """
    doc = fitz.open(file_path)
    metadata = {
        "page_count": len(doc),
        "sections": [],
    }

    # 尝试用 fitz metadata 获取标题
    doc_meta = doc.metadata
    if doc_meta.get("title"):
        metadata["pdf_title"] = doc_meta["title"]

    full_text_parts = []
    current_section = None
    section_start_page = 0

    for page_num, page in enumerate(doc):
        page_text = page.get_text("text")

        if preserve_structure and page_num == 0:
            # 尝试从第一页提取标题（通常字体更大）
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span["size"] > 14:  # 大字体 = 标题候选
                                candidate = span["text"].strip()
                                if len(candidate) > 10:
                                    metadata["detected_title"] = candidate
                                    break

        # 简单的章节检测：全大写 + 短行
        for line in page_text.split("\n"):
            stripped = line.strip()
            if stripped.isupper() and 5 < len(stripped) < 80 and not stripped.startswith("HTTP"):
                if current_section:
                    metadata["sections"].append({
                        "title": current_section,
                        "start_page": section_start_page,
                        "end_page": page_num,
                    })
                current_section = stripped
                section_start_page = page_num

        full_text_parts.append(page_text)

    # 记录最后一个章节
    if current_section:
        metadata["sections"].append({
            "title": current_section,
            "start_page": section_start_page,
            "end_page": len(doc) - 1,
        })

    doc.close()
    full_text = "\n\n".join(full_text_parts)
    return full_text, metadata


def extract_text_from_first_pages(file_path: str, num_pages: int = 3) -> str:
    """只提取前几页文本，用于快速分析（摘要、引言）"""
    doc = fitz.open(file_path)
    texts = []
    for page_num in range(min(num_pages, len(doc))):
        texts.append(doc[page_num].get_text("text"))
    doc.close()
    return "\n\n".join(texts)
