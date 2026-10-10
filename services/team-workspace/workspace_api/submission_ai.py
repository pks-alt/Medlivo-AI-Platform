from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol


@dataclass(frozen=True)
class SubmissionAIResult:
    candidate_summary: str
    resume_markdown: str
    claims: list[dict]
    warnings: list[str]
    provider: str
    model: str


class SubmissionAIComposer(Protocol):
    def compose(self, context: dict) -> SubmissionAIResult: ...


class VertexGeminiSubmissionAIComposer:
    """Source-grounded narrative/resume composer using Google Gen AI SDK on Vertex AI."""

    def __init__(self, *, project: str, location: str, model: str):
        if not project or not location or not model:
            raise ValueError("Submission AI project, location, and model are required")
        self.project = project
        self.location = location
        self.model = model

    def compose(self, context: dict) -> SubmissionAIResult:
        # Import lazily so disabled/test environments do not initialize model clients.
        from google import genai
        from google.genai.types import GenerateContentConfig, HttpOptions

        client = genai.Client(
            vertexai=True,
            project=self.project,
            location=self.location,
            http_options=HttpOptions(api_version="v1"),
        )
        system = (
            "You are the Medlivo healthcare staffing submission composer. "
            "Use ONLY facts provided in SOURCE_CONTEXT. Never invent experience, dates, "
            "skills, licenses, certifications, case volume, procedures, availability, "
            "malpractice history, rates, or customer requirements. If a useful claim is "
            "not supported, omit it. Preserve employment gaps rather than hiding them. "
            "Do not include home address, DOB, SSN, government ID data, vaccination details, "
            "or other restricted information unless SOURCE_CONTEXT explicitly marks the "
            "field as allowed_for_narrative=true. Remove drafting/editorial notes from resume text. "
            "Return concise professional language suitable for recruiter review, not final autonomous submission."
        )
        prompt = {
            "task": {
                "candidate_summary": (
                    "Draft a concise customer-facing presentation focused on direct fit for this job."
                ),
                "resume_markdown": (
                    "Create a clean Medlivo-formatted resume in Markdown. Reorder source-supported "
                    "experience for relevance, but do not change facts."
                ),
                "claims": (
                    "List material claims used in candidate_summary with source_keys supporting each claim."
                ),
                "warnings": (
                    "List factual conflicts, stale credentials, suspicious drafting artifacts, or missing "
                    "information that a recruiter should review."
                ),
            },
            "SOURCE_CONTEXT": context,
            "required_json_shape": {
                "candidate_summary": "string",
                "resume_markdown": "string",
                "claims": [{"text": "string", "source_keys": ["string"]}],
                "warnings": ["string"],
            },
        }
        response = client.models.generate_content(
            model=self.model,
            contents=json.dumps(prompt, separators=(",", ":"), default=str),
            config=GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=0,
                max_output_tokens=12000,
            ),
        )
        raw = json.loads(response.text or "{}")
        summary = str(raw.get("candidate_summary") or "").strip()
        resume = str(raw.get("resume_markdown") or "").strip()
        claims = raw.get("claims") if isinstance(raw.get("claims"), list) else []
        warnings = raw.get("warnings") if isinstance(raw.get("warnings"), list) else []
        if not summary or not resume:
            raise ValueError("Submission AI returned incomplete structured output")

        allowed_keys = set(context.get("source_keys") or [])
        safe_claims = []
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            text = str(claim.get("text") or "").strip()
            source_keys = claim.get("source_keys")
            if not text or not isinstance(source_keys, list) or not source_keys:
                continue
            normalized = [str(x) for x in source_keys]
            if not set(normalized).issubset(allowed_keys):
                raise ValueError("Submission AI cited unsupported source keys")
            safe_claims.append({"text": text, "source_keys": normalized})

        return SubmissionAIResult(
            candidate_summary=summary,
            resume_markdown=resume,
            claims=safe_claims,
            warnings=[str(x)[:1000] for x in warnings if str(x).strip()][:50],
            provider="vertex_gemini",
            model=self.model,
        )
