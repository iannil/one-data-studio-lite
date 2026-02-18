"""Tests for OCR API endpoints."""

from __future__ import annotations

import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status


class TestOCREndpoints:
    """Test OCR API endpoints."""

    @pytest.fixture
    def mock_ocr_service(self):
        """Create a mock OCR service."""
        with patch("app.api.v1.ocr.OCRService") as mock:
            service_instance = MagicMock()
            mock.return_value = service_instance
            yield service_instance

    def test_get_supported_types(self, client, auth_headers):
        """Test getting supported file types."""
        response = client.get("/api/v1/ocr/supported-types", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "supported_types" in data
        assert "descriptions" in data
        assert ".pdf" in data["supported_types"]
        assert ".png" in data["supported_types"]
        assert ".jpg" in data["supported_types"]

    def test_process_document_unsupported_type(self, client, auth_headers):
        """Test processing document with unsupported file type."""
        file_content = b"test content"
        files = {"file": ("test.doc", io.BytesIO(file_content), "application/msword")}

        response = client.post(
            "/api/v1/ocr/process",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported file type" in response.json()["detail"]

    def test_process_document_no_file(self, client, auth_headers):
        """Test processing without file."""
        response = client.post(
            "/api/v1/ocr/process",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_process_document_success(self, client, auth_headers, mock_ocr_service):
        """Test successful document processing."""
        mock_ocr_service.process_document = AsyncMock(return_value={
            "file_name": "test.pdf",
            "file_type": ".pdf",
            "raw_text": "Sample OCR text",
            "structured_data": {
                "document_type": "invoice",
                "key_values": {"total": "100.00"},
            },
        })

        file_content = b"%PDF-1.4 fake pdf content"
        files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

        response = client.post(
            "/api/v1/ocr/process",
            files=files,
            params={"extract_structured": True},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["file_name"] == "test.pdf"
        assert data["status"] == "success"

    def test_batch_process_too_many_files(self, client, auth_headers):
        """Test batch processing with too many files."""
        files = [
            ("files", (f"test{i}.png", io.BytesIO(b"content"), "image/png"))
            for i in range(25)
        ]

        response = client.post(
            "/api/v1/ocr/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Maximum 20 files" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_batch_process_success(self, client, auth_headers, mock_ocr_service):
        """Test successful batch processing."""
        mock_ocr_service.process_document = AsyncMock(return_value={
            "file_name": "test.png",
            "file_type": ".png",
            "raw_text": "Sample text",
        })

        files = [
            ("files", ("test1.png", io.BytesIO(b"content1"), "image/png")),
            ("files", ("test2.png", io.BytesIO(b"content2"), "image/png")),
        ]

        response = client.post(
            "/api/v1/ocr/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2


class TestOCRSchemas:
    """Test OCR Pydantic schemas."""

    def test_ocr_process_response_schema(self):
        """Test OCRProcessResponse schema."""
        from app.schemas.ocr import OCRProcessResponse

        response = OCRProcessResponse(
            file_name="test.pdf",
            file_type=".pdf",
            raw_text="Sample text",
            status="success",
        )

        assert response.file_name == "test.pdf"
        assert response.status == "success"
        assert response.structured_data is None
        assert response.error is None

    def test_ocr_batch_response_schema(self):
        """Test OCRBatchResponse schema."""
        from app.schemas.ocr import OCRBatchResponse, OCRProcessResponse

        results = [
            OCRProcessResponse(
                file_name="test1.pdf",
                file_type=".pdf",
                raw_text="Text 1",
                status="success",
            ),
            OCRProcessResponse(
                file_name="test2.pdf",
                file_type=".pdf",
                raw_text="",
                status="error",
                error="Processing failed",
            ),
        ]

        batch = OCRBatchResponse(
            results=results,
            total=2,
            successful=1,
            failed=1,
        )

        assert batch.total == 2
        assert batch.successful == 1
        assert batch.failed == 1
        assert len(batch.results) == 2
