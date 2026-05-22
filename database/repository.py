import json
from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import or_

from .models import (
    Paper, Concept, PaperConcept, PaperRelation,
    ReadingLog, Idea, Recommendation,
)
from .connection import get_session


class PaperRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._own_session = session is None

    def _get_session(self) -> Session:
        if self._session is not None:
            return self._session
        return get_session()

    def __enter__(self):
        if self._own_session:
            self._session = get_session()
        return self

    def __exit__(self, *args):
        if self._own_session and self._session:
            self._session.close()
            self._session = None

    # ─── Paper CRUD ──────────────────────────────────────

    def add_paper(self, **kwargs) -> Paper:
        s = self._get_session()
        paper = Paper(**kwargs)
        s.add(paper)
        if self._own_session:
            s.commit()
            s.refresh(paper)
        return paper

    def get_paper(self, paper_id: int) -> Optional[Paper]:
        return self._get_session().query(Paper).filter(Paper.id == paper_id).first()

    def get_paper_by_arxiv(self, arxiv_id: str) -> Optional[Paper]:
        return self._get_session().query(Paper).filter(Paper.arxiv_id == arxiv_id).first()

    def get_paper_by_doi(self, doi: str) -> Optional[Paper]:
        return self._get_session().query(Paper).filter(Paper.doi == doi).first()

    def list_papers(
        self,
        status: Optional[str] = None,
        venue: Optional[str] = None,
        keyword: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Paper]:
        s = self._get_session()
        q = s.query(Paper)

        if status:
            q = q.filter(Paper.status == status)
        if venue:
            q = q.filter(Paper.venue.like(f"%{venue}%"))
        if keyword:
            pattern = f"%{keyword}%"
            q = q.filter(or_(
                Paper.title.like(pattern),
                Paper.abstract.like(pattern),
                Paper.keywords.like(pattern),
                Paper.authors.like(pattern),
            ))
        if year_from:
            q = q.filter(Paper.year >= year_from)
        if year_to:
            q = q.filter(Paper.year <= year_to)

        col = getattr(Paper, sort_by, Paper.created_at)
        if sort_desc:
            col = col.desc()
        return q.order_by(col).offset(offset).limit(limit).all()

    def count_papers(self, **filters) -> int:
        s = self._get_session()
        q = s.query(Paper)
        if filters.get("status"):
            q = q.filter(Paper.status == filters["status"])
        return q.count()

    def update_paper(self, paper_id: int, **kwargs) -> Optional[Paper]:
        s = self._get_session()
        paper = s.query(Paper).filter(Paper.id == paper_id).first()
        if paper:
            for k, v in kwargs.items():
                if hasattr(paper, k):
                    setattr(paper, k, v)
            paper.updated_at = datetime.now(timezone.utc)
            if self._own_session:
                s.commit()
        return paper

    def delete_paper(self, paper_id: int) -> bool:
        s = self._get_session()
        paper = s.query(Paper).filter(Paper.id == paper_id).first()
        if paper:
            s.delete(paper)
            if self._own_session:
                s.commit()
            # 同时清理 ChromaDB 向量数据
            _delete_paper_vectors(paper_id)
            return True
        return False

    def get_paper_count_by_venue(self) -> dict:
        s = self._get_session()
        rows = s.query(Paper.venue_type).all()  # simplified — returns venue types counts
        result = {}
        for row in rows:
            if row[0]:
                result[row[0]] = result.get(row[0], 0) + 1
        return result

    # ─── Reading Log ─────────────────────────────────────

    def add_reading_log(self, paper_id: int, notes: str = "", key_points: str = "") -> ReadingLog:
        s = self._get_session()
        log = ReadingLog(paper_id=paper_id, notes=notes, key_points=key_points)
        s.add(log)
        if self._own_session:
            s.commit()
        return log

    def get_reading_logs(self, paper_id: int) -> List[ReadingLog]:
        return (
            self._get_session()
            .query(ReadingLog)
            .filter(ReadingLog.paper_id == paper_id)
            .order_by(ReadingLog.date.desc())
            .all()
        )

    # ─── Concept ──────────────────────────────────────────

    def get_or_create_concept(self, name: str, category: str = "", description: str = "") -> Concept:
        s = self._get_session()
        concept = s.query(Concept).filter(Concept.name == name).first()
        if not concept:
            concept = Concept(name=name, category=category, description=description)
            s.add(concept)
            if self._own_session:
                s.commit()
        return concept

    def get_paper_concepts(self, paper_id: int):
        s = self._get_session()
        return (
            s.query(PaperConcept)
            .filter(PaperConcept.paper_id == paper_id)
            .all()
        )

    def link_paper_concept(self, paper_id: int, concept_id: int, relevance: str = "related"):
        s = self._get_session()
        existing = (
            s.query(PaperConcept)
            .filter(PaperConcept.paper_id == paper_id, PaperConcept.concept_id == concept_id)
            .first()
        )
        if not existing:
            pc = PaperConcept(paper_id=paper_id, concept_id=concept_id, relevance=relevance)
            s.add(pc)
            if self._own_session:
                s.commit()

    # ─── Paper Relations ──────────────────────────────────

    def add_relation(self, source_id: int, target_id: int, relation_type: str):
        s = self._get_session()
        existing = (
            s.query(PaperRelation)
            .filter(
                PaperRelation.source_id == source_id,
                PaperRelation.target_id == target_id,
                PaperRelation.relation_type == relation_type,
            )
            .first()
        )
        if not existing:
            rel = PaperRelation(source_id=source_id, target_id=target_id, relation_type=relation_type)
            s.add(rel)
            if self._own_session:
                s.commit()

    def get_paper_relations(self, paper_id: int) -> List[PaperRelation]:
        return (
            self._get_session()
            .query(PaperRelation)
            .filter(or_(
                PaperRelation.source_id == paper_id,
                PaperRelation.target_id == paper_id,
            ))
            .all()
        )

    # ─── Idea ─────────────────────────────────────────────

    def add_idea(self, title: str, description: str = "", motivation: str = "",
                 source_paper_ids: List[int] = None) -> Idea:
        s = self._get_session()
        idea = Idea(
            title=title,
            description=description,
            motivation=motivation,
            source_paper_ids=json.dumps(source_paper_ids or []),
        )
        s.add(idea)
        if self._own_session:
            s.commit()
        return idea

    def list_ideas(self, status: Optional[str] = None, limit: int = 50) -> List[Idea]:
        s = self._get_session()
        q = s.query(Idea)
        if status:
            q = q.filter(Idea.status == status)
        return q.order_by(Idea.created_at.desc()).limit(limit).all()

    def update_idea(self, idea_id: int, **kwargs) -> Optional[Idea]:
        s = self._get_session()
        idea = s.query(Idea).filter(Idea.id == idea_id).first()
        if idea:
            for k, v in kwargs.items():
                if hasattr(idea, k):
                    setattr(idea, k, v)
            if self._own_session:
                s.commit()
        return idea

    # ─── Recommendations ──────────────────────────────────

    def add_recommendation(self, **kwargs) -> Optional[Recommendation]:
        s = self._get_session()
        arxiv_id = kwargs.get("arxiv_id")
        if arxiv_id and s.query(Recommendation).filter(Recommendation.arxiv_id == arxiv_id).first():
            return None  # already exists
        rec = Recommendation(**kwargs)
        s.add(rec)
        if self._own_session:
            s.commit()
        return rec

    def list_recommendations(self, unread_only: bool = True, limit: int = 50) -> List[Recommendation]:
        s = self._get_session()
        q = s.query(Recommendation)
        if unread_only:
            q = q.filter(Recommendation.is_read == False)
        return q.order_by(Recommendation.created_at.desc()).limit(limit).all()

    def mark_recommendation_read(self, rec_id: int):
        s = self._get_session()
        rec = s.query(Recommendation).filter(Recommendation.id == rec_id).first()
        if rec:
            rec.is_read = True
            if self._own_session:
                s.commit()

    def commit(self):
        if self._session:
            self._session.commit()


def _delete_paper_vectors(paper_id: int):
    """删除论文在 ChromaDB 中的所有向量数据"""
    try:
        from embeddings.vector_store import get_vector_store
        vs = get_vector_store()
        vs.delete_paper(paper_id)
    except Exception:
        pass  # ChromaDB 可能未初始化，静默忽略
