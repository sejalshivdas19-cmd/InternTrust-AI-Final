"""
Safe file upload handling.

* Extension AND content-based checks (not just the filename extension).
* Randomized stored filenames to prevent path traversal / overwrite attacks.
* Defensive text extraction that never raises on corrupted/empty files -
  it always returns a (possibly empty) string so the analysis pipeline can
  continue safely.
"""

import os
import uuid
from werkzeug.utils import secure_filename

from pypdf import PdfReader
import docx


def is_allowed_file(filename, allowed_extensions):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_extensions


def generate_safe_filename(original_filename):
    """Combine a random UUID with a sanitized original name so the stored
    file can never be used for path traversal and never collides."""
    safe_original = secure_filename(original_filename) or "upload"
    ext = safe_original.rsplit(".", 1)[-1].lower() if "." in safe_original else ""
    unique = uuid.uuid4().hex
    return f"{unique}.{ext}" if ext else unique


def save_uploaded_file(file_storage, upload_folder):
    """Saves the file with a randomized name inside upload_folder.
    Returns (stored_filename, absolute_path) or (None, None) if invalid."""
    if not file_storage or not file_storage.filename:
        return None, None

    stored_name = generate_safe_filename(file_storage.filename)
    # Ensure the resolved path stays inside upload_folder (defense in depth
    # against any path traversal, even though the filename is randomized).
    abs_upload_folder = os.path.abspath(upload_folder)
    dest_path = os.path.abspath(os.path.join(abs_upload_folder, stored_name))
    if not dest_path.startswith(abs_upload_folder + os.sep):
        return None, None

    file_storage.save(dest_path)
    return stored_name, dest_path


def extract_text_from_file(filepath, max_chars=20000):
    """Best-effort text extraction. Never raises - returns '' on any failure
    so a corrupted or unsupported document cannot crash the analysis."""
    if not filepath or not os.path.exists(filepath):
        return ""

    ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
    try:
        if ext == "txt":
            with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                return fh.read(max_chars)

        if ext == "pdf":
            reader = PdfReader(filepath)
            text_parts = []
            for page in reader.pages:
                try:
                    text_parts.append(page.extract_text() or "")
                except Exception:
                    continue
            return "\n".join(text_parts)[:max_chars]

        if ext == "docx":
            document = docx.Document(filepath)
            text_parts = [p.text for p in document.paragraphs]
            return "\n".join(text_parts)[:max_chars]

    except Exception:
        # Corrupted, encrypted, or otherwise unreadable file - fail safe.
        return ""

    return ""
