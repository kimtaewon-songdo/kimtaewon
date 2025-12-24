# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# 유틸 함수 (파일 인식 핵심)
# ===============================
def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text)

def find_file(data_dir: Path, keyword: str, suffix: str):
    for f in data_dir.iterdir():
        if f.suffix == suffix:
            if keyword in normalize(f.name):
                return f
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data():
    data_dir = Path("data")
    school_map = {
        "송도고": "송도고",
        "하늘고": "하늘고",
        "아라고": "아라고",
        "동산고": "동산고"
    }

    env_data = {}

    with st.spinner("환경 데이터 로딩 중..."):
        for school, key in school_map.items():
            file_path = find_file(data_dir, key, ".csv")
            if file_path is None:
                st.error(f"{school} 환경 데이터 파일을 찾을 수 없습니다.")
                continue
            df = pd.read_csv(file_path)
            df["time"] = pd.to_datetime(df["time"])
            env_data[school] = df

    return env_data

@st.cache_data
def load_growth_data():
    data_dir = Path("data")
    xlsx_file = None

    for f in data_dir.iterdir():
        if f.suffix == ".xlsx":
            xlsx_file = f
            break

    if xlsx_file is None:
        st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return {}

    with st.spinner("생육 데이터 로딩 중..."):
        xls = pd.ExcelFile(xlsx_file)
        growth_data = {}
        for sheet in xls.sheet_names:
            df = pd.read_excel(xlsx_file, sheet_name=sheet)
            growth_data[sheet] = df

    return growth_data

env_data = load_environment_data()
growth_data = load_growth_data()

if not env_data or not growth_data:
    st.stop()

# ===============================
# 메타 정보
# ===============================
ec_target = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

school_colors = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728"
}

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

# ===============================
# 사이드바
# ===============================
school_option = st.sidebar.selectbox(
    "학교 선택",
    ["전체", "송도고", "하늘고", "아라고", "동산고"]
)

selected_schools = list(env_data.keys()) if school_option == "전체" else [school_option]

# ===============================
# 탭 구성
# ===============================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ===============================
# Tab 1: 실험 개요
# ===============================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.markdown("""
    본 연구는 극지식물 재배 환경에서 **EC(양액 농도)**가 생육에 미치는 영향을 분석하여  
    **최적 EC 농도 범위**를 도출하는 것을 목표로 한다.
    """)

    summary_rows = []
    total_count = 0
    for school, df in growth_data.items():
        count = len(df)
        total_count += count
        summary_rows.append([school, ec_target.get(school), count])

    summary_df = pd.DataFrame(
        summary_rows,
        columns=["학교명", "EC 목표", "개체 수"]
    )

    st.dataframe(summary_df, use_container_width=True)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_humi = pd.concat(env_data.values())["humidity"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 개체 수", f"{total_count} 개")
    col2.metric("평균 온도", f"{avg_temp:.1f} ℃")
    col3.metric("평균 습도", f"{avg_humi:.1f} %")
    col4.metric("최적 EC", "2.0 (하늘고)")

# ===============================
# Tab 2: 환경 데이터
# ===============================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_env = []
    for school in selected_schools:
        df = env_data[school]
        avg_env.append([
            school,
            df["temperature"].mean(),
            df["humidity"].mean(),
            df["ph"].mean(),
            df["ec"].mean()
        ])

    avg_df = pd.DataFrame(
        avg_env,
        columns=["학교", "온도", "습도", "pH", "EC"]
    )

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["온도"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["습도"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["pH"], row=2, col=1)

    fig.add_bar(
        x=avg_df["학교"],
        y=[ec_target[s] for s in avg_df["학교"]],
        name="목표 EC",
        row=2, col=2
    )
    fig.add_bar(
        x=avg_df["학교"],
        y=avg_df["EC"],
        name="실측 EC",
        row=2, col=2
    )

    fig.update_layout(
        height=600,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("환경 데이터 시계열")

    for metric in ["temperature", "humidity", "ec"]:
        fig_ts = go.Figure()
        for school in selected_schools:
            df = env_data[school]
            fig_ts.add_scatter(
                x=df["time"],
                y=df[metric],
                mode="lines",
                name=school
            )
            if metric == "ec":
                fig_ts.add_hline(
                    y=ec_target[school],
                    line_dash="dot"
                )

        fig_ts.update_layout(
            title=metric,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("환경 데이터 원본"):
        full_env = pd.concat(
            [df.assign(학교=school) for school, df in env_data.items()]
        )
        st.dataframe(full_env)

        buffer = io.BytesIO()
        full_env.to_csv(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            "CSV 다운로드",
            data=buffer,
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# ===============================
# Tab 3: 생육 결과
# ===============================
with tab3:
    st.subheader("EC별 평균 생중량")

    ec_summary = []
    for school, df in growth_data.items():
        ec_summary.append([
            school,
            ec_target.get(school),
            df["생중량(g)"].mean(),
            len(df)
        ])

    ec_df = pd.DataFrame(
        ec_summary,
        columns=["학교", "EC", "평균 생중량", "개체수"]
    )

    best_row = ec_df.loc[ec_df["평균 생중량"].idxmax()]
    st.metric(
        "🥇 최고 생중량 EC",
        f"{best_row['EC']} (학교: {best_row['학교']})"
    )

    fig_bar = px.bar(
        ec_df,
        x="학교",
        y="평균 생중량",
        color="학교"
    )
    fig_bar.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    fig_box = px.box(
        pd.concat(
            [df.assign(학교=school) for school, df in growth_data.items()]
        ),
        x="학교",
        y="생중량(g)"
    )
    fig_box.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("상관관계 분석")

    merged = []
    for school, df in growth_data.items():
        merged.append(df.assign(학교=school))
    merged_df = pd.concat(merged)

    fig_sc1 = px.scatter(
        merged_df,
        x="잎 수(장)",
        y="생중량(g)",
        color="학교"
    )
    fig_sc2 = px.scatter(
        merged_df,
        x="지상부 길이(mm)",
        y="생중량(g)",
        color="학교"
    )

    fig_sc1.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    fig_sc2.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))

    st.plotly_chart(fig_sc1, use_container_width=True)
    st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("생육 데이터 원본"):
        st.dataframe(merged_df)

        buffer = io.BytesIO()
        merged_df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

