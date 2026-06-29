"""Face recognition service.

Handles face encoding extraction from images, persistence, and real-time
face matching against the database using the face_recognition library (dlib).

Key design decisions:
- load_image_file() receives io.BytesIO, not raw bytes (PIL requires file-like object).
- Encodings are fetched with joinedload(user) to avoid lazy-load errors in async.
- A parallel list tracks valid encodings so skipped rows don't shift indices.
- Deleted encodings (deleted_at IS NOT NULL) are excluded from recognition.
"""

import io
import json
import logging
import os
import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.models.face_encoding import FaceEncoding
from app.schemas.face import (
    FaceEncodingListResponse,
    FaceEncodingResponse,
    FaceRecognizeResponse,
    FaceUploadResponse,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy imports — face_recognition / numpy are optional in test environments
# ---------------------------------------------------------------------------

def _get_face_recognition():
    try:
        import face_recognition
        return face_recognition
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="face_recognition module not installed. Contact the administrator.",
        )


def _get_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="numpy module not installed.",
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_encoding(image_bytes: bytes) -> List[float]:
    """Extract a 128-D face encoding from raw image bytes.

    Raises:
        HTTPException 400: No face detected, multiple faces, or invalid image.
    """
    face_recognition = _get_face_recognition()

    try:
        # PIL (used internally by face_recognition) requires a file-like object
        image = face_recognition.load_image_file(io.BytesIO(image_bytes))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {exc}",
        )

    face_locations = face_recognition.face_locations(image)

    if len(face_locations) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected. Upload a photo with a single, clearly visible face.",
        )
    if len(face_locations) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{len(face_locations)} faces detected. Upload a photo with exactly one face.",
        )

    encodings = face_recognition.face_encodings(image, face_locations)
    if not encodings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Face detected but encoding could not be computed. Try a clearer photo.",
        )

    return encodings[0].tolist()


async def save_encoding(
    db: AsyncSession,
    user_id: str,
    encoding: List[float],
    image_path: Optional[str] = None,
) -> FaceEncoding:
    """Persist a face encoding row linked to a user."""
    face_enc = FaceEncoding(
        user_id=user_id,
        encoding=json.dumps(encoding),
        image_path=image_path,
    )
    db.add(face_enc)
    await db.flush()
    await db.refresh(face_enc)
    return face_enc


async def recognize_face(
    db: AsyncSession,
    image_bytes: bytes,
    tolerance: float = 0.6,
) -> FaceRecognizeResponse:
    """Match a face from an image against all stored encodings.

    Returns the best match if euclidean distance ≤ tolerance.
    confidence = 1 - distance  (range 0-1, higher is better).
    """
    face_recognition = _get_face_recognition()
    np = _get_numpy()

    try:
        image = face_recognition.load_image_file(io.BytesIO(image_bytes))
    except Exception:
        return FaceRecognizeResponse(
            recognized=False,
            message="Invalid image file",
            threshold=tolerance,
        )

    face_locations = face_recognition.face_locations(image)

    if len(face_locations) == 0:
        return FaceRecognizeResponse(
            recognized=False,
            message="No face detected in the image",
            threshold=tolerance,
        )
    if len(face_locations) > 1:
        return FaceRecognizeResponse(
            recognized=False,
            message=f"{len(face_locations)} faces detected — present only one face",
            threshold=tolerance,
        )

    input_encodings = face_recognition.face_encodings(image, face_locations)
    if not input_encodings:
        return FaceRecognizeResponse(
            recognized=False,
            message="Could not compute face encoding",
            threshold=tolerance,
        )

    input_encoding = np.array(input_encodings[0])

    # Fetch all active encodings with their users (joinedload prevents async lazy-load errors)
    result = await db.execute(
        select(FaceEncoding)
        .options(joinedload(FaceEncoding.user))
        .where(FaceEncoding.deleted_at.is_(None))
    )
    stored = result.scalars().all()

    if not stored:
        return FaceRecognizeResponse(
            recognized=False,
            message="No reference encodings in database",
            threshold=tolerance,
        )

    # Build parallel lists so skipped rows don't shift indices
    known_vectors: List = []
    valid_encodings: List[FaceEncoding] = []

    for fe in stored:
        try:
            vec = np.array(json.loads(fe.encoding))
            known_vectors.append(vec)
            valid_encodings.append(fe)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Skipping corrupt encoding %s: %s", fe.id, exc)

    if not known_vectors:
        return FaceRecognizeResponse(
            recognized=False,
            message="No valid encodings found",
            threshold=tolerance,
        )

    distances = face_recognition.face_distance(known_vectors, input_encoding)
    min_distance = float(np.min(distances))
    best_idx = int(np.argmin(distances))

    if min_distance <= tolerance:
        matched = valid_encodings[best_idx]
        matched_user = matched.user
        return FaceRecognizeResponse(
            recognized=True,
            user_id=matched.user_id,
            user_name=matched_user.full_name if matched_user else "Unknown",
            confidence=round(1.0 - min_distance, 4),
            threshold=tolerance,
            message="Face recognized",
        )

    return FaceRecognizeResponse(
        recognized=False,
        message="Face not recognized",
        threshold=tolerance,
    )


async def get_user_encodings(
    db: AsyncSession, user_id: str
) -> FaceEncodingListResponse:
    """Return all active (non-deleted) encodings for a user."""
    result = await db.execute(
        select(FaceEncoding)
        .where(FaceEncoding.user_id == user_id, FaceEncoding.deleted_at.is_(None))
        .order_by(FaceEncoding.created_at.desc())
    )
    encodings = result.scalars().all()
    return FaceEncodingListResponse(
        items=[FaceEncodingResponse.model_validate(e) for e in encodings],
        total=len(encodings),
    )


async def delete_encoding(db: AsyncSession, encoding_id: str) -> None:
    """Soft-delete a face encoding by ID.

    Raises:
        HTTPException 404: If encoding not found or already deleted.
    """
    from datetime import datetime, timezone

    result = await db.execute(
        select(FaceEncoding).where(
            FaceEncoding.id == encoding_id,
            FaceEncoding.deleted_at.is_(None),
        )
    )
    encoding = result.scalar_one_or_none()
    if not encoding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face encoding not found",
        )
    encoding.deleted_at = datetime.now(timezone.utc)
    await db.flush()
