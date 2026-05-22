# KnowledgeDB — 项目开发规范

## 分支策略

- `master` 分支保持可运行状态，不直接在 master 上开发
- 每个功能/修复从 master 拉新分支：`feature/<功能名>` 或 `fix/<修复内容>`
- 开发完成后推送到 GitHub，提 Pull Request 合并到 master
- 分支命名用 kebab-case，英文

## 环境

- 使用 conda 环境 `knowledgedb`，Python 3.11
- 首次运行：`conda activate knowledgedb && pip install -r requirements.txt`
- 启动：`streamlit run app.py`
- .env 文件不入版本控制（已在 .gitignore）

## 技术栈

- Web: Streamlit
- 数据库: SQLite + SQLAlchemy
- 向量库: ChromaDB + sentence-transformers/all-MiniLM-L6-v2
- LLM: DeepSeek V4-pro (Anthropic 兼容接口) / Claude 可切换
- PDF: PyMuPDF + pikepdf
- 图谱: NetworkX + PyVis
