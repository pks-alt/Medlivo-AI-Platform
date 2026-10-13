from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol


@dataclass(frozen=True)
class OutreachAIResult:
    subject: str | None
    body: str
    warnings: list[str]
    provider: str
    model: str


class OutreachAIComposer(Protocol):
    def compose(self, context: dict) -> OutreachAIResult: ...


class VertexGeminiOutreachAIComposer:
    """Source-grounded recruiter email/SMS drafter for human review."""

    def __init__(self, *, project: str, location: str, model: str):
        if not project or not location or not model:
            raise ValueError("Outreach AI project, location, and model are required")
        self.project = project
        self.location = location
        self.model = model

    def compose(self, context: dict) -> OutreachAIResult:
        from google import genai
        from google.genai.types import GenerateContentConfig, HttpOptions

        client = genai.Client(
            vertexai=True,
            project=self.project,
            location=self.location,
            http_options=HttpOptions(api_version="v1"),
        )
        channel = str(context.get("channel") or "email")
        system = (
            "You are the Medlivo healthcare staffing recruiter communication assistant. "
            "Draft a concise HUMAN-REVIEWED recruiter message using ONLY SOURCE_CONTEXT. "
            "Never invent pay, stipend amounts, housing availability, client promises, interview outcomes, "
            "licenses, certifications, credentialing status, schedule details, dates, or candidate preferences. "
            "If a requested fact is not supported, say it needs confirmation rather than guessing. "
            "Do not make autonomous commitments. Do not pressure the candidate. "
            "Do not include sensitive health information or restricted personal data. "
            "Email should be warm and professional. SMS should be concise and natural. "
            "Return JSON only."
        )
        prompt = {
            "channel": channel,
            "purpose": context.get("purpose"),
            "instruction": context.get("instruction"),
            "SOURCE_CONTEXT": context.get("source_context") or {},
            "required_json_shape": {
                "subject": "string or null",
                "body": "string",
                "warnings": ["string"],
            },
        }
        response = client.models.generate_content(
            model=self.model,
            contents=json.dumps(prompt, separators=(",", ":"), default=str),
            config=GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=2200,
            ),
        )
        raw = json.loads(response.text or "{}")
        body = str(raw.get("body") or "").strip()
        if not body:
            raise ValueError("Outreach AI returned an empty draft")
        subject = raw.get("subject")
        if channel == "sms":
            subject = None
            body = body[:1200]
        else:
            subject = str(subject or "").strip()[:250] or None
            body = body[:6000]
        warnings = raw.get("warnings") if isinstance(raw.get("warnings"), list) else []
        return OutreachAIResult(
            subject=subject,
            body=body,
            warnings=[str(x).strip()[:1000] for x in warnings if str(x).strip()][:30],
            provider="vertex_gemini",
            model=self.model,
        )
