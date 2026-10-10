from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
import re
from typing import Protocol
from urllib.parse import urlparse
from zipfile import ZIP_DEFLATED, ZipFile


MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
MAX_PACKET_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class ResolvedDocument:
    content: bytes
    content_type: str
    filename: str


@dataclass(frozen=True)
class GeneratedPacket:
    content: bytes
    filename: str
    manifest: dict


class DocumentResolver(Protocol):
    def fetch(self, storage_reference: str) -> ResolvedDocument: ...


def safe_filename(value: str, fallback: str = "document") -> str:
    value = re.sub(r"[^A-Za-z0-9._ -]+", "", value or "").strip()
    value = re.sub(r"\s+", "_", value)
    value = value.strip("._")
    return (value or fallback)[:160]


class GCSDocumentResolver:
    def __init__(self, *, allowed_buckets: set[str]):
        if not allowed_buckets:
            raise ValueError("At least one approved source-document bucket is required")
        self.allowed_buckets = set(allowed_buckets)

    def fetch(self, storage_reference: str) -> ResolvedDocument:
        parsed = urlparse(storage_reference)
        if parsed.scheme != "gs" or not parsed.netloc or not parsed.path.startswith("/"):
            raise ValueError("Only approved gs:// document references are supported")
        bucket_name = parsed.netloc
        if bucket_name not in self.allowed_buckets:
            raise ValueError("Document bucket is not approved for submission export")
        object_name = parsed.path.lstrip("/")
        if not object_name or ".." in object_name.split("/"):
            raise ValueError("Invalid document object path")

        from google.cloud import storage

        client = storage.Client()
        blob = client.bucket(bucket_name).blob(object_name)
        blob.reload()
        size = int(blob.size or 0)
        if size <= 0 or size > MAX_DOCUMENT_BYTES:
            raise ValueError("Submission source document has an invalid size")
        content = blob.download_as_bytes(timeout=30)
        if len(content) > MAX_DOCUMENT_BYTES:
            raise ValueError("Submission source document is too large")
        content_type = blob.content_type or "application/octet-stream"
        filename = object_name.rsplit("/", 1)[-1]
        return ResolvedDocument(
            content=content,
            content_type=content_type,
            filename=safe_filename(filename, "document"),
        )


class SubmissionPacketGenerator:
    def __init__(self, resolver: DocumentResolver):
        self.resolver = resolver

    @staticmethod
    def _text_pdf(title: str, sections: list[tuple[str, str]]) -> bytes:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        out = BytesIO()
        doc = SimpleDocTemplate(
            out,
            pagesize=LETTER,
            rightMargin=42,
            leftMargin=42,
            topMargin=42,
            bottomMargin=42,
            title=title,
        )
        styles = getSampleStyleSheet()
        story = [Paragraph(title, styles["Title"]), Spacer(1, 14)]
        for heading, body in sections:
            if heading:
                story.extend([Paragraph(heading, styles["Heading2"]), Spacer(1, 5)])
            for paragraph in str(body or "").split("\n"):
                text = paragraph.strip()
                if not text:
                    story.append(Spacer(1, 6))
                    continue
                if text.startswith("#"):
                    clean = text.lstrip("#").strip()
                    story.append(Paragraph(clean, styles["Heading2"]))
                elif text.startswith(("- ", "* ")):
                    story.append(Paragraph("• " + text[2:].strip(), styles["BodyText"]))
                else:
                    story.append(Paragraph(text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles["BodyText"]))
                story.append(Spacer(1, 4))
        doc.build(story)
        return out.getvalue()

    @staticmethod
    def _image_to_pdf(document: ResolvedDocument) -> bytes:
        from PIL import Image

        image = Image.open(BytesIO(document.content))
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        out = BytesIO()
        image.save(out, format="PDF", resolution=144.0)
        return out.getvalue()

    @staticmethod
    def _merge_pdfs(pdf_parts: list[bytes]) -> bytes:
        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()
        for content in pdf_parts:
            reader = PdfReader(BytesIO(content), strict=False)
            for page in reader.pages:
                writer.add_page(page)
        out = BytesIO()
        writer.write(out)
        return out.getvalue()

    def generate(self, context: dict) -> GeneratedPacket:
        candidate = context["candidate"]
        job = context["job"]
        package = context["package"]
        summary = str(context.get("candidate_summary") or "").strip()
        resume_text = str(context.get("resume_text") or "").strip()
        if not summary:
            raise ValueError("Reviewed candidate presentation is required")
        if not resume_text:
            raise ValueError("Reviewed resume content is required")

        candidate_name = candidate.get("canonical_name") or "Candidate"
        role = candidate.get("specialty") or candidate.get("profession") or job.get("title") or "Submission"
        base = safe_filename(f"{candidate_name}_{role}_Submission_v{package['version']}", "Medlivo_Submission")

        presentation_sections = [
            ("Candidate", candidate_name),
            ("Position", job.get("title") or ""),
            ("Division", job.get("division") or ""),
            ("Location", ", ".join(x for x in [job.get("city"), job.get("state")] if x)),
            ("Candidate Presentation", summary),
        ]
        licenses = context.get("licenses") or []
        if licenses:
            license_lines = []
            for row in licenses:
                state = row.get("state") or ""
                number = row.get("license_number") or ""
                expires = row.get("expires_at") or ""
                status = row.get("status") or ""
                license_lines.append(f"{state} {row.get('license_type') or 'License'} #{number} · {status} · Expires {expires}".strip())
            presentation_sections.append(("Licensure", "\n".join(license_lines)))

        presentation_pdf = self._text_pdf("Medlivo Candidate Presentation", presentation_sections)
        resume_pdf = self._text_pdf(
            f"{candidate_name} · Resume",
            [("", resume_text)],
        )

        pdf_parts = [presentation_pdf, resume_pdf]
        source_files = []
        warnings = []
        total_bytes = len(presentation_pdf) + len(resume_pdf)
        for index, item in enumerate(context.get("supporting_documents") or [], start=2):
            storage_reference = item.get("storage_reference")
            if not storage_reference:
                if item.get("required"):
                    raise ValueError(f"Required document is not retrievable: {item.get('label') or 'document'}")
                continue
            document = self.resolver.fetch(storage_reference)
            total_bytes += len(document.content)
            if total_bytes > MAX_PACKET_BYTES:
                raise ValueError("Submission packet exceeds the maximum export size")
            suffix = ""
            if "." in document.filename:
                suffix = "." + document.filename.rsplit(".", 1)[-1].lower()
            filename = f"{index:02d}_{safe_filename(item.get('label') or document.filename)}{suffix}"
            source_files.append((filename, document))
            if document.content_type == "application/pdf" or suffix == ".pdf":
                pdf_parts.append(document.content)
            elif document.content_type in {"image/jpeg", "image/png", "image/webp"} or suffix in {".jpg", ".jpeg", ".png", ".webp"}:
                try:
                    pdf_parts.append(self._image_to_pdf(document))
                except Exception:
                    warnings.append(f"{filename} could not be added to the combined PDF; original is included in ZIP.")
            else:
                warnings.append(f"{filename} is included as an original file but not converted into the combined PDF.")

        combined_pdf = self._merge_pdfs(pdf_parts)
        manifest = {
            "candidate": candidate_name,
            "job": job.get("title"),
            "division": job.get("division"),
            "template": context.get("template_name"),
            "template_version": package.get("template_version"),
            "package_version": package.get("version"),
            "documents": [
                {"filename": name, "label": item.get("label")}
                for (name, _), item in zip(source_files, context.get("supporting_documents") or [])
            ],
            "warnings": warnings,
            "generated_by": "Medlivo Submission Studio",
        }

        out = BytesIO()
        with ZipFile(out, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr(f"{base}_Combined.pdf", combined_pdf)
            archive.writestr("00_Candidate_Presentation.pdf", presentation_pdf)
            archive.writestr("01_Resume.pdf", resume_pdf)
            for filename, document in source_files:
                archive.writestr(filename, document.content)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
        content = out.getvalue()
        if len(content) > MAX_PACKET_BYTES:
            raise ValueError("Generated submission package is too large")
        return GeneratedPacket(content=content, filename=base + ".zip", manifest=manifest)
