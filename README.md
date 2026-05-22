# KnowledgeDB — 智能知识库问答系统

面向计算机专业研究生的个人知识库系统，辅助论文阅读、知识体系构建、研究灵感发散。

**研究方向**: 多智能体协作 & 强化学习

## 功能概览

### 论文库
- **上传 PDF**：本地上传，自动解密（pikepdf → qpdf fallback）、提取文本、分块向量化
- **arXiv 导入**：输入 arXiv 链接或 ID（如 `2301.12345`），自动下载并摄入
- **搜索筛选**：按标题/作者/摘要关键词搜索，按阅读状态筛选，按时间/年份/评分排序

### 阅读器
- 论文元信息展示（标题、作者、年份、会议、arXiv/DOI 链接）
- 阅读状态管理（未读 → 在读 → 已读）+ 星级评分 + 进度滑块
- PDF 内嵌预览 + 下载按钮
- 笔记系统（核心要点 + 详细笔记，按时间线记录）
- AI 总结生成（调用 LLM 自动生成结构化中文总结）

### 智能问答
- 基于知识库论文的 RAG 问答，答案附引用来源
- 快捷提问：CTDE 概念、QMIX vs VDN、通信机制发展、未来趋势
- 专项分析：概念解释 / 算法对比 / 文献综述 / 研究趋势

## 技术栈

| 层面 | 技术 |
|------|------|
| Web 界面 | Streamlit |
| 数据库 | SQLite + SQLAlchemy |
| 向量存储 | ChromaDB + sentence-transformers (all-MiniLM-L6-v2) |
| LLM | DeepSeek V4-pro（Anthropic 兼容接口）/ Claude 可切换 |
| PDF 处理 | PyMuPDF + pikepdf |
| 论文元数据 | arXiv API |
| 知识图谱 | NetworkX + PyVis（待上线） |

## 快速启动

### 环境要求
- Python 3.11+（推荐 Anaconda）
- Windows / macOS / Linux

### 安装

```bash
# 1. 创建虚拟环境
conda create -n knowledgedb python=3.11 -y
conda activate knowledgedb

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY（或 ANTHROPIC_API_KEY）
```

`.env` 示例：
```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_MODEL=DeepSeek-V4-pro[1m]
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
```

### 启动

```bash
conda activate knowledgedb
streamlit run app.py
```

浏览器访问 `http://localhost:8501`。首次启动自动下载 embedding 模型（约 90MB，已配置国内镜像）。

## 项目结构

```
knowledgeDB/
├── app.py                  # Streamlit 主入口
├── config.py               # 全局配置（自动加载 .env）
├── .env                    # API Key 配置（不入版本控制）
├── requirements.txt
├── database/               # SQLite 数据库层
│   ├── models.py           #   7 张表 ORM 模型
│   ├── connection.py       #   连接管理
│   └── repository.py       #   CRUD 封装
├── ingestion/              # 论文摄入管道
│   ├── arxiv_downloader.py #   arXiv 链接解析 + PDF 下载
│   ├── pdf_decryptor.py    #   PDF 解密（pikepdf / qpdf）
│   ├── pdf_parser.py       #   文本提取（PyMuPDF）
│   ├── metadata_fetcher.py #   元数据获取（arXiv API）
│   ├── chunker.py          #   文本分块
│   └── pipeline.py         #   完整流程编排
├── embeddings/             # 向量化
│   ├── embedder.py         #   sentence-transformers 封装
│   └── vector_store.py     #   ChromaDB 操作
├── rag/                    # RAG 引擎
│   ├── retriever.py        #   混合检索（向量 + 关键词 + RRF）
│   ├── qa_engine.py        #   问答流水线
│   └── prompts.py          #   Claude/DeepSeek 提示词模板
├── llm/                    # LLM 抽象层
│   ├── factory.py          #   自动检测 DeepSeek / Claude
│   └── anthropic_client.py #   Anthropic 兼容客户端
├── ui/                     # Web 界面
│   ├── pages/
│   │   ├── library.py      #   论文库页面
│   │   ├── reader.py       #   阅读器页面
│   │   └── qa.py           #   智能问答页面
│   └── components/
│       ├── sidebar.py      #   侧边栏导航
│       └── paper_card.py   #   论文卡片组件
└── data/                   # 本地数据
    ├── papers/             #   PDF 文件
    ├── chroma/             #   向量数据库
    └── knowledge.db        #   SQLite 数据库
```

## LLM 切换

系统支持 DeepSeek 和 Claude，通过 `.env` 切换：

```bash
# 用 DeepSeek（默认，国内推荐）
DEEPSEEK_API_KEY=sk-xxxxxxxx

# 用 Claude（需代理）
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx

# 指定优先使用哪个
LLM_PROVIDER=claude
```

两者均通过 Anthropic Messages API 调用，架构统一，无需改代码。

## 路线图

- [x] **Phase 1**: 论文管理（上传、arXiv 导入、搜索、阅读器、笔记）
- [x] **Phase 2**: 智能问答（RAG 检索 + LLM 生成 + 多类 prompt 模板）
- [ ] **Phase 3**: 知识图谱（概念抽取、论文关系、可视化探索）
- [ ] **Phase 4**: 灵感生成 + 论文推荐（研究空白分析、arXiv 热点追踪）
