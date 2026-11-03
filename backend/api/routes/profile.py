import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from core.database import engine
from models.models import UserProfile

router = APIRouter()

UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads" / "avatars"


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=1, le=99)


class ProfileRead(BaseModel):
    id: int
    name: str
    age: int
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


@router.get("/profile", response_model=ProfileRead | None)
def get_profile(request: Request):
    """Get the user profile (scoped to principal if present)."""
    principal = getattr(request.state, "principal", None)
    with Session(engine) as db:
        if principal and principal.user_id:
            profile = db.exec(select(UserProfile).where(UserProfile.user_id == principal.user_id)).first()
            if profile and profile.name and profile.name.strip().lower() != "invitado":
                return profile
        return None


@router.post("/profile", response_model=ProfileRead)
def create_or_update_profile(data: ProfileCreate, request: Request):
    """Create or update the user profile (scoped to principal if present)."""
    principal = getattr(request.state, "principal", None)
    with Session(engine) as db:
        if principal and principal.user_id:
            existing = db.exec(select(UserProfile).where(UserProfile.user_id == principal.user_id)).first()
            clean_name = data.name.strip()
            if existing:
                existing.name = clean_name
                existing.age = data.age
                profile = existing
            else:
                profile = UserProfile(user_id=principal.user_id, name=clean_name, age=data.age)
                db.add(profile)
            db.commit()
            db.refresh(profile)
            return profile

        existing = db.exec(select(UserProfile).where(UserProfile.name == data.name)).first()
        if existing:
            existing.name = data.name
            existing.age = data.age
            profile = existing
        else:
            profile = UserProfile(name=data.name, age=data.age)
            db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _validate_image_magic_bytes(content: bytes) -> bool:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if content.startswith(b"\xff\xd8\xff"):
        return True
    if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return True
    if content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP":
        return True
    return False


@router.post("/profile/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Formato inválido: el archivo debe ser una imagen")

    ext = (Path(file.filename).suffix if file.filename else ".png").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Extensión de archivo no permitida ({ext}). Formato no admitido.")

    content = await file.read()
    if not _validate_image_magic_bytes(content):
        raise HTTPException(400, "Firma mágica (magic bytes) inválida. El archivo no corresponde a una imagen válida.")

    filename = f"{uuid.uuid4()}{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filepath = UPLOAD_DIR / filename

    filepath.write_bytes(content)

    avatar_url = f"/uploads/avatars/{filename}"
    principal = getattr(request.state, "principal", None)
    with Session(engine) as db:
        if principal and principal.user_id:
            profile = db.exec(select(UserProfile).where(UserProfile.user_id == principal.user_id)).first()
        else:
            profile = db.exec(select(UserProfile)).first()
        if profile:
            profile.avatar_url = avatar_url
            db.add(profile)
            db.commit()

    return {"avatar_url": avatar_url}
