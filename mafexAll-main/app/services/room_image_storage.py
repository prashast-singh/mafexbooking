import io
import uuid
from pathlib import Path

from PIL import Image

from app.core.config import get_settings

ALLOWED_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})
MAX_LONG_SIDE = 1600


def validate_upload_filename(filename: str | None) -> None:
    if not filename or not filename.strip():
        raise ValueError("Missing filename")
    suf = Path(filename).suffix.lower()
    if suf not in ALLOWED_SUFFIXES:
        raise ValueError(
            f"Unsupported file type. Allowed extensions: {', '.join(sorted(ALLOWED_SUFFIXES))}"
        )


def resize_to_max_long_side(img: Image.Image, max_side: int = MAX_LONG_SIDE) -> Image.Image:
    w, h = img.size
    longest = max(w, h)
    if longest <= max_side:
        return img
    ratio = max_side / longest
    new_w = max(1, int(round(w * ratio)))
    new_h = max(1, int(round(h * ratio)))
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def prepare_rgb_image(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg
    if img.mode == "P":
        if "transparency" in img.info:
            img = img.convert("RGBA")
            return prepare_rgb_image(img)
        return img.convert("RGB")
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def process_upload_bytes(content: bytes, original_filename: str) -> tuple[str, Path]:
    validate_upload_filename(original_filename)
    img: Image.Image | None = None
    try:
        try:
            img = Image.open(io.BytesIO(content))
        except Image.UnidentifiedImageError as e:
            raise ValueError("Invalid or corrupt image file") from e
        img.load()
        img = prepare_rgb_image(img)
        img = resize_to_max_long_side(img)
        settings = get_settings()
        out_dir = settings.room_images_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}.jpg"
        path = out_dir / name
        img.save(path, format="JPEG", quality=85, optimize=True, progressive=True)
        public_url = f"/storage/room_images/{name}"
        return public_url, path
    finally:
        if img is not None:
            img.close()


def delete_local_room_image(file_url: str) -> None:
    if not file_url.startswith("/storage/room_images/"):
        return
    fname = Path(file_url).name
    if not fname or fname != Path(fname).name:
        return
    settings = get_settings()
    base = settings.room_images_dir.resolve()
    path = (base / fname).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        return
    if path.is_file():
        path.unlink()


__all__ = [
    "ALLOWED_SUFFIXES",
    "MAX_LONG_SIDE",
    "delete_local_room_image",
    "process_upload_bytes",
    "resize_to_max_long_side",
]
