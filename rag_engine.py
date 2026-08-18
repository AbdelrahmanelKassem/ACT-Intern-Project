import logging
import re
from enum import Enum
from io import BytesIO

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document as DocxDocument
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class SourceType(str, Enum):
    URL = "url"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    DATABASE = "database"


class DocumentProcessingError(Exception):
    pass


_TABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


async def process_document(source_url: str, source_type: str) -> str:
    if not source_url or not source_url.strip():
        raise DocumentProcessingError("source_url is empty.")

    try:
        source_type_enum = SourceType(source_type.lower())
    except ValueError:
        raise DocumentProcessingError(
            f"Unsupported source_type '{source_type}'. "
            f"Expected one of: {[t.value for t in SourceType]}"
        )

    logger.info(f"Processing document: {source_url} (type={source_type_enum})")

    if source_type_enum == SourceType.URL:
        raw_text = await _extract_from_webpage(source_url)
    elif source_type_enum == SourceType.DATABASE:
        raw_text = await _extract_from_database(source_url)
    else:
        file_bytes = await _download_bytes(source_url)
        if source_type_enum == SourceType.PDF:
            raw_text = _extract_from_pdf(file_bytes)
        elif source_type_enum == SourceType.DOCX:
            raw_text = _extract_from_docx(file_bytes)
        else:
            raw_text = file_bytes.decode("utf-8", errors="ignore")

    raw_text = _clean_text(raw_text)

    if not raw_text:
        raise DocumentProcessingError(
            f"No extractable text found at {source_url}."
        )

    logger.info(f"Extracted {len(raw_text)} characters from {source_url}")
    return raw_text


async def _download_bytes(url: str) -> bytes:
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
    except httpx.HTTPError as e:
        raise DocumentProcessingError(f"Failed to download {url}: {e}")


async def _extract_from_webpage(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "HotelChatbot/1.0"})
            response.raise_for_status()
    except httpx.HTTPError as e:
        raise DocumentProcessingError(f"Failed to fetch {url}: {e}")

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    return soup.get_text(separator="\n")


async def _extract_from_database(table_name: str) -> str:
    if not _TABLE_NAME_PATTERN.match(table_name):
        raise DocumentProcessingError(
            f"Invalid database source '{table_name}'. Expected a plain table name."
        )

    try:
        async with AsyncSessionLocal() as session:  # type: AsyncSession
            result = await session.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.mappings().all()
    except Exception as e:
        raise DocumentProcessingError(f"Failed to query database table '{table_name}': {e}")

    if not rows:
        return ""

    lines = []
    for row in rows:
        row_text = ", ".join(f"{key}: {value}" for key, value in row.items() if value is not None)
        lines.append(row_text)

    return "\n".join(lines)


def _extract_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise DocumentProcessingError(f"Failed to parse PDF: {e}")


def _extract_from_docx(file_bytes: bytes) -> str:
    try:
        doc = DocxDocument(BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        raise DocumentProcessingError(f"Failed to parse DOCX: {e}")


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()
