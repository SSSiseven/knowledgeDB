import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent

# 自动加载 .env 文件
load_dotenv(BASE_DIR / ".env")

# Hugging Face 镜像（国内用户无需手动设置，默认使用国内镜像加速）
if not os.getenv("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

DATA_DIR = BASE_DIR / "data"
PAPER_DIR = DATA_DIR / "papers"
CHROMA_DIR = DATA_DIR / "chroma"
GRAPH_DIR = DATA_DIR / "graph"

SQLITE_PATH = DATA_DIR / "knowledge.db"

PAPER_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# DeepSeek API settings
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# arXiv API settings
ARXIV_SEARCH_MAX_RESULTS = 20
ARXIV_DOWNLOAD_DELAY = 3.0  # 礼貌延迟，避免被封

# Embedding settings
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"  # 本地开发用 cpu
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Top conferences to track
TOP_VENUES = [
    "NeurIPS", "ICML", "ICLR", "AAAI", "IJCAI", "AAMAS",
    "CVPR", "ACL", "EMNLP", "KDD", "WWW", "SIGIR",
]

# Keywords for the user's research interest
DEFAULT_KEYWORDS = [
    "multi-agent reinforcement learning",
    "MARL",
    "multi-agent collaboration",
    "cooperative AI",
    "decentralized execution",
    "CTDE",
    "agent communication",
    "emergent cooperation",
    "social dilemma",
    "multi-agent systems",
]
