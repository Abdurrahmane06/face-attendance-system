"""AbsenceType ORM model.

Catalogue of absence categories (sick leave, vacation, unjustified, etc.).
Used by Justification records to classify an absence.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AbsenceType(Base):
    """Absence category.

    Attributes:
        id: Primary UUID.
        name: Category label (e.g. "Maladie", "Congés payés").
        description: Optional longer description.
        requires_justification: Whether a supporting document is required.
        deleted_at: Soft-delete timestamp.
        created_at: Row creation timestamp.
    """

    __tablename__ = "absence_types"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_justification: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    justifications = relationship("Justification", back_populates="absence_type")
