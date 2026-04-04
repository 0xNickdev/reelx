# app/services/frame_uploader.py
import os
import base64
from app.core.database import get_supabase_admin

def upload_frames_to_storage(frame_paths: list, job_id: str) -> list:
    """
    Upload frame images to Supabase Storage.
    Returns list of public URLs.
    """
    db = get_supabase_admin()
    urls = []

    for i, frame_path in enumerate(frame_paths[:8]):
        try:
            with open(frame_path, 'rb') as f:
                data = f.read()

            file_name = f"{job_id}/frame_{i:04d}.jpg"

            # Upload to Supabase Storage
            res = db.storage.from_('frames').upload(
                path=file_name,
                file=data,
                file_options={"content-type": "image/jpeg", "upsert": "true"}
            )

            # Get public URL
            url = db.storage.from_('frames').get_public_url(file_name)
            urls.append(url)
            print(f"[frames] uploaded frame {i} -> {url}")

        except Exception as e:
            print(f"[frames] upload error frame {i}: {e}")
            urls.append(None)

    return urls
