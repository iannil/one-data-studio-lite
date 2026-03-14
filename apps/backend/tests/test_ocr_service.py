"""Tests for OCR service functionality."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ocr_service import OCRService


class TestOCRService:
    """Test suite for OCRService."""

    @pytest.fixture
    def service(self):
        """Create an OCRService instance."""
        with patch("app.services.ocr_service.AsyncOpenAI"):
            return OCRService()

    @pytest.fixture
    def sample_text(self):
        """Sample OCR text for testing."""
        return """
        Invoice #12345
        Date: 2024-01-15
        Customer: John Doe

        Item          Qty    Price
        Widget A      2      $50.00
        Widget B      3      $75.00

        Total: $175.00
        """


class TestDocumentProcessing(TestOCRService):
    """Test document processing operations."""

    @pytest.mark.asyncio
    async def test_process_document_file_not_found(self, service):
        """Test processing nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            await service.process_document("/nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_process_document_unsupported_type(self, service):
        """Test processing unsupported file type raises error."""
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "suffix", new_callable=lambda: property(lambda self: ".xyz")):
                path = Path("/test/file.xyz")
                with pytest.raises(ValueError, match="Unsupported file type"):
                    await service.process_document(str(path))

    @pytest.mark.asyncio
    async def test_process_pdf_document(self, service, sample_text):
        """Test processing PDF document."""
        with patch.object(Path, "exists", return_value=True):
            with patch("app.services.ocr_service.convert_from_path") as mock_convert:
                with patch("app.services.ocr_service.pytesseract") as mock_tesseract:
                    mock_image = MagicMock()
                    mock_convert.return_value = [mock_image]
                    mock_tesseract.image_to_string.return_value = sample_text

                    with patch.object(service, "_extract_structured_data") as mock_extract:
                        mock_extract.return_value = {"document_type": "invoice"}

                        result = await service.process_document("/test/file.pdf")

                        assert result["file_type"] == ".pdf"
                        assert "raw_text" in result
                        assert "structured_data" in result

    @pytest.mark.asyncio
    async def test_process_image_document(self, service, sample_text):
        """Test processing image document."""
        with patch.object(Path, "exists", return_value=True):
            with patch("app.services.ocr_service.Image") as mock_image:
                with patch("app.services.ocr_service.pytesseract") as mock_tesseract:
                    mock_tesseract.image_to_string.return_value = sample_text

                    with patch.object(service, "_extract_structured_data") as mock_extract:
                        mock_extract.return_value = {"document_type": "receipt"}

                        result = await service.process_document("/test/file.png")

                        assert result["file_type"] == ".png"

    @pytest.mark.asyncio
    async def test_process_document_without_structured(self, service, sample_text):
        """Test processing without structured data extraction."""
        with patch.object(Path, "exists", return_value=True):
            with patch("app.services.ocr_service.Image") as mock_image:
                with patch("app.services.ocr_service.pytesseract") as mock_tesseract:
                    mock_tesseract.image_to_string.return_value = sample_text

                    result = await service.process_document(
                        "/test/file.jpg",
                        extract_structured=False
                    )

                    assert "raw_text" in result
                    assert "structured_data" not in result


class TestStructuredExtraction(TestOCRService):
    """Test structured data extraction."""

    @pytest.mark.asyncio
    async def test_extract_structured_data(self, service, sample_text):
        """Test AI-powered structured data extraction."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "document_type": "invoice",
                        "key_values": {
                            "invoice_number": "12345",
                            "date": "2024-01-15",
                            "customer": "John Doe",
                        },
                        "entities": {
                            "names": ["John Doe"],
                            "dates": ["2024-01-15"],
                            "amounts": ["$175.00"],
                        },
                    })
                )
            )
        ]

        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service._extract_structured_data(sample_text)

        assert result["document_type"] == "invoice"
        assert "key_values" in result
        assert result["key_values"]["invoice_number"] == "12345"


class TestBatchProcessing(TestOCRService):
    """Test batch document processing."""

    @pytest.mark.asyncio
    async def test_batch_process_success(self, service, sample_text):
        """Test batch processing multiple documents."""
        with patch.object(service, "process_document") as mock_process:
            mock_process.return_value = {
                "raw_text": sample_text,
                "structured_data": {"document_type": "invoice"},
            }

            results = await service.batch_process(
                ["/test/file1.pdf", "/test/file2.pdf"]
            )

            assert len(results) == 2
            assert all(r["status"] == "success" for r in results)

    @pytest.mark.asyncio
    async def test_batch_process_with_error(self, service, sample_text):
        """Test batch processing handles errors gracefully."""
        with patch.object(service, "process_document") as mock_process:
            mock_process.side_effect = [
                {"raw_text": sample_text},
                FileNotFoundError("File not found"),
            ]

            results = await service.batch_process(
                ["/test/file1.pdf", "/test/missing.pdf"]
            )

            assert len(results) == 2
            assert results[0]["status"] == "success"
            assert results[1]["status"] == "error"
            assert "error" in results[1]


class TestPDFProcessing(TestOCRService):
    """Test PDF-specific processing."""

    @pytest.mark.asyncio
    async def test_process_pdf_multiple_pages(self, service):
        """Test processing multi-page PDF."""
        with patch("app.services.ocr_service.convert_from_path") as mock_convert:
            with patch("app.services.ocr_service.pytesseract") as mock_tesseract:
                mock_images = [MagicMock(), MagicMock(), MagicMock()]
                mock_convert.return_value = mock_images
                mock_tesseract.image_to_string.side_effect = [
                    "Page 1 content",
                    "Page 2 content",
                    "Page 3 content",
                ]

                result = await service._process_pdf(Path("/test/multi.pdf"))

                assert "Page 1" in result
                assert "Page 2" in result
                assert "Page 3" in result
                assert mock_tesseract.image_to_string.call_count == 3


class TestImageProcessing(TestOCRService):
    """Test image-specific processing."""

    @pytest.mark.asyncio
    async def test_process_image_jpeg(self, service):
        """Test processing JPEG image."""
        with patch("app.services.ocr_service.Image") as mock_image_module:
            with patch("app.services.ocr_service.pytesseract") as mock_tesseract:
                mock_image = MagicMock()
                mock_image_module.open.return_value = mock_image
                mock_tesseract.image_to_string.return_value = "Extracted text"

                result = await service._process_image(Path("/test/image.jpeg"))

                assert result == "Extracted text"
                mock_image_module.open.assert_called_once()
                mock_tesseract.image_to_string.assert_called_once()
