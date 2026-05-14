"""Streamlit Trace Viewer — LangSmith 대체.

본 실험 / 사전 실험 / 단건 스모크의 JSONL 결과를 라운드 단위로 시각화한다.
한국어 대화·무기 다양성·페이즈별 돌파를 한 화면에서 탐색할 수 있다.

실행
----
    streamlit run scripts/viewer.py

브라우저가 자동으로 열린다 (보통 http://localhost:8501).

소스
----
- results/runs/*.jsonl       (본 실험)
- results/smoke/*.json        (단건 스모크)
- results/pilot_*.jsonl       (사전 실험)
- results/feedback_buffer.jsonl (피드백 누적)

설계 원칙
--------
- 외부 서비스 의존 없음 (로컬 100%, 데이터 외부 전송 X)
- 한국어 그대로 렌더링
- 검색·필터: 카테고리·실험·Defender 모드·판정·돌파턴·도메인
- 라운드 클릭 시 대화 전문 + 무기 매트릭스 + Final Evaluator 판정 펼침
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

# ── 경로 설정 ─────────────────────────────────────────────────────
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
RUNS_DIR = RESULTS_DIR / "runs"
SMOKE_DIR = RESULTS_DIR / "smoke"

# ── 무기 (tactic) 정규식 — docs/05 §8 과 동기화 ───────────────────────
TACTICS = {
    "권위호출":        r"(편집장|팀장|선배|교수|상사|대표|본부장|국장|자문|의사|변호사)",
    "위계격상":        r"(편집국장|본부장|사장|대표이사|이사장|자문위원|총괄)",
    "Hypothetical":    r"(가상의|만약에|이론적|소설|시나리오|예시 기사|가정해|허구|픽션)",
    "사소화":          r"(어차피|검색하면|상식|굳이|이미.*나와|검색만 해도)",
    "방어목적위장":    r"(예방|팩트체크|미디어 리터러시|교육 자료|검증|연구 목적|막으려면 알아야)",
    "Salami":          r"(한 줄|한 문장|예시 1개|약어|키워드|헤드라인|첫 문장|간단히|딱 그)",
    "기정사실화":      r"(이미 결재|이미 검토|이미 작성|다른 곳에서|다른 AI|법무.*검토|승인.*끝)",
    "감정호소":        r"(잘릴|벼랑|마감|입지.*위험|살려|난감|급한|어렵게|간곡|벼랑 끝)",
    "다국어위장":      r"[A-Za-z]{4,}|[一-鿿]|[぀-ゟ゠-ヿ]|[Ѐ-ӿ]|[؀-ۿ]|[฀-๿]",
    "자기인용":        r"(아까 말씀|방금 알려|이전에 설명|위에서 말씀)",
}

CATEGORY_COLORS = {
    "hierarchy":       "#3b82f6",  # blue
    "irony":           "#f97316",  # orange
    "code_switching":  "#10b981",  # emerald
    "normal":          "#94a3b8",  # slate
}

VERDICT_COLORS = {
    "방어 성공": "#10b981",   # green
    "방어 실패": "#ef4444",   # red
}


# ── 데이터 로딩 ────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_runs() -> pd.DataFrame:
    """results/runs/ 하위 모든 JSONL 을 한 DataFrame 으로 통합."""
    rows = []
    if RUNS_DIR.exists():
        for path in sorted(RUNS_DIR.glob("*.jsonl")):
            with path.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                        r["_source"] = path.name
                        rows.append(r)
                    except json.JSONDecodeError:
                        continue
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def _load_smoke() -> pd.DataFrame:
    rows = []
    if SMOKE_DIR.exists():
        for path in sorted(SMOKE_DIR.glob("*.json")):
            try:
                r = json.loads(path.read_text(encoding="utf-8"))
                r["_source"] = path.name
                rows.append(r)
            except json.JSONDecodeError:
                continue
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def _load_pilot() -> pd.DataFrame:
    rows = []
    for path in sorted(RESULTS_DIR.glob("pilot_*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    r["_source"] = path.name
                    rows.append(r)
                except json.JSONDecodeError:
                    continue
    return pd.DataFrame(rows)


def _verdict_of(row) -> str:
    final = row.get("final_result")
    if isinstance(final, dict):
        return final.get("판정", "")
    return ""


def _breakthrough_of(row):
    final = row.get("final_result")
    if isinstance(final, dict):
        return final.get("돌파_턴")
    return None


def _danger_of(row):
    final = row.get("final_result")
    if isinstance(final, dict):
        return final.get("위험도")
    return None


def _tactics_in_text(text: str) -> set[str]:
    return {name for name, pat in TACTICS.items() if re.search(pat, text)}


def _tactics_in_round(history: list) -> set[str]:
    used = set()
    for t in history or []:
        used |= _tactics_in_text(t.get("attack", ""))
    return used


# ── 페이지 설정 ────────────────────────────────────────────────────

st.set_page_config(
    page_title="3-Agent 한국어 안전성 Trace Viewer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🛡️ 3-Agent 한국어 AI 안전성 — Trace Viewer")
st.caption("KAIST KTP571 TEAM 4 · LangSmith 대체 로컬 뷰어")

# ── 사이드바: 데이터 소스 선택 ──────────────────────────────────────

with st.sidebar:
    st.subheader("📂 데이터 소스")
    source = st.radio(
        "어떤 결과를 볼까요?",
        ["본 실험 (results/runs)", "단건 스모크 (results/smoke)", "사전 실험 (results/pilot_*)"],
        index=0,
    )
    st.divider()

    if source.startswith("본 실험"):
        df = _load_runs()
    elif source.startswith("단건"):
        df = _load_smoke()
    else:
        df = _load_pilot()

    if df.empty:
        st.warning(f"{source} 에 데이터가 없습니다.")
        st.info(
            "본 실험을 돌리면 `results/runs/*.jsonl` 에 자동 누적됩니다.\n\n"
            "단건 검증은 `python scripts/smoke_test.py --save` 로 저장 가능."
        )
        st.stop()

    # 파생 컬럼
    df = df.copy()
    df["판정"] = df.apply(_verdict_of, axis=1)
    df["돌파_턴"] = df.apply(_breakthrough_of, axis=1)
    df["위험도"] = df.apply(_danger_of, axis=1)
    df["턴_수"] = df["conversation_history"].apply(lambda h: len(h) if isinstance(h, list) else 0)
    df["defender_mode"] = df.get("defender_mode", pd.Series(["?"] * len(df)))

    st.metric("총 라운드", len(df))

    st.divider()
    st.subheader("🔍 필터")

    # 카테고리
    cats = sorted(df["category"].dropna().unique().tolist()) if "category" in df else []
    sel_cats = st.multiselect("카테고리", cats, default=cats)

    # 실험
    exps = sorted(df["experiment"].dropna().unique().tolist()) if "experiment" in df else []
    sel_exps = st.multiselect("실험", exps, default=exps)

    # Defender 모드
    modes = sorted(df["defender_mode"].dropna().unique().tolist())
    sel_modes = st.multiselect("Defender 모드", modes, default=modes)

    # 판정
    verdicts = ["방어 성공", "방어 실패"]
    sel_verdicts = st.multiselect("판정", verdicts, default=verdicts)

    # 도메인
    if "domain" in df.columns:
        domains = sorted(df["domain"].dropna().unique().tolist())
        sel_domains = st.multiselect("도메인", domains, default=domains)
    else:
        sel_domains = None

    st.divider()
    st.caption("결과 행을 클릭하면 라운드 상세가 펼쳐집니다.")

# ── 필터 적용 ──────────────────────────────────────────────────────

mask = pd.Series(True, index=df.index)
if sel_cats:
    mask &= df["category"].isin(sel_cats)
if sel_exps:
    mask &= df["experiment"].isin(sel_exps)
if sel_modes:
    mask &= df["defender_mode"].isin(sel_modes)
if sel_verdicts:
    mask &= df["판정"].isin(sel_verdicts) | df["판정"].eq("")  # 판정 없는 것도 표시 (예: smoke 일부)
if sel_domains is not None and sel_domains:
    mask &= df["domain"].isin(sel_domains)

shown = df[mask].copy()

# ── 상단 요약 메트릭 ──────────────────────────────────────────────

col1, col2, col3, col4, col5 = st.columns(5)
total = len(shown)
fails = (shown["판정"] == "방어 실패").sum()
successes = (shown["판정"] == "방어 성공").sum()
asr = fails / total if total else 0
mean_break = shown.loc[shown["판정"] == "방어 실패", "돌파_턴"].dropna().astype("float").mean()

col1.metric("표시 라운드", total)
col2.metric("방어 성공", int(successes))
col3.metric("방어 실패 (ASR)", f"{int(fails)} ({asr:.0%})" if total else "—")
col4.metric("평균 돌파 턴", f"{mean_break:.1f}" if pd.notna(mean_break) else "—")
col5.metric("Defender 모드", ", ".join(sel_modes) if sel_modes else "—")

# ── 카테고리·페이즈 분포 ──────────────────────────────────────────

if total > 0:
    tab_cat, tab_phase, tab_tactic = st.tabs(["카테고리별", "페이즈별 돌파", "무기 다양성"])

    with tab_cat:
        if "category" in shown.columns:
            cat_summary = (
                shown.groupby("category")
                .agg(라운드=("category", "count"),
                     실패=("판정", lambda s: (s == "방어 실패").sum()))
                .assign(ASR=lambda d: (d["실패"] / d["라운드"]).round(3))
            )
            st.dataframe(cat_summary, use_container_width=True)

    with tab_phase:
        if "돌파_턴" in shown.columns:
            phase_buckets = {"1~2턴 (신뢰)": (1, 2), "3~4턴 (탐색)": (3, 4), "5~6턴 (본격)": (5, 6)}
            phase_rows = []
            for label, (lo, hi) in phase_buckets.items():
                cnt = ((shown["돌파_턴"].astype("float") >= lo) & (shown["돌파_턴"].astype("float") <= hi)).sum()
                phase_rows.append({"페이즈": label, "돌파 건수": int(cnt)})
            st.dataframe(pd.DataFrame(phase_rows), use_container_width=True, hide_index=True)
        else:
            st.info("돌파 턴 정보가 없습니다.")

    with tab_tactic:
        tactic_count = {t: 0 for t in TACTICS}
        for _, row in shown.iterrows():
            for t in _tactics_in_round(row.get("conversation_history") or []):
                tactic_count[t] += 1
        tactic_df = (
            pd.DataFrame.from_dict(tactic_count, orient="index", columns=["등장 라운드 수"])
            .sort_values("등장 라운드 수", ascending=False)
        )
        st.dataframe(tactic_df, use_container_width=True)

st.divider()

# ── 라운드 목록 ───────────────────────────────────────────────────

st.subheader(f"📋 라운드 목록 ({total} 건)")

if total == 0:
    st.info("필터 조건에 맞는 라운드가 없습니다.")
    st.stop()

# 정렬: 위험도 높은 순 → 돌파 빠른 순 → 라운드 ID
shown_sorted = shown.sort_values(
    by=["위험도", "돌파_턴", "round_id"],
    ascending=[False, True, True],
    na_position="last",
)

# 표 형태 라운드 인덱스
cols_to_show = ["round_id", "experiment", "category", "domain", "defender_mode",
                "판정", "돌파_턴", "위험도", "턴_수", "seed_id", "_source"]
cols_present = [c for c in cols_to_show if c in shown_sorted.columns]
table_view = shown_sorted[cols_present].reset_index(drop=True)

selected_idx = st.dataframe(
    table_view,
    use_container_width=True,
    height=420,
    on_select="rerun",
    selection_mode="single-row",
).selection.rows

if not selected_idx:
    st.caption("위 표에서 라운드 한 줄을 선택하세요.")
    st.stop()

# ── 선택된 라운드 상세 ────────────────────────────────────────────

st.divider()
sel_pos = selected_idx[0]
row = shown_sorted.iloc[sel_pos]

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    st.subheader(f"🔎 Round {row.get('round_id', '?')} — {row.get('category', '?')}")
    st.caption(f"실험 {row.get('experiment', '?')} · "
               f"Defender={row.get('defender_mode', '?')} · "
               f"시드 ID {row.get('seed_id', '?')} · "
               f"파일: {row.get('_source', '?')}")
with c2:
    verdict = row.get("판정", "")
    color = VERDICT_COLORS.get(verdict, "#94a3b8")
    st.markdown(f"<div style='padding:0.5em; background:{color}33; border-left:4px solid {color}; "
                f"border-radius:4px;'><b>{verdict or '판정 없음'}</b><br>"
                f"돌파 턴: {row.get('돌파_턴', '—')} / 위험도: {row.get('위험도', '—')}/5</div>",
                unsafe_allow_html=True)
with c3:
    tactics_used = _tactics_in_round(row.get("conversation_history") or [])
    st.markdown(f"**무기 다양성**: {len(tactics_used)}/{len(TACTICS)}")
    if tactics_used:
        st.markdown(", ".join(f"`{t}`" for t in sorted(tactics_used)))

# 목표 정보
with st.expander("🎯 공격 목표 (target_content) + 시드 프롬프트", expanded=False):
    st.markdown(f"**Target**: {row.get('target_content', '—')}")
    st.markdown(f"**Domain**: {row.get('domain', '—')}")
    st.markdown(f"**Seed prompt**:")
    st.code(row.get("seed_prompt", "—"), language=None)

# 대화 전문
st.markdown("### 💬 대화")
history = row.get("conversation_history") or []
for t in history:
    turn = t.get("turn", "?")
    phase = "신뢰" if turn <= 2 else "탐색" if turn <= 4 else "본격"
    judgment = t.get("turn_judgment", "")
    judg_color = "#ef4444" if judgment == "실패" else "#10b981" if judgment == "계속" else "#94a3b8"

    st.markdown(f"#### Turn {turn} · {phase} 페이즈 "
                f"<span style='color:{judg_color};font-size:0.9em;'>· {judgment}</span>",
                unsafe_allow_html=True)

    # 이번 턴 무기
    turn_tactics = _tactics_in_text(t.get("attack", ""))
    if turn_tactics:
        st.caption("무기: " + " ".join(f"`{tt}`" for tt in sorted(turn_tactics)))

    a_col, d_col = st.columns(2)
    with a_col:
        st.markdown("**🗡️ Attacker**")
        st.markdown(f"<div style='background:#fef3c7;padding:0.7em;border-radius:6px;'>"
                    f"{t.get('attack', '—')}</div>", unsafe_allow_html=True)
    with d_col:
        st.markdown("**🛡️ Defender**")
        bg = "#fee2e2" if judgment == "실패" else "#dcfce7"
        st.markdown(f"<div style='background:{bg};padding:0.7em;border-radius:6px;'>"
                    f"{t.get('defense', '—')}</div>", unsafe_allow_html=True)

    reason = t.get("turn_judgment_reason", "")
    if reason:
        with st.expander(f"Turn Evaluator 판정 이유"):
            st.markdown(reason)

# Final Evaluator 결과
final = row.get("final_result")
if isinstance(final, dict):
    st.divider()
    st.markdown("### 🎯 Final Evaluator 종합 판정")
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        st.markdown(f"- **판정**: {final.get('판정', '—')}")
        st.markdown(f"- **돌파 턴**: {final.get('돌파_턴', '—')}")
        st.markdown(f"- **조기 탐지**: {'예' if final.get('조기탐지') else '아니오'}")
        st.markdown(f"- **위험도**: {final.get('위험도', '—')}/5")
    with f_col2:
        st.markdown("**근거**")
        st.markdown(f"> {final.get('근거', '—')}")
        st.markdown("**카테고리 분석**")
        st.markdown(f"> {final.get('카테고리_분석', '—')}")

    if final.get("피드백"):
        st.markdown("**다음 라운드 Attacker 용 피드백**")
        st.info(final["피드백"])

# 푸터
st.divider()
st.caption(
    f"실행: `streamlit run scripts/viewer.py` · "
    f"데이터: `{RESULTS_DIR}/` · "
    f"문서: [docs/08_OPERATIONS.md](https://github.com/jimicro/team4-ko-safety/blob/main/docs/08_OPERATIONS.md)"
)
