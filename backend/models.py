"""
models.py — SQLAlchemy ORM models.
All vector columns use pgvector's Vector type.
"""
import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
    JSON, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from config import settings

EMBED_DIM = settings.EMBEDDING_DIMENSION


# ─────────────────────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_sub: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String)
    picture_url: Mapped[Optional[str]] = mapped_column(String)
    # Refresh token is AES-encrypted at rest; never sent to frontend
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    folder_index = relationship("FolderIndex", back_populates="user", cascade="all, delete-orphan")
    clusters = relationship("Cluster", back_populates="user", cascade="all, delete-orphan")
    placement_rules = relationship("PlacementRule", back_populates="user", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# Documents
# ─────────────────────────────────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    drive_file_id: Mapped[Optional[str]] = mapped_column(String)  # null until placed in Drive
    filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    doc_type: Mapped[Optional[str]] = mapped_column(String)       # invoice | contract | notes | ...
    entities: Mapped[Optional[dict]] = mapped_column(JSON)        # {dates, orgs, amounts}
    suggested_topic: Mapped[Optional[str]] = mapped_column(String)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(EMBED_DIM))
    # Path to preserved original file bytes (for Drive upload on /confirm)
    stored_file_path: Mapped[Optional[str]] = mapped_column(String)
    # pending | extracting | classifying | needs_input | placing | placed | error
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="documents")
    placements = relationship("Placement", back_populates="document", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# Folder Index (cached Drive folder tree)
# ─────────────────────────────────────────────────────────────────────────────
class FolderIndex(Base):
    __tablename__ = "folder_index"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    drive_folder_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_drive_id: Mapped[Optional[str]] = mapped_column(String)  # null = root
    path: Mapped[Optional[str]] = mapped_column(String)             # human-readable "Work/Projects/2024"
    embedding: Mapped[Optional[list]] = mapped_column(Vector(EMBED_DIM))
    last_synced: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="folder_index")


# ─────────────────────────────────────────────────────────────────────────────
# Placements (placement decisions + history for learning loop)
# ─────────────────────────────────────────────────────────────────────────────
class Placement(Base):
    __tablename__ = "placements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    suggested_folder_id: Mapped[Optional[str]] = mapped_column(String)   # Drive folder id
    final_folder_id: Mapped[Optional[str]] = mapped_column(String)       # Drive folder id (set on confirm)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    why_explanation: Mapped[Optional[str]] = mapped_column(Text)
    was_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="placements")


# ─────────────────────────────────────────────────────────────────────────────
# Clusters (groupings of unfiled docs that share a topic)
# ─────────────────────────────────────────────────────────────────────────────
class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    topic_label: Mapped[Optional[str]] = mapped_column(String)
    suggested_folder_name: Mapped[Optional[str]] = mapped_column(String)
    member_document_ids: Mapped[list] = mapped_column(JSON, default=list)  # list of UUID strings
    # suggested | accepted | dismissed
    status: Mapped[str] = mapped_column(String, default="suggested", nullable=False)
    created_folder_id: Mapped[Optional[str]] = mapped_column(String)  # Drive folder id after accept
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="clusters")


# ─────────────────────────────────────────────────────────────────────────────
# Placement Rules (learning loop)
# ─────────────────────────────────────────────────────────────────────────────
class PlacementRule(Base):
    __tablename__ = "placement_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    pattern_label: Mapped[Optional[str]] = mapped_column(String)
    pattern_embedding: Mapped[Optional[list]] = mapped_column(Vector(EMBED_DIM))
    target_folder_id: Mapped[str] = mapped_column(String, nullable=False)
    target_folder_name: Mapped[Optional[str]] = mapped_column(String)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="placement_rules")
