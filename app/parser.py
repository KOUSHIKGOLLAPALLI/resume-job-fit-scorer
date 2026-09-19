from pathlib import Path
from io import BytesIO
from pypdf import PdfReader


class ResumeParser:
    def extract(self, filename: str, content: bytes) -> tuple[str, str | None]:
        suffix = Path(filename).suffix.lower()

        if suffix == ".txt":
            text = content.decode("utf-8", errors="replace").strip()
            return text, None if text else "TXT file was empty."

        if suffix == ".pdf":
            try:
                # PdfReader needs a file-like object, not raw bytes.
                reader = PdfReader(BytesIO(content))

                pages = []
                for page in reader.pages:
                    pages.append(page.extract_text() or "")

                text = "\n".join(pages).strip()

                if len(text) < 40:
                    return "", (
                        "PDF was readable as a file, but no usable text could "
                        "be extracted. This may be a scanned/image-only PDF."
                    )

                return text, None

            except Exception as exc:
                return "", f"PDF parsing failed: {type(exc).__name__}: {exc}"

        raise ValueError("Resume must be a PDF or TXT file.")