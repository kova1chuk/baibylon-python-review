from fastapi import HTTPException, UploadFile

from app.config import settings


async def read_bounded_upload(file: UploadFile) -> bytes:
    max_bytes = settings.MAX_UPLOAD_BYTES
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail="File too large")
        chunks.append(chunk)
    return b"".join(chunks)
