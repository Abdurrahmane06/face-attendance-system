"""Face recognition service for FaceAttend.

Handles face encoding extraction from images, storage in the database,
and real-time face recognition against stored encodings using
the face_recognition library (dlib backend).
"""

import json
import logging
import os
import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

def _get_face_recognition():
    try:
        import face_recognition
        return face_recognition
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Le module face_recognition n'est pas installé. Veuillez contacter l'administrateur.",
        )

def _get_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        raise HTTPException(status_code=503, detail="Module numpy manquant.")

from app.core.config import settings
from app.models.face_encoding import FaceEncoding
from app.schemas.face import (
    FaceEncodingListResponse,
    FaceEncodingResponse,
    FaceRecognizeResponse,
    FaceUploadResponse,
)

logger = logging.getLogger(__name__)


async def extract_encoding(image_bytes: bytes) -> List[float]:
    """Extract a 128-dimensional face encoding from image bytes.

    Args:
        image_bytes: Raw image file bytes (JPEG or PNG).

    Returns:
        List of 128 float values representing the face encoding.

    Raises:
        HTTPException 400: If no face or multiple faces are detected,
                          or if the image is invalid.
    """
    face_recognition = _get_face_recognition()
    try:
        image = face_recognition.load_image_file(image_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {str(exc)}",
        )

    face_locations = face_recognition.face_locations(image)
    if len(face_locations) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected in the image. Please upload a photo with a clear face.",
        )
    if len(face_locations) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple faces detected. Please upload a photo with exactly one face.",
        )

    encodings = face_recognition.face_encodings(image, face_locations)
    if not encodings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not compute face encoding from the image.",
        )

    return encodings[0].tolist()


async def save_encoding(
    db: AsyncSession,
    user_id: str,
    encoding: List[float],
    image_path: Optional[str] = None,
) -> FaceEncoding:
    """Save a face encoding to the database.

    Args:
        db: Database session.
        user_id: Owner user UUID.
        encoding: 128-dimensional encoding vector.
        image_path: Optional path to source image.

    Returns:
        FaceEncoding model instance.
    """
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
    """Recognize a face from an image against all stored encodings.

    Args:
        db: Database session.
        image_bytes: Raw image file bytes.
        tolerance: Face distance threshold (default 0.6).

    Returns:
        FaceRecognizeResponse with recognition result.

    Raises:
        HTTPException 400: If face detection fails on input.
    """
    face_recognition = _get_face_recognition()
    np = _get_numpy()
    image = face_recognition.load_image_file(image_bytes)
    face_locations = face_recognition.face_locations(image)

    if len(face_locations) == 0:
        return FaceRecognizeResponse(
            recognized=False,
            message="Aucun visage détecté dans l'image",
            threshold=tolerance,
        )
    if len(face_locations) > 1:
        return FaceRecognizeResponse(
            recognized=False,
            message="Plusieurs visages détectés",
            threshold=tolerance,
        )

    input_encodings = face_recognition.face_encodings(image, face_locations)
    if not input_encodings:
        return FaceRecognizeResponse(
            recognized=False,
            message="Impossible de calculer l'encodage facial",
            threshold=tolerance,
        )

    input_encoding = np.array(input_encodings[0])

    result = await db.execute(select(FaceEncoding))
    stored_encodings = result.scalars().all()

    if not stored_encodings:
        return FaceRecognizeResponse(
            recognized=False,
            message="Aucun encodage de référence en base de données",
            threshold=tolerance,
        )

    known_encodings = []
    known_user_map = {}

    for se in stored_encodings:
        try:
            enc_data = json.loads(se.encoding)
            known_encodings.append(np.array(enc_data))
            known_user_map[se.user_id] = se.user
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Invalid encoding data for %s: %s", se.id, exc)
            continue

    if not known_encodings:
        return FaceRecognizeResponse(
            recognized=False,
            message="Aucun encodage valide trouvé",
            threshold=tolerance,
        )

    distances = face_recognition.face_distance(known_encodings, input_encoding)
    min_distance = float(np.min(distances))
    best_match_idx = int(np.argmin(distances))

    if min_distance <= tolerance:
        matched_user_id = stored_encodings[best_match_idx].user_id
        matched_user = known_user_map.get(matched_user_id)
        confidence = 1.0 - min_distance
        return FaceRecognizeResponse(
            recognized=True,
            user_id=matched_user_id,
            user_name=matched_user.full_name if matched_user else "Unknown",
            confidence=round(confidence, 4),
            threshold=tolerance,
            message="Visage reconnu",
        )

    return FaceRecognizeResponse(
        recognized=False,
        message="Visage non identifié",
        threshold=tolerance,
    )


async def get_user_encodings(
    db: AsyncSession, user_id: str
) -> FaceEncodingListResponse:
    """Get all face encodings for a specific user.

    Args:
        db: Database session.
        user_id: User UUID.

    Returns:
        FaceEncodingListResponse with encoding list.
    """
    result = await db.execute(
        select(FaceEncoding).where(FaceEncoding.user_id == user_id).order_by(FaceEncoding.created_at.desc())
    )
    encodings = result.scalars().all()
    return FaceEncodingListResponse(
        items=[FaceEncodingResponse.model_validate(e) for e in encodings],
        total=len(encodings),
    )


async def delete_encoding(db: AsyncSession, encoding_id: str) -> None:
    """Delete a face encoding by ID.

    Args:
        db: Database session.
        encoding_id: Encoding UUID.

    Raises:
        HTTPException 404: If encoding not found.
    """
    result = await db.execute(select(FaceEncoding).where(FaceEncoding.id == encoding_id))
    encoding = result.scalar_one_or_none()
    if not encoding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face encoding not found",
        )
    await db.delete(encoding)
    await db.flush()
