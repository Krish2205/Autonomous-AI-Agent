"""
JARVIS — Document Loader
Unified file parser supporting PDF, TXT, DOCX, PPTX, and images.
Extracted from analyse.py for reuse across agents.
"""

import base64
import os

from langchain_community.document_loaders import PyPDFLoader
from backend.logger import get_logger

logger = get_logger("tools.document_loader")


def encode_image(image_path: str) -> str:
    """Encode an image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def load_and_parse_file(file_path: str, vision_llm=None) -> str:
    """
    Parse a file and return its text content.

    Supports: .txt, .md, .pdf, .docx, .pptx, .png, .jpg, .jpeg
    For images, requires a vision_llm to be passed.
    """
    ext = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else ""
    logger.info(f"Parsing file: {os.path.basename(file_path)} (type: .{ext})")

    if ext in ("txt", "md"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif ext == "pdf":
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        return "\n".join([doc.page_content for doc in docs])

    elif ext == "docx":
        import docx2txt
        from docx import Document

        text = docx2txt.process(file_path)
        try:
            doc = Document(file_path)
            tables_text = []
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(" | ".join(row_data))
                tables_text.append("\n".join(table_data))
            if tables_text:
                text += "\n\nExtracted Tables:\n" + "\n\n".join(tables_text)
        except Exception as e:
            logger.warning(f"Error extracting Word tables: {e}")
        return text

    elif ext == "pptx":
        from pptx import Presentation

        prs = Presentation(file_path)
        text_runs = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    text_runs.append(shape.text.strip())
                if shape.has_table:
                    table_data = []
                    for row in shape.table.rows:
                        row_data = [cell.text.strip() for cell in row.cells]
                        table_data.append(" | ".join(row_data))
                    text_runs.append("Slide Table:\n" + "\n".join(table_data))
        return "\n".join(text_runs)

    elif ext in ("png", "jpg", "jpeg"):
        if not vision_llm:
            logger.warning("No vision LLM provided for image parsing.")
            return "[Image file — vision LLM required for extraction]"

        base64_image = encode_image(file_path)
        prompt = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text, tables, and describe the content of this image in detail for indexing in a database.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ]
        response = vision_llm.invoke(prompt)
        return response.content

    else:
        logger.warning(f"Unsupported file type: .{ext}")
        return ""
