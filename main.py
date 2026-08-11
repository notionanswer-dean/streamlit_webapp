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

    # 필터 1: 분기 (기본값 전체)
    selected_labels = st.multiselect(
        "📅 분기",
        options=list(quarter_map.keys()),
        default=list(quarter_map.keys()),
        help="기본값은 전체 분기입니다.",
    )

    # 필터 2: 상권유형 (기본값 골목상권 + 전통시장)
    selected_area_types = st.multiselect(
        "🏘️ 상권유형",
        options=area_types,
        default=[t for t in DEFAULT_AREA_TYPES if t in area_types],
    )

    # 필터 3: 업종 (기본값 매출 상위 5개)
    selected_categories = st.multiselect(
        "🍽️ 업종",
        options=categories,
        default=default_categories,
        help=f"기본값은 전체 기간 매출 상위 {TOP_N_DEFAULT_CATEGORIES}개 업종입니다.",
    )

# 비어 있는 필터가 있으면 결과가 없으므로 안내 후 중단
empty = [
    name
    for name, values in [
        ("분기", selected_labels),
        ("상권유형", selected_area_types),
        ("업종", selected_categories),
    ]
    if not values
]
if empty:
    st.warning(f"⚠️ **{', '.join(empty)}** 필터가 비어 있습니다. 항목을 하나 이상 선택해 주세요.")
    st.stop()

selected_codes = [quarter_map[label] for label in selected_labels]

filtered = df[
    df["기준_년분기_코드"].isin(selected_codes)
    & df["상권유형"].isin(selected_area_types)
    & df["업종"].isin(selected_categories)
]

with st.sidebar:
    st.markdown("---")
    st.markdown(
        f"✅ 분기 **{len(selected_codes)}개** · "
        f"상권유형 **{len(selected_area_types)}개** · "
        f"업종 **{len(selected_categories)}개**  \n"
        f"🧾 대상 데이터 **{len(filtered):,}행**"
    )

if filtered.empty:
    st.info("🔍 선택한 조건에 해당하는 데이터가 없습니다. 필터를 조정해 보세요.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# 핵심 지표 4칸
# ─────────────────────────────────────────────────────────────
total_sales_eok = filtered["분기매출액"].sum() / 1e8
total_count_man = filtered["분기거래건수"].sum() / 1e4
n_areas = filtered["상권이름"].nunique()
n_categories = filtered["업종"].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 총 분기 매출액", f"{total_sales_eok:,.0f} 억원")
col2.metric("🧾 총 분기 거래건수", f"{total_count_man:,.0f} 만 건")
col3.metric("📍 분석 상권 수", f"{n_areas:,} 곳")
col4.metric("🍽️ 업종 종류", f"{n_categories:,} 개")

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# 분기 매출 TOP 10 업종
# ─────────────────────────────────────────────────────────────
st.subheader("🏆 분기 매출 TOP 10 업종")

top10 = (
    filtered.groupby("업종", as_index=False)["분기매출액"]
    .sum()
    .sort_values("분기매출액", ascending=False)
    .head(10)
)
top10["매출액_억원"] = top10["분기매출액"] / 1e8
top10["라벨"] = top10["매출액_억원"].map(lambda v: f"{v:,.0f} 억원")

# 막대 끝 라벨이 잘리지 않도록 x축에 여유를 둡니다
x_max = float(top10["매출액_억원"].max()) * 1.18

base = alt.Chart(top10).encode(
    y=alt.Y("업종:N", sort="-x", title=None),
    x=alt.X(
        "매출액_억원:Q",
        title="분기매출액 (억원)",
        scale=alt.Scale(domain=[0, x_max]),
        axis=alt.Axis(format=",.0f"),
    ),
)

bars = base.mark_bar(cornerRadiusEnd=4, color="#4C78A8").encode(
    tooltip=[
        alt.Tooltip("업종:N", title="업종"),
        alt.Tooltip("매출액_억원:Q", title="매출액(억원)", format=",.0f"),
    ]
)

value_labels = base.mark_text(
    align="left", baseline="middle", dx=6, fontSize=13
).encode(text=alt.Text("라벨:N"))

st.altair_chart(
    (bars + value_labels).properties(height=max(240, 38 * len(top10))),
    use_container_width=True,
)

st.caption(
    f"💡 선택한 조건에서 매출 상위 {len(top10)}개 업종입니다. "
    "업종 필터를 늘리면 더 많은 업종이 후보에 들어옵니다."
)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# 데이터 미리보기
# ─────────────────────────────────────────────────────────────
with st.expander("🔍 필터 적용 데이터 미리보기 (상위 20행)"):
    preview_cols = [
        "기준_년분기_코드",
        "상권유형",
        "상권코드",
        "상권이름",
        "업종",
        "분기매출액",
        "분기거래건수",
    ]
    st.dataframe(
        filtered[preview_cols].head(20),
        use_container_width=True,
        hide_index=True,
    )
