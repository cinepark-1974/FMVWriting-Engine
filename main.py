"""
🎬 BLUE JEANS FMV ENGINE v1.0 — main.py
게임형 FMV (캐릭터 공략형 멀티 루트 로맨스)
STEP 0~7 파이프라인 · 집필: Opus / 구조·검증: Sonnet
© 2026 BLUE JEANS PICTURES
"""

import json
import time
import streamlit as st
import streamlit.components.v1 as components

import prompt as P
from parser import parse_uploaded_file, truncate_for_prompt

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

MODEL_OPUS = "claude-opus-4-8"
MODEL_SONNET = "claude-sonnet-5"

MAX_TOKENS_CONCEPT = 5000
MAX_TOKENS_CHAPTER = 5000
MAX_TOKENS_BRANCH = 5000
MAX_TOKENS_SCENE = 4000
MAX_TOKENS_ADAPT = 6000

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


def call_claude(prompt_text, max_tokens=4096, model=None):
    if not _HAS_ANTHROPIC:
        st.error("anthropic 패키지가 설치되지 않았습니다. requirements.txt를 확인하세요.")
        return ""
    key = _get_api_key()
    if not key:
        st.error("API Key가 없습니다. Secrets에 넣거나 아래 설정에서 입력하세요.")
        return ""
    if model is None:
        model = MODEL_SONNET
    last_error = None
    for attempt in range(2):
        try:
            client = anthropic.Anthropic(api_key=key)
            full = []
            with client.messages.stream(
                model=model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt_text}],
            ) as stream:
                for text in stream.text_stream:
                    full.append(text)
            result = "".join(full).strip()
            if not result or len(result) < 30:
                last_error = f"응답 너무 짧음 ({len(result)}자)"
                if attempt == 0:
                    time.sleep(2); continue
                st.error(f"⚠️ API 응답 부족 (2회 실패): {last_error}")
                return ""
            return result
        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)[:180]}"
            if attempt == 0:
                time.sleep(3); continue
            st.error(f"❌ API 호출 실패 (2회 시도): {last_error}")
            st.caption("네트워크·rate limit·토큰 한도·안전 필터·인증 오류 가능. 잠시 후 재시도하세요.")
            return ""


def sh(title, en):
    st.markdown(f'<div class="section-header"><span>{title} · {en}</span></div>', unsafe_allow_html=True)


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

# 백업 / 복원
with st.expander("💾 작업 저장 / 불러오기"):
    col_a, col_b = st.columns(2)
    backup_payload = {
        "project": st.session_state["project"], "characters": st.session_state["characters"],
        "chapter_map": st.session_state["chapter_map"], "treatments": st.session_state["treatments"],
        "branches": st.session_state["branches"], "scenes": st.session_state["scenes"],
        "flowchart": st.session_state["flowchart"],
    }
    with col_a:
        st.download_button(
            "📥 기획 저장 (.json)",
            data=json.dumps(backup_payload, ensure_ascii=False, indent=2),
            file_name=f"fmv_{st.session_state['project'].get('title','untitled') or 'untitled'}.json",
            mime="application/json", use_container_width=True,
        )
    with col_b:
        restore = st.file_uploader("📂 불러오기 (.json)", type=["json"], label_visibility="collapsed")
        if restore is not None:
            try:
                data = json.load(restore)
                for k in backup_payload:
                    if k in data:
                        st.session_state[k] = data[k]
                st.success("✅ 복원 완료"); st.rerun()
            except Exception as e:
                st.error(f"복원 실패: {e}")

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
                                    max_tokens=MAX_TOKENS_ADAPT, model=MODEL_SONNET))


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

    st.markdown('<div class="callout"><b>① 훅 발굴</b> — 아이디어 한 조각만 있어도 시작하세요. 완성된 한 줄 훅 후보를 뽑아드립니다.</div>', unsafe_allow_html=True)
    fragment = st.text_input("재료 한두 조각 (막연해도 됩니다)",
        placeholder="예: 좀비 / 요가복 / 회사 상사 / 무인도 / 룸메이트")
    if st.button("💡 한 줄 훅 후보 생성", key="btn_hook"):
        if not fragment.strip():
            st.error("재료를 한 조각이라도 입력하세요. (단어 하나면 충분합니다)")
        else:
            with st.spinner("스토리타코 훅 공식으로 후보를 뽑는 중..."):
                st.markdown(call_claude(
                    P.build_hook_finder_prompt(fragment, proj["target"]),
                    max_tokens=MAX_TOKENS_CONCEPT, model=MODEL_SONNET))
                st.caption("💡 마음에 드는 훅을 위 '한 줄 훅' 칸에 옮겨 적으면 다음 단계로 이어집니다.")

    st.markdown('<div class="callout"><b>② 컨셉 브레인스토밍</b></div>', unsafe_allow_html=True)
    keywords = st.text_area("소재 키워드",
        placeholder="예: 좀비 아포칼립스, 셸터 고립, 미녀 생존자들, 지켜야 하는 남자 주인공", height=70)
    if st.button("🔥 컨셉 후보 생성", key="btn_concept"):
        with st.spinner("스토리타코 수준 컨셉 후보를 뽑는 중..."):
            st.markdown(call_claude(P.build_concept_prompt(proj, keywords),
                                    max_tokens=MAX_TOKENS_CONCEPT, model=MODEL_SONNET))

    st.markdown('<div class="callout"><b>③ 공략 캐릭터 설계</b></div>', unsafe_allow_html=True)
    n_char = st.slider("공략 캐릭터 수", 2, 5, 4)
    if st.button("👥 캐릭터 라인업 생성", key="btn_char"):
        with st.spinner("컨셉 비중복·난이도 차등으로 설계하는 중..."):
            st.markdown(call_claude(
                P.build_character_prompt(proj, n_char, st.session_state["characters"]),
                max_tokens=MAX_TOKENS_CONCEPT, model=MODEL_SONNET))
            st.caption("💡 확정한 캐릭터는 아래에 정리해 저장하세요.")
    with st.expander("✏️ 확정 캐릭터 저장 (JSON)"):
        raw = st.text_area("이름/concept/difficulty/charm/conflict",
            value=json.dumps(st.session_state["characters"], ensure_ascii=False, indent=2), height=180)
        if st.button("💾 캐릭터 저장", key="save_char"):
            try:
                st.session_state["characters"] = json.loads(raw)
                st.success(f"{len(st.session_state['characters'])}명 저장 완료")
            except Exception as e:
                st.error(f"JSON 오류: {e}")


# ── STEP 2. 챕터맵 & 트리트먼트 ────────────────────
with tabs[2]:
    sh("챕터맵 & 트리트먼트", "CHAPTER MAP")
    st.markdown('<span class="rule-badge">LOCKED</span> 최소 6챕터 · 1챕터 무료 데모 · 캐릭터별 에피소드 5~6개 · 캐릭터별 엔딩', unsafe_allow_html=True)
    proj = st.session_state["project"]; chars = st.session_state["characters"]
    if not chars:
        st.warning("STEP 1에서 공략 캐릭터를 먼저 확정하세요.")
    else:
        if st.button("🗺️ 챕터맵 설계", key="btn_cmap"):
            with st.spinner("6챕터 이상 구조로 설계하는 중..."):
                st.session_state["chapter_map"] = call_claude(
                    P.build_chaptermap_prompt(proj, chars), max_tokens=MAX_TOKENS_CHAPTER, model=MODEL_SONNET)
        if st.session_state["chapter_map"]:
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
                        max_tokens=MAX_TOKENS_CHAPTER, model=MODEL_SONNET)
                    st.session_state["treatments"][tchar] = res
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
                    max_tokens=MAX_TOKENS_BRANCH, model=MODEL_SONNET)
                st.session_state["branches"][bchar] = res
                st.markdown(res)


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
                    max_tokens=MAX_TOKENS_SCENE, model=MODEL_OPUS)
                st.session_state["scenes"][node_info["node_id"]] = res
                st.code(res, language="markdown")
        elif st.session_state["scenes"]:
            st.caption(f"저장된 씬: {len(st.session_state['scenes'])}개")
            pick = st.selectbox("저장된 씬 보기", list(st.session_state["scenes"].keys()))
            st.code(st.session_state["scenes"][pick], language="markdown")


# ── STEP 5. 스팀 정책 검증 ────────────────────────
with tabs[5]:
    sh("스팀 정책 검증", "STEAM POLICY")
    st.caption("미성년·범죄유도·강제·음주·문화분쟁·노골수위 점검 · FMV 전용 안전 게이트")
    content = st.text_area("검토할 기획/원고 붙여넣기", height=220)
    if st.button("🛡️ 정책 검증", key="btn_steam"):
        if not content.strip():
            st.error("검토할 내용을 입력하세요.")
        else:
            with st.spinner("스팀 정책 위반 소지를 점검하는 중..."):
                st.markdown(call_claude(P.build_steam_check_prompt(content), model=MODEL_SONNET))


# ── STEP 6. 분기 흐름도 ───────────────────────────
with tabs[6]:
    sh("분기 흐름도", "FLOWCHART")
    st.caption("노드 분기표 → Mermaid 흐름도 · 미연결(죽은) 분기와 도달 불가 보상 경고")
    node_table = st.text_area("노드 분기표 (STEP 3 결과)",
        value="\n\n".join(st.session_state["branches"].values()) if st.session_state["branches"] else "",
        height=180)
    if st.button("🕸️ 흐름도 생성", key="btn_flow"):
        with st.spinner("Mermaid 흐름도를 생성하는 중..."):
            code = call_claude(P.build_flowchart_prompt(node_table), model=MODEL_SONNET)
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
        if st.button("📋 기획 요약 생성", key="btn_summary"):
            if not chars or not st.session_state["chapter_map"]:
                st.error("STEP 1~2를 먼저 완료하세요.")
            else:
                with st.spinner("기획 요약을 생성하는 중..."):
                    summary = call_claude(
                        P.build_final_summary_prompt(proj, chars, st.session_state["chapter_map"]),
                        model=MODEL_SONNET)
                    st.markdown(summary)
                    st.download_button("📥 요약 다운로드 (.md)", data=summary,
                        file_name=f"fmv_summary_{proj.get('title','untitled') or 'untitled'}.md",
                        mime="text/markdown")
        st.caption("💡 DOCX 기획서·시나리오 출력은 다음 버전에서 스킬 연동으로 추가됩니다.")

st.markdown(
    '<div style="text-align:center;font-size:.62rem;padding:30px 0 16px;letter-spacing:2px;opacity:.25;">'
    '© 2026 BLUE JEANS PICTURES · FMV Engine v1.0 · Opus(집필) + Sonnet(구조·검증)'
    '</div>', unsafe_allow_html=True)
