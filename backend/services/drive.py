"""
services/drive.py — Google Drive API helpers.
Uses drive.file scope for writes and drive.metadata.readonly for tree reads.
All token refresh is handled server-side only.
"""
import asyncio
import logging
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

from config import settings
from services.crypto import decrypt_token

logger = logging.getLogger(__name__)

FOLDER_MIME = "application/vnd.google-apps.folder"


def _get_drive_service(access_token: str):
    creds = Credentials(token=access_token)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


async def refresh_access_token(refresh_token_encrypted: str) -> str:
    """Decrypt stored refresh token and exchange for a fresh access token."""
    refresh_token = decrypt_token(refresh_token_encrypted)
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: creds.refresh(Request()))
    return creds.token


async def list_folders(access_token: str) -> list[dict]:
    """Return all folders in the user's Drive (for folder_index sync)."""
    service = _get_drive_service(access_token)
    folders = []
    page_token = None

    loop = asyncio.get_event_loop()
    while True:
        def _fetch(pt=page_token):
            return service.files().list(
                q=f"mimeType='{FOLDER_MIME}' and trashed=false",
                fields="nextPageToken, files(id, name, parents)",
                pageSize=1000,
                pageToken=pt,
            ).execute()

        result = await loop.run_in_executor(None, _fetch)
        folders.extend(result.get("files", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return folders


async def create_folder(access_token: str, name: str, parent_id: Optional[str] = None) -> dict:
    """Create a new Drive folder; returns {id, name}."""
    service = _get_drive_service(access_token)
    metadata = {"name": name, "mimeType": FOLDER_MIME}
    if parent_id:
        metadata["parents"] = [parent_id]

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: service.files().create(body=metadata, fields="id, name").execute(),
    )
    return result


async def upload_file(
    access_token: str,
    filename: str,
    content: bytes,
    mime_type: str,
    folder_id: str,
) -> dict:
    """Upload file bytes to Drive inside folder_id; returns {id, name, webViewLink}."""
    service = _get_drive_service(access_token)
    metadata = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: service.files().create(
            body=metadata,
            media_body=media,
            fields="id, name, webViewLink",
        ).execute(),
    )
    return result


async def move_file(access_token: str, file_id: str, new_folder_id: str, old_folder_id: str) -> dict:
    """Move a file from old_folder_id to new_folder_id."""
    service = _get_drive_service(access_token)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: service.files().update(
            fileId=file_id,
            addParents=new_folder_id,
            removeParents=old_folder_id,
            fields="id, name, parents",
        ).execute(),
    )
    return result


async def list_files_in_folder(access_token: str, folder_id: str) -> list[dict]:
    """List files in a folder for duplicate checking."""
    service = _get_drive_service(access_token)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: service.files().list(
            q=f"'{folder_id}' in parents and trashed=false and mimeType!='{FOLDER_MIME}'",
            fields="files(id, name, mimeType, modifiedTime, size)",
        ).execute(),
    )
    return result.get("files", [])


async def delete_file(access_token: str, file_id: str) -> None:
    """Move a file to trash (soft delete)."""
    service = _get_drive_service(access_token)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: service.files().trash(fileId=file_id).execute(),
    )
