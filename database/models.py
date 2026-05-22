from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


def _now():
    return datetime.now(timezone.utc)


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    authors = Column(Text, default="[]")          # JSON array
    year = Column(Integer)
    venue = Column(String(200))
    venue_type = Column(String(50))               # conference/journal/workshop/preprint
    doi = Column(String(200), unique=True)
    arxiv_id = Column(String(50), unique=True)
    abstract = Column(Text)
    file_path = Column(String(500))
    status = Column(String(20), default="unread") # unread/reading/read
    rating = Column(Integer, default=0)           # 1-5
    reading_progress = Column(Float, default=0.0)
    summary = Column(Text)
    keywords = Column(Text, default="[]")         # JSON array
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    # relationships
    paper_concepts = relationship("PaperConcept", back_populates="paper", cascade="all, delete-orphan")
    reading_logs = relationship("ReadingLog", back_populates="paper", cascade="all, delete-orphan")


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(50))                  # algorithm/framework/problem/metric/theory

    paper_concepts = relationship("PaperConcept", back_populates="concept", cascade="all, delete-orphan")


class PaperConcept(Base):
    __tablename__ = "paper_concepts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    relevance = Column(String(20))                 # core/related/mentioned

    paper = relationship("Paper", back_populates="paper_concepts")
    concept = relationship("Concept", back_populates="paper_concepts")

    __table_args__ = (
        UniqueConstraint("paper_id", "concept_id", name="uq_paper_concept"),
    )


class PaperRelation(Base):
    __tablename__ = "paper_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(30))             # cites/extended_by/compared_with/similar_to

    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation_type", name="uq_paper_relation"),
    )


class ReadingLog(Base):
    __tablename__ = "reading_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, default=_now)
    notes = Column(Text)
    key_points = Column(Text)

    paper = relationship("Paper", back_populates="reading_logs")


class Idea(Base):
    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    motivation = Column(Text)
    source_paper_ids = Column(Text, default="[]")   # JSON array
    status = Column(String(20), default="draft")     # draft/developing/abandoned/implemented
    created_at = Column(DateTime, default=_now)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    arxiv_id = Column(String(50), unique=True)
    title = Column(String(500))
    authors = Column(Text)
    year = Column(Integer)
    abstract = Column(Text)
    venue = Column(String(200))
    reason = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)
