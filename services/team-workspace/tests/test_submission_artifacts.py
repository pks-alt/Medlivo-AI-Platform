from io import BytesIO
import json
from zipfile import ZipFile

import pytest

from workspace_api.submission_artifacts import (
    GeneratedPacket,
    ResolvedDocument,
    SubmissionPacketGenerator,
    safe_filename,
)


class FakeResolver:
    def __init__(self, documents):
        self.documents = documents
        self.calls = []

    def fetch(self, storage_reference):
        self.calls.append(storage_reference)
        return self.documents[storage_reference]


def test_submission_packet_generator_builds_combined_and_separate_outputs():
    source_pdf = SubmissionPacketGenerator._text_pdf(
        "License Verification",
        [("License", "Synthetic active license verification")],
    )
    resolver = FakeResolver({
        "gs://approved/license.pdf": ResolvedDocument(
            content=source_pdf,
            content_type="application/pdf",
            filename="license.pdf",
        )
    })
    generator = SubmissionPacketGenerator(resolver)
    packet = generator.generate({
        "package": {"version": 2, "template_version": 3},
        "template_name": "Synthetic MSP Template",
        "candidate": {
            "canonical_name": "Synthetic Candidate",
            "profession": "Physical Therapist",
            "specialty": "PT",
        },
        "job": {
            "title": "Physical Therapist",
            "division": "Rehabilitation",
            "city": "Seattle",
            "state": "WA",
        },
        "candidate_summary": "Source-grounded candidate presentation.",
        "resume_text": "# Experience\n- Verified rehabilitation experience",
        "licenses": [
            {
                "state": "WA",
                "license_type": "PT",
                "license_number": "12345",
                "status": "active",
                "expires_at": "2028-01-01",
            }
        ],
        "supporting_documents": [
            {
                "label": "License Verification",
                "required": True,
                "storage_reference": "gs://approved/license.pdf",
            }
        ],
    })
    assert isinstance(packet, GeneratedPacket)
    assert packet.filename.endswith(".zip")
    assert resolver.calls == ["gs://approved/license.pdf"]

    with ZipFile(BytesIO(packet.content)) as archive:
        names = set(archive.namelist())
        combined = next(x for x in names if x.endswith("_Combined.pdf"))
        assert combined
        assert "00_Candidate_Presentation.pdf" in names
        assert "01_Resume.pdf" in names
        assert any("License_Verification" in x for x in names)
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["candidate"] == "Synthetic Candidate"
        assert manifest["template_version"] == 3
        assert manifest["documents"][0]["label"] == "License Verification"


def test_required_unretrievable_document_fails_closed():
    generator = SubmissionPacketGenerator(FakeResolver({}))
    with pytest.raises((KeyError, ValueError)):
        generator.generate({
            "package": {"version": 1, "template_version": 1},
            "template_name": "Template",
            "candidate": {"canonical_name": "Candidate", "profession": "RN"},
            "job": {"title": "RN", "division": "Nursing & Allied"},
            "candidate_summary": "Reviewed summary",
            "resume_text": "Reviewed resume",
            "licenses": [],
            "supporting_documents": [
                {
                    "label": "Required License",
                    "required": True,
                    "storage_reference": "gs://approved/missing.pdf",
                }
            ],
        })


def test_safe_filename_removes_path_and_control_characters():
    value = safe_filename("../Jane / Smith\nSubmission?.zip")
    assert "/" not in value
    assert "\n" not in value
    assert ".." not in value
