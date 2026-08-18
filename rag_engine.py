import logging
import re
import uuid
from enum import Enum
from io import BytesIO

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document as DocxDocument
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai

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
        row_text = ", ".join(f"{key}: {value}" for row in rows for key, value in row.items() if value is not None)
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




async def embed_vectors(chunks: list[str], document_id: str, db: AsyncSession) -> None:
    """
    Loops through the text chunks, calls the Gemini embedding AI model to convert 
    them into mathematical vectors, and saves them permanently into the database.
    """
    try:
        for chunk_text in chunks:
            # 1. Generate the vector using Google Gemini
            embedding_response = genai.embed_content(
                model="models/gemini-embedding-001",
                content=chunk_text,
                task_type="retrieval_document"
            )
            
            # The API returns a list of floats (3072 dimensions)
            vector_array = embedding_response['embedding']
            
            # Format the vector as a string so PostgreSQL's pgvector extension can read it
            formatted_vector = f"[{','.join(map(str, vector_array))}]"
            
            # 2. Generate a unique ID for this chunk
            chunk_id = str(uuid.uuid4())
            
            # 3. Save to database using raw SQL text mapping to your schema
            insert_query = text("""
                INSERT INTO chunking_table (id, document_id, content_text, vector_embedding)
                VALUES (:id, :document_id, :content_text, :vector_embedding)
            """)
            
            await db.execute(insert_query, {
                "id": chunk_id,
                "document_id": document_id,
                "content_text": chunk_text,
                "vector_embedding": formatted_vector
            })
        
        # 4. Commit all inserted chunks to the database
        await db.commit()
        logger.info(f"Successfully embedded and saved {len(chunks)} chunks for document {document_id}")
        
    except Exception as e:
        # If anything fails, rollback so we don't save partial data
        await db.rollback()
        logger.error(f"Failed to embed vectors for document {document_id}: {e}")
        raise DocumentProcessingError(f"Embedding failed: {e}")