import os
import zipfile
from xml.etree import ElementTree as ET
import logging

try:
    import pdfplumber
except Exception:
    pdfplumber = None

logger = logging.getLogger("backend.resume")


class ResumeExtractionError(Exception):
    pass


MAX_RESUME_UPLOAD_BYTES = 10 * 1024 * 1024
SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".docx"}
SUPPORTED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _get_upload_size(file_storage):
    stream = getattr(file_storage, "stream", file_storage)
    size = 0
    current_position = None
    try:
        current_position = stream.tell()
    except Exception:
        current_position = None
    try:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
    finally:
        if current_position is not None:
            try:
                stream.seek(current_position)
            except Exception:
                pass
    return size


def _extract_text_from_docx(file_storage):
    try:
        file_storage.seek(0)
    except Exception:
        pass

    try:
        with zipfile.ZipFile(file_storage) as docx_zip:
            with docx_zip.open("word/document.xml") as document_xml:
                root = ET.fromstring(document_xml.read())
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for paragraph in root.findall(".//w:p", namespace):
            texts = [node.text for node in paragraph.findall(".//w:t", namespace) if node.text]
            line = "".join(texts).strip()
            if line:
                paragraphs.append(line)
        return "\n".join(paragraphs).strip()
    except KeyError:
        raise ResumeExtractionError("The DOCX file is missing expected document content.")
    except zipfile.BadZipFile:
        raise ResumeExtractionError("The DOCX file is corrupted or invalid.")
    except Exception as e:
        logger.error(f"docx.extract_error error={e}")
        raise ResumeExtractionError("Failed to extract text from DOCX.")


def extract_text_from_pdf(file_storage):
    filename = getattr(file_storage, "filename", "") or ""
    mimetype = (getattr(file_storage, "mimetype", "") or "").lower()
    extension = os.path.splitext(filename)[1].lower()

    if not filename:
        raise ResumeExtractionError("No selected file")

    if extension not in SUPPORTED_RESUME_EXTENSIONS and mimetype not in SUPPORTED_RESUME_MIME_TYPES:
        raise ResumeExtractionError("Unsupported file format. Please upload a PDF or DOCX resume.")

    size = _get_upload_size(file_storage)
    if size <= 0:
        raise ResumeExtractionError("Uploaded file is empty.")
    if size > MAX_RESUME_UPLOAD_BYTES:
        raise ResumeExtractionError("File is too large. Maximum allowed size is 10MB.")

    try:
        file_storage.seek(0)
    except Exception:
        pass

    if extension == ".docx" or mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = _extract_text_from_docx(file_storage)
        if not text:
            raise ResumeExtractionError("No extractable text found in DOCX.")
        return text

    if not pdfplumber:
        raise ResumeExtractionError("PDF extraction library not available.")

    try:
        file_storage.seek(0)
        with pdfplumber.open(file_storage) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        full_text = full_text.strip()
        if not full_text:
            raise ResumeExtractionError("no extractable text found in PDF.")
        return full_text
    except ResumeExtractionError:
        raise
    except Exception as e:
        message = f"{type(e).__name__}: {e}".lower()
        logger.error(f"pdf.extract_error error={e}")
        if "password" in message or "encrypt" in message:
            raise ResumeExtractionError("Password-protected PDFs are not supported.")
        # Some PDF parsing errors indicate no extractable text (e.g., missing MediaBox)
        if "nonetype" in message or "mediabox" in message or "no /root" in message or "none type" in message:
            raise ResumeExtractionError("no extractable text found in PDF.")
        raise ResumeExtractionError("Failed to extract text from PDF.")


def trim_resume_for_prompt(resume_text, max_length=800):
    if not resume_text:
        return ""
    sections = parse_resume_sections(resume_text)
    trimmed_parts = []
    if 'summary' in sections:
        trimmed_parts.append(sections['summary'][:400])
    elif 'profile' in sections:
        trimmed_parts.append(sections['profile'][:400])
    if 'skills_list_raw' in sections:
        skills_str = ", ".join(sections['skills_list_raw'][:15])
        trimmed_parts.append(f"Key Skills: {skills_str}")
    elif 'skills' in sections:
        trimmed_parts.append(sections['skills'][:300])
    if 'experience' in sections:
        exp_lines = sections['experience'].split('\n')[:2]
        trimmed_parts.append("\n".join(exp_lines)[:400])
    trimmed = "\n".join(trimmed_parts)
    return trimmed[:max_length]


SECTION_HEADERS = [
    'experience', 'work experience', 'professional experience', 'education', 'projects', 'skills', 'certifications',
    'achievements', 'summary', 'profile'
]


def parse_resume_sections(text):
    sections = {}
    current = 'summary'
    sections[current] = []
    for line in text.splitlines():
        clean = line.strip()
        low = clean.lower()
        if any(__import__('re').fullmatch(rf"{h}\:?", low) for h in SECTION_HEADERS):
            current = low.split(':')[0]
            if current not in sections:
                sections[current] = []
            continue
        if clean:
            sections.setdefault(current, []).append(clean)
    joined = {k: '\n'.join(v) for k, v in sections.items() if v}
    if 'skills' in joined:
        skill_line = joined['skills']
        tokens = __import__('re').split(r"[,;\n]\s*", skill_line)
        joined['skills_list_raw'] = [t.strip() for t in tokens if t.strip()]
    return joined
