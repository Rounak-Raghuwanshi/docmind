import uuid

import pytest
from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Chunk, Document, Workspace
from app.rag.ocr import tesseract_available
from app.services.ingestion import Ingestor
from tests.factories import make_docx, make_pdf

from .conftest import Api, ingest


async def test_upload_ingest_ready_with_correct_pages(api: Api, ingestor: Ingestor) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    r = await api.upload(user, ws, "tax-guide.pdf", make_pdf())
    assert r.status_code == 202, r.text
    doc = r.json()
    assert doc["status"] == "queued"
    assert doc["content_type"] == "application/pdf"

    await ingest(ingestor, doc["id"])

    r = await api.client.get(f"/api/documents/{doc['id']}", headers=user["headers"])
    ready = r.json()
    assert ready["status"] == "ready"
    assert ready["pages_total"] == ready["pages_done"] == 3
    assert ready["chunk_count"] >= 1
    assert ready["embedding_model"] == "fake-hashing"

    async with SessionLocal() as s:
        chunks = (
            (
                await s.execute(
                    select(Chunk)
                    .where(Chunk.document_id == uuid.UUID(doc["id"]))
                    .order_by(Chunk.chunk_index)
                )
            )
            .scalars()
            .all()
        )
        assert all(c.workspace_id == uuid.UUID(ws) for c in chunks)
        by_page = {c.page_start: c.content for c in chunks}
        assert len(chunks) == 3, by_page  # page breaks are soft chunk boundaries
        assert any("80D" in c.content and c.page_start == c.page_end == 2 for c in chunks), by_page
        # the running header "INCOME TAX GUIDE" repeats on every page and is stripped
        assert not any("INCOME TAX GUIDE" in c.content for c in chunks)
        assert all(c.context.startswith("tax-guide") for c in chunks)
        version = (await s.get(Workspace, uuid.UUID(ws))).corpus_version  # type: ignore[union-attr]
        assert version == 1

    # the original file is served back to authorised users only
    r = await api.client.get(f"/api/documents/{doc['id']}/file", headers=user["headers"])
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    r = await api.client.get(f"/api/documents/{doc['id']}/pages/2", headers=user["headers"])
    assert any("80D" in c for c in r.json()["chunks"])


async def test_reingestion_is_idempotent(api: Api, ingestor: Ingestor) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    doc_id = (await api.upload(user, ws, "a.pdf", make_pdf())).json()["id"]
    await ingest(ingestor, doc_id)
    await ingest(ingestor, doc_id)
    async with SessionLocal() as s:
        n = await s.scalar(select(func.count()).where(Chunk.document_id == uuid.UUID(doc_id)))
        doc = await s.get(Document, uuid.UUID(doc_id))
    assert doc is not None and n == doc.chunk_count


async def test_duplicate_upload_is_rejected(api: Api) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    pdf = make_pdf()
    first = await api.upload(user, ws, "a.pdf", pdf)
    r = await api.upload(user, ws, "renamed.pdf", pdf)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "duplicate_document"
    assert r.json()["error"]["details"]["document_id"] == first.json()["id"]
    # ...but the same file is fine in a different workspace
    other = (
        await api.client.post("/api/workspaces", headers=user["headers"], json={"name": "B"})
    ).json()["id"]
    assert (await api.upload(user, other, "a.pdf", pdf)).status_code == 202


async def test_upload_validation(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    r = await api.upload(user, ws, "fake.pdf", b"MZ this is an exe")
    assert r.status_code == 415
    r = await api.upload(user, ws, "script.sh", b"#!/bin/sh")
    assert r.status_code == 415
    r = await api.upload(user, ws, "empty.txt", b"")
    assert r.status_code == 400
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    r = await api.upload(user, ws, "big.txt", b"x" * 10)
    assert r.status_code == 413


async def test_docx_and_markdown_ingest(api: Api, ingestor: Ingestor) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    docx = make_docx(
        [("Heading 1", "Leave policy"), ("Normal", "Employees receive 24 days of paid leave.")]
    )
    md = b"# Travel\n\nEconomy class for flights under six hours.\n\n# Meals\n\nUp to Rs 1500 per day."
    for name, data in (("hr.docx", docx), ("travel.md", md)):
        doc_id = (await api.upload(user, ws, name, data)).json()["id"]
        await ingest(ingestor, doc_id)
        r = await api.client.get(f"/api/documents/{doc_id}", headers=user["headers"])
        assert r.json()["status"] == "ready", name


async def test_unreadable_pdf_fails_with_readable_reason(api: Api, ingestor: Ingestor) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    blank = make_pdf(["", ""])
    doc_id = (await api.upload(user, ws, "scan.pdf", blank)).json()["id"]
    from app.rag.parser import IngestionError

    with pytest.raises(IngestionError):
        await ingestor.run(uuid.UUID(doc_id))


@pytest.mark.skipif(not tesseract_available(), reason="tesseract not installed")
async def test_scanned_page_is_ocred(api: Api, ingestor: Ingestor) -> None:
    import pymupdf

    # Render text to an image, then build a PDF that contains only that image (a "scan").
    src = pymupdf.open(stream=make_pdf(["Section 80D allows a deduction for health insurance."]))
    pix = src[0].get_pixmap(dpi=200)
    scan = pymupdf.open()
    page = scan.new_page()
    page.insert_image(page.rect, pixmap=pix)
    user = await api.signup()
    ws = await api.personal_workspace(user)
    doc_id = (await api.upload(user, ws, "scan.pdf", scan.tobytes())).json()["id"]
    await ingest(ingestor, doc_id)
    r = await api.client.get(f"/api/documents/{doc_id}/pages/1", headers=user["headers"])
    assert "80D" in " ".join(r.json()["chunks"])


async def test_delete_document_removes_chunks_and_bumps_version(
    api: Api, ingestor: Ingestor
) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    doc_id = (await api.upload(user, ws, "a.pdf", make_pdf())).json()["id"]
    await ingest(ingestor, doc_id)
    r = await api.client.delete(f"/api/documents/{doc_id}", headers=user["headers"])
    assert r.status_code == 204
    async with SessionLocal() as s:
        assert (
            await s.scalar(select(func.count()).where(Chunk.document_id == uuid.UUID(doc_id))) == 0
        )
        assert (await s.get(Workspace, uuid.UUID(ws))).corpus_version == 2  # type: ignore[union-attr]


async def test_list_documents_paginates(api: Api) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    for i in range(3):
        await api.upload(user, ws, f"n{i}.txt", f"note number {i}".encode())
    r = await api.client.get(f"/api/workspaces/{ws}/documents?limit=2", headers=user["headers"])
    page1 = r.json()
    assert len(page1["items"]) == 2 and page1["next_cursor"]
    r = await api.client.get(
        f"/api/workspaces/{ws}/documents?limit=2&cursor={page1['next_cursor']}",
        headers=user["headers"],
    )
    page2 = r.json()
    assert len(page2["items"]) == 1 and page2["next_cursor"] is None
    names = {d["filename"] for d in page1["items"] + page2["items"]}
    assert names == {"n0.txt", "n1.txt", "n2.txt"}
