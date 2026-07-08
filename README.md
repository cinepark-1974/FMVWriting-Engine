# 🎬 BLUE JEANS FMV ENGINE v1.0

> BLUE JEANS PICTURES · FMV 각본 작성 엔진
> 게임형 FMV (캐릭터 공략형 멀티 루트 로맨스)

실사 영상 기반 인터랙티브 드라마(FMV, Full Motion Video)의 **기획 → 분기 설계 → 집필**을 수행하는 각본 엔진입니다. 선형 시나리오가 아니라, 플레이어 선택에 따라 갈라지는 멀티 루트 로맨스를 설계합니다. 

---

## 특징

- **실전 하드 룰 내장** — 6챕터 강제(스팀 환불 정책 대응), 1챕터 무료 데모, 캐릭터별 에피소드 5~6개, 캐릭터별 엔딩 챕터
- **관능적 로맨스 톤 LOCKED** — 메인 톤 고정 + 코믹 서브톤 비율 제한으로 오글거림·톤 흔들림 방지
- **스팀 정책 자동 검증 게이트** — 미성년·범죄유도·강제·노골수위를 기획 단계에서 차단(판매 중단 리스크 예방)
- **수집요소 도달성 검증** — 열린다고 표기된 보상이 실제 도달 가능한지 검증(죽은 분기 방지)
- **각색 모드** — 기존 웹소설·웹툰 원고(DOCX/PDF/TXT)를 넣어 FMV로 해체·재구성
- **BLUE JEANS 디자인 시스템** — 네이비 #191970 / 옐로우 #FFCB05 (기존 엔진과 통일)

---

## 파이프라인 (STEP 0~7)

```
STEP 0. 원고 각색 (선택)   — 웹소설/웹툰 원고 → 캐릭터·분기점 추출
STEP 1. 컨셉 & 캐릭터       — 로맨스 서브컨셉 + 공략 캐릭터(비중복·난이도 차등)
STEP 2. 챕터맵 & 트리트먼트 — 6챕터+ 구조, 캐릭터별 에피소드·엔딩
STEP 3. 분기 & 기능 설계    — 호감도/플래그/아이템 + 인게임 기능 + 배드엔딩 트랩
STEP 4. 씬 집필 (Opus)      — 블루진 시나리오 형식 + FMV 확장 문법
STEP 5. 스팀 정책 검증      — 판매 중단 리스크 게이트
STEP 6. 분기 흐름도         — Mermaid 노드맵 (죽은 분기 경고)
STEP 7. 시뮬레이터 & 출력   — 플레이 테스트 + 기획 요약
```

모델 분리: 집필 = Claude Opus / 구조·검증 = Claude Sonnet

---

## 파일 구조

```
FMV-Engine/
├── main.py              # Streamlit UI + API + 세션/백업 + 시뮬레이터
├── prompt.py            # 시스템 프롬프트 + 스토리타코 룰셋 + 10개 빌더 함수
├── parser.py            # 원고 파서 (DOCX/PDF/TXT/MD)
├── requirements.txt
├── README.md
└── .streamlit/
    └── config.toml
```

---

## 설치 및 실행

```bash
streamlit run main.py
```

Streamlit Cloud 배포 시 Secrets에 추가:
```toml
ANTHROPIC_API_KEY = "sk-ant-api03-..."
```
(또는 앱 사이드바에서 직접 키 입력)

---

## 엔진 생태계

```
Idea Engine → Creator Engine → Writer / Series / Novel / WebNovel Engine
                            └─→ ★ FMV Engine (인터랙티브 멀티 루트)
                            └─→ Rewrite / Revise Engine → Translator Engines
```

FMV Engine은 선형 서사 엔진들과 데이터 구조가 다른(노드·분기·변수) 독립 엔진입니다. 기획부터 FMV 전용 논리로 움직입니다.

---

## 버전 히스토리

| 버전 | 변경 |
|------|------|
| v1.0 | 초기 빌드. STEP 0~7 파이프라인. 관능적 로맨스 톤 LOCKED. 스팀 정책 게이트. 수집요소 도달성 검증. 각색 모드. |

---

© 2026 BLUE JEANS PICTURES · FMV Engine v1.0
