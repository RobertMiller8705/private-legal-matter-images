from functools import lru_cache

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from openai import APIStatusError

from .matter_images import MatterImageService, build_service
from .models import MatterImageRequest, MatterImageResult

app = FastAPI(title="Legal matter image workflow")


@app.exception_handler(APIStatusError)
def image_api_rejection(_, exc: APIStatusError) -> JSONResponse:
    status = exc.status_code if 400 <= exc.status_code < 500 else 502
    detail = exc.body if isinstance(exc.body, dict) else {"message": "Image request rejected"}
    return JSONResponse(status_code=status, content={"detail": detail})


@lru_cache
def service() -> MatterImageService:
    return build_service()


@app.post("/matter-images", response_model=MatterImageResult, status_code=201)
def create_matter_image(request: MatterImageRequest) -> MatterImageResult:
    return service().create(request)
