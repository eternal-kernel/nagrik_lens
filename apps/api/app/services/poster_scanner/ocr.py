import io
from typing import Optional
from fastapi import HTTPException, status
from PIL import Image, ImageOps, UnidentifiedImageError
import pytesseract

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/jpg",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def extract_text_from_image(
    image_bytes: bytes,
    content_type: Optional[str] = None,
) -> str:
    """Validate image bytes, preprocess, and extract text using PyTesseract.

    Args:
        image_bytes: Raw binary bytes of uploaded image.
        content_type: MIME content type header (if provided).

    Returns:
        Extracted text string from OCR.

    Raises:
        HTTPException: If file is too large, format is invalid, or image cannot be decoded.
    """
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty.",
        )

    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image file exceeds maximum permitted size of {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type '{content_type}'. Allowed formats: JPEG, PNG, WebP.",
        )

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()  # Verify integrity of file header
    except (UnidentifiedImageError, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid or decodable image.",
        ) from exc

    # Re-open after verify() (Pillow closes file on verify)
    image = Image.open(io.BytesIO(image_bytes))

    # Convert transparency/palette to clean RGB with white background
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[3])
        image = background
    else:
        image = image.convert("RGB")

    # Determine available Tesseract languages
    try:
        available_langs = pytesseract.get_languages()
    except Exception:
        available_langs = ["eng"]

    wanted = ["eng", "hin", "tel"]
    active_langs = [l for l in wanted if l in available_langs]
    lang_str = "+".join(active_langs) if active_langs else "eng"

    try:
        text = pytesseract.image_to_string(image, lang=lang_str)
    except pytesseract.TesseractError:
        # Graceful fallback to pure English if multi-lang fails
        try:
            text = pytesseract.image_to_string(image, lang="eng")
        except Exception as ocr_err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OCR engine failure: {ocr_err}",
            ) from ocr_err

    return text.strip()
