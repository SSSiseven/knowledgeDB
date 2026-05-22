"""论文摄入管道 — 编排完整的 PDF → 知识库流程"""

import json
from pathlib import Path
from typing import Optional

from database.repository import PaperRepository
from .arxiv_downloader import download_pdf, parse_arxiv_id
from .pdf_decryptor import decrypt_pdf
from .pdf_parser import extract_text, extract_text_from_first_pages
from .metadata_fetcher import fetch_metadata, extract_arxiv_id_from_text, extract_doi_from_text
from .chunker import chunk_text
from utils.logger import logger


def ingest_pdf(file_path: str, status: str = "unread") -> Optional[int]:
    """摄入本地 PDF 文件。返回 paper_id 或 None。"""
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"文件不存在: {file_path}")
        return None

    # 检查是否已摄入（按文件路径查重）
    with PaperRepository() as repo:
        from database.connection import get_session
        from database.models import Paper
        s = get_session()
        try:
            existing = s.query(Paper).filter(Paper.file_path == str(file_path)).first()
            if existing:
                logger.info(f"论文已存在 (file): {file_path.name} -> ID={existing.id}")
                # 如果标题仍是文件名，尝试重新获取元数据
                if existing.title == file_path.stem:
                    _try_update_metadata(existing)
                return existing.id
        finally:
            s.close()

    logger.info(f"开始摄入: {file_path.name}")

    # Step 1: 解密 PDF（如果需要）
    working_path = str(file_path)
    decrypted_temp = None
    try:
        from .pdf_decryptor import is_pdf_encrypted
        if is_pdf_encrypted(working_path):
            logger.info(f"PDF 需要解密: {file_path.name}")
            decrypted_temp = decrypt_pdf(working_path)
            working_path = decrypted_temp
    except Exception as e:
        logger.warning(f"解密检测失败，尝试直接提取: {e}")

    # Step 2: 提取文本
    full_text, text_metadata = extract_text(working_path)
    logger.info(f"提取文本完成: {len(full_text)} 字符, {text_metadata['page_count']} 页")

    # Step 3: 提取前几页用于元数据获取
    first_pages_text = extract_text_from_first_pages(working_path, num_pages=2)

    # Step 4: 获取元数据
    arxiv_id = extract_arxiv_id_from_text(first_pages_text)
    doi = extract_doi_from_text(first_pages_text)
    metadata = fetch_metadata(arxiv_id=arxiv_id, doi=doi, first_page_text=first_pages_text)

    # Step 5: 存入数据库
    with PaperRepository() as repo:
        # 检查是否已存在
        if arxiv_id:
            existing = repo.get_paper_by_arxiv(arxiv_id)
            if existing:
                logger.info(f"论文已存在 (arXiv:{arxiv_id})，跳过")
                return existing.id
        if doi:
            existing = repo.get_paper_by_doi(doi)
            if existing:
                logger.info(f"论文已存在 (DOI:{doi})，跳过")
                return existing.id

        paper = repo.add_paper(
            title=metadata["title"] or file_path.stem,
            authors=json.dumps(metadata["authors"], ensure_ascii=False),
            year=metadata["year"],
            venue=metadata["venue"],
            venue_type=metadata["venue_type"],
            doi=metadata["doi"],
            arxiv_id=metadata["arxiv_id"],
            abstract=metadata["abstract"],
            file_path=str(file_path),
            status=status,
        )
        paper_id = paper.id
        logger.info(f"论文已入库: ID={paper_id}, 标题={metadata['title'][:60]}...")

    # Step 6: 分块 + 向量化
    chunks = chunk_text(full_text)
    logger.info(f"文本分块完成: {len(chunks)} chunks")
    _vectorize_paper(paper_id, chunks)

    # Step 7: 生成 AI 总结并向量化（异步，失败不影响主流程）
    try:
        _generate_and_index_summary(paper_id, full_text, metadata)
    except Exception as e:
        logger.warning(f"AI 总结生成失败: {e}")

    # Step 8: 清理临时解密文件
    if decrypted_temp and decrypted_temp != str(file_path):
        try:
            Path(decrypted_temp).unlink(missing_ok=True)
            logger.info(f"已清理临时解密文件: {decrypted_temp}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

    logger.info(f"摄入完成: paper_id={paper_id}")
    return paper_id


def ingest_from_arxiv(arxiv_url_or_id: str, status: str = "unread") -> Optional[int]:
    """从 arXiv 链接/ID 直接下载并摄入。返回 paper_id 或 None。"""
    arxiv_id = parse_arxiv_id(arxiv_url_or_id)
    if not arxiv_id:
        logger.error(f"无效的 arXiv 链接/ID: {arxiv_url_or_id}")
        return None

    logger.info(f"从 arXiv 下载并摄入: {arxiv_id}")

    # Step 1: 下载 PDF
    result = download_pdf(arxiv_id)
    if not result:
        return None

    file_path = result["file_path"]

    # Step 2: 用 arXiv API 预先获取元数据（比从PDF提取更准确）
    metadata = fetch_metadata(arxiv_id=arxiv_id)

    # Step 3: 检查是否已存在
    with PaperRepository() as repo:
        existing = repo.get_paper_by_arxiv(arxiv_id)
        if existing:
            logger.info(f"论文已存在 (arXiv:{arxiv_id})，跳过")
            return existing.id

    # Step 4: 走正常摄入流程（会解密、提取文本、入库）
    return ingest_pdf(file_path, status=status)


def _vectorize_paper(paper_id: int, chunks: list[dict]):
    """生成 embedding 并存入 ChromaDB"""
    try:
        from embeddings.embedder import get_embedder
        from embeddings.vector_store import get_vector_store

        embedder = get_embedder()
        vector_store = get_vector_store()

        texts = [c["text"] for c in chunks]
        embeddings = embedder.embed(texts)
        vector_store.add_chunks(paper_id, chunks, embeddings)
        logger.info(f"向量化完成: paper_{paper_id}, {len(chunks)} 个分块")
    except Exception as e:
        logger.error(f"向量化失败: {e}")


def _generate_and_index_summary(paper_id: int, full_text: str, metadata: dict):
    """生成论文总结并向量化"""
    from embeddings.embedder import get_embedder
    from embeddings.vector_store import get_vector_store

    # 尝试用 Claude 生成总结
    summary = ""
    try:
        from rag.qa_engine import get_qa_engine
        qa = get_qa_engine()
        summary = qa.summarize_paper(
            title=metadata.get("title", ""),
            abstract=metadata.get("abstract", ""),
            content=full_text[:3000],
        )
        # 保存到数据库
        with PaperRepository() as repo:
            repo.update_paper(paper_id, summary=summary)
    except Exception as e:
        logger.warning(f"总结生成失败: {e}")
        summary = metadata.get("abstract", "")

    # 向量化摘要
    if summary:
        try:
            embedder = get_embedder()
            vector_store = get_vector_store()
            embedding = embedder.embed_query(summary)
            vector_store.add_summary(paper_id, summary, embedding)
        except Exception as e:
            logger.error(f"摘要向量化失败: {e}")


def reindex_all_papers():
    """重新向量化知识库中的所有论文"""
    from pathlib import Path
    from database.connection import get_session
    from database.models import Paper
    from .pdf_parser import extract_text
    from .chunker import chunk_text

    s = get_session()
    try:
        papers = s.query(Paper).all()
    finally:
        s.close()

    logger.info(f"开始全量重建索引: {len(papers)} 篇论文")
    for paper in papers:
        if not paper.file_path or not Path(paper.file_path).exists():
            logger.warning(f"跳过 (无PDF): {paper.title[:50]}")
            continue

        try:
            full_text, _ = extract_text(paper.file_path)
            chunks = chunk_text(full_text)
            _vectorize_paper(paper.id, chunks)

            if paper.abstract and not paper.summary:
                _generate_and_index_summary(paper.id, full_text, {
                    "title": paper.title,
                    "abstract": paper.abstract,
                })
        except Exception as e:
            logger.error(f"重建索引失败 paper_{paper.id}: {e}")

    logger.info("全量重建索引完成")


def _try_update_metadata(paper):
    """当论文标题为文件名时，尝试从 PDF 文本中重新获取元数据并更新"""
    from pathlib import Path
    if not paper.file_path or not Path(paper.file_path).exists():
        return

    try:
        from .pdf_parser import extract_text_from_first_pages
        from .metadata_fetcher import fetch_metadata, extract_arxiv_id_from_text

        first_pages = extract_text_from_first_pages(paper.file_path, num_pages=2)
        arxiv_id = extract_arxiv_id_from_text(first_pages)
        if arxiv_id:
            metadata = fetch_metadata(arxiv_id=arxiv_id)
            if metadata and metadata.get("title"):
                with PaperRepository() as repo:
                    repo.update_paper(
                        paper.id,
                        title=metadata["title"],
                        authors=json.dumps(metadata.get("authors", []), ensure_ascii=False),
                        year=metadata.get("year"),
                        abstract=metadata.get("abstract", ""),
                        arxiv_id=arxiv_id,
                    )
                logger.info(f"元数据已更新: {metadata['title'][:60]}")
    except Exception as e:
        logger.warning(f"元数据更新失败: {e}")
