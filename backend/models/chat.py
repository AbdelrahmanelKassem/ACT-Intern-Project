import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, ForeignKey, DateTime, Numeric
from database import Base

from sqlalchemy import Integer
# (Make sure Integer is imported from sqlalchemy at the top)

class SessionContext(Base):
    __tablename__ = 'session_context'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hotel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel.id'))
    guest_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50)) # e.g., "active", "ended"
    started_at = mapped_column(DateTime, default=datetime.utcnow)
    
    # --- NEW COLUMN ---
    rating: Mapped[int] = mapped_column(Integer, nullable=True)

class MessageLog(Base):
    __tablename__ = 'message_log'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('session_context.id'))
    sender: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class IntentLog(Base):
    __tablename__ = 'intent_log'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('message_log.id'))
    detected_intent: Mapped[str] = mapped_column(String(255))
    confidence_score: Mapped[float] = mapped_column(Numeric)

class RagCitation(Base):
    __tablename__ = 'rag_citation'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('message_log.id'))
    chunk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('chunking_table.id'))
    similarity_score: Mapped[float] = mapped_column(Numeric)

class EscalationTicket(Base):
    __tablename__ = 'escalation_ticket'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('session_context.id'))
    issue_description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50))