"""Tests for OCR API endpoints."""

from __future__ import annotations

import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.security import create_access_token
from app.models import User
from app.api.deps import get_current_user, get_db


def create_test_app():
    """Create a test FastAPI app without audit middleware."""
    from fastapi import FastAPI
    from app.api.v1 import api_router
    from app.core import settings

    test_app = FastAPI(
        title="Test API",
        version="1.0.0",
    )

    test_app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Add health endpoint
    @test_app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return test_app


# Simple test client that doesn't require database
@pytest.fixture
async def test_client():
    """Create a test client with mocked dependencies."""
    test_app = create_test_app()

    # Mock authentication
    mock_user = MagicMock(spec=User)
    mock_user.id = "550e8400-e29b-41d4-a716-446655440000"
    mock_user.email = "test@example.com"
    mock_user.is_active = True
    mock_user.is_superuser = True

    # Mock database session
    mock_db = AsyncMock()

    # Override the auth dependency and database
    test_app.dependency_overrides[get_current_user] = lambda: mock_user
    test_app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


class TestOCREndpoints:
    """Test OCR API endpoints."""

    @pytest.fixture
    def mock_ocr_service(self):
        """Create a mock OCR service."""
        with patch("app.api.v1.ocr.OCRService") as mock:
            service_instance = MagicMock()
            mock.return_value = service_instance
            yield service_instance

    @pytest.mark.asyncio
    async def test_get_supported_types(self, test_client):
        """Test getting supported file types."""
        response = await test_client.get("/api/v1/ocr/supported-types")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "supported_types" in data
        assert "descriptions" in data
        assert ".pdf" in data["supported_types"]
        assert ".png" in data["supported_types"]
        assert ".jpg" in data["supported_types"]

    @pytest.mark.asyncio
    async def test_process_document_unsupported_type(self, test_client):
        """Test processing document with unsupported file type."""
        file_content = b"test content"
        files = {"file": ("test.doc", io.BytesIO(file_content), "application/msword")}

        response = await test_client.post(
            "/api/v1/ocr/process",
            files=files,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_process_document_no_file(self, test_client):
        """Test processing without file."""
        response = await test_client.post(
            "/api/v1/ocr/process",
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_process_document_success(self, test_client, mock_ocr_service):
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

        # Mock the audit logging
        with patch("app.api.v1.ocr._log_ocr_operation", new=AsyncMock()):
            response = await test_client.post(
                "/api/v1/ocr/process",
                files=files,
                params={"extract_structured": True},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["file_name"] == "test.pdf"
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_batch_process_too_many_files(self, test_client):
        """Test batch processing with too many files."""
        files = [
            ("files", (f"test{i}.png", io.BytesIO(b"content"), "image/png"))
            for i in range(25)
        ]

        response = await test_client.post(
            "/api/v1/ocr/batch",
            files=files,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Maximum 20 files" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_batch_process_success(self, test_client, mock_ocr_service):
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

        # Mock the audit logging
        with patch("app.api.v1.ocr._log_ocr_operation", new=AsyncMock()):
            response = await test_client.post(
                "/api/v1/ocr/batch",
                files=files,
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
