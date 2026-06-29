"""FaceEncoding ORM model.

Stores the 128-dimensional face encodings extracted from uploaded images.
Multiple encodings can exist per user (different angles / lighting).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FaceEncoding(Base):
    """Face encoding row.

    Attributes:
        id: Primary UUID.
        user_id: FK to users.
        encoding: JSON array of 128 float values.
        image_path: Optional path to the source image on disk.
        deleted_at: Soft-delete timestamp.
        created_at: Row creation timestamp.
    """

    __tablename__ = "face_encodings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encoding: Mapped[str] = mapped_column(Text, nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", back_populates="face_encodings")
