# ─────────────────────────────────────────────────────────────
# BLUE JEANS FMV ENGINE v1.2.0
# parser.py — 원고/기획서 파일 파서 + JSON 관용 추출기
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


def extract_json(text):
    """
    모델 응답에서 JSON 객체/배열을 관용적으로 추출한다. (v1.2.0)

    모델은 순수 JSON만 달라고 지시해도 다음처럼 응답하는 경우가 있다.
      - ```json 코드펜스로 감싼다
      - 앞뒤에 설명 문장을 붙인다
      - 스마트 인용부호를 쓴다
      - 마지막 항목 뒤에 쉼표를 남긴다

    파싱 성공 시 dict/list, 실패 시 None을 반환한다.
    None이면 호출부는 원문 텍스트 표시로 폴백해야 한다.
    """
    if not text or not text.strip():
        return None

    s = text.strip()

    # 1) 코드펜스 제거
    if "```" in s:
        blocks = []
        parts = s.split("```")
        for i in range(1, len(parts), 2):
            blk = parts[i]
            if blk.lower().startswith("json"):
                blk = blk[4:]
            blocks.append(blk.strip())
        if blocks:
            s = max(blocks, key=len)

    # 2) 최외곽 괄호 구간만 잘라낸다 (앞뒤 설명 문장 제거)
    starts = [i for i in (s.find("{"), s.find("[")) if i != -1]
    if not starts:
        return None
    start = min(starts)
    opener = s[start]
    closer = "}" if opener == "{" else "]"
    depth, end, in_str, esc = 0, None, False, False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    candidate = s[start:end] if end else s[start:]

    # 3) 단계적 복구 시도
    import json as _json
    import re as _re

    attempts = [candidate]
    # 스마트 인용부호 정규화
    fixed = (candidate
             .replace("\u201c", '"').replace("\u201d", '"')
             .replace("\u2018", "'").replace("\u2019", "'"))
    attempts.append(fixed)
    # 트레일링 콤마 제거
    attempts.append(_re.sub(r",(\s*[}\]])", r"\1", fixed))

    for a in attempts:
        try:
            return _json.loads(a)
        except Exception:
            continue
    return None

