# ─────────────────────────────────────────────────────────────
# BLUE JEANS FMV ENGINE v1.0
# parser.py — 원고/기획서 파일 파서 (각색 모드 입력용)
# © 2026 BLUE JEANS PICTURES
#
# 지원 형식: DOCX / PDF / TXT / MD
# 용도: 기존 웹소설·웹툰 원고나 기획서를 업로드해 FMV 각색의 입력으로 사용
# ─────────────────────────────────────────────────────────────

import io


def parse_docx(file_bytes):
    """DOCX 바이트 → 텍스트. python-docx 사용."""
    try:
        from docx import Document
    except ImportError:
        return "[오류] python-docx가 설치되지 않았습니다. requirements.txt를 확인하세요."
    try:
        doc = Document(io.BytesIO(file_bytes))
        lines = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(lines)
    except Exception as e:
        return f"[오류] DOCX 파싱 실패: {e}"


def parse_pdf(file_bytes):
    """PDF 바이트 → 텍스트. pypdf 사용."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return "[오류] pypdf가 설치되지 않았습니다. requirements.txt를 확인하세요."
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except Exception as e:
        return f"[오류] PDF 파싱 실패: {e}"


def parse_txt(file_bytes):
    """TXT/MD 바이트 → 텍스트. UTF-8 우선, 실패 시 CP949."""
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="ignore")


def parse_uploaded_file(uploaded_file):
    """
    Streamlit UploadedFile → 텍스트.
    파일 확장자에 따라 적절한 파서로 분기한다.
    """
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()

    if name.endswith(".docx"):
        return parse_docx(file_bytes)
    elif name.endswith(".pdf"):
        return parse_pdf(file_bytes)
    elif name.endswith((".txt", ".md")):
        return parse_txt(file_bytes)
    else:
        return f"[오류] 지원하지 않는 형식입니다: {uploaded_file.name} (DOCX/PDF/TXT/MD만 지원)"


def truncate_for_prompt(text, max_chars=40000):
    """
    긴 원고를 프롬프트 입력 한도에 맞게 자른다.
    앞부분(도입·인물 소개)과 뒷부분(결말)을 함께 남겨 서사 파악을 돕는다.
    """
    if len(text) <= max_chars:
        return text
    head = int(max_chars * 0.7)
    tail = max_chars - head
    return (
        text[:head]
        + f"\n\n[...중략 (전체 {len(text):,}자 중 일부 생략)...]\n\n"
        + text[-tail:]
    )
