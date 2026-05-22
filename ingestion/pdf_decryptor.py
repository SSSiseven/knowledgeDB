import subprocess
import tempfile
from pathlib import Path
from utils.logger import logger


def decrypt_pdf(input_path: str, output_path: str | None = None) -> str:
    """解密 arXiv 等来源的权限保护 PDF。
    优先用 pikepdf（纯 Python），失败则用 qpdf 命令行。
    返回解密后的 PDF 文件路径。
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = str(input_path.parent / f"{input_path.stem}_decrypted.pdf")
    output_path = Path(output_path)

    # 方案1: pikepdf
    try:
        import pikepdf
        pdf = pikepdf.open(str(input_path), allow_overwriting_input=True)
        pdf.save(str(output_path))
        pdf.close()
        logger.info(f"pikepdf 解密成功: {input_path.name}")
        return str(output_path)
    except Exception as e:
        logger.warning(f"pikepdf 解密失败 ({e})，尝试 qpdf...")

    # 方案2: qpdf
    try:
        result = subprocess.run(
            ["qpdf", "--decrypt", str(input_path), str(output_path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and output_path.exists():
            logger.info(f"qpdf 解密成功: {input_path.name}")
            return str(output_path)
        else:
            logger.error(f"qpdf 解密失败: {result.stderr}")
    except FileNotFoundError:
        logger.warning("qpdf 未安装，无法解密")
    except Exception as e:
        logger.error(f"qpdf 异常: {e}")

    # 方案3: 尝试直接复制（某些 PDF 实际上没有真正加密）
    try:
        with open(input_path, "rb") as src:
            content = src.read()
        with open(output_path, "wb") as dst:
            dst.write(content)
        logger.info(f"直接复制 PDF: {input_path.name}")
        return str(output_path)
    except Exception:
        pass

    logger.error(f"所有解密方案均失败: {input_path.name}")
    return str(input_path)  # 返回原路径，让后续流程自行判断


def is_pdf_encrypted(file_path: str) -> bool:
    """检查 PDF 是否加密/有权限限制"""
    try:
        import fitz
        doc = fitz.open(file_path)
        is_encrypted = doc.is_encrypted
        needs_pass = doc.needs_pass
        doc.close()
        return is_encrypted or needs_pass
    except Exception:
        return False  # 无法判断时假定不需要解密
