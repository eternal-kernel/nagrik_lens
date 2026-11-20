from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.poster import PosterScanResponse
from app.services.poster_scanner import extract_text_from_image, match_candidates_from_ocr

router = APIRouter(tags=["Poster Scanner"])


@router.post("/poster/scan", response_model=PosterScanResponse)
async def scan_campaign_poster(
    file: UploadFile = File(..., description="Campaign poster image file (JPEG, PNG, WebP)"),
    constituency_id: Optional[int] = Query(None, description="Optional constituency ID to filter or boost matching candidates"),
    db: Session = Depends(get_db),
) -> PosterScanResponse:
    """Scan a campaign poster image, extract text via OCR, and fuzzy match against candidates in the database.

    Privacy Guarantee:
        Uploaded image files are processed strictly in-memory (using BytesIO) and are never written to disk or logged.
    """
    image_bytes = await file.read()
    ocr_text = extract_text_from_image(image_bytes, content_type=file.content_type)
    response = match_candidates_from_ocr(
        ocr_text=ocr_text,
        db=db,
        constituency_id=constituency_id,
    )
    return response
