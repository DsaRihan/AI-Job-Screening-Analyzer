"""
Tests for file upload validation, DOCX extraction, and edge case handling.
Validates: empty files, large files, unsupported formats, password-protected PDFs, DOCX extraction.
"""
import os
import sys
import json
import io
import pytest
from unittest.mock import patch, MagicMock
from zipfile import ZipFile
from xml.etree import ElementTree as ET

os.environ.setdefault("DEV_BYPASS_AUTH", "1")
os.environ.setdefault("APP_VERSION", "1.0.0-test")


# =============================
# 1. File Validation Tests (Unit Tests)
# =============================
class TestFileValidation:
    """Unit tests for file upload validation without requiring Flask client."""
    
    def test_extract_text_empty_file(self):
        """Should reject empty files with clear error."""
        from backend.app import extract_text_from_pdf, ResumeExtractionError
        from werkzeug.datastructures import FileStorage

        fake_file = FileStorage(stream=io.BytesIO(b""), filename="empty.pdf")
        
        with pytest.raises(ResumeExtractionError, match="empty"):
            extract_text_from_pdf(fake_file)

    def test_extract_text_no_filename(self):
        """Should reject files with no filename."""
        from backend.app import extract_text_from_pdf, ResumeExtractionError
        from werkzeug.datastructures import FileStorage

        fake_file = FileStorage(stream=io.BytesIO(b"%PDF-1.4"), filename="")
        with pytest.raises(ResumeExtractionError, match="no selected file|No selected file"):
            extract_text_from_pdf(fake_file)

    def test_extract_text_unsupported_format(self):
        """Should reject unsupported file formats."""
        from backend.app import extract_text_from_pdf, ResumeExtractionError
        from werkzeug.datastructures import FileStorage

        fake_file = FileStorage(stream=io.BytesIO(b"not a pdf"), filename="resume.txt")
        
        with pytest.raises(ResumeExtractionError, match="unsupported|format"):
            extract_text_from_pdf(fake_file)

    def test_extract_text_large_file(self):
        """Should reject files larger than 10MB."""
        from backend.app import extract_text_from_pdf, ResumeExtractionError
        from werkzeug.datastructures import FileStorage

        # 11MB of data
        large_data = b"x" * (11 * 1024 * 1024)
        fake_file = FileStorage(stream=io.BytesIO(large_data), filename="resume.pdf")
        
        with pytest.raises(ResumeExtractionError, match="large|size"):
            extract_text_from_pdf(fake_file)


# =============================
# 2. DOCX Extraction Tests
# =============================
class TestDocxExtraction:
    """Unit tests for DOCX extraction and edge case handling."""
    
    @staticmethod
    def create_valid_docx():
        """Create a valid minimal DOCX file in memory."""
        docx_buffer = io.BytesIO()
        with ZipFile(docx_buffer, 'w') as docx_zip:
            # Create minimal document.xml with proper namespace
            xml_content = """<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p><w:r><w:t>This is test content</w:t></w:r></w:p>
        <w:p><w:r><w:t>for DOCX extraction</w:t></w:r></w:p>
    </w:body>
</w:document>"""
            docx_zip.writestr("word/document.xml", xml_content)
        docx_buffer.seek(0)
        return docx_buffer

    def test_extract_docx_valid(self):
        """Should extract text from valid DOCX files."""
        from backend.app import extract_text_from_pdf
        from werkzeug.datastructures import FileStorage

        docx_buffer = self.create_valid_docx()
        fake_file = FileStorage(stream=docx_buffer, filename="resume.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        text = extract_text_from_pdf(fake_file)
        assert text is not None
        assert "test content" in text.lower()
        assert "extraction" in text.lower()

    def test_extract_docx_empty_content(self):
        """Should handle DOCX with no extractable text."""
        from backend.app import extract_text_from_pdf, ResumeExtractionError
        from werkzeug.datastructures import FileStorage

        docx_buffer = io.BytesIO()
        with ZipFile(docx_buffer, 'w') as docx_zip:
            xml_content = """<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body></w:body>
</w:document>"""
            docx_zip.writestr("word/document.xml", xml_content)
        docx_buffer.seek(0)

        fake_file = FileStorage(stream=docx_buffer, filename="empty.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        with pytest.raises(ResumeExtractionError, match="(?i)no extractable text"):
            extract_text_from_pdf(fake_file)

    def test_extract_corrupted_docx(self):
        """Should reject corrupted DOCX files."""
        from backend.app import extract_text_from_pdf, ResumeExtractionError
        from werkzeug.datastructures import FileStorage

        fake_file = FileStorage(stream=io.BytesIO(b"not a valid zip"), filename="corrupted.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        with pytest.raises(ResumeExtractionError, match="corrupted|invalid"):
            extract_text_from_pdf(fake_file)

    def test_docx_missing_document_xml(self):
        """Should reject DOCX without word/document.xml."""
        from backend.app import extract_text_from_pdf, ResumeExtractionError
        from werkzeug.datastructures import FileStorage

        docx_buffer = io.BytesIO()
        with ZipFile(docx_buffer, 'w') as docx_zip:
            docx_zip.writestr("word/styles.xml", "<styles/>")  # Missing document.xml
        docx_buffer.seek(0)

        fake_file = FileStorage(stream=docx_buffer, filename="invalid.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        with pytest.raises(ResumeExtractionError, match="missing|content"):
            extract_text_from_pdf(fake_file)


# =============================
# 3. PDF Edge Case Tests
# =============================
class TestPdfEdgeCases:
    """Unit tests for PDF parsing edge cases."""
    
    def test_extract_pdf_no_text(self):
        """Should reject PDFs with no extractable text."""
        from backend.app import extract_text_from_pdf, ResumeExtractionError
        from werkzeug.datastructures import FileStorage

        # Create a minimal valid PDF with no text
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000056 00000 n
0000000115 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
        fake_file = FileStorage(stream=io.BytesIO(minimal_pdf), filename="blank.pdf", content_type="application/pdf")
        
        with pytest.raises(ResumeExtractionError, match="no extractable text"):
            extract_text_from_pdf(fake_file)

    @patch("backend.app.pdfplumber.open")
    def test_extract_pdf_password_protected(self, mock_pdf_open):
        """Should detect password-protected PDFs and return clear error."""
        from backend.app import extract_text_from_pdf, ResumeExtractionError
        from werkzeug.datastructures import FileStorage

        # Simulate pdfplumber raising an error for encrypted PDFs
        mock_pdf_open.side_effect = Exception("PDF appears to be encrypted (requires password)")
        
        fake_file = FileStorage(stream=io.BytesIO(b"%PDF-1.4 encrypted"), filename="protected.pdf", content_type="application/pdf")
        
        with pytest.raises(ResumeExtractionError, match="password|Password"):
            extract_text_from_pdf(fake_file)

    def test_extract_pdf_invalid_format(self):
        """Should reject invalid PDF files."""
        from backend.app import extract_text_from_pdf, ResumeExtractionError
        from werkzeug.datastructures import FileStorage

        fake_file = FileStorage(stream=io.BytesIO(b"%PDF-invalid malformed content"), filename="resume.pdf", content_type="application/pdf")
        
        with pytest.raises(ResumeExtractionError, match="failed|extract"):
            extract_text_from_pdf(fake_file)


# =============================
# 4. File Type Constants Tests
# =============================
class TestFileTypeConstants:
    """Verify file type configuration is correct."""
    
    def test_supported_extensions_configured(self):
        """Verify PDF and DOCX extensions are configured."""
        from backend.app import SUPPORTED_RESUME_EXTENSIONS
        
        assert ".pdf" in SUPPORTED_RESUME_EXTENSIONS
        assert ".docx" in SUPPORTED_RESUME_EXTENSIONS

    def test_supported_mimetypes_configured(self):
        """Verify PDF and DOCX MIME types are configured."""
        from backend.app import SUPPORTED_RESUME_MIME_TYPES
        
        assert "application/pdf" in SUPPORTED_RESUME_MIME_TYPES
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in SUPPORTED_RESUME_MIME_TYPES

    def test_max_upload_size_set(self):
        """Verify max upload size is 10MB."""
        from backend.app import MAX_RESUME_UPLOAD_BYTES
        
        assert MAX_RESUME_UPLOAD_BYTES == 10 * 1024 * 1024
