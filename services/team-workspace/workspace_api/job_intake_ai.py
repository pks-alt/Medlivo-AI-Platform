from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol


@dataclass(frozen=True)
class JobIntakeAIResult:
    job_description: str
    responsibilities: list[str]
    required_qualifications: list[str]
    preferred_qualifications: list[str]
    schedule_summary: str | None
    warnings: list[str]
    provider: str
    model: str


class JobIntakeAIComposer(Protocol):
    def compose(self, context: dict) -> JobIntakeAIResult: ...


class VertexGeminiJobIntakeAIComposer:
    """Human-reviewed JD drafter for direct-customer intake."""

    def __init__(self, *, project: str, location: str, model: str):
        if not project or not location or not model:
            raise ValueError("Job Intake AI project, location, and model are required")
        self.project = project
        self.location = location
        self.model = model

    def compose(self, context: dict) -> JobIntakeAIResult:
        from google import genai
        from google.genai.types import GenerateContentConfig, HttpOptions

        client = genai.Client(
            vertexai=True,
            project=self.project,
            location=self.location,
            http_options=HttpOptions(api_version="v1"),
        )
        system = (
            "You are the Medlivo healthcare staffing Job Intake JD drafting assistant. "
            "Create a concise internal recruiting job description for HUMAN REVIEW. "
            "Use confirmed source facts exactly where provided. You MAY draft standard role responsibilities "
            "and common qualifications when the source JD is missing, but those must be treated as AI suggestions, "
            "not customer-confirmed requirements. Never invent pay, dates, schedule, facility facts, licenses, "
            "certifications, headcount, call expectations, shift details, patient ratios, or client-specific policy. "
            "If a material fact is unknown, omit it or place it in warnings. "
            "Return professional healthcare staffing language and JSON only."
        )
        prompt = {
            "task": "Draft an internal JD for manager review before recruiting approval.",
            "SOURCE_CONTEXT": context,
            "required_json_shape": {
                "job_description": "string",
                "responsibilities": ["string"],
                "required_qualifications": ["string"],
                "preferred_qualifications": ["string"],
                "schedule_summary": "string or null",
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
                max_output_tokens=6000,
            ),
        )
        raw = json.loads(response.text or "{}")
        description = str(raw.get("job_description") or "").strip()
        if not description:
            raise ValueError("Job Intake AI returned an empty JD draft")

        def strings(name: str, limit: int = 30) -> list[str]:
            value = raw.get(name)
            if not isinstance(value, list):
                return []
            return [str(x).strip()[:1000] for x in value if str(x).strip()][:limit]

        schedule_summary = raw.get("schedule_summary")
        return JobIntakeAIResult(
            job_description=description[:12000],
            responsibilities=strings("responsibilities"),
            required_qualifications=strings("required_qualifications"),
            preferred_qualifications=strings("preferred_qualifications"),
            schedule_summary=str(schedule_summary).strip()[:2000] if schedule_summary else None,
            warnings=strings("warnings", 50),
            provider="vertex_gemini",
            model=self.model,
        )
