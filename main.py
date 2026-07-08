# ─────────────────────────────────────────────────────────────
# BLUE JEANS FMV ENGINE v1.0
# main.py — Streamlit UI + Claude API + 세션/백업 + 시뮬레이터 + DOCX
# © 2026 BLUE JEANS PICTURES
#
# 결과물 유형: 게임형 FMV (스토리타코 모델 — 캐릭터 공략형 멀티 루트 로맨스)
# GitHub: cinepark-1974/FMV-Engine
# ─────────────────────────────────────────────────────────────

import json
import streamlit as st
import streamlit.components.v1 as components

import prompt as P
from parser import parse_uploaded_file, truncate_for_prompt

# ── Anthropic SDK ─────────────────────────────────────────────
try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

# 모델 상수 (기존 엔진과 통일: Opus=집필, Sonnet=구조)
MODEL_OPUS = "claude-opus-4-8"
MODEL_SONNET = "claude-sonnet-5"

# ═══════════════════════════════════════════════════════════
# 페이지 설정 & BLUE JEANS CI 테마 (네이비 #191970 / 옐로우 #FFCB05)
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="BLUE JEANS FMV ENGINE",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root {
    --navy: #191970;
    --yellow: #FFCB05;
    --bg: #F7F7F5;
    --ink: #1A1A2E;
}
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg);
    font-family: 'Pretendard', -apple-system, sans-serif;
}
[data-testid="stSidebar"] {
    background-color: var(--navy);
}
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stRadio label { color: #E8E8F0 !important; }
h1, h2, h3 { color: var(--navy) !important; font-weight: 800 !important; }
.bj-header {
    border-left: 6px solid var(--yellow);
    padding: 4px 0 4px 14px;
    margin-bottom: 8px;
}
.bj-tag {
    display: inline-block; background: var(--yellow); color: var(--navy);
    font-weight: 700; font-size: 0.72rem; padding: 2px 10px;
    border-radius: 4px; letter-spacing: 1px;
}
div.stButton > button {
    background: var(--navy); color: #FFFFFF; border: none;
    border-radius: 6px; font-weight: 700; padding: 10px 20px; width: 100%;
}
div.stButton > button:hover {
    background: var(--yellow); color: var(--navy);
}
div[data-testid="stExpander"] {
    border: 1px solid #E0E0E8; border-radius: 8px; background: #FFFFFF;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# 세션 상태 초기화
# ═══════════════════════════════════════════════════════════

def _init_state():
    defaults = {
        "api_key": "",
        "project": {
            "title": "",
            "subconcept": "순정 로맨스",
            "target": "남성향",
            "hook": "",
            "world": "",
            "pov": "1인칭 남성 주인공",
        },
        "characters": [],       # 공략 캐릭터 리스트
        "chapter_map": "",      # 챕터맵 텍스트
        "treatments": {},       # 캐릭터명 → 트리트먼트
        "branches": {},         # 캐릭터명 → 분기 설계
        "scenes": {},           # 노드ID → 씬 원고
        "flowchart": "",        # Mermaid 코드
        "manuscript": "",       # 각색 모드 원고 텍스트
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ═══════════════════════════════════════════════════════════
# Claude API 호출 래퍼
# ═══════════════════════════════════════════════════════════

def call_claude(prompt_text, model=MODEL_SONNET, max_tokens=4000):
    """Anthropic API 호출. 실패 시 오류 문자열 반환."""
    if not _HAS_ANTHROPIC:
        return "[오류] anthropic 패키지가 설치되지 않았습니다. requirements.txt 확인."
    key = st.session_state.get("api_key", "").strip()
    if not key:
        return "[오류] 사이드바에 Anthropic API Key를 입력하세요."
    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt_text}],
        )
        return "".join(
            block.text for block in resp.content if hasattr(block, "text")
        ).strip()
    except Exception as e:
        return f"[오류] API 호출 실패: {e}"


# ═══════════════════════════════════════════════════════════
# 사이드바 — 브랜딩 / API / 백업·복원 / 단계 선택
# ═══════════════════════════════════════════════════════════

st.sidebar.markdown("""
<div style="text-align:center; padding:14px 0; border-bottom:2px solid #FFCB05; margin-bottom:16px;">
  <div style="font-size:1.4rem; font-weight:800; color:#FFCB05; letter-spacing:1px;">FMV ENGINE</div>
  <div style="font-size:0.7rem; color:#C8C8E0; letter-spacing:3px; margin-top:4px;">BLUE JEANS PICTURES</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.subheader("🔑 AI 엔진 설정")
st.session_state["api_key"] = st.sidebar.text_input(
    "Anthropic API Key", type="password", value=st.session_state["api_key"],
    help="집필(Opus)·구조(Sonnet) 호출에 사용됩니다.",
)

st.sidebar.markdown("---")

# 백업 / 복원
st.sidebar.subheader("💾 작업 저장소")
backup_payload = {
    "project": st.session_state["project"],
    "characters": st.session_state["characters"],
    "chapter_map": st.session_state["chapter_map"],
    "treatments": st.session_state["treatments"],
    "branches": st.session_state["branches"],
    "scenes": st.session_state["scenes"],
    "flowchart": st.session_state["flowchart"],
}
st.sidebar.download_button(
    "📥 기획 저장 (.json)",
    data=json.dumps(backup_payload, ensure_ascii=False, indent=2),
    file_name=f"fmv_{st.session_state['project'].get('title','untitled') or 'untitled'}.json",
    mime="application/json",
    use_container_width=True,
)
restore = st.sidebar.file_uploader("📂 기획 불러오기 (.json)", type=["json"])
if restore is not None:
    try:
        data = json.load(restore)
        for k in backup_payload:
            if k in data:
                st.session_state[k] = data[k]
        st.sidebar.success("✅ 복원 완료")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"복원 실패: {e}")

st.sidebar.markdown("---")

# 단계 선택
st.sidebar.markdown("### 🎬 제작 단계")
menu = st.sidebar.radio(
    "파이프라인",
    [
        "STEP 0. 📄 원고 각색 (선택)",
        "STEP 1. 💡 컨셉 & 캐릭터",
        "STEP 2. 🗂️ 챕터맵 & 트리트먼트",
        "STEP 3. 🌿 분기 & 기능 설계",
        "STEP 4. ✍️ 씬 집필",
        "STEP 5. 🛡️ 스팀 정책 검증",
        "STEP 6. 🕸️ 분기 흐름도",
        "STEP 7. 🎮 시뮬레이터 & 출력",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption("게임형 FMV · 스토리타코 모델\n캐릭터 공략형 멀티 루트 로맨스")


# ═══════════════════════════════════════════════════════════
# STEP 0. 원고 각색 (선택)
# ═══════════════════════════════════════════════════════════

if menu.startswith("STEP 0"):
    st.markdown('<div class="bj-header"><span class="bj-tag">STEP 0</span></div>', unsafe_allow_html=True)
    st.title("📄 원고 각색 — 웹소설/웹툰 → FMV")
    st.write("기존 완성 원고(웹소설·웹툰)나 기획서를 넣으면, FMV 각색용으로 캐릭터·분기점을 해체합니다. 신규 창작이면 이 단계를 건너뛰고 STEP 1로 가세요.")
    st.write("---")

    up = st.file_uploader("원고 파일 업로드 (DOCX / PDF / TXT / MD)", type=["docx", "pdf", "txt", "md"])
    target = st.selectbox("타깃 성향", P.TARGET_TYPES, index=P.TARGET_TYPES.index("여성향(오토메)"))

    if up is not None:
        text = parse_uploaded_file(up)
        st.session_state["manuscript"] = text
        st.success(f"원고 로드 완료 — 총 {len(text):,}자")
        with st.expander("📖 원고 미리보기 (앞부분)"):
            st.text(text[:2000])

    if st.session_state["manuscript"] and st.button("🔍 FMV 각색 해체 실행 (Sonnet)"):
        with st.spinner("원고를 해체해 캐릭터·분기점을 추출하는 중..."):
            manuscript = truncate_for_prompt(st.session_state["manuscript"])
            result = call_claude(
                P.build_adaptation_prompt(manuscript, target),
                model=MODEL_SONNET, max_tokens=6000,
            )
            st.markdown(result)
            st.info("추출된 캐릭터·컨셉을 참고해 STEP 1에서 프로젝트를 확정하세요.")


# ═══════════════════════════════════════════════════════════
# STEP 1. 컨셉 & 캐릭터
# ═══════════════════════════════════════════════════════════

elif menu.startswith("STEP 1"):
    st.markdown('<div class="bj-header"><span class="bj-tag">STEP 1</span></div>', unsafe_allow_html=True)
    st.title("💡 컨셉 & 캐릭터 기획")
    st.write("---")

    proj = st.session_state["project"]
    c1, c2 = st.columns(2)
    with c1:
        proj["title"] = st.text_input("작품 제목", value=proj["title"])
        proj["subconcept"] = st.selectbox(
            "서브컨셉", list(P.SUBCONCEPTS.keys()),
            index=list(P.SUBCONCEPTS.keys()).index(proj["subconcept"]) if proj["subconcept"] in P.SUBCONCEPTS else 0,
        )
        st.caption(P.SUBCONCEPTS.get(proj["subconcept"], ""))
    with c2:
        proj["target"] = st.selectbox(
            "타깃 성향", P.TARGET_TYPES,
            index=P.TARGET_TYPES.index(proj["target"]) if proj["target"] in P.TARGET_TYPES else 0,
        )
        proj["pov"] = st.text_input("주인공 시점", value=proj["pov"])

    proj["hook"] = st.text_input("한 줄 훅", value=proj["hook"])
    proj["world"] = st.text_area("세계관 원포인트 (고립·공존 공간 등)", value=proj["world"], height=80)
    st.session_state["project"] = proj

    st.write("---")
    st.subheader("① 컨셉 브레인스토밍")
    keywords = st.text_area(
        "소재 키워드",
        placeholder="예: 좀비 아포칼립스, 셸터 고립, 미녀 생존자들, 지켜야 하는 남자 주인공",
        height=80,
    )
    if st.button("🔥 컨셉 후보 생성 (Sonnet)"):
        with st.spinner("스토리타코 수준 컨셉 후보를 뽑는 중..."):
            st.markdown(call_claude(P.build_concept_prompt(proj, keywords), model=MODEL_SONNET))

    st.write("---")
    st.subheader("② 공략 캐릭터 설계")
    n_char = st.slider("공략 캐릭터 수", 2, 5, 4)
    if st.button("👥 캐릭터 라인업 생성 (Sonnet)"):
        with st.spinner("컨셉 비중복·난이도 차등으로 캐릭터를 설계하는 중..."):
            result = call_claude(
                P.build_character_prompt(proj, n_char, st.session_state["characters"]),
                model=MODEL_SONNET,
            )
            st.markdown(result)
            st.caption("💡 확정한 캐릭터는 아래 입력란에 정리해 저장하세요. (다음 단계가 이 데이터를 참조합니다)")

    with st.expander("✏️ 확정 캐릭터 수동 입력/편집"):
        raw = st.text_area(
            "캐릭터 JSON 리스트 (이름/concept/difficulty/charm/conflict)",
            value=json.dumps(st.session_state["characters"], ensure_ascii=False, indent=2),
            height=200,
        )
        if st.button("💾 캐릭터 저장"):
            try:
                st.session_state["characters"] = json.loads(raw)
                st.success(f"{len(st.session_state['characters'])}명 저장 완료")
            except Exception as e:
                st.error(f"JSON 형식 오류: {e}")


# ═══════════════════════════════════════════════════════════
# STEP 2. 챕터맵 & 트리트먼트
# ═══════════════════════════════════════════════════════════

elif menu.startswith("STEP 2"):
    st.markdown('<div class="bj-header"><span class="bj-tag">STEP 2</span></div>', unsafe_allow_html=True)
    st.title("🗂️ 챕터맵 & 트리트먼트")
    st.write("스토리타코 하드 룰: 최소 6챕터 · 1챕터 무료 데모 · 캐릭터별 에피소드 5~6개 · 캐릭터별 엔딩 챕터")
    st.write("---")

    proj = st.session_state["project"]
    chars = st.session_state["characters"]

    if not chars:
        st.warning("STEP 1에서 공략 캐릭터를 먼저 확정하세요.")
    else:
        st.subheader("① 전체 챕터맵")
        if st.button("🗺️ 챕터맵 설계 (Sonnet)"):
            with st.spinner("6챕터 이상 구조로 챕터맵을 설계하는 중..."):
                st.session_state["chapter_map"] = call_claude(
                    P.build_chaptermap_prompt(proj, chars), model=MODEL_SONNET, max_tokens=5000,
                )
        if st.session_state["chapter_map"]:
            st.markdown(st.session_state["chapter_map"])

        st.write("---")
        st.subheader("② 캐릭터별 루트 트리트먼트")
        char_names = [c.get("name", f"캐릭터{i+1}") for i, c in enumerate(chars)]
        target_char = st.selectbox("트리트먼트를 쓸 캐릭터", char_names)
        if st.button("📝 트리트먼트 작성 (Sonnet)"):
            if not st.session_state["chapter_map"]:
                st.error("먼저 챕터맵을 설계하세요.")
            else:
                with st.spinner(f"{target_char} 루트 트리트먼트 작성 중..."):
                    result = call_claude(
                        P.build_treatment_prompt(proj, chars, st.session_state["chapter_map"], target_char),
                        model=MODEL_SONNET, max_tokens=5000,
                    )
                    st.session_state["treatments"][target_char] = result
                    st.markdown(result)


# ═══════════════════════════════════════════════════════════
# STEP 3. 분기 & 기능 설계
# ═══════════════════════════════════════════════════════════

elif menu.startswith("STEP 3"):
    st.markdown('<div class="bj-header"><span class="bj-tag">STEP 3</span></div>', unsafe_allow_html=True)
    st.title("🌿 분기 & 기능 설계")
    st.write("호감도·플래그·아이템 변수 + 인게임 기능 매핑 + 배드엔딩 트랩 + 수집요소 도달성 검증")
    st.write("---")

    proj = st.session_state["project"]
    chars = st.session_state["characters"]

    if not chars:
        st.warning("STEP 1에서 캐릭터를 먼저 확정하세요.")
    else:
        char_names = [c.get("name", f"캐릭터{i+1}") for i, c in enumerate(chars)]
        target_char = st.selectbox("분기를 설계할 캐릭터", char_names)
        treatment = st.session_state["treatments"].get(target_char, "")
        if not treatment:
            st.info(f"{target_char}의 트리트먼트가 없습니다. STEP 2에서 먼저 작성하면 더 정확합니다.")
        with st.expander("🎛️ 인게임 기능 참고"):
            for k, v in P.INGAME_FEATURES.items():
                st.markdown(f"- **{k}** — {v}")
        if st.button("🌿 분기·변수 설계 (Sonnet)"):
            with st.spinner(f"{target_char} 루트 분기 구조를 설계하는 중..."):
                result = call_claude(
                    P.build_branch_design_prompt(proj, chars, treatment, target_char),
                    model=MODEL_SONNET, max_tokens=5000,
                )
                st.session_state["branches"][target_char] = result
                st.markdown(result)


# ═══════════════════════════════════════════════════════════
# STEP 4. 씬 집필
# ═══════════════════════════════════════════════════════════

elif menu.startswith("STEP 4"):
    st.markdown('<div class="bj-header"><span class="bj-tag">STEP 4</span></div>', unsafe_allow_html=True)
    st.title("✍️ 씬 집필")
    st.write("블루진 시나리오 형식 + FMV 확장 문법(노드ID·선택지·기능태그). 관능적 로맨스 톤 LOCKED.")
    st.write("---")

    proj = st.session_state["project"]
    chars = st.session_state["characters"]

    c1, c2 = st.columns([1, 1.3])
    with c1:
        st.subheader("🛠️ 노드 정보")
        node_info = {
            "node_id": st.text_input("노드 ID", value="CH1_S01"),
            "location": st.text_input("장소", value="지하 벙커 거실"),
            "time": st.text_input("시간", value="밤"),
            "cast": st.text_input("등장 캐릭터", value=""),
            "goal": st.text_area("이 씬의 목적", height=70),
            "choices": st.text_area("선택지 설계(선택)", height=70),
        }
        prev_scene = st.text_area("직전 씬 원고(연결 참고, 선택)", height=100)
        go = st.button("✍️ 씬 집필 (Opus)")
    with c2:
        st.subheader("📄 생성 원고")
        if go:
            with st.spinner("씬을 집필하는 중..."):
                result = call_claude(
                    P.build_scene_writing_prompt(proj, chars, node_info, prev_scene or None),
                    model=MODEL_OPUS, max_tokens=4000,
                )
                st.session_state["scenes"][node_info["node_id"]] = result
                st.code(result, language="markdown")
        elif st.session_state["scenes"]:
            st.caption(f"저장된 씬: {len(st.session_state['scenes'])}개")
            pick = st.selectbox("저장된 씬 보기", list(st.session_state["scenes"].keys()))
            st.code(st.session_state["scenes"][pick], language="markdown")


# ═══════════════════════════════════════════════════════════
# STEP 5. 스팀 정책 검증
# ═══════════════════════════════════════════════════════════

elif menu.startswith("STEP 5"):
    st.markdown('<div class="bj-header"><span class="bj-tag">STEP 5</span></div>', unsafe_allow_html=True)
    st.title("🛡️ 스팀 정책 검증")
    st.write("미성년·범죄유도·강제·음주·문화분쟁·노골수위를 점검합니다. FMV 전용 안전 게이트.")
    st.write("---")

    content = st.text_area("검토할 기획/원고 붙여넣기", height=250)
    if st.button("🛡️ 정책 검증 (Sonnet)"):
        if not content.strip():
            st.error("검토할 내용을 입력하세요.")
        else:
            with st.spinner("스팀 정책 위반 소지를 점검하는 중..."):
                st.markdown(call_claude(P.build_steam_check_prompt(content), model=MODEL_SONNET))


# ═══════════════════════════════════════════════════════════
# STEP 6. 분기 흐름도 (Mermaid)
# ═══════════════════════════════════════════════════════════

elif menu.startswith("STEP 6"):
    st.markdown('<div class="bj-header"><span class="bj-tag">STEP 6</span></div>', unsafe_allow_html=True)
    st.title("🕸️ 분기 흐름도")
    st.write("노드 분기표 → Mermaid 흐름도. 미연결(죽은) 분기와 도달 불가 보상을 경고합니다.")
    st.write("---")

    node_table = st.text_area(
        "노드 분기표 붙여넣기 (STEP 3 결과)",
        value="\n\n".join(st.session_state["branches"].values()) if st.session_state["branches"] else "",
        height=200,
    )
    if st.button("🕸️ 흐름도 생성 (Sonnet)"):
        with st.spinner("Mermaid 흐름도를 생성하는 중..."):
            code = call_claude(P.build_flowchart_prompt(node_table), model=MODEL_SONNET)
            code = code.replace("```mermaid", "").replace("```", "").strip()
            st.session_state["flowchart"] = code

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


# ═══════════════════════════════════════════════════════════
# STEP 7. 시뮬레이터 & 출력
# ═══════════════════════════════════════════════════════════

elif menu.startswith("STEP 7"):
    st.markdown('<div class="bj-header"><span class="bj-tag">STEP 7</span></div>', unsafe_allow_html=True)
    st.title("🎮 시뮬레이터 & 출력")
    st.write("---")

    proj = st.session_state["project"]
    chars = st.session_state["characters"]

    tab1, tab2 = st.tabs(["🎮 플레이 시뮬레이터", "📤 기획서 출력"])

    with tab1:
        st.write("저장된 씬 노드를 따라가며 선택지 플레이를 시뮬레이션합니다. (STEP 4에서 씬을 저장하세요)")
        if not st.session_state["scenes"]:
            st.info("아직 저장된 씬이 없습니다.")
        else:
            node_ids = list(st.session_state["scenes"].keys())
            cur = st.selectbox("현재 노드", node_ids)
            st.code(st.session_state["scenes"][cur], language="markdown")
            st.caption("선택지 이동은 노드 ID 표기를 따라가며 확인하세요. 자동 분기 이동은 향후 버전에서 지원 예정입니다.")

    with tab2:
        st.write("전체 기획을 요약해 제작·투자 검토용으로 정리합니다.")
        if st.button("📋 기획 요약 생성 (Sonnet)"):
            if not chars or not st.session_state["chapter_map"]:
                st.error("STEP 1~2를 먼저 완료하세요.")
            else:
                with st.spinner("기획 요약을 생성하는 중..."):
                    summary = call_claude(
                        P.build_final_summary_prompt(proj, chars, st.session_state["chapter_map"]),
                        model=MODEL_SONNET,
                    )
                    st.markdown(summary)
                    st.download_button(
                        "📥 요약 다운로드 (.md)",
                        data=summary,
                        file_name=f"fmv_summary_{proj.get('title','untitled') or 'untitled'}.md",
                        mime="text/markdown",
                    )
        st.caption("💡 DOCX 기획서·시나리오 출력은 다음 버전에서 bluejeans-proposal / bluejeans-screenplay-format 스킬 연동으로 추가됩니다.")
