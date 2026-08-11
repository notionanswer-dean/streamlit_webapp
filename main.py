"""
서울시 상권분석 대시보드 (Streamlit)
- 데이터 파일은 main.py와 같은 폴더에 있어야 합니다.
- 표준 라이브러리 + streamlit + pandas 만 사용합니다. (추가 설치 불필요)
"""

import unicodedata
from pathlib import Path

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

st.set_page_config(
    page_title="서울시 상권분석 대시보드",
    page_icon="🏙️",
    layout="wide",
)


# ─────────────────────────────────────────────────────────────
# 데이터 파일 찾기
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

    # 이름이 달라도 CSV가 하나뿐이면 그것을 사용
    if len(csv_files) == 1:
        return csv_files[0]

    return None


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    """CSV를 cp949로 읽고 열 이름을 정리해서 반환합니다."""
    df = pd.read_csv(path, encoding="cp949", low_memory=False)
    return df.rename(columns=RENAME_MAP)


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
# 사이드바 필터 (디폴트: 전체 분기)
# ─────────────────────────────────────────────────────────────
quarter_codes = sorted(df["기준_년분기_코드"].unique())
labels = {quarter_label(c): c for c in quarter_codes}

with st.sidebar:
    st.header("🔎 필터")
    selected_labels = st.multiselect(
        "📅 분기 선택",
        options=list(labels.keys()),
        default=list(labels.keys()),
        help="비우면 전체 분기가 적용됩니다.",
    )

# 아무것도 선택하지 않으면 전체를 사용
selected_codes = (
    [labels[label] for label in selected_labels]
    if selected_labels
    else quarter_codes
)
filtered = df[df["기준_년분기_코드"].isin(selected_codes)]

with st.sidebar:
    st.markdown("---")
    st.markdown(
        f"✅ **{len(selected_codes)}개 분기** 선택 중  \n"
        f"🧾 대상 데이터 **{len(filtered):,}행**"
    )

# ─────────────────────────────────────────────────────────────
# 핵심 지표 4칸
# ─────────────────────────────────────────────────────────────
total_sales_eok = filtered["분기매출액"].sum() / 1e8  # 억원
total_count_man = filtered["분기거래건수"].sum() / 1e4  # 만 건
n_areas = filtered["상권이름"].nunique()
n_categories = filtered["업종"].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 총 분기 매출액", f"{total_sales_eok:,.0f} 억원")
col2.metric("🧾 총 분기 거래건수", f"{total_count_man:,.0f} 만 건")
col3.metric("📍 분석 상권 수", f"{n_areas:,} 곳")
col4.metric("🍽️ 업종 종류", f"{n_categories:,} 개")

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# 데이터 미리보기
# ─────────────────────────────────────────────────────────────
with st.expander("🔍 선택한 분기 데이터 미리보기 (상위 20행)"):
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
