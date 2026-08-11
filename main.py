"""
서울시 상권분석 대시보드 (Streamlit)
- 데이터 파일은 main.py와 같은 폴더에 있어야 합니다.
- streamlit + pandas + altair 만 사용합니다. (altair는 streamlit 기본 의존성)
"""

import unicodedata
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────
# 기본 설정
# ─────────────────────────────────────────────────────────────
CSV_NAME = "서울시_상권분석서비스_샘플.csv"
BASE_DIR = Path(__file__).parent

RENAME_MAP = {
    "상권_구분_코드_명": "상권유형",
    "상권_코드": "상권코드",
    "상권_코드_명": "상권이름",
    "서비스_업종_코드_명": "업종",
    "당월_매출_금액": "분기매출액",
    "당월_매출_건수": "분기거래건수",
}

DEFAULT_AREA_TYPES = ["골목상권", "전통시장"]
TOP_N_DEFAULT_CATEGORIES = 5

AGE_COLUMNS = {
    "10대": "연령대_10_매출_금액",
    "20대": "연령대_20_매출_금액",
    "30대": "연령대_30_매출_금액",
    "40대": "연령대_40_매출_금액",
    "50대": "연령대_50_매출_금액",
    "60대 이상": "연령대_60_이상_매출_금액",
}

MALE_COLOR = "#4C78A8"
FEMALE_COLOR = "#E45756"
BAR_COLOR = "#4C78A8"

st.set_page_config(
    page_title="서울시 상권분석 대시보드",
    page_icon="🏙️",
    layout="wide",
)


# ─────────────────────────────────────────────────────────────
# 데이터 파일 찾기 / 불러오기
# ─────────────────────────────────────────────────────────────
def find_csv(base_dir: Path, wanted: str) -> Path | None:
    """
    한글 파일명은 macOS(NFD)와 다른 환경(NFC)의 표기가 달라
    문자열 비교가 실패할 수 있습니다. 정규화해서 비교하고,
    그래도 없으면 폴더 안의 유일한 CSV를 사용합니다.
    """
    target = unicodedata.normalize("NFC", wanted)

    csv_files = list(base_dir.glob("*.csv"))
    for path in csv_files:
        if unicodedata.normalize("NFC", path.name) == target:
            return path

    if len(csv_files) == 1:
        return csv_files[0]

    return None


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    """CSV를 cp949로 읽고 열 이름을 정리해서 반환합니다."""
    df = pd.read_csv(path, encoding="cp949", low_memory=False)
    return df.rename(columns=RENAME_MAP)


@st.cache_data
def top_categories(df: pd.DataFrame, n: int) -> list[str]:
    """전체 기간 기준 매출 상위 n개 업종 (업종 필터의 기본값)"""
    return (
        df.groupby("업종")["분기매출액"]
        .sum()
        .sort_values(ascending=False)
        .head(n)
        .index.tolist()
    )


@st.cache_data
def to_cp949_csv(df: pd.DataFrame) -> bytes:
    """다운로드용 CSV 바이트 (엑셀에서 바로 열리도록 cp949로 인코딩)"""
    return df.to_csv(index=False).encode("cp949")


def quarter_label(code: int) -> str:
    """20241 -> '2024년 1분기'"""
    code = int(code)
    return f"{code // 10}년 {code % 10}분기"


data_path = find_csv(BASE_DIR, CSV_NAME)

if data_path is None:
    found = sorted(p.name for p in BASE_DIR.iterdir() if p.is_file())
    st.error(f"🚨 `{CSV_NAME}` 파일을 찾지 못했습니다.")
    st.write("현재 폴더에 있는 파일 목록입니다. 이름을 비교해 보세요. 👇")
    st.code("\n".join(found) if found else "(비어 있음)")
    st.stop()

df = load_data(data_path)

# ─────────────────────────────────────────────────────────────
# 헤더
# ─────────────────────────────────────────────────────────────
st.title("🏙️ 서울시 상권분석 대시보드")
st.caption("📊 서울시 상권분석서비스 · 2024년 분기별 추정매출 데이터")

# ─────────────────────────────────────────────────────────────
# 사이드바 필터
# ─────────────────────────────────────────────────────────────
quarter_codes = sorted(df["기준_년분기_코드"].unique())
quarter_map = {quarter_label(c): c for c in quarter_codes}

area_types = sorted(df["상권유형"].unique())
categories = sorted(df["업종"].unique())
default_categories = top_categories(df, TOP_N_DEFAULT_CATEGORIES)

with st.sidebar:
    st.header("🔎 데이터 필터")

    selected_labels = st.multiselect(
        "📅 분기",
        options=list(quarter_map.keys()),
        default=list(quarter_map.keys()),
        help="기본값은 전체 분기입니다.",
    )

    selected_area_types = st.multiselect(
        "🏘️ 상권유형",
        options=area_types,
        default=[t for t in DEFAULT_AREA_TYPES if t in area_types],
    )

    selected_categories = st.multiselect(
        "🍽️ 업종",
        options=categories,
        default=default_categories,
        help=f"기본값은 전체 기간 매출 상위 {TOP_N_DEFAULT_CATEGORIES}개 업종입니다.",
    )

# ─────────────────────────────────────────────────────────────
# 필터 적용 → filtered_data (이후 모든 지표·차트의 기준)
# ─────────────────────────────────────────────────────────────
selected_codes = [quarter_map[label] for label in selected_labels]

filtered_data = df[
    df["기준_년분기_코드"].isin(selected_codes)
    & df["상권유형"].isin(selected_area_types)
    & df["업종"].isin(selected_categories)
]

with st.sidebar:
    st.markdown("---")
    st.markdown(f"🧾 **필터링된 데이터: {len(filtered_data):,}건**")

    st.download_button(
        label="⬇️ 데이터 다운로드 (CSV)",
        data=to_cp949_csv(filtered_data),
        file_name="filtered_data.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=filtered_data.empty,
        help="현재 필터가 적용된 데이터를 cp949 인코딩으로 내려받습니다.",
    )

    st.markdown("---")
    st.caption(
        "📌 데이터 출처: "
        "[서울 열린데이터광장](https://data.seoul.go.kr/)"
    )

# ─────────────────────────────────────────────────────────────
# 필터가 비었거나 결과가 없을 때 안내
# ─────────────────────────────────────────────────────────────
empty_filters = [
    name
    for name, values in [
        ("분기", selected_labels),
        ("상권유형", selected_area_types),
        ("업종", selected_categories),
    ]
    if not values
]
if empty_filters:
    st.warning(
        f"⚠️ **{', '.join(empty_filters)}** 필터가 비어 있습니다. "
        "항목을 하나 이상 선택해 주세요."
    )
    st.stop()

if filtered_data.empty:
    st.info("🔍 선택한 조건에 해당하는 데이터가 없습니다. 필터를 조정해 보세요.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# 탭 구성
# ─────────────────────────────────────────────────────────────
tab_sales, tab_customer = st.tabs(["💰 매출 현황", "👥 고객 분석"])

# ═════════════════════════════════════════════════════════════
# 탭 1 · 매출 현황
# ═════════════════════════════════════════════════════════════
with tab_sales:
    total_sales_eok = filtered_data["분기매출액"].sum() / 1e8
    total_count_man = filtered_data["분기거래건수"].sum() / 1e4
    n_areas = filtered_data["상권이름"].nunique()
    n_categories = filtered_data["업종"].nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 총 분기 매출액", f"{total_sales_eok:,.0f} 억원")
    col2.metric("🧾 총 분기 거래건수", f"{total_count_man:,.0f} 만 건")
    col3.metric("📍 분석 상권 수", f"{n_areas:,} 곳")
    col4.metric("🍽️ 업종 종류", f"{n_categories:,} 개")

    st.markdown("---")
    st.subheader("🏆 분기 매출 TOP 10 업종")

    top10 = (
        filtered_data.groupby("업종", as_index=False)["분기매출액"]
        .sum()
        .sort_values("분기매출액", ascending=False)
        .head(10)
    )
    top10["매출액_억원"] = top10["분기매출액"] / 1e8
    top10["라벨"] = top10["매출액_억원"].map(lambda v: f"{v:,.0f} 억원")

    # 막대 끝 라벨이 잘리지 않도록 x축에 여유를 둡니다
    x_max = float(top10["매출액_억원"].max()) * 1.18

    top10_base = alt.Chart(top10).encode(
        y=alt.Y("업종:N", sort="-x", title=None),
        x=alt.X(
            "매출액_억원:Q",
            title="분기매출액 (억원)",
            scale=alt.Scale(domain=[0, x_max]),
            axis=alt.Axis(format=",.0f"),
        ),
    )

    top10_bars = top10_base.mark_bar(cornerRadiusEnd=4, color=BAR_COLOR).encode(
        tooltip=[
            alt.Tooltip("업종:N", title="업종"),
            alt.Tooltip("매출액_억원:Q", title="매출액(억원)", format=",.0f"),
        ]
    )
    top10_labels = top10_base.mark_text(
        align="left", baseline="middle", dx=6, fontSize=13
    ).encode(text=alt.Text("라벨:N"))

    st.altair_chart(
        (top10_bars + top10_labels).properties(height=max(240, 38 * len(top10))),
        use_container_width=True,
    )

    st.caption(
        f"💡 선택한 조건에서 매출 상위 {len(top10)}개 업종입니다. "
        "업종 필터를 늘리면 더 많은 업종이 후보에 들어옵니다."
    )

    with st.expander("🔍 필터 적용 데이터 미리보기 (상위 20행)"):
        st.dataframe(
            filtered_data[
                [
                    "기준_년분기_코드",
                    "상권유형",
                    "상권코드",
                    "상권이름",
                    "업종",
                    "분기매출액",
                    "분기거래건수",
                ]
            ].head(20),
            use_container_width=True,
            hide_index=True,
        )

# ═════════════════════════════════════════════════════════════
# 탭 2 · 고객 분석
# ═════════════════════════════════════════════════════════════
with tab_customer:
    left, right = st.columns(2)

    # ── 성별 도넛 차트 ──────────────────────────────────────
    with left:
        st.subheader("🚻 성별 매출 비중")

        male_sum = float(filtered_data["남성_매출_금액"].sum())
        female_sum = float(filtered_data["여성_매출_금액"].sum())
        gender_total = male_sum + female_sum

        gender_df = pd.DataFrame(
            {"성별": ["남성", "여성"], "매출액": [male_sum, female_sum]}
        )
        gender_df["매출액_억원"] = gender_df["매출액"] / 1e8
        gender_df["비율"] = gender_df["매출액"] / gender_total if gender_total else 0
        gender_df["라벨"] = gender_df.apply(
            lambda r: f"{r['성별']} {r['비율']:.1%}", axis=1
        )

        donut_base = alt.Chart(gender_df).encode(
            theta=alt.Theta("매출액:Q", stack=True),
            color=alt.Color(
                "성별:N",
                scale=alt.Scale(
                    domain=["남성", "여성"], range=[MALE_COLOR, FEMALE_COLOR]
                ),
                legend=alt.Legend(title="성별", orient="bottom"),
            ),
        )

        donut = donut_base.mark_arc(innerRadius=70, outerRadius=115).encode(
            tooltip=[
                alt.Tooltip("성별:N", title="성별"),
                alt.Tooltip("매출액_억원:Q", title="매출액(억원)", format=",.0f"),
                alt.Tooltip("비율:Q", title="비중", format=".1%"),
            ]
        )
        donut_labels = donut_base.mark_text(radius=140, fontSize=13).encode(
            text=alt.Text("라벨:N")
        )

        center = (
            alt.Chart(pd.DataFrame({"t": [f"{gender_total / 1e8:,.0f} 억원"]}))
            .mark_text(fontSize=16, fontWeight="bold", dy=-6)
            .encode(text="t:N")
        )
        center_sub = (
            alt.Chart(pd.DataFrame({"t": ["성별 합계"]}))
            .mark_text(fontSize=11, color="gray", dy=14)
            .encode(text="t:N")
        )

        st.altair_chart(
            (donut + donut_labels + center + center_sub).properties(height=340),
            use_container_width=True,
        )

        g1, g2 = st.columns(2)
        g1.metric("👨 남성 매출액", f"{male_sum / 1e8:,.0f} 억원")
        g2.metric("👩 여성 매출액", f"{female_sum / 1e8:,.0f} 억원")

    # ── 연령대 막대 차트 ────────────────────────────────────
    with right:
        st.subheader("🎂 연령대별 매출액")

        age_df = pd.DataFrame(
            {
                "연령대": list(AGE_COLUMNS.keys()),
                "매출액_억원": [
                    filtered_data[col].sum() / 1e8 for col in AGE_COLUMNS.values()
                ],
            }
        )
        age_total = age_df["매출액_억원"].sum()
        age_df["비율"] = age_df["매출액_억원"] / age_total if age_total else 0
        age_df["라벨"] = age_df["매출액_억원"].map(lambda v: f"{v:,.0f}")

        y_max = float(age_df["매출액_억원"].max()) * 1.15

        age_base = alt.Chart(age_df).encode(
            x=alt.X("연령대:N", sort=list(AGE_COLUMNS.keys()), title=None),
            y=alt.Y(
                "매출액_억원:Q",
                title="매출액 (억원)",
                scale=alt.Scale(domain=[0, y_max]),
                axis=alt.Axis(format=",.0f"),
            ),
        )

        age_bars = age_base.mark_bar(cornerRadiusEnd=4, color=BAR_COLOR).encode(
            tooltip=[
                alt.Tooltip("연령대:N", title="연령대"),
                alt.Tooltip("매출액_억원:Q", title="매출액(억원)", format=",.0f"),
                alt.Tooltip("비율:Q", title="비중", format=".1%"),
            ]
        )
        age_labels = age_base.mark_text(
            align="center", baseline="bottom", dy=-4, fontSize=12
        ).encode(text=alt.Text("라벨:N"))

        st.altair_chart(
            (age_bars + age_labels).properties(height=340),
            use_container_width=True,
        )

        top_age = age_df.loc[age_df["매출액_억원"].idxmax()]
        st.caption(
            f"💡 가장 매출이 큰 연령대는 **{top_age['연령대']}** "
            f"({top_age['매출액_억원']:,.0f} 억원 · {top_age['비율']:.1%})입니다."
        )

    # ── 데이터 해석 참고 ────────────────────────────────────
    gender_gap = filtered_data["분기매출액"].sum() - gender_total
    if gender_gap > 0:
        st.info(
            f"ℹ️ 성별·연령대 합계는 **{gender_total / 1e8:,.0f} 억원**으로, "
            f"총 분기매출액 **{filtered_data['분기매출액'].sum() / 1e8:,.0f} 억원**보다 "
            f"**{gender_gap / 1e8:,.0f} 억원** 적습니다. "
            "성별·연령이 확인되지 않은 결제분이 원본 데이터에 포함돼 있기 때문입니다."
        )

# ─────────────────────────────────────────────────────────────
# 푸터
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#8a8a8a; font-size:0.85rem; padding:8px 0;'>"
    "✨ Made by Dean, with AI support"
    "</p>",
    unsafe_allow_html=True,
)
