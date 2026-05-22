"""arXiv PDF 下载器 — 支持多种输入格式的 arXiv 链接"""

import re
import time
import requests
from pathlib import Path
from config import PAPER_DIR, ARXIV_DOWNLOAD_DELAY
from utils.logger import logger

ARXIV_ID_PATTERN = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/([\w.\-]+?)(?:v\d+)?(?:\.pdf)?$)|"
    r"(?:^(\d{4}\.\d{4,5})(?:v\d+)?$)"
)

def parse_arxiv_id(raw: str) -> str | None:
    """从 arXiv URL 或纯 ID 中提取 arXiv ID。
    支持格式:
      - https://arxiv.org/abs/2301.12345
      - https://arxiv.org/abs/2301.12345v2
      - https://arxiv.org/pdf/2301.12345.pdf
      - 2301.12345
      - 2301.12345v2
      - arXiv:2301.12345
    """
    raw = raw.strip()
    # 去掉可能的 arXiv: 前缀
    raw = raw.replace("arXiv:", "").replace("arxiv:", "")
    match = ARXIV_ID_PATTERN.search(raw)
    if match:
        return match.group(1) or match.group(2)
    return None


def download_pdf(arxiv_id_or_url: str, target_dir: Path | None = None) -> dict | None:
    """根据 arXiv ID 或链接下载 PDF 到本地。
    返回 {"arxiv_id": str, "file_path": str, "title_hint": str} 或 None。
    """
    arxiv_id = parse_arxiv_id(arxiv_id_or_url)
    if not arxiv_id:
        logger.error(f"无法解析 arXiv ID: {arxiv_id_or_url}")
        return None

    target_dir = target_dir or PAPER_DIR
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    pdf_filename = f"{arxiv_id.replace('/', '_')}.pdf"
    pdf_path = target_dir / pdf_filename

    # 如果已下载过，直接返回
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        logger.info(f"PDF 已存在: {pdf_path}")
        return {"arxiv_id": arxiv_id, "file_path": str(pdf_path), "title_hint": ""}

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    # 礼貌延迟
    time.sleep(ARXIV_DOWNLOAD_DELAY)

    try:
        logger.info(f"下载 PDF: {pdf_url}")
        resp = requests.get(pdf_url, timeout=60, stream=True)
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "")
            if "html" in content_type:
                logger.error(f"返回的是 HTML 而非 PDF，arXiv ID 可能不存在: {arxiv_id}")
                return None

            with open(pdf_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 验证下载的文件
            if pdf_path.stat().st_size < 1000:  # 小于1KB肯定有问题
                logger.error(f"下载的 PDF 异常小: {pdf_path.stat().st_size} bytes")
                pdf_path.unlink()
                return None

            logger.info(f"PDF 下载完成: {pdf_path} ({pdf_path.stat().st_size} bytes)")
            return {"arxiv_id": arxiv_id, "file_path": str(pdf_path), "title_hint": ""}
        else:
            logger.error(f"下载失败，HTTP {resp.status_code}: {pdf_url}")
            return None
    except requests.Timeout:
        logger.error(f"下载超时: {pdf_url}")
        return None
    except Exception as e:
        logger.error(f"下载异常: {e}")
        return None


def fetch_arxiv_metadata(arxiv_id: str) -> dict | None:
    """通过 arXiv API 获取论文元数据（标题、作者、摘要等）"""
    import xml.etree.ElementTree as ET

    api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
    time.sleep(0.5)

    try:
        resp = requests.get(api_url, timeout=30)
        if resp.status_code != 200:
            logger.error(f"arXiv API 返回 HTTP {resp.status_code}")
            return None

        # 解析 Atom XML
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(resp.text)
        entry = root.find("atom:entry", ns)
        if entry is None:
            return None

        title = entry.find("atom:title", ns)
        title_text = " ".join(title.text.split()) if title is not None and title.text else ""

        summary = entry.find("atom:summary", ns)
        summary_text = " ".join(summary.text.split()) if summary is not None and summary.text else ""

        authors = []
        for author in entry.findall("atom:author", ns):
            name = author.find("atom:name", ns)
            if name is not None and name.text:
                authors.append(name.text.strip())

        published = entry.find("atom:published", ns)
        year = int(published.text[:4]) if published is not None and published.text else None

        # arXiv 主分类
        primary_cat = entry.find("arxiv:primary_category", ns)
        category = primary_cat.get("term") if primary_cat is not None else None

        return {
            "arxiv_id": arxiv_id,
            "title": title_text,
            "authors": authors,
            "year": year,
            "abstract": summary_text,
            "category": category,
        }
    except Exception as e:
        logger.error(f"解析 arXiv 元数据异常: {e}")
        return None
