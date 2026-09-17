
import streamlit as st
import pandas as pd
import numpy as np


# =========================================================
# 생성형 AI 정책 제안 기능
# =========================================================

import os
import json
from openai import OpenAI

def get_ai_policy_suggestion(current_gap, south_internal, north_internal, bottom20, user_scenario=""):

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수를 찾을 수 없습니다.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
당신은 통일한국 지역균형발전 정책 시뮬레이션의 정책 시나리오 설계 AI입니다.

현재 Day 0 상태:
- 남북 평균 균형발전 격차: {current_gap:.3f}
- 남한 내부 지역격차: {south_internal:.3f}
- 북한 내부 지역격차: {north_internal:.3f}
- 하위 20% 지역 평균 균형발전지수: {bottom20:.3f}
사용자가 설정한 정책 시나리오:
{user_scenario if user_scenario.strip() else "별도의 시나리오가 입력되지 않았습니다. 현재 지역격차 지표를 중심으로 정책을 설계하십시오."}

위 시나리오의 정책목표와 우선순위를 고려하되, 현재 Day 0의 지역격차 지표도 함께 고려하십시오.
연간 가상 정책재원을 다음 두 단계로 배분하십시오.

1. 남한지역 / 북한지역 투자 비중
2. 다음 5개 정책 분야 투자 비중
   - 경제·산업
   - 교통·물류
   - 의료·보건
   - 교육
   - 생활인프라

조건:
- 남한예산 + 북한예산 = 100
- 5개 분야 투자 비중 합계 = 100
- 모든 값은 0~100 사이의 정수
- 지역격차와 하위지역 개선을 함께 고려
- 실제 미래예측이나 정책 권고가 아니라 시뮬레이션용 정책 시나리오로 설계

반드시 아래 JSON 형식만 출력하십시오.

{{
  "남한예산": 35,
  "북한예산": 65,
  "분야배분": {{
    "경제·산업": 28,
    "교통·물류": 24,
    "의료·보건": 16,
    "교육": 14,
    "생활인프라": 18
  }},
  "정책설명": "이 배분을 제안한 이유를 간결하게 설명"
}}
"""

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    text = response.output_text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    policy = json.loads(text)

    if policy["남한예산"] + policy["북한예산"] != 100:
        raise ValueError("AI의 남북한 예산 비중 합계가 100이 아닙니다.")

    sector_sum = sum(policy["분야배분"].values())

    if sector_sum != 100:
        raise ValueError("AI의 분야별 투자 비중 합계가 100이 아닙니다.")

    return policy


# =========================================================
# 1. 페이지 기본 설정
# =========================================================


import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 한글 폰트 설정
import urllib.request

font_path = "/tmp/NanumGothic.ttf"

if not os.path.exists(font_path):
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Regular.ttf",
        font_path
    )

fm.fontManager.addfont(font_path)
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

st.set_page_config(
    page_title="통일한국 균형발전 AI 시뮬레이션",
    page_icon="🇰🇷",
    layout="wide"
)

st.title("통일한국 균형발전 AI 시뮬레이션")
st.subheader(
    "데이터 기반 통일한국 지역균형발전 정책 의사결정지원 프로토타입"
)

st.info("""
남북한 30개 광역지역의 기초자료를 기반으로 Day 0 균형발전지수를 구성하고,
정책재원의 배분에 따른 변화를 Python으로 시뮬레이션하며,
생성형 AI가 정책배분안을 제안하는 정책 의사결정지원 프로토타입입니다.
""")

st.warning("""
본 모형은 실제 통일 이후의 미래를 예측하는 모형이 아닙니다.
북한 자료의 제약과 남북 통계체계의 차이로 일부 추정치·대리지표를 사용하며,
정책효과 계수 역시 프로토타입 작동을 위한 가정값입니다.
결과는 동일한 가정 아래 정책 시나리오를 비교하기 위한 실험적 결과입니다.
""")


# =========================================================
# 2. 원자료 불러오기
# =========================================================

FILE_PATH = "남북한 광역지역별 초기데이터.xlsx"

try:
    raw = pd.read_excel(
        FILE_PATH,
        sheet_name="시트1",
        header=None
    )
except Exception as e:
    st.error("원자료 Excel 파일을 불러오지 못했습니다.")
    st.code(str(e))
    st.stop()


# =========================================================
# 3. Excel 복합 헤더 정리
# =========================================================

df = raw.iloc[3:].copy()

new_columns = []

for i in range(raw.shape[1]):

    level2 = raw.iloc[1, i]
    level3 = raw.iloc[2, i]

    if pd.notna(level3):
        new_columns.append(str(level3).strip())

    elif pd.notna(level2):
        new_columns.append(str(level2).strip())

    elif i == 0:
        new_columns.append("지역")

    else:
        new_columns.append(f"변수_{i}")

df.columns = new_columns
df = df.reset_index(drop=True)


# =========================================================
# 4. 숫자형 변환
# =========================================================

text_columns = [
    "지역",
    "위도",
    "경도",
    "주요 산업"
]

for col in df.columns:
    if col not in text_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


# =========================================================
# 5. 남한 / 북한 구분
# =========================================================

df["권역"] = "북한"
df.loc[df.index < 17, "권역"] = "남한"


# =========================================================
# 6. 파생변수 계산
# =========================================================

df["도로밀도"] = (
    df["도로 연장(km)"]
    / df["면적(㎢)"]
)

df["철도밀도"] = (
    df["철도 총연장(km)"]
    / df["면적(㎢)"]
)

df["1인당 발전설비"] = (
    df["발전설비현황"]
    / df["총인구(명)"]
)


# =========================================================
# 7. 산업구조 계산
# =========================================================

primary = [
    "농업, 임업 및 어업"
]

secondary = [
    "광업",
    "제조업",
    "전기, 가스, 증기 및 공기 조절 공급업",
    "수도, 하수 및 폐기물 처리, 원료 재생업",
    "건설업"
]

exclude = primary + secondary + [
    "가구 내 고용활동 및 달리 분류되지 않은 자가소비 생산활동",
    "국제 및 외국기관"
]

industry_columns = list(df.columns[6:27])

tertiary = [
    x for x in industry_columns
    if x not in exclude
]

df["1차산업_종사자"] = (
    df[primary].sum(axis=1, min_count=1)
)

df["2차산업_종사자"] = (
    df[secondary].sum(axis=1, min_count=1)
)

df["3차산업_종사자"] = (
    df[tertiary].sum(axis=1, min_count=1)
)

df["산업종사자_총합"] = (
    df["1차산업_종사자"]
    + df["2차산업_종사자"]
    + df["3차산업_종사자"]
)

df["1차산업_비중"] = (
    df["1차산업_종사자"]
    / df["산업종사자_총합"]
    * 100
)

df["2차산업_비중"] = (
    df["2차산업_종사자"]
    / df["산업종사자_총합"]
    * 100
)

df["3차산업_비중"] = (
    df["3차산업_종사자"]
    / df["산업종사자_총합"]
    * 100
)


# =========================================================
# 8. 지표 표준화
# =========================================================

positive_indicators = [
    "도로밀도",
    "도로 포장률(%)",
    "철도밀도",
    "항만 수(개)",
    "공항 수(개)",
    "BCG 접종률(%)",
    "유아교육 참여율(%)",
    "고등교육 이수자 비율(%)",
    "1인당 발전설비",
    "관망급수 보급·이용률(%)",
    "남: 하수도 보급률(%) 북: Piped sewer system(%)"
]

negative_indicators = [
    "저체중 출생아 비율(%)",
    "가정출산율(%)"
]


def minmax_positive(series):

    min_val = series.min()
    max_val = series.max()

    if max_val == min_val:
        return series * 0

    return (
        (series - min_val)
        / (max_val - min_val)
        * 100
    )


def minmax_negative(series):

    min_val = series.min()
    max_val = series.max()

    if max_val == min_val:
        return series * 0

    return (
        (max_val - series)
        / (max_val - min_val)
        * 100
    )


for col in positive_indicators:
    df[col + "_점수"] = minmax_positive(
        df[col]
    )

for col in negative_indicators:
    df[col + "_점수"] = minmax_negative(
        df[col]
    )


# =========================================================
# 9. 분야별 점수
# =========================================================

transport_scores = [
    "도로밀도_점수",
    "도로 포장률(%)_점수",
    "철도밀도_점수",
    "항만 수(개)_점수",
    "공항 수(개)_점수"
]

health_scores = [
    "저체중 출생아 비율(%)_점수",
    "가정출산율(%)_점수",
    "BCG 접종률(%)_점수"
]

education_scores = [
    "유아교육 참여율(%)_점수",
    "고등교육 이수자 비율(%)_점수"
]

living_scores = [
    "1인당 발전설비_점수",
    "관망급수 보급·이용률(%)_점수",
    "남: 하수도 보급률(%) 북: Piped sewer system(%)_점수"
]

df["교통·물류_점수"] = (
    df[transport_scores]
    .mean(axis=1, skipna=True)
)

df["의료·보건_점수"] = (
    df[health_scores]
    .mean(axis=1, skipna=True)
)

df["교육_점수"] = (
    df[education_scores]
    .mean(axis=1, skipna=True)
)

df["생활인프라_점수"] = (
    df[living_scores]
    .mean(axis=1, skipna=True)
)


# =========================================================
# 10. 경제·산업 점수
# =========================================================
# 남한 실제 GRDP와 북한 야간조도 기반 대리지표의
# 직접 비교를 피하기 위해 각각 내부 표준화

south = df.index < 17
north = df.index >= 17

south_min = df.loc[south, "GRDP"].min()
south_max = df.loc[south, "GRDP"].max()

df.loc[south, "경제·산업_점수"] = (
    (df.loc[south, "GRDP"] - south_min)
    / (south_max - south_min)
    * 100
)

north_min = df.loc[north, "GRDP"].min()
north_max = df.loc[north, "GRDP"].max()

df.loc[north, "경제·산업_점수"] = (
    (df.loc[north, "GRDP"] - north_min)
    / (north_max - north_min)
    * 100
)


# =========================================================
# 11. Day 0 균형발전지수
# =========================================================

sector_columns = [
    "경제·산업_점수",
    "교통·물류_점수",
    "의료·보건_점수",
    "교육_점수",
    "생활인프라_점수"
]

df["Day0_균형발전지수"] = (
    df[sector_columns]
    .mean(axis=1, skipna=True)
)


# =========================================================
# 12. 데이터 커버리지
# =========================================================

df["분야_데이터수"] = (
    df[sector_columns]
    .notna()
    .sum(axis=1)
)

df["데이터커버리지(%)"] = (
    df["분야_데이터수"]
    / len(sector_columns)
    * 100
)


def coverage_label(x):

    if x == 100:
        return "높음"

    elif x >= 60:
        return "보통"

    else:
        return "낮음"


df["데이터신뢰도"] = (
    df["데이터커버리지(%)"]
    .apply(coverage_label)
)


# =========================================================
# 13. 데이터 연결 상태
# =========================================================

st.success(
    f"원자료 연결 완료 · 남북한 총 {len(df)}개 광역지역"
)

st.divider()


# =========================================================
# 14. 프로그램 구조
# =========================================================

st.header("프로그램 구조")

st.markdown("""
**30개 광역지역 기초데이터**
→ **Day 0 균형발전지수**
→ **정책재원 배분**
→ **생성형 AI 정책 제안**
→ **Python 정책효과 계산**
→ **정책성과 평가**
→ **다음 연도 정책 재설계**
""")

st.caption(
    "생성형 AI는 정책배분안을 제안하고, "
    "수치적 정책효과는 사전에 설정된 계산규칙에 따라 Python이 산출합니다."
)

st.divider()


# =========================================================
# 15. Day 0 현황
# =========================================================

st.header("Day 0 · 통일한국 초기 균형발전 현황")

overall_mean = df["Day0_균형발전지수"].mean()

south_mean = (
    df.loc[south, "Day0_균형발전지수"]
    .mean()
)

north_mean = (
    df.loc[north, "Day0_균형발전지수"]
    .mean()
)

gap = south_mean - north_mean

summary_df = pd.DataFrame({
    "구분": [
        "30개 지역 평균",
        "남한 17개 지역 평균",
        "북한 13개 지역 평균",
        "남북 평균격차"
    ],
    "Day 0 지수": [
        overall_mean,
        south_mean,
        north_mean,
        gap
    ]
})

summary_df["Day 0 지수"] = (
    summary_df["Day 0 지수"]
    .round(2)
)

st.table(summary_df)

st.caption(
    "지수는 현재 구축된 데이터와 표준화 방식에 따른 상대적 지표이며, "
    "절대적인 지역 발전수준을 의미하지 않습니다."
)


# =========================================================
# 16. 30개 지역 Day 0 순위
# =========================================================

st.subheader("30개 광역지역 Day 0 균형발전지수")

ranking = (
    df[
        [
            "지역",
            "권역",
            "Day0_균형발전지수",
            "데이터커버리지(%)",
            "데이터신뢰도"
        ]
    ]
    .sort_values(
        "Day0_균형발전지수",
        ascending=False
    )
    .copy()
)

ranking["Day0_균형발전지수"] = (
    ranking["Day0_균형발전지수"]
    .round(2)
)

ranking["데이터커버리지(%)"] = (
    ranking["데이터커버리지(%)"]
    .round(0)
)

st.table(
    ranking,
    
    hide_index=True
)


# =========================================================
# 17. Day 0 그래프
# =========================================================

st.subheader("지역별 Day 0 균형발전지수 시각화")

chart_data = (
    df[
        [
            "지역",
            "Day0_균형발전지수"
        ]
    ]
    .sort_values(
        "Day0_균형발전지수",
        ascending=False
    )
    .set_index("지역")
)

st.bar_chart(
    chart_data,
    height=600
)

st.caption(
    "높은 점수는 본 프로젝트의 지표체계 안에서 상대적으로 높은 위치를 의미합니다."
)


# =========================================================
# 18. 개별 지역 분석
# =========================================================

st.divider()

st.header("지역 상세 분석")

selected_region = st.selectbox(
    "분석할 지역을 선택하세요.",
    df["지역"].tolist()
)

selected = (
    df[df["지역"] == selected_region]
    .iloc[0]
)

st.subheader(f"{selected_region} · 분야별 균형발전 점수")

region_sector_df = pd.DataFrame({
    "분야": [
        "경제·산업",
        "교통·물류",
        "의료·보건",
        "교육",
        "생활인프라"
    ],

    "점수": [
        selected["경제·산업_점수"],
        selected["교통·물류_점수"],
        selected["의료·보건_점수"],
        selected["교육_점수"],
        selected["생활인프라_점수"]
    ]
})

region_sector_df["점수"] = (
    region_sector_df["점수"]
    .round(2)
)

st.bar_chart(
    region_sector_df.set_index("분야"),
    height=400
)

detail_df = pd.DataFrame({
    "항목": [
        "Day 0 균형발전지수",
        "데이터 커버리지",
        "데이터 신뢰도"
    ],

    "값": [
        round(
            selected["Day0_균형발전지수"],
            2
        ),

        f"{selected['데이터커버리지(%)']:.0f}%",

        selected["데이터신뢰도"]
    ]
})

st.table(detail_df)


# =========================================================
# 19. 해석 주의사항
# =========================================================

st.divider()

st.header("Day 0 해석 시 주의사항")

st.markdown("""
- **100점은 이상적인 발전상태를 의미하지 않습니다.** 비교집단 내 상대적 위치입니다.
- 남한의 경제자료는 실제 GRDP를 사용하지만, 북한은 야간조도 기반 경제활동 대리지표를 사용합니다.
- 따라서 경제·산업 점수는 남한과 북한을 각각 내부 표준화하였습니다.
- 북한의 일부 의료·교육·생활인프라 자료는 남한 자료와 기준연도와 정의가 다릅니다.
- 일부 지역은 자료가 부족하므로 균형발전지수와 함께 데이터 커버리지를 확인해야 합니다.
- 본 결과는 실제 통일한국의 발전수준을 예측하는 값이 아니라 정책 시뮬레이션의 초기 상태를 구성하기 위한 실험적 지표입니다.
""")


# ============================================================
# 11. 정책 시뮬레이션 설정
# ============================================================

st.divider()

st.header("정책 시뮬레이션")


st.subheader("🤖 생성형 AI 정책 제안")

st.write(
    "현재 Day 0의 지역격차를 바탕으로 생성형 AI가 "
    "남북한 재원 및 5개 정책 분야의 투자비중을 제안합니다."
)
user_scenario = st.text_area(
    "정책 시나리오 입력",
    placeholder=(
        "예: 통일 초기 북한 지역의 전력·상하수도 등 기초생활 인프라 복구를 "
        "우선하면서 남북 간 교통망 연결도 함께 추진하고 싶다."
    ),
    height=120
)

st.caption(
    "원하는 통일·개발 상황이나 정책목표를 자유롭게 입력하면 "
    "생성형 AI가 해당 시나리오를 고려해 투자정책을 제안합니다."
)
if st.button("🤖 AI 정책 제안 받기"):

    try:
        ai_south = df.iloc[:17]
        ai_north = df.iloc[17:]

        ai_current_gap = (
            ai_south["Day0_균형발전지수"].mean()
            - ai_north["Day0_균형발전지수"].mean()
        )

        ai_south_internal = ai_south[
            "Day0_균형발전지수"
        ].std()

        ai_north_internal = ai_north[
            "Day0_균형발전지수"
        ].std()

        ai_bottom20 = (
            df["Day0_균형발전지수"]
            .nsmallest(max(1, int(len(df) * 0.2)))
            .mean()
        )

        with st.spinner("AI가 정책배분안을 설계하고 있습니다..."):

            ai_policy = get_ai_policy_suggestion(
                current_gap=ai_current_gap,
                south_internal=ai_south_internal,
                north_internal=ai_north_internal,
                bottom20=ai_bottom20,
                user_scenario=user_scenario
            )

        st.session_state["ai_policy"] = ai_policy

    except Exception as e:
        st.error(f"AI 정책 제안 중 오류가 발생했습니다: {e}")


if "ai_policy" in st.session_state:

    ai_policy = st.session_state["ai_policy"]

    st.success("AI 정책 제안이 생성되었습니다.")

    st.markdown(
        f"""
**남한지역 투자 비중:** {ai_policy["남한예산"]}%  
**북한지역 투자 비중:** {ai_policy["북한예산"]}%

**분야별 투자 비중**

- 경제·산업: {ai_policy["분야배분"]["경제·산업"]}%
- 교통·물류: {ai_policy["분야배분"]["교통·물류"]}%
- 의료·보건: {ai_policy["분야배분"]["의료·보건"]}%
- 교육: {ai_policy["분야배분"]["교육"]}%
- 생활인프라: {ai_policy["분야배분"]["생활인프라"]}%

**AI 제안 이유**

{ai_policy["정책설명"]}
"""
    )

    st.caption(
        "※ AI 제안은 실제 정책의 최적해나 미래 예측이 아니라 "
        "본 프로토타입의 데이터와 가정을 바탕으로 생성된 정책 시나리오입니다."
    )


    if st.button("✅ AI 제안값을 시뮬레이션에 적용"):
        st.session_state["apply_ai_policy"] = True
        st.rerun()



st.write(
    "연간 가상 정책재원을 남한·북한 및 5개 정책 분야에 배분하여 "
    "10년 동안 균형발전지수가 어떻게 변화하는지 실험합니다."
)

st.caption(
    "아래 재원 규모와 배분 비율은 실제 정책 권고가 아니라 "
    "시뮬레이션을 위한 가정값입니다."
)

# -----------------------------
# 기본 설정
# -----------------------------

col1, col2 = st.columns(2)

with col1:
    annual_budget = st.number_input(
        "연간 가상 정책재원 (조 원)",
        min_value=10,
        max_value=500,
        value=100,
        step=10
    )

with col2:
    simulation_years = st.slider(
        "시뮬레이션 기간 (년)",
        min_value=1,
        max_value=20,
        value=10
    )

st.subheader("남북한 재원 배분")

north_default = 70

if st.session_state.pop("apply_ai_policy", False):
    if "ai_policy" in st.session_state:
        p = st.session_state["ai_policy"]

        st.session_state["north_slider"] = int(p["북한예산"])
        st.session_state["economy_slider"] = int(p["분야배분"]["경제·산업"])
        st.session_state["transport_slider"] = int(p["분야배분"]["교통·물류"])
        st.session_state["health_slider"] = int(p["분야배분"]["의료·보건"])
        st.session_state["education_slider"] = int(p["분야배분"]["교육"])
        st.session_state["living_slider"] = int(p["분야배분"]["생활인프라"])

        st.session_state["ai_applied_notice"] = True

north_budget_ratio = st.slider(
    "북한지역 투자 비중 (%)",
    min_value=0,
    max_value=100,
    value=north_default,
    key="north_slider"
)

if st.session_state.pop("ai_applied_notice", False):
    st.success("✅ AI 제안값이 아래 정책 슬라이더에 적용되었습니다.")

south_budget_ratio = 100 - north_budget_ratio

c1, c2 = st.columns(2)

with c1:
    st.markdown(f"**남한지역**  \n{south_budget_ratio}%")

with c2:
    st.markdown(f"**북한지역**  \n{north_budget_ratio}%")

st.subheader("분야별 투자 비중")

economy_ratio = st.slider(
    "경제·산업 (%)",
    0, 100, 30,
    key="economy_slider"
)

transport_ratio = st.slider(
    "교통·물류 (%)",
    0, 100, 25,
    key="transport_slider"
)

health_ratio = st.slider(
    "의료·보건 (%)",
    0, 100, 15,
    key="health_slider"
)

education_ratio = st.slider(
    "교육 (%)",
    0, 100, 15,
    key="education_slider"
)

living_ratio = st.slider(
    "생활인프라 (%)",
    0, 100, 15,
    key="living_slider"
)

sector_total = (
    economy_ratio
    + transport_ratio
    + health_ratio
    + education_ratio
    + living_ratio
)

if sector_total == 100:
    st.success("분야별 투자 비중 합계: 100%")
else:
    st.error(
        f"현재 분야별 투자 비중 합계는 {sector_total}%입니다. "
        "합계가 100%가 되도록 조정해주세요."
    )

st.subheader("현재 정책 시나리오")

policy_summary = pd.DataFrame({
    "정책 분야": [
        "경제·산업",
        "교통·물류",
        "의료·보건",
        "교육",
        "생활인프라"
    ],
    "투자 비중(%)": [
        economy_ratio,
        transport_ratio,
        health_ratio,
        education_ratio,
        living_ratio
    ]
})

st.table(policy_summary)

if sector_total == 100:
    st.info(
        f"연간 {annual_budget}조 원을 {simulation_years}년 동안 투자하는 "
        f"가상 시나리오입니다. 누적 정책재원은 "
        f"{annual_budget * simulation_years:,}조 원입니다."
    )


# ============================================================
# 12. 10년 정책 시뮬레이션 엔진
# ============================================================

if sector_total == 100:

    st.divider()
    st.header("10년 정책 시뮬레이션")

    # 프로토타입 가정값
    investment_efficiency = {
        "경제·산업": 0.8,
        "교통·물류": 0.6,
        "의료·보건": 0.7,
        "교육": 0.5,
        "생활인프라": 0.7
    }

    time_effect = {
        "경제·산업": 0.7,
        "교통·물류": 0.3,
        "의료·보건": 0.7,
        "교육": 0.3,
        "생활인프라": 0.6
    }

    sector_map = {
        "경제·산업": "경제·산업_점수",
        "교통·물류": "교통·물류_점수",
        "의료·보건": "의료·보건_점수",
        "교육": "교육_점수",
        "생활인프라": "생활인프라_점수"
    }

    sector_ratios = {
        "경제·산업": economy_ratio / 100,
        "교통·물류": transport_ratio / 100,
        "의료·보건": health_ratio / 100,
        "교육": education_ratio / 100,
        "생활인프라": living_ratio / 100
    }

    # 시뮬레이션용 데이터 복사
    sim_df = df.copy()

    # 미실현 정책효과 저장
    carryover = {
        sector: pd.Series(0.0, index=sim_df.index)
        for sector in sector_map
    }

    history = []

    def record_year(year, data):
        south_data = data.iloc[:17]
        north_data = data.iloc[17:]

        south_mean = south_data["Day0_균형발전지수"].mean()
        north_mean = north_data["Day0_균형발전지수"].mean()

        history.append({
            "연도": year,
            "남한 평균": south_mean,
            "북한 평균": north_mean,
            "남북 격차": south_mean - north_mean,
            "남한 내부격차": south_data["Day0_균형발전지수"].std(),
            "북한 내부격차": north_data["Day0_균형발전지수"].std(),
            "하위20% 평균": data["Day0_균형발전지수"]
                            .nsmallest(max(1, int(len(data) * 0.2)))
                            .mean()
        })

    # Year 0 기록
    record_year(0, sim_df)

    # --------------------------------------------------------
    # 연도별 계산
    # --------------------------------------------------------

    for year in range(1, simulation_years + 1):

        for region_index in sim_df.index:

            is_south = region_index < 17

            if is_south:
                regional_budget = annual_budget * (south_budget_ratio / 100) / 17
            else:
                regional_budget = annual_budget * (north_budget_ratio / 100) / 13

            for sector, score_col in sector_map.items():

                current_score = sim_df.loc[region_index, score_col]

                if pd.isna(current_score):
                    continue

                sector_budget = regional_budget * sector_ratios[sector]

                # 현재 점수가 낮을수록 투자효과가 크게 나타나는 구조
                gap_factor = (100 - current_score) / 100

                potential_effect = (
                    sector_budget
                    * investment_efficiency[sector]
                    * gap_factor
                )

                # 이전 연도의 미실현 효과 + 올해 새 효과
                total_effect = (
                    carryover[sector].loc[region_index]
                    + potential_effect
                )

                realized_effect = (
                    total_effect
                    * time_effect[sector]
                )

                remaining_effect = (
                    total_effect
                    - realized_effect
                )

                new_score = min(
                    current_score + realized_effect,
                    100
                )

                sim_df.loc[region_index, score_col] = new_score
                carryover[sector].loc[region_index] = remaining_effect

        # 균형발전지수 다시 계산
        sim_df["Day0_균형발전지수"] = sim_df[
            [
                "경제·산업_점수",
                "교통·물류_점수",
                "의료·보건_점수",
                "교육_점수",
                "생활인프라_점수"
            ]
        ].mean(axis=1, skipna=True)

        record_year(year, sim_df)

    history_df = pd.DataFrame(history)
# 현재 시나리오의 10년 결과를 저장
if st.button("📌 현재 결과를 시나리오 A로 저장"):
    st.session_state["scenario_A"] = {
        "scenario_text": user_scenario,
        "history": history_df.copy(),
"south_budget": south_budget_ratio,
"north_budget": north_budget_ratio,
"sector_weights": {
    "경제·산업": economy_ratio,
    "교통·물류": transport_ratio,
    "의료·보건": health_ratio,
    "교육": education_ratio,
    "생활인프라": living_ratio
}
}
    st.success("시나리오 A가 저장되었습니다.")
    st.success(
        f"{simulation_years}년 정책 시뮬레이션 계산이 완료되었습니다."
    )

    # --------------------------------------------------------
# 핵심 결과
# --------------------------------------------------------

start = history_df.iloc[0]
end = history_df.iloc[-1]

c1, c2, c3 = st.columns(3)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**남북 평균격차**")
    st.write(f"{end['남북 격차']:.2f}")
    st.caption(f"변화: {end['남북 격차'] - start['남북 격차']:.2f}")

with c2:
    st.markdown("**북한 평균지수**")
    st.write(f"{end['북한 평균']:.2f}")
    st.caption(f"변화: {end['북한 평균'] - start['북한 평균']:.2f}")


# --------------------------------------------------------
# 연도별 결과
# --------------------------------------------------------

st.subheader("연도별 시뮬레이션 결과")

display_history = history_df.copy()

numeric_cols = display_history.columns[1:]
display_history[numeric_cols] = (
    display_history[numeric_cols].round(3)
)

st.table(display_history)

# 터널 환경에서도 비교적 안정적으로 표시되도록
# Streamlit 기본 line_chart 대신 matplotlib 사용
st.subheader("남북 평균 균형발전지수 변화")

import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(
    history_df["연도"],
    history_df["남한 평균"],
    marker="o",
    label="남한 평균"
)

ax.plot(
    history_df["연도"],
    history_df["북한 평균"],
    marker="o",
    label="북한 평균"
)

ax.set_xlabel("연도")
ax.set_ylabel("균형발전지수")
ax.set_title("정책 시나리오에 따른 10년 변화")
ax.legend()
ax.grid(alpha=0.3)

st.pyplot(fig)

st.caption(
    "투자효율과 시간효과 계수는 실제 정책효과의 추정값이 아니라 "
    "프로토타입 작동을 위해 설정한 가정값입니다."
)
# ============================================================
# 시나리오 A / B 비교 기능
# ============================================================

st.divider()
st.header("정책 시나리오 비교")

if "scenario_A" in st.session_state:
    st.success("시나리오 A가 저장되어 있습니다.")

    if st.button("현재 결과를 시나리오 B로 저장"):
        st.session_state["scenario_B"] = {
            "scenario_text": user_scenario,
            "history": history_df.copy(),
            "south_budget": south_budget_ratio,
            "north_budget": north_budget_ratio,
            "sector_weights": {
                "경제·산업": economy_ratio,
                "교통·물류": transport_ratio,
                "의료·보건": health_ratio,
                "교육": education_ratio,
                "생활인프라": living_ratio
            }
        }
        st.success("시나리오 B가 저장되었습니다.")
