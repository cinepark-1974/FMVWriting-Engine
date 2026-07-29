"""
🎬 BLUE JEANS FMV ENGINE v1.2.2 — main.py
게임형 FMV (캐릭터 공략형 멀티 루트 로맨스)
STEP 0~7 파이프라인 · 집필: Opus / 구조·검증: Sonnet
© 2026 BLUE JEANS PICTURES

[변경 이력]
v1.0    (2026) 초기 빌드. STEP 0~7 파이프라인.
v1.0.1  (2026-07-28) 외부 레퍼런스 명칭 제거 · 일반화.
        - UI 스피너 문구의 외부 브랜드 언급을 일반 표현으로 교체
        - 푸터 버전 표기를 prompt.ENGINE_VERSION 참조로 변경
v1.1.0  (2026-07-28) 흥행 필수 요소 반영 — 결정론적 검증 도구 3종 추가.
        - STEP 2: 플레이 타임 추정기 (환불 임계선 2시간 돌파 판정)
        - STEP 3: 선택 비율 감사기 (진짜/페이크/트랩 비율 판정)
        - STEP 4: 자막 길이 진단기 (P4 규격 초과 줄 표시, 자동 수정 없음)
        - STEP 5: 결제 대행사 기준 안내 (2025-07 스팀 조항)
        - 세션 키 신설: playtime / choice_audit
          (_init_state defaults + backup_payload 동시 반영, 복원 루프는 자동 커버)
v1.2.0  (2026-07-28) STEP 1 후보 선택 방식 전환 — 복사·붙여넣기 제거.
        - 훅/컨셉/캐릭터 3개 생성기를 JSON 모드로 호출해 후보를 구조화
        - 훅·컨셉: 라디오 선택 → '적용' 버튼이 필드에 직접 기입 후 st.rerun()
        - 캐릭터: 멀티셀렉트 → 교체 저장 / 기존 목록에 추가 (JSON 수동 편집 불필요)
        - parser.extract_json() 도입 (코드펜스·설명문·트레일링 콤마·스마트 인용부호 관용 처리)
        - 파싱 실패 시 원문 마크다운 표시로 폴백 — 기능이 죽지 않는다
        - 세션 키 신설: cand_hooks / cand_concepts / cand_chars
          ※ 후보는 적용 시 소거되는 임시 상태이므로 backup_payload에는 의도적으로 넣지 않았다.
            (defaults에만 등록. 향후 패치에서 누락으로 오인하지 않도록 명시)
v1.2.1  (2026-07-28) 출력 절단·빈 응답 사고 수정. (실측 백업 JSON 기반)
        - 원인: v1.1.0에서 출력 양식(표 4종)을 늘렸는데 max_tokens를 5000으로 방치.
          한국어는 문자당 토큰 소모가 크므로 표 출력이 1,200~2,600자에서 절단됐다.
          실측: chapter_map 1,159자 · branches['소은'] 704자 모두 문장 중간 절단.
        - max_tokens 재산정: CONCEPT 10k / CHAPTER 20k / BRANCH 20k /
          SCENE 10k / ADAPT 16k / DEFAULT 10k
        - call_claude 개편: stop_reason 확보(max_tokens·refusal·end_turn 구분),
          1회차 스트리밍 / 2회차 비스트리밍(messages.create) 재시도,
          절단 시 경고 표시, 빈 응답 시 원인별 안내
        - check_truncation() 신설 — 저장된 본문·복원 백업의 절단을 정적 판정
          주입: STEP2 챕터맵 표시 / STEP3 분기표 저장 / STEP6 흐름도 입력 전
        - 'API 진단' 패널 신설 (입력·출력·종료 사유·경로 표시)
        - 세션 키 신설: last_api_diag (defaults 전용, 임시 상태)
        - 전 호출부에 label 부여 — 어느 단계에서 실패했는지 진단에 남는다
v1.2.2  (2026-07-28) 백업 불러오기 실패 수정. (실측 재현 완료)
        - 원인: json.load(restore)가 업로드 파일 객체를 EOF까지 소비한 뒤
          st.rerun()을 호출했다. 재실행 시 업로더는 같은 객체를 그대로 반환하는데
          읽기 위치가 EOF라 두 번째 파싱이 빈 문자열을 만나 JSONDecodeError가 났다.
          1회차 성공 메시지는 rerun으로 사라지고 실패 메시지만 남아
          '복원이 안 된다'로 보였다. (실제로는 1회차에 반영은 됐다)
        - 조치: restore.seek(0) 후 바이트를 명시적으로 읽어 파싱.
          파일 서명(name:size)으로 1회만 적용하고 재실행 시에는 재파싱하지 않는다.
        - PERSIST_KEYS 상수 신설 — 저장·복원 대상 키를 한 곳에서 관리한다.
          (backup_payload 딕셔너리와 복원 루프가 갈라져 유실되는 사고를 원천 차단)
        - 복원 리포트 표시: 적용된 키·백업에 없던 키·현재 상태 요약
        - 탭 위에 '현재 로드 상태' 상시 표시 (제목/훅/캐릭터/챕터맵/트리트먼트/분기표/씬)
        - 복원 직후 절단 항목 일괄 경고 (챕터맵·분기표·트리트먼트)
        - 세션 키 신설: restore_sig / restore_report (defaults 전용, 임시 상태)
"""

import json
import time
import streamlit as st
import streamlit.components.v1 as components

import prompt as P
from parser import parse_uploaded_file, truncate_for_prompt, extract_json

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

MODEL_OPUS = "claude-opus-4-8"
MODEL_SONNET = "claude-sonnet-5"

# max_tokens — 한국어 출력 기준으로 산정 (v1.2.1)
# 한국어는 문자당 토큰 소모가 영어의 2~3배다. 표 형식 출력은 더 든다.
# 5000 토큰으로는 한국어 표 출력이 1,200~2,600자에서 절단된다. (v1.2.0 실측)
MAX_TOKENS_CONCEPT = 10000   # 후보 3~6개 JSON
MAX_TOKENS_CHAPTER = 20000   # 챕터맵(산출표+6챕터+엔딩) · 트리트먼트(EP6+표2종)
MAX_TOKENS_BRANCH = 20000    # 노드 분기표 + 감사표 3종 — 가장 무겁다
MAX_TOKENS_SCENE = 10000     # 씬 원고 1개
MAX_TOKENS_ADAPT = 16000     # 원고 해체
MAX_TOKENS_DEFAULT = 10000   # 정책검증 · 흐름도 · 요약

st.set_page_config(
    page_title="BLUE JEANS · FMV Engine",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
@import url('https://cdn.jsdelivr.net/gh/projectnoonnu/2408-3@latest/Paperlogy.css');
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&display=swap');

:root {
    --navy: #191970; --y: #FFCB05; --bg: #F7F7F5; --card: #FFFFFF;
    --card-border: #E2E2E0; --t: #1A1A2E; --r: #D32F2F; --g: #2EC484;
    --dim: #8E8E99; --light-bg: #EEEEF6;
    --display: 'Playfair Display', 'Paperlogy', 'Georgia', serif;
    --heading: 'Paperlogy', 'Pretendard', sans-serif;
    --body: 'Pretendard', -apple-system, sans-serif;
}
html, body, [class*="css"] { font-family: var(--body) !important; color: var(--t); }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stMainBlockContainer"], [data-testid="stHeader"],
[data-testid="stBottom"], [data-testid="stSidebar"] {
    background-color: var(--bg) !important; color: var(--t) !important;
}
h1, h2, h3, h4, h5, h6 { color: var(--navy) !important; font-family: var(--heading) !important; }
.stMarkdown, .stText { color: var(--t) !important; }
.brand-header { text-align: center; padding: 2rem 0 1.5rem; border-bottom: 2px solid var(--y); margin-bottom: 1.5rem; }
.brand-header .company { font-family: var(--display); font-weight: 900; font-size: 0.85rem; letter-spacing: 0.35em; color: var(--navy); margin-bottom: 0.25rem; }
.brand-header .engine { font-family: var(--heading); font-weight: 700; font-size: 1.6rem; letter-spacing: 0.5em; color: var(--navy); margin-bottom: 0.3rem; }
.brand-header .tagline { font-family: var(--body); font-weight: 300; font-size: 0.7rem; letter-spacing: 0.3em; color: var(--dim); }
.section-header { background: var(--y); padding: 8px 16px; border-radius: 4px; margin: 1.2rem 0 0.6rem; display: inline-block; }
.section-header span { font-family: var(--heading); font-weight: 700; color: var(--navy); font-size: 0.85rem; letter-spacing: 0.05em; }
.stButton > button { background: var(--navy) !important; color: #FFFFFF !important; border: none !important; font-family: var(--heading) !important; font-weight: 600 !important; letter-spacing: 0.05em !important; border-radius: 6px !important; padding: 0.5rem 1.5rem !important; }
.stButton > button:hover { background: var(--y) !important; color: var(--navy) !important; }
[data-testid="stDownloadButton"] button { background: var(--navy) !important; color: #FFFFFF !important; border: none !important; font-weight: 700 !important; }
.stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 2px solid var(--card-border); flex-wrap: wrap; }
.stTabs [data-baseweb="tab"] { font-family: var(--heading) !important; font-weight: 600 !important; color: var(--dim) !important; font-size: 0.82rem !important; padding: 0.7rem 1.1rem !important; }
.stTabs [aria-selected="true"] { color: var(--navy) !important; border-bottom: 3px solid var(--y) !important; }
.stTextInput input, .stTextArea textarea { background: var(--card) !important; color: var(--t) !important; border: 1.5px solid var(--card-border) !important; border-radius: 8px !important; font-family: var(--body) !important; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--navy) !important; box-shadow: 0 0 0 2px rgba(25,25,112,.08) !important; }
.stSelectbox > div > div, [data-baseweb="select"] > div { background: var(--card) !important; color: var(--t) !important; border-color: var(--card-border) !important; border-radius: 8px !important; }
.stTextInput label, .stTextArea label, .stSelectbox label { color: var(--t) !important; font-weight: 600 !important; font-size: 0.82rem !important; }
.seq { display: inline-block; background: var(--navy); color: #FFFFFF !important; padding: 2px 10px; border-radius: 12px; font-family: var(--heading); font-weight: 700; font-size: 0.75rem; letter-spacing: 0.03em; margin-right: 6px; }
.mode-card { background: var(--card); border: 1px solid var(--card-border); border-radius: 8px; padding: 1rem; margin: 0.5rem 0; }
.callout { background: var(--light-bg); border-left: 4px solid var(--navy); border-radius: 0 8px 8px 0; padding: 0.9rem 1.1rem; margin: 0.5rem 0; font-size: 0.88rem; }
.rule-badge { display: inline-block; background: var(--r); color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; margin-right: 4px; }
.stProgress > div > div { background-color: var(--y) !important; }
hr { border-color: var(--card-border) !important; }
.stCaption, small { color: var(--dim) !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="brand-header">
    <div class="company">BLUE JEANS PICTURES</div>
    <div class="engine">FMV ENGINE</div>
    <div class="tagline">YOUNG · VINTAGE · FREE · INNOVATIVE</div>
</div>
""", unsafe_allow_html=True)


def _get_api_key():
    try:
        k = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        k = ""
    if k:
        return k
    return st.session_state.get("api_key", "").strip()


def _extract_text(msg):
    """messages.create 응답에서 text 블록만 이어붙인다."""
    out = []
    for b in getattr(msg, "content", []) or []:
        if getattr(b, "type", "") == "text":
            out.append(getattr(b, "text", ""))
    return "".join(out).strip()


def call_claude(prompt_text, max_tokens=MAX_TOKENS_DEFAULT, model=None, label=""):
    """
    Claude 호출. (v1.2.1 — 실패 원인을 감추지 않는다)

    1회차는 스트리밍, 2회차는 비스트리밍으로 재시도한다.
      (스트림에서만 빈 응답이 나오는 경우가 있어 경로를 바꿔 확인한다)
    stop_reason을 반드시 확보해 절단·거부를 구분한다.
      - max_tokens : 출력이 잘렸다 → 경고를 띄운다 (본문은 그대로 반환)
      - refusal    : 모델이 응답을 거부했다 → 프롬프트 소재를 손봐야 한다
      - end_turn   : 정상 완료
    진단 결과는 st.session_state['last_api_diag']에 남겨 UI에서 확인할 수 있다.
    """
    diag = {
        "label": label, "model": model or MODEL_SONNET,
        "prompt_chars": len(prompt_text), "max_tokens": max_tokens,
        "stop_reason": None, "out_chars": 0, "out_tokens": None,
        "truncated": False, "path": None, "error": None,
    }
    st.session_state["last_api_diag"] = diag

    if not _HAS_ANTHROPIC:
        diag["error"] = "anthropic 패키지 미설치"
        st.error("anthropic 패키지가 설치되지 않았습니다. requirements.txt를 확인하세요.")
        return ""
    key = _get_api_key()
    if not key:
        diag["error"] = "API Key 없음"
        st.error("API Key가 없습니다. Secrets에 넣거나 아래 설정에서 입력하세요.")
        return ""
    if model is None:
        model = MODEL_SONNET
        diag["model"] = model

    last_error = None
    for attempt in range(2):
        try:
            client = anthropic.Anthropic(api_key=key)
            payload = dict(model=model, max_tokens=max_tokens,
                           messages=[{"role": "user", "content": prompt_text}])

            if attempt == 0:
                diag["path"] = "stream"
                full = []
                with client.messages.stream(**payload) as stream:
                    for text in stream.text_stream:
                        full.append(text)
                    final = stream.get_final_message()
                result = "".join(full).strip()
                stop = getattr(final, "stop_reason", None)
                usage = getattr(final, "usage", None)
            else:
                diag["path"] = "create (비스트리밍 재시도)"
                msg = client.messages.create(**payload)
                result = _extract_text(msg)
                stop = getattr(msg, "stop_reason", None)
                usage = getattr(msg, "usage", None)

            diag["stop_reason"] = stop
            diag["out_chars"] = len(result)
            diag["out_tokens"] = getattr(usage, "output_tokens", None) if usage else None
            diag["truncated"] = (stop == "max_tokens")

            if not result or len(result) < 30:
                last_error = f"본문 {len(result)}자 · stop_reason={stop}"
                if attempt == 0:
                    time.sleep(2)
                    continue
                st.error(f"⚠️ 응답 본문이 비었습니다 — {last_error}")
                if stop == "refusal":
                    st.warning(
                        "모델이 응답을 거부했습니다(stop_reason=refusal). "
                        "프롬프트에 포함된 소재·표현 중 정책 판정에 걸리는 부분이 있습니다. "
                        "해당 캐릭터의 트리트먼트에서 강제·구금·비동의로 읽힐 수 있는 서술을 "
                        "완화한 뒤 다시 시도하세요. 룰셋을 끌 필요는 없습니다.")
                else:
                    st.caption(
                        f"진단 — 모델 {model} · 입력 {len(prompt_text):,}자 · "
                        f"max_tokens {max_tokens:,} · 경로 {diag['path']}. "
                        "네트워크·rate limit·일시 과부하 가능. 아래 'API 진단'을 확인하세요.")
                return ""

            if diag["truncated"]:
                st.warning(
                    f"⚠️ 출력이 max_tokens({max_tokens:,})에서 절단됐습니다. "
                    f"본문 {len(result):,}자만 생성됐습니다. "
                    "표 마지막 행이 중간에 끊겼을 수 있으니 그대로 다음 단계로 넘기지 마시고, "
                    "캐릭터 수나 요구 섹션을 줄여 다시 생성하거나 절단 지점을 직접 이어 주세요.")
            return result

        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)[:180]}"
            diag["error"] = last_error
            if attempt == 0:
                time.sleep(3)
                continue
            st.error(f"❌ API 호출 실패 (2회 시도): {last_error}")
            st.caption("네트워크·rate limit·토큰 한도·인증 오류 가능. 잠시 후 재시도하세요.")
            return ""


def sh(title, en):
    st.markdown(f'<div class="section-header"><span>{title} · {en}</span></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
# 결정론적 검증 도구 (v1.1.0)
# API 호출 없이 계산만 수행한다. 결과는 진단이며 본문을 수정하지 않는다.
# ══════════════════════════════════════════════

REFUND_THRESHOLD_MIN = 120      # 스팀 환불 임계선: 플레이 2시간
PLAYTIME_TARGET_MIN = 150       # 목표: 2시간 30분 (30분 안전 마진)
SUBTITLE_MAX_CHARS = 30         # P4: 한 호흡 한국어 30자
CHOICE_REAL_MIN_RATIO = 0.50    # P2: 진짜 선택 50% 이상
CHOICE_FAKE_MAX_RATIO = 0.40    # P2: 페이크 선택 40% 이하


def estimate_playtime(chapters, scenes_per_chapter, sec_per_scene, choices_total,
                      sec_per_choice=12):
    """
    1회차 클리어 예상 플레이 타임을 산출한다.
    영상 재생 시간 + 선택지 노출·대기 시간의 합.
    """
    total_scenes = chapters * scenes_per_chapter
    video_sec = total_scenes * sec_per_scene
    choice_sec = choices_total * sec_per_choice
    total_min = (video_sec + choice_sec) / 60
    return {
        "chapters": chapters,
        "total_scenes": total_scenes,
        "video_min": round(video_sec / 60, 1),
        "choice_min": round(choice_sec / 60, 1),
        "total_min": round(total_min, 1),
        "over_refund": total_min >= REFUND_THRESHOLD_MIN,
        "over_target": total_min >= PLAYTIME_TARGET_MIN,
        "gap_to_target": round(PLAYTIME_TARGET_MIN - total_min, 1),
    }


def audit_choice_ratio(real_n, fake_n, trap_n):
    """진짜/페이크/트랩 선택 비율을 감사한다. (사고 패턴 F 대응)"""
    total = real_n + fake_n + trap_n
    if total == 0:
        return {"total": 0, "verdict": "입력 없음", "issues": []}
    real_r, fake_r = real_n / total, fake_n / total
    issues = []
    if real_r < CHOICE_REAL_MIN_RATIO:
        issues.append(f"진짜 선택 비율 {real_r:.0%} — 50% 미만입니다. "
                      "페이크를 진짜 선택으로 승격하거나 변수 변동을 부여하세요.")
    if fake_r > CHOICE_FAKE_MAX_RATIO:
        issues.append(f"페이크 선택 비율 {fake_r:.0%} — 40% 초과입니다. "
                      "유저가 '선택해봐야 소용없다'를 학습할 위험이 있습니다.")
    if trap_n == 0:
        issues.append("즉사 트랩이 0개입니다. 루트당 1~2개를 권장합니다.")
    elif trap_n > 2:
        issues.append(f"즉사 트랩 {trap_n}개 — 루트당 1~2개를 초과합니다. "
                      "선택 공포로 저장·로드 반복을 유발할 수 있습니다.")
    return {
        "total": total, "real_ratio": real_r, "fake_ratio": fake_r, "trap_n": trap_n,
        "verdict": "적정" if not issues else "조정 필요", "issues": issues,
    }


def check_subtitle_length(script_text, limit=SUBTITLE_MAX_CHARS):
    """
    P4 자막 규격 초과 줄을 찾아 표시한다. (진단 전용 — 본문을 수정하지 않는다)
    씬 헤딩·전환·선택지·태그·노드ID 줄은 대상에서 제외한다.
    구조 판정이 아니라 길이 표시이므로, 지문이 섞여 나와도 참고값으로 유효하다.
    """
    skip_prefix = ("[", "▶", "INT.", "EXT.", "CUT TO", "CLOSE UP", "INSERT",
                   "#", "-", "|", "1)", "2)", "3)", "4)", "※")
    over = []
    for i, raw in enumerate(script_text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(skip_prefix):
            continue
        # 캐릭터명 + 탭/공백 다중 → 대사부만 계산
        body = line.split("\t", 1)[1].strip() if "\t" in line else line
        if len(body) > limit:
            over.append({"line_no": i, "chars": len(body), "text": body})
    return over


def _norm_heading(line):
    """헤딩 줄에서 '#' 레벨과 공백을 제거해 비교용으로 정규화한다."""
    return line.strip().lstrip("#").strip()


def check_truncation(text, required_marker=None):
    """
    저장된 본문이 절단됐는지 정적으로 판정한다. (v1.2.1 — 진단 전용, 본문 수정 없음)

    판정 근거는 두 가지만 쓴다. 문장 종결 여부는 쓰지 않는다.
    (한국어 항목은 '…루트 종료'처럼 마침표 없이 끝나는 것이 정상이라 오탐이 난다)
      1) 출력 양식이 요구하는 마지막 섹션이 없다 → 끝까지 생성되지 않았다
      2) 마지막 줄이 표 행인데 '|'로 닫히지 않았다 → 표 중간에서 끊겼다

    required_marker는 헤딩 '레벨을 무시하고' 비교한다.
    모델이 같은 섹션을 '## 엔딩 연결' 또는 '### 엔딩 연결'로 번갈아 쓰기 때문이다.
    (실측: 트리트먼트 4건 중 3건이 ##, 1건이 ### — 레벨 고정 비교는 오탐을 낸다)
    """
    if not text or not text.strip():
        return {"ok": False, "reason": "본문이 비어 있습니다.", "tail": ""}
    t = text.rstrip()
    tail = t[-40:]
    lines = [l for l in t.splitlines() if l.strip()]
    last = lines[-1].strip() if lines else ""

    if last.startswith("|") and not last.endswith("|"):
        return {"ok": False, "reason": "표 행이 중간에서 끊겼습니다.", "tail": tail}

    if required_marker:
        want = _norm_heading(required_marker)
        heads = {_norm_heading(l) for l in lines if l.strip().startswith("#")}
        if want not in heads:
            return {"ok": False,
                    "reason": f"필수 섹션 '{want}'이 없습니다. 끝까지 생성되지 않았습니다.",
                    "tail": tail}
    return {"ok": True, "reason": "완결 확인 — 절단 흔적 없음", "tail": tail}


# 각 단계 출력 양식의 마지막 섹션 마커 (check_truncation 판정 기준)
TAIL_MARKER_CHAPTERMAP = "## 캐릭터별 엔딩 챕터"
TAIL_MARKER_TREATMENT = "### 엔딩 연결"
TAIL_MARKER_BRANCH = "## 수집요소 도달성 검증"


# ══════════════════════════════════════════════
# 세션 상태
# ══════════════════════════════════════════════
def _init_state():
    defaults = {
        "api_key": "",
        "project": {"title": "", "subconcept": "순정 로맨스", "target": "남성향",
                    "hook": "", "world": "", "pov": "1인칭 남성 주인공"},
        "characters": [], "chapter_map": "", "treatments": {},
        "branches": {}, "scenes": {}, "flowchart": "", "manuscript": "",
        "playtime": {}, "choice_audit": {},
        "cand_hooks": {}, "cand_concepts": {}, "cand_chars": {},
        "last_api_diag": {},
        "restore_sig": "", "restore_report": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# API Key 입력 (Secrets 없을 때만 노출)
_secret_present = bool(_get_api_key() and not st.session_state.get("api_key"))
try:
    _has_secret = bool(st.secrets.get("ANTHROPIC_API_KEY", ""))
except Exception:
    _has_secret = False

if _has_secret:
    st.caption("✅ Secrets에서 API Key 로드됨")
else:
    with st.expander("🔑 API Key 설정", expanded=not st.session_state["api_key"]):
        st.session_state["api_key"] = st.text_input(
            "Anthropic API Key", type="password", value=st.session_state["api_key"],
            help="Streamlit Secrets에 ANTHROPIC_API_KEY를 넣으면 자동 로드됩니다.",
        )

with st.expander("🔎 API 진단 — 마지막 호출 결과", expanded=False):
    _dg = st.session_state.get("last_api_diag") or {}
    if not _dg:
        st.caption("아직 호출 기록이 없습니다. 생성 버튼을 누르면 여기에 결과가 남습니다.")
    else:
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("단계", _dg.get("label") or "-")
        g2.metric("입력", f"{_dg.get('prompt_chars', 0):,}자")
        g3.metric("출력", f"{_dg.get('out_chars', 0):,}자",
                  f"{_dg.get('out_tokens')}토큰" if _dg.get("out_tokens") else None)
        g4.metric("종료 사유", str(_dg.get("stop_reason") or "-"))
        st.caption(
            f"모델 {_dg.get('model')} · max_tokens {_dg.get('max_tokens'):,} · 경로 {_dg.get('path')}"
            + (f" · 오류 {_dg['error']}" if _dg.get("error") else ""))
        if _dg.get("truncated"):
            st.warning("이 호출은 max_tokens에서 절단됐습니다. 저장된 본문 끝이 잘려 있을 수 있습니다.")
        elif _dg.get("stop_reason") == "refusal":
            st.error("모델이 응답을 거부했습니다. 프롬프트 소재를 완화해야 합니다.")
        elif _dg.get("stop_reason") == "end_turn":
            st.success("정상 완료 — 출력이 끝까지 생성됐습니다.")

# 백업 / 복원
# ── 저장·복원 대상 키를 한 곳에서 관리한다 (v1.2.2)
#    이전에는 backup_payload 딕셔너리를 만들고 그 키를 복원 루프가 재사용했다.
#    두 곳이 갈라지면 복원 시 데이터가 조용히 유실되므로 단일 상수로 고정한다.
PERSIST_KEYS = ("project", "characters", "chapter_map", "treatments",
                "branches", "scenes", "flowchart", "playtime", "choice_audit")


def _state_summary():
    """현재 세션에 무엇이 들어있는지 한 줄로 요약한다."""
    s = st.session_state
    return {
        "제목": s["project"].get("title") or "(무제)",
        "훅": "있음" if s["project"].get("hook") else "없음",
        "캐릭터": f"{len(s['characters'])}명",
        "챕터맵": f"{len(s['chapter_map']):,}자" if s["chapter_map"] else "없음",
        "트리트먼트": f"{len(s['treatments'])}건",
        "분기표": f"{len(s['branches'])}건",
        "씬": f"{len(s['scenes'])}개",
    }


with st.expander("💾 작업 저장 / 불러오기", expanded=False):
    col_a, col_b = st.columns(2)
    backup_payload = {k: st.session_state[k] for k in PERSIST_KEYS}
    with col_a:
        st.download_button(
            "📥 기획 저장 (.json)",
            data=json.dumps(backup_payload, ensure_ascii=False, indent=2),
            file_name=f"fmv_{st.session_state['project'].get('title','untitled') or 'untitled'}.json",
            mime="application/json", use_container_width=True,
        )
    with col_b:
        restore = st.file_uploader("📂 불러오기 (.json)", type=["json"],
                                   label_visibility="collapsed", key="restore_up")
        if restore is not None:
            # 같은 파일을 재실행마다 다시 읽지 않도록 서명으로 1회만 적용한다. (v1.2.2)
            # st.rerun() 이후에도 업로더는 같은 객체를 반환하는데, 그때 읽기 위치가
            # 이미 EOF라 json.load가 빈 문자열을 만나 '복원 실패'로 오인됐다.
            _sig = f"{restore.name}:{restore.size}"
            if st.session_state.get("restore_sig") != _sig:
                try:
                    restore.seek(0)                      # 읽기 위치를 반드시 처음으로
                    data = json.loads(restore.read().decode("utf-8"))
                    if not isinstance(data, dict):
                        raise ValueError("최상위가 객체(dict)가 아닙니다.")
                    applied, missing = [], []
                    for k in PERSIST_KEYS:
                        if k in data:
                            st.session_state[k] = data[k]
                            applied.append(k)
                        else:
                            missing.append(k)
                    st.session_state["restore_sig"] = _sig
                    st.session_state["restore_report"] = {
                        "file": restore.name, "applied": applied, "missing": missing,
                    }
                    st.rerun()
                except Exception as e:
                    st.session_state["restore_sig"] = _sig
                    st.error(f"복원 실패: {type(e).__name__} — {e}")
                    st.caption("파일이 이 엔진의 '기획 저장 (.json)'으로 만든 백업인지 확인하세요.")

        _rep = st.session_state.get("restore_report") or {}
        if _rep:
            st.success(f"✅ 복원 완료 — {_rep['file']}")
            _sm = _state_summary()
            st.caption(" · ".join(f"{k} {v}" for k, v in _sm.items()))
            if _rep.get("missing"):
                st.caption("이 백업에 없던 항목(기본값 유지): " + ", ".join(_rep["missing"]))

# 복원한 본문 중 절단된 것이 있으면 알린다 (v1.2.2)
_warn = []
if st.session_state["chapter_map"] and not check_truncation(
        st.session_state["chapter_map"], TAIL_MARKER_CHAPTERMAP)["ok"]:
    _warn.append("챕터맵")
_warn += [f"분기표({k})" for k, v in st.session_state["branches"].items()
          if not check_truncation(v, TAIL_MARKER_BRANCH)["ok"]]
_warn += [f"트리트먼트({k})" for k, v in st.session_state["treatments"].items()
          if not check_truncation(v, TAIL_MARKER_TREATMENT)["ok"]]
if _warn:
    st.warning("⚠️ 다음 항목이 끝까지 생성되지 않은 상태로 저장돼 있습니다: "
               + ", ".join(_warn)
               + " — 해당 STEP에서 다시 생성하신 뒤 다음 단계로 넘어가시기를 권합니다.")

# 현재 로드 상태 — 어느 탭에 있든 무엇이 들어있는지 보인다 (v1.2.2)
_sm = _state_summary()
_cols = st.columns(len(_sm))
for _c, (_k, _v) in zip(_cols, _sm.items()):
    _c.metric(_k, _v)

# ══════════════════════════════════════════════
# 상단 탭 네비게이션 (STEP 0~7)
# ══════════════════════════════════════════════
tabs = st.tabs([
    "0 · 원고각색", "1 · 컨셉/캐릭터", "2 · 챕터맵", "3 · 분기설계",
    "4 · 씬집필", "5 · 정책검증", "6 · 흐름도", "7 · 출력",
])


# ── STEP 0. 원고 각색 ────────────────────────────
with tabs[0]:
    sh("원고 각색", "ADAPTATION")
    st.caption("기존 웹소설·웹툰 원고나 기획서를 넣으면 FMV용으로 캐릭터·분기점을 해체합니다. 신규 창작이면 건너뛰세요.")
    up = st.file_uploader("원고 파일 (DOCX / PDF / TXT / MD)", type=["docx", "pdf", "txt", "md"], key="adapt_up")
    target0 = st.selectbox("타깃 성향", P.TARGET_TYPES,
                           index=P.TARGET_TYPES.index("여성향(오토메)"), key="adapt_target")
    if up is not None:
        text = parse_uploaded_file(up)
        st.session_state["manuscript"] = text
        st.success(f"원고 로드 완료 — 총 {len(text):,}자")
        with st.expander("📖 원고 미리보기"):
            st.text(text[:2000])
    if st.session_state["manuscript"] and st.button("🔍 FMV 각색 해체 실행", key="btn_adapt"):
        with st.spinner("원고를 해체해 캐릭터·분기점을 추출하는 중..."):
            manuscript = truncate_for_prompt(st.session_state["manuscript"])
            st.markdown(call_claude(P.build_adaptation_prompt(manuscript, target0),
                                    max_tokens=MAX_TOKENS_ADAPT, model=MODEL_SONNET,
                                    label="STEP0 원고각색"))


# ── STEP 1. 컨셉 & 캐릭터 ─────────────────────────
with tabs[1]:
    sh("컨셉 & 캐릭터", "CONCEPT & CHARACTER")
    proj = st.session_state["project"]
    c1, c2 = st.columns(2)
    with c1:
        proj["title"] = st.text_input("작품 제목", value=proj["title"])
        sub_keys = list(P.SUBCONCEPTS.keys())
        proj["subconcept"] = st.selectbox("서브컨셉", sub_keys,
            index=sub_keys.index(proj["subconcept"]) if proj["subconcept"] in sub_keys else 0)
        st.caption(P.SUBCONCEPTS.get(proj["subconcept"], ""))
    with c2:
        proj["target"] = st.selectbox("타깃 성향", P.TARGET_TYPES,
            index=P.TARGET_TYPES.index(proj["target"]) if proj["target"] in P.TARGET_TYPES else 0)
        proj["pov"] = st.text_input("주인공 시점", value=proj["pov"])
    proj["hook"] = st.text_input("한 줄 훅", value=proj["hook"])
    proj["world"] = st.text_area("세계관 원포인트 (고립·공존 공간 등)", value=proj["world"], height=70)
    st.session_state["project"] = proj

    st.markdown('<div class="callout"><b>① 훅 발굴</b> — 아이디어 한 조각만 있어도 시작하세요. 후보를 뽑아 드리면 원하는 것을 골라 바로 적용합니다.</div>', unsafe_allow_html=True)
    fragment = st.text_input("재료 한두 조각 (막연해도 됩니다)",
        placeholder="예: 좀비 / 요가복 / 회사 상사 / 무인도 / 룸메이트")
    if st.button("💡 한 줄 훅 후보 생성", key="btn_hook"):
        if not fragment.strip():
            st.error("재료를 한 조각이라도 입력하세요. (단어 하나면 충분합니다)")
        else:
            with st.spinner("FMV 훅 공식으로 후보를 뽑는 중..."):
                raw = call_claude(
                    P.build_hook_finder_prompt(fragment, proj["target"], as_json=True),
                    max_tokens=MAX_TOKENS_CONCEPT, model=MODEL_SONNET, label="STEP1 훅발굴")
                data = extract_json(raw)
                st.session_state["cand_hooks"] = {
                    "raw": raw,
                    "items": (data or {}).get("candidates", []) if isinstance(data, dict) else [],
                    "recommend": (data or {}).get("recommend", {}) if isinstance(data, dict) else {},
                }

    _ch = st.session_state.get("cand_hooks") or {}
    if _ch.get("items"):
        _rec = _ch.get("recommend") or {}
        opts = []
        for i, it in enumerate(_ch["items"]):
            tag = ""
            if it.get("hook") == _rec.get("commercial"):
                tag += " ⭐상업성"
            if it.get("hook") == _rec.get("distinctive"):
                tag += " ✨차별화"
            opts.append(f"{i+1}. [{it.get('subconcept','?')}] {it.get('hook','')}{tag}")
        sel = st.radio("훅 후보 — 하나를 고르세요", opts, key="pick_hook", index=0)
        it = _ch["items"][opts.index(sel)]
        st.markdown(
            f'<div class="mode-card">'
            f'<b>고립 공간</b> — {it.get("isolation","-")}<br>'
            f'<b>공략 대상 구성</b> — {it.get("cast","-")}<br>'
            f'<b>관계 압력</b> — {it.get("pressure","-")}<br>'
            f'<b>서브컨셉</b> — {it.get("subconcept","-")}</div>',
            unsafe_allow_html=True)
        hk1, hk2 = st.columns([1, 2])
        with hk1:
            if st.button("✅ 이 후보 적용", key="apply_hook", use_container_width=True):
                proj["hook"] = it.get("hook", "")
                _w = it.get("isolation", "")
                _p = it.get("pressure", "")
                proj["world"] = f"{_w} / {_p}".strip(" /")
                if it.get("subconcept") in P.SUBCONCEPTS:
                    proj["subconcept"] = it["subconcept"]
                st.session_state["project"] = proj
                st.session_state["cand_hooks"] = {}
                st.success("적용 완료 — 위 필드에 반영했습니다.")
                st.rerun()
        with hk2:
            st.caption("적용하면 한 줄 훅 · 세계관 원포인트 · 서브컨셉이 위 필드에 자동 입력됩니다.")
    elif _ch.get("raw"):
        st.warning("후보를 구조화하지 못했습니다. 아래 원문에서 직접 옮겨 주세요.")
        st.markdown(_ch["raw"])

    st.markdown('<div class="callout"><b>② 컨셉 브레인스토밍</b> — 소재 키워드만 넣으세요. ①의 결과를 붙여넣지 않아도 됩니다.</div>', unsafe_allow_html=True)
    keywords = st.text_area("소재 키워드",
        placeholder="예: 좀비 아포칼립스, 셸터 고립, 미녀 생존자들, 지켜야 하는 남자 주인공", height=70)
    if st.button("🔥 컨셉 후보 생성", key="btn_concept"):
        with st.spinner("상업성 있는 컨셉 후보를 뽑는 중..."):
            raw = call_claude(P.build_concept_prompt(proj, keywords, as_json=True),
                              max_tokens=MAX_TOKENS_CONCEPT, model=MODEL_SONNET,
                              label="STEP1 컨셉후보")
            data = extract_json(raw)
            st.session_state["cand_concepts"] = {
                "raw": raw,
                "items": (data or {}).get("candidates", []) if isinstance(data, dict) else [],
            }

    _cc = st.session_state.get("cand_concepts") or {}
    if _cc.get("items"):
        opts = [f"{it.get('label','?')} · {it.get('subconcept','?')} — {it.get('hook','')}"
                for it in _cc["items"]]
        sel = st.radio("컨셉 후보 — 하나를 고르세요", opts, key="pick_concept", index=0)
        it = _cc["items"][opts.index(sel)]
        st.markdown(
            f'<div class="mode-card">'
            f'<b>훅</b> — {it.get("hook","-")}<br>'
            f'<b>세계관 원포인트</b> — {it.get("world","-")}<br>'
            f'<b>강점</b> — {it.get("strength","-")}<br>'
            f'<b>리스크</b> — {it.get("risk","-")}</div>',
            unsafe_allow_html=True)
        cc1, cc2 = st.columns([1, 2])
        with cc1:
            if st.button("✅ 이 컨셉 적용", key="apply_concept", use_container_width=True):
                proj["hook"] = it.get("hook", proj["hook"])
                proj["world"] = it.get("world", proj["world"])
                if it.get("subconcept") in P.SUBCONCEPTS:
                    proj["subconcept"] = it["subconcept"]
                st.session_state["project"] = proj
                st.session_state["cand_concepts"] = {}
                st.success("적용 완료 — 위 필드에 반영했습니다.")
                st.rerun()
        with cc2:
            st.caption("적용하면 한 줄 훅 · 세계관 원포인트 · 서브컨셉이 위 필드에 자동 입력됩니다.")
    elif _cc.get("raw"):
        st.warning("후보를 구조화하지 못했습니다. 아래 원문에서 직접 옮겨 주세요.")
        st.markdown(_cc["raw"])

    st.markdown('<div class="callout"><b>③ 공략 캐릭터 설계</b> — 생성 후 쓸 캐릭터만 체크해서 저장하세요. JSON을 손으로 쓰지 않아도 됩니다.</div>', unsafe_allow_html=True)
    n_char = st.slider("공략 캐릭터 수", 2, 5, 4)
    if st.button("👥 캐릭터 라인업 생성", key="btn_char"):
        with st.spinner("컨셉 비중복·난이도 차등으로 설계하는 중..."):
            raw = call_claude(
                P.build_character_prompt(proj, n_char, st.session_state["characters"], as_json=True),
                max_tokens=MAX_TOKENS_CONCEPT, model=MODEL_SONNET, label="STEP1 캐릭터")
            data = extract_json(raw)
            st.session_state["cand_chars"] = {
                "raw": raw,
                "items": (data or {}).get("characters", []) if isinstance(data, dict) else [],
            }

    _cs = st.session_state.get("cand_chars") or {}
    if _cs.get("items"):
        st.caption("생성된 라인업")
        for i, c in enumerate(_cs["items"]):
            st.markdown(
                f'<div class="mode-card"><b>{i+1}. {c.get("name","(이름미정)")}</b> '
                f'<span class="seq">{c.get("difficulty","보통")}</span><br>'
                f'아키타입 — {c.get("archetype","-")}<br>'
                f'컨셉 — {c.get("concept","-")}<br>'
                f'매력 — {c.get("charm","-")}<br>'
                f'갈등 — {c.get("conflict","-")}<br>'
                f'첫 등장 — {c.get("first_impression","-")}</div>',
                unsafe_allow_html=True)
        names = [f"{i+1}. {c.get('name','(이름미정)')}" for i, c in enumerate(_cs["items"])]
        picks = st.multiselect("저장할 캐릭터를 고르세요", names, default=names, key="pick_chars")
        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("💾 선택 캐릭터로 교체 저장", key="apply_chars", use_container_width=True):
                chosen = [_cs["items"][names.index(p)] for p in picks]
                st.session_state["characters"] = chosen
                st.session_state["cand_chars"] = {}
                st.success(f"{len(chosen)}명 저장 완료")
                st.rerun()
        with sc2:
            if st.button("➕ 기존 목록에 추가", key="append_chars", use_container_width=True):
                chosen = [_cs["items"][names.index(p)] for p in picks]
                _have = {c.get("name") for c in st.session_state["characters"]}
                _new = [c for c in chosen if c.get("name") not in _have]
                _dup = [c.get("name") for c in chosen if c.get("name") in _have]
                st.session_state["characters"] = st.session_state["characters"] + _new
                st.session_state["cand_chars"] = {}
                if _dup:
                    st.warning("이름이 중복돼 제외했습니다: " + ", ".join(_dup)
                               + " — 같은 이름이 두 명이면 씬 대사 표기가 깨집니다.")
                st.success(f"{len(_new)}명 추가 — 총 {len(st.session_state['characters'])}명")
                st.rerun()
    elif _cs.get("raw"):
        st.warning("라인업을 구조화하지 못했습니다. 아래 원문을 참고해 수동 저장하세요.")
        st.markdown(_cs["raw"])

    if st.session_state["characters"]:
        st.caption(f"현재 확정 캐릭터 {len(st.session_state['characters'])}명 — "
                   + " / ".join(c.get("name", "?") for c in st.session_state["characters"]))
    with st.expander("✏️ 확정 캐릭터 직접 편집 (JSON)"):
        st.caption("위 선택 저장으로 충분합니다. 세부 수정이 필요할 때만 사용하세요.")
        raw_json = st.text_area("이름/concept/difficulty/charm/conflict",
            value=json.dumps(st.session_state["characters"], ensure_ascii=False, indent=2), height=180)
        if st.button("💾 캐릭터 저장", key="save_char"):
            try:
                st.session_state["characters"] = json.loads(raw_json)
                st.success(f"{len(st.session_state['characters'])}명 저장 완료")
            except Exception as e:
                st.error(f"JSON 오류: {e}")


# ── STEP 2. 챕터맵 & 트리트먼트 ────────────────────
with tabs[2]:
    sh("챕터맵 & 트리트먼트", "CHAPTER MAP")
    st.markdown('<span class="rule-badge">LOCKED</span> 최소 6챕터 · 1챕터 무료 데모 · 캐릭터별 에피소드 5~6개 · 캐릭터별 엔딩', unsafe_allow_html=True)

    with st.expander("⏱️ 플레이 타임 추정기 — 환불 임계선 검증 (하드 룰 1)", expanded=False):
        st.markdown(
            '<div class="callout">스팀 환불은 <b>구매 14일 이내 + 플레이 2시간 미만</b>일 때 승인됩니다. '
            '따라서 판정 기준은 챕터 수가 아니라 실제 플레이 타임입니다. '
            '목표는 <b>2시간 30분</b>(임계선 + 30분 안전 마진)입니다.</div>',
            unsafe_allow_html=True)
        pc1, pc2, pc3, pc4 = st.columns(4)
        with pc1:
            _ch = st.number_input("챕터 수", 1, 30, 6, key="pt_ch")
        with pc2:
            _spc = st.number_input("챕터당 씬 수", 1, 100, 12, key="pt_spc")
        with pc3:
            _sps = st.number_input("씬당 재생(초)", 5, 600, 75, key="pt_sps")
        with pc4:
            _cho = st.number_input("총 선택지 수", 0, 300, 30, key="pt_cho")
        if st.button("⏱️ 플레이 타임 산출", key="btn_playtime"):
            r = estimate_playtime(_ch, _spc, _sps, _cho)
            st.session_state["playtime"] = r
        r = st.session_state.get("playtime") or {}
        if r:
            m1, m2, m3 = st.columns(3)
            m1.metric("총 씬 수", f"{r['total_scenes']}개")
            m2.metric("영상 / 선택지", f"{r['video_min']}분 / {r['choice_min']}분")
            m3.metric("1회차 예상", f"{int(r['total_min'])}분",
                      f"{r['total_min'] / 60:.1f}시간")
            if r["over_target"]:
                st.success(f"목표 충족 — 2시간 30분 기준을 {abs(r['gap_to_target'])}분 초과합니다.")
            elif r["over_refund"]:
                st.warning(
                    f"환불 임계선(2시간)은 넘겼으나 안전 마진이 부족합니다. "
                    f"목표까지 {r['gap_to_target']}분 남았습니다. "
                    "챕터를 늘리기 전에 씬 밀도부터 올리세요.")
            else:
                st.error(
                    f"환불 임계선 미달입니다. 2시간까지 "
                    f"{round(REFUND_THRESHOLD_MIN - r['total_min'], 1)}분, "
                    f"목표까지 {r['gap_to_target']}분 부족합니다. "
                    "이 상태로 출시하면 환불률이 매출을 잠식합니다.")

    proj = st.session_state["project"]; chars = st.session_state["characters"]
    if not chars:
        st.warning("STEP 1에서 공략 캐릭터를 먼저 확정하세요.")
    else:
        if st.button("🗺️ 챕터맵 설계", key="btn_cmap"):
            with st.spinner("6챕터 이상 구조로 설계하는 중..."):
                st.session_state["chapter_map"] = call_claude(
                    P.build_chaptermap_prompt(proj, chars), max_tokens=MAX_TOKENS_CHAPTER,
                    model=MODEL_SONNET, label="STEP2 챕터맵")
        if st.session_state["chapter_map"]:
            _tc = check_truncation(st.session_state["chapter_map"], TAIL_MARKER_CHAPTERMAP)
            if not _tc["ok"]:
                st.error(f"⚠️ 저장된 챕터맵이 완결되지 않았습니다 — {_tc['reason']} "
                         f"(끝부분: …{_tc['tail']}) 다시 생성하시기를 권합니다.")
            st.markdown(st.session_state["chapter_map"])
        st.markdown("---")
        names = [c.get("name", f"캐릭터{i+1}") for i, c in enumerate(chars)]
        tchar = st.selectbox("트리트먼트를 쓸 캐릭터", names, key="tr_char")
        if st.button("📝 트리트먼트 작성", key="btn_tr"):
            if not st.session_state["chapter_map"]:
                st.error("먼저 챕터맵을 설계하세요.")
            else:
                with st.spinner(f"{tchar} 루트 트리트먼트 작성 중..."):
                    res = call_claude(
                        P.build_treatment_prompt(proj, chars, st.session_state["chapter_map"], tchar),
                        max_tokens=MAX_TOKENS_CHAPTER, model=MODEL_SONNET,
                        label=f"STEP2 트리트먼트({tchar})")
                    st.session_state["treatments"][tchar] = res
                    _tt = check_truncation(res, TAIL_MARKER_TREATMENT)
                    if not _tt["ok"]:
                        st.error(f"⚠️ 트리트먼트가 완결되지 않았습니다 — {_tt['reason']} "
                                 f"(끝부분: …{_tt['tail']})")
                    st.markdown(res)


# ── STEP 3. 분기 & 기능 설계 ──────────────────────
with tabs[3]:
    sh("분기 & 기능 설계", "BRANCH DESIGN")
    st.caption("호감도·플래그·아이템 변수 + 인게임 기능 매핑 + 배드엔딩 트랩 + 수집요소 도달성 검증")
    proj = st.session_state["project"]; chars = st.session_state["characters"]
    if not chars:
        st.warning("STEP 1에서 캐릭터를 먼저 확정하세요.")
    else:
        names = [c.get("name", f"캐릭터{i+1}") for i, c in enumerate(chars)]
        bchar = st.selectbox("분기를 설계할 캐릭터", names, key="br_char")
        treatment = st.session_state["treatments"].get(bchar, "")
        if not treatment:
            st.info(f"{bchar}의 트리트먼트가 없습니다. STEP 2에서 먼저 작성하면 더 정확합니다.")
        with st.expander("🎛️ 인게임 기능 참고"):
            for k, v in P.INGAME_FEATURES.items():
                st.markdown(f"- **{k}** — {v}")
        if st.button("🌿 분기·변수 설계", key="btn_branch"):
            with st.spinner(f"{bchar} 루트 분기 구조를 설계하는 중..."):
                res = call_claude(
                    P.build_branch_design_prompt(proj, chars, treatment, bchar),
                    max_tokens=MAX_TOKENS_BRANCH, model=MODEL_SONNET,
                    label=f"STEP3 분기설계({bchar})")
                st.session_state["branches"][bchar] = res
                _tb = check_truncation(res, TAIL_MARKER_BRANCH)
                if not _tb["ok"]:
                    st.error(f"⚠️ 분기표가 완결되지 않았습니다 — {_tb['reason']} "
                             f"(끝부분: …{_tb['tail']}) 이 상태로 STEP 6 흐름도에 넘기면 "
                             "노드가 누락된 채 렌더링됩니다.")
                st.markdown(res)

        st.markdown("---")
        with st.expander("📊 선택 비율 감사 — 페이크 남용 진단 (P2)", expanded=False):
            st.markdown(
                '<div class="callout">위 분기표를 보고 유형별 개수를 세어 입력하세요. '
                '<b>진짜 선택 50% 이상 · 페이크 40% 이하 · 트랩 루트당 1~2개</b>가 기준입니다. '
                '페이크가 과반이면 유저는 "선택해봐야 소용없다"를 학습하고 이탈합니다.</div>',
                unsafe_allow_html=True)
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                _real = st.number_input("진짜 선택", 0, 200, 0, key="au_real")
            with ac2:
                _fake = st.number_input("페이크 선택", 0, 200, 0, key="au_fake")
            with ac3:
                _trap = st.number_input("즉사 트랩", 0, 50, 0, key="au_trap")
            if st.button("📊 비율 감사 실행", key="btn_audit"):
                st.session_state["choice_audit"][bchar] = audit_choice_ratio(_real, _fake, _trap)
            a = st.session_state["choice_audit"].get(bchar)
            if a and a["total"]:
                b1, b2, b3 = st.columns(3)
                b1.metric("진짜 선택", f"{a['real_ratio']:.0%}", "기준 50%↑")
                b2.metric("페이크 선택", f"{a['fake_ratio']:.0%}", "기준 40%↓")
                b3.metric("즉사 트랩", f"{a['trap_n']}개", "기준 1~2개")
                if a["verdict"] == "적정":
                    st.success("적정 — 선택 비율이 기준을 충족합니다.")
                else:
                    for msg in a["issues"]:
                        st.warning(msg)


# ── STEP 4. 씬 집필 ───────────────────────────────
with tabs[4]:
    sh("씬 집필", "SCENE WRITING")
    st.caption("블루진 시나리오 형식 + FMV 확장 문법 · 관능적 로맨스 톤 LOCKED")
    proj = st.session_state["project"]; chars = st.session_state["characters"]
    c1, c2 = st.columns([1, 1.3])
    with c1:
        node_info = {
            "node_id": st.text_input("노드 ID", value="CH1_S01"),
            "location": st.text_input("장소", value="지하 벙커 거실"),
            "time": st.text_input("시간", value="밤"),
            "cast": st.text_input("등장 캐릭터", value=""),
            "goal": st.text_area("이 씬의 목적", height=68),
            "choices": st.text_area("선택지 설계(선택)", height=68),
        }
        prev_scene = st.text_area("직전 씬 원고(연결 참고, 선택)", height=90)
        go = st.button("✍️ 씬 집필 (Opus)", key="btn_scene")
    with c2:
        if go:
            with st.spinner("씬을 집필하는 중..."):
                res = call_claude(
                    P.build_scene_writing_prompt(proj, chars, node_info, prev_scene or None),
                    max_tokens=MAX_TOKENS_SCENE, model=MODEL_OPUS,
                    label=f"STEP4 씬집필({node_info['node_id']})")
                st.session_state["scenes"][node_info["node_id"]] = res
                st.code(res, language="markdown")
        elif st.session_state["scenes"]:
            st.caption(f"저장된 씬: {len(st.session_state['scenes'])}개")
            pick = st.selectbox("저장된 씬 보기", list(st.session_state["scenes"].keys()))
            st.code(st.session_state["scenes"][pick], language="markdown")

    if st.session_state["scenes"]:
        st.markdown("---")
        with st.expander("💬 자막 길이 진단 — 글로벌 자막 규격 (P4)", expanded=False):
            st.markdown(
                f'<div class="callout">실사 FMV는 재더빙이 불가능해 글로벌 유저는 전원 자막으로 봅니다. '
                f'한 호흡은 <b>한국어 {SUBTITLE_MAX_CHARS}자 이내</b>(영어 2줄×42자 환산)가 기준입니다. '
                f'초과 줄은 자막이 화면을 덮거나 읽기 전에 넘어갑니다.<br>'
                f'<b>진단 전용입니다. 원고는 자동으로 수정하지 않습니다.</b></div>',
                unsafe_allow_html=True)
            snode = st.selectbox("진단할 씬", list(st.session_state["scenes"].keys()),
                                 key="sub_node")
            slimit = st.slider("기준 글자 수", 15, 60, SUBTITLE_MAX_CHARS, key="sub_limit")
            if st.button("💬 자막 길이 검사", key="btn_sub"):
                over = check_subtitle_length(st.session_state["scenes"][snode], slimit)
                if not over:
                    st.success(f"기준 초과 줄이 없습니다. ({slimit}자 기준)")
                else:
                    st.warning(f"{len(over)}개 줄이 {slimit}자를 초과합니다. "
                               "리액션 샷이나 짧은 지문을 사이에 넣어 두 덩어리로 쪼개는 방식을 권합니다.")
                    for o in over:
                        st.markdown(f"- **{o['line_no']}행 · {o['chars']}자** — {o['text']}")
                    st.caption("지문이 함께 잡힐 수 있습니다. 대사 줄만 참고하세요.")


# ── STEP 5. 스팀 정책 검증 ────────────────────────
with tabs[5]:
    sh("스팀 정책 검증", "STEAM POLICY")
    st.caption("미성년·범죄유도·강제·음주·문화분쟁·노골수위 점검 · FMV 전용 안전 게이트")
    st.markdown(
        '<div class="callout"><span class="rule-badge">HIGH RISK</span> '
        '<b>결제 대행사 기준 (하드 룰 12)</b><br>'
        '2025년 7월 스팀은 결제 대행사·카드 네트워크·은행의 기준을 위반할 소지가 있는 콘텐츠, '
        '특히 특정 종류의 성인 전용 콘텐츠를 금지하는 조항을 추가했고, 실제로 다수 작품이 일괄 삭제됐습니다.<br>'
        '판정 주체가 밸브가 아니라 카드사이며, 기준은 비공개이고, 출시 후 소급 삭제됩니다. '
        '소명 절차가 없으므로 <b>애매하면 배제</b>가 유일한 방어입니다. '
        '실사는 애니메이션·일러스트보다 훨씬 강하게 판정된다는 점도 전제하세요.</div>',
        unsafe_allow_html=True)
    content = st.text_area("검토할 기획/원고 붙여넣기", height=220)
    if st.button("🛡️ 정책 검증", key="btn_steam"):
        if not content.strip():
            st.error("검토할 내용을 입력하세요.")
        else:
            with st.spinner("스팀 정책 위반 소지를 점검하는 중..."):
                st.markdown(call_claude(P.build_steam_check_prompt(content), model=MODEL_SONNET,
                                        label="STEP5 정책검증"))


# ── STEP 6. 분기 흐름도 ───────────────────────────
with tabs[6]:
    sh("분기 흐름도", "FLOWCHART")
    st.caption("노드 분기표 → Mermaid 흐름도 · 미연결(죽은) 분기와 도달 불가 보상 경고")
    node_table = st.text_area("노드 분기표 (STEP 3 결과)",
        value="\n\n".join(st.session_state["branches"].values()) if st.session_state["branches"] else "",
        height=180)
    if st.session_state["branches"]:
        _bad = [k for k, v in st.session_state["branches"].items()
                if not check_truncation(v, TAIL_MARKER_BRANCH)["ok"]]
        if _bad:
            st.warning("다음 루트의 분기표가 완결되지 않았습니다: " + ", ".join(_bad)
                       + " — 흐름도에 노드가 누락될 수 있습니다. STEP 3에서 먼저 재생성하세요.")
    if st.button("🕸️ 흐름도 생성", key="btn_flow"):
        with st.spinner("Mermaid 흐름도를 생성하는 중..."):
            code = call_claude(P.build_flowchart_prompt(node_table), model=MODEL_SONNET,
                               label="STEP6 흐름도")
            st.session_state["flowchart"] = code.replace("```mermaid", "").replace("```", "").strip()
    if st.session_state["flowchart"]:
        html = f"""
        <div class="mermaid" style="background:#fff;padding:20px;border-radius:10px;">
        {st.session_state['flowchart']}
        </div>
        <script type="module">
          import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
          mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
        </script>
        """
        components.html(html, height=560, scrolling=True)
        with st.expander("📝 Mermaid 소스"):
            st.code(st.session_state["flowchart"], language="markdown")


# ── STEP 7. 시뮬레이터 & 출력 ─────────────────────
with tabs[7]:
    sh("시뮬레이터 & 출력", "SIMULATOR & EXPORT")
    proj = st.session_state["project"]; chars = st.session_state["characters"]
    t1, t2 = st.tabs(["🎮 플레이 시뮬레이터", "📤 기획 요약 출력"])
    with t1:
        st.caption("저장된 씬 노드를 따라가며 선택지 플레이를 확인합니다. (STEP 4에서 씬 저장)")
        if not st.session_state["scenes"]:
            st.info("아직 저장된 씬이 없습니다.")
        else:
            cur = st.selectbox("현재 노드", list(st.session_state["scenes"].keys()))
            st.code(st.session_state["scenes"][cur], language="markdown")
            st.caption("선택지 이동은 노드 ID 표기를 따라가며 확인하세요. 자동 분기 이동은 향후 버전 지원 예정입니다.")
    with t2:
        st.caption("전체 기획을 제작·투자 검토용으로 요약합니다.")
        _pt = st.session_state.get("playtime") or {}
        _ca = st.session_state.get("choice_audit") or {}
        if _pt or _ca:
            st.markdown("**진단 현황**")
            d1, d2 = st.columns(2)
            with d1:
                if _pt:
                    _mark = "충족" if _pt.get("over_target") else (
                        "임계선 통과·마진 부족" if _pt.get("over_refund") else "미달")
                    st.metric("1회차 플레이 타임", f"{int(_pt['total_min'])}분", _mark)
                else:
                    st.caption("플레이 타임 미산출 (STEP 2)")
            with d2:
                if _ca:
                    _ng = [k for k, v in _ca.items() if v.get("verdict") != "적정"]
                    st.metric("선택 비율 감사", f"{len(_ca)}개 루트",
                              "전체 적정" if not _ng else f"조정 필요: {', '.join(_ng)}")
                else:
                    st.caption("선택 비율 미감사 (STEP 3)")
            st.markdown("---")
        if st.button("📋 기획 요약 생성", key="btn_summary"):
            if not chars or not st.session_state["chapter_map"]:
                st.error("STEP 1~2를 먼저 완료하세요.")
            else:
                with st.spinner("기획 요약을 생성하는 중..."):
                    summary = call_claude(
                        P.build_final_summary_prompt(proj, chars, st.session_state["chapter_map"]),
                        model=MODEL_SONNET, label="STEP7 기획요약")
                    st.markdown(summary)
                    st.download_button("📥 요약 다운로드 (.md)", data=summary,
                        file_name=f"fmv_summary_{proj.get('title','untitled') or 'untitled'}.md",
                        mime="text/markdown")
        st.caption("💡 DOCX 기획서·시나리오 출력은 다음 버전에서 스킬 연동으로 추가됩니다.")

st.markdown(
    '<div style="text-align:center;font-size:.62rem;padding:30px 0 16px;letter-spacing:2px;opacity:.25;">'
    f'© 2026 BLUE JEANS PICTURES · FMV Engine {P.ENGINE_VERSION} '
    f'({P.ENGINE_BUILD_DATE}) · Opus(집필) + Sonnet(구조·검증)'
    '</div>', unsafe_allow_html=True)
