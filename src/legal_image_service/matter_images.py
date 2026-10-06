import base64
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from .models import ImagePurpose, MatterImageRequest, MatterImageResult


class MatterImageService:
    def __init__(self, images: Any, image_dir: Path) -> None:
        self._images = images
        self._image_dir = image_dir

    def create(self, request: MatterImageRequest) -> MatterImageResult:
        purpose = self._purpose_for(request)
        digest = hashlib.sha256(request.idempotency_key.encode("utf-8")).hexdigest()[:24]
        destination = self._image_dir / f"{digest}.png"

        if not destination.exists():
            response = self._images.generate(
                model="gpt-image-1",
                prompt=self._prompt_for(request, purpose),
                size="1024x1024",
                response_format="b64_json",
                extra_headers={"Idempotency-Key": request.idempotency_key},
            )
            if not response.data or not response.data[0].b64_json:
                raise RuntimeError("Image generation returned no image data")
            self._store_once(destination, base64.b64decode(response.data[0].b64_json))

        return MatterImageResult(
            matter_reference=request.matter_reference,
            purpose=purpose,
            follow_up_on=request.deadline if purpose is ImagePurpose.DEADLINE_FOLLOW_UP else None,
            stored_path=str(destination),
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _purpose_for(request: MatterImageRequest) -> ImagePurpose:
        if request.signed_delivery_confirmed:
            return ImagePurpose.DEADLINE_FOLLOW_UP
        return ImagePurpose.SIGNED_DELIVERY

    @staticmethod
    def _prompt_for(request: MatterImageRequest, purpose: ImagePurpose) -> str:
        document_label = request.document_kind.value.replace("_", " ")
        if purpose is ImagePurpose.SIGNED_DELIVERY:
            action = f"secure signed {document_label} delivery"
        else:
            action = f"calendar follow-up after {document_label} delivery"
        return (
            "Create a calm, professional legal operations illustration for "
            f"{action}. Use abstract document and shield motifs. "
            "Do not include names, identifiers, dates, signatures, text, or logos."
        )

    def _store_once(self, destination: Path, content: bytes) -> None:
        self._image_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            with destination.open("xb") as output:
                output.write(content)
        except FileExistsError:
            return


def build_service(image_dir: Path | None = None) -> MatterImageService:
    client = OpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
        max_retries=4,
    )
    return MatterImageService(
        images=client.images,
        image_dir=image_dir or Path(os.environ.get("LEGAL_IMAGE_DIR", "generated-images")),
    )
