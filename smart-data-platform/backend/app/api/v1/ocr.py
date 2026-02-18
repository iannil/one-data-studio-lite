from __future__ import annotations

import os
import tempfile
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DBSession
from app.models import AuditLog, AuditAction
from app.schemas.ocr import (
    OCRProcessRequest,
    OCRProcessResponse,
    OCRBatchResponse,
    SupportedTypesResponse,
)
from app.services.ocr_service import OCRService

router = APIRouter(prefix="/ocr", tags=["OCR Document Processing"])

SUPPORTED_FILE_TYPES = {
    ".pdf": "PDF documents",
    ".png": "PNG images",
    ".jpg": "JPEG images",
    ".jpeg": "JPEG images",
    ".tiff": "TIFF images",
    ".bmp": "BMP images",
}


async def _log_ocr_operation(
    db: DBSession,
    user: CurrentUser,
    action: AuditAction,
    file_name: str,
    success: bool,
    error: str | None = None,
) -> None:
    """Log OCR operation to audit log."""
    audit = AuditLog(
        user_id=user.id,
        user_email=user.email,
        action=action,
        resource_type="ocr_document",
        resource_name=file_name,
        description=f"OCR {'succeeded' if success else 'failed'}: {file_name}",
        new_value={"success": success, "error": error} if error else {"success": success},
    )
    db.add(audit)
    await db.commit()


@router.post("/process", response_model=OCRProcessResponse)
async def process_document(
    file: UploadFile = File(...),
    extract_structured: bool = True,
    db: DBSession = None,
    current_user: CurrentUser = None,
) -> OCRProcessResponse:
    """Process a single document with OCR.

    Upload a PDF or image file and extract text using OCR.
    Optionally use AI to extract structured data from the text.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required",
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Supported: {list(SUPPORTED_FILE_TYPES.keys())}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        ocr_service = OCRService()
        result = await ocr_service.process_document(
            file_path=tmp_path,
            extract_structured=extract_structured,
        )

        await _log_ocr_operation(db, current_user, AuditAction.EXECUTE, file.filename, True)

        return OCRProcessResponse(
            file_name=result.get("file_name", file.filename),
            file_type=result.get("file_type", ext),
            raw_text=result.get("raw_text", ""),
            structured_data=result.get("structured_data"),
            status="success",
        )

    except FileNotFoundError as e:
        await _log_ocr_operation(db, current_user, AuditAction.EXECUTE, file.filename, False, str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        await _log_ocr_operation(db, current_user, AuditAction.EXECUTE, file.filename, False, str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        await _log_ocr_operation(db, current_user, AuditAction.EXECUTE, file.filename, False, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}",
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/batch", response_model=OCRBatchResponse)
async def batch_process_documents(
    files: list[UploadFile] = File(...),
    extract_structured: bool = True,
    db: DBSession = None,
    current_user: CurrentUser = None,
) -> OCRBatchResponse:
    """Process multiple documents with OCR.

    Upload multiple PDF or image files and extract text from each.
    Returns results for all files, including any that failed.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required",
        )

    if len(files) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 files allowed per batch",
        )

    results: list[OCRProcessResponse] = []
    successful = 0
    failed = 0

    ocr_service = OCRService()

    for file in files:
        if not file.filename:
            results.append(OCRProcessResponse(
                file_name="unknown",
                file_type="unknown",
                raw_text="",
                status="error",
                error="File name is required",
            ))
            failed += 1
            continue

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in SUPPORTED_FILE_TYPES:
            results.append(OCRProcessResponse(
                file_name=file.filename,
                file_type=ext,
                raw_text="",
                status="error",
                error=f"Unsupported file type: {ext}",
            ))
            failed += 1
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = await ocr_service.process_document(
                file_path=tmp_path,
                extract_structured=extract_structured,
            )

            results.append(OCRProcessResponse(
                file_name=result.get("file_name", file.filename),
                file_type=result.get("file_type", ext),
                raw_text=result.get("raw_text", ""),
                structured_data=result.get("structured_data"),
                status="success",
            ))
            successful += 1

        except Exception as e:
            results.append(OCRProcessResponse(
                file_name=file.filename,
                file_type=ext,
                raw_text="",
                status="error",
                error=str(e),
            ))
            failed += 1

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    await _log_ocr_operation(
        db, current_user, AuditAction.EXECUTE,
        f"batch_{len(files)}_files",
        failed == 0,
        f"{successful} succeeded, {failed} failed" if failed > 0 else None,
    )

    return OCRBatchResponse(
        results=results,
        total=len(files),
        successful=successful,
        failed=failed,
    )


@router.get("/supported-types", response_model=SupportedTypesResponse)
async def get_supported_types() -> SupportedTypesResponse:
    """Get list of supported file types for OCR.

    Returns all file extensions that can be processed,
    along with descriptions of each type.
    """
    return SupportedTypesResponse(
        supported_types=list(SUPPORTED_FILE_TYPES.keys()),
        descriptions=SUPPORTED_FILE_TYPES,
    )
