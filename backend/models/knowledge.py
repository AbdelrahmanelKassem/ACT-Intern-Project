import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, ForeignKey
from pgvector.sqlalchemy import Vector
from database import Base

class KnowledgeBase(Base):
    __tablename__ = 'knowledge_base'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hotel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel.id'))
    name: Mapped[str] = mapped_column(String(255))

class Document(Base):
    __tablename__ = 'document'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('knowledge_base.id'))
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50))

class ChunkingTable(Base):
    __tablename__ = 'chunking_table'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('document.id'))
    content_text: Mapped[str] = mapped_column(Text)
    vector_embedding = mapped_column(Vector(768))