import base64
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from legal_image_service import MatterImageRequest, MatterImageService
from legal_image_service.models import DocumentKind, ImagePurpose


class RecordingImages:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        encoded = base64.b64encode(b"private image bytes").decode("ascii")
        return SimpleNamespace(data=[SimpleNamespace(b64_json=encoded)])


def test_confirmed_delivery_moves_workflow_to_deadline_follow_up(tmp_path: Path) -> None:
    images = RecordingImages()
    workflow = MatterImageService(images=images, image_dir=tmp_path)
    request = MatterImageRequest(
        matter_reference="MAT-2048-SENSITIVE",
        document_kind=DocumentKind.SETTLEMENT_AGREEMENT,
        signed_delivery_confirmed=True,
        deadline=date(2027, 1, 14),
        idempotency_key="matter-2048-v1",
    )

    first = workflow.create(request)
    second = workflow.create(request)

    assert first.purpose is ImagePurpose.DEADLINE_FOLLOW_UP
    assert first.follow_up_on == date(2027, 1, 14)
    assert Path(first.stored_path).read_bytes() == b"private image bytes"
    assert second.stored_path == first.stored_path
    assert len(images.calls) == 1
    prompt = str(images.calls[0]["prompt"])
    assert "MAT-2048-SENSITIVE" not in prompt
    assert "2027-01-14" not in prompt
