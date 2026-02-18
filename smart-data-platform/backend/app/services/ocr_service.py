from __future__ import annotations

from pathlib import Path
from typing import Any

import pytesseract
from openai import AsyncOpenAI
from pdf2image import convert_from_path
from PIL import Image

from app.core.config import settings


class OCRService:
    """Service for OCR and document processing."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def process_document(
        self,
        file_path: str,
        extract_structured: bool = True,
    ) -> dict[str, Any]:
        """Process a document and extract text/structured data."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() == ".pdf":
            text = await self._process_pdf(path)
        elif path.suffix.lower() in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            text = await self._process_image(path)
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        result: dict[str, Any] = {
            "raw_text": text,
            "file_name": path.name,
            "file_type": path.suffix.lower(),
        }

        if extract_structured:
            structured = await self._extract_structured_data(text)
            result["structured_data"] = structured

        return result

    async def _process_pdf(self, path: Path) -> str:
        """Process PDF file using OCR."""
        images = convert_from_path(str(path))
        texts = []

        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image, lang="chi_sim+eng")
            texts.append(f"--- Page {i + 1} ---\n{text}")

        return "\n\n".join(texts)

    async def _process_image(self, path: Path) -> str:
        """Process image file using OCR."""
        image = Image.open(path)
        return pytesseract.image_to_string(image, lang="chi_sim+eng")

    async def _extract_structured_data(self, text: str) -> dict[str, Any]:
        """Use AI to extract structured data from OCR text."""
        prompt = f"""Extract structured information from the following OCR text.
Identify and extract:
1. Key-value pairs (e.g., Name: John, Date: 2024-01-01)
2. Tables or tabular data
3. Important entities (names, dates, amounts, etc.)
4. Document type and category

OCR Text:
{text[:4000]}

Respond in JSON format:
{{
  "document_type": "invoice|receipt|contract|form|other",
  "key_values": {{"key": "value"}},
  "tables": [
    {{
      "headers": ["col1", "col2"],
      "rows": [["val1", "val2"]]
    }}
  ],
  "entities": {{
    "names": [],
    "dates": [],
    "amounts": [],
    "addresses": []
  }},
  "summary": "Brief summary of the document"
}}"""

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a document analysis expert. Extract structured data from OCR text.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        import json
        return json.loads(response.choices[0].message.content or "{}")

    async def batch_process(
        self,
        file_paths: list[str],
        extract_structured: bool = True,
    ) -> list[dict[str, Any]]:
        """Process multiple documents."""
        results = []

        for file_path in file_paths:
            try:
                result = await self.process_document(file_path, extract_structured)
                result["status"] = "success"
            except Exception as e:
                result = {
                    "file_path": file_path,
                    "status": "error",
                    "error": str(e),
                }
            results.append(result)

        return results
