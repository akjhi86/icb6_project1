import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import os
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go

# .env 파일 로드
load_dotenv()

# 설정
st.set_page_config(page_title="서울 상권 및 실거래가 분석 대시보드", layout="wide", page_icon="🏙️")

# --- Custom CSS (Premium UI) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&family=Inter:wght@400;600&display=swap');

    /* 전체 배경 및 폰트 설정 */
    .stApp {
        background: radial-gradient(circle at top left, #f8f9ff, #ffffff);
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: #1E1E1E;
        letter-spacing: -0.5px;
    }

    /* 카드 스타일 (Expander 및 Metric 모사) */
    .st-emotion-cache-1vt4y6f {
        background-color: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(10px);
        border-radius: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07) !important;
    }

    /* 버튼 스타일 */
    .stButton > button {
        background: linear-gradient(135deg, #4F46E5, #3B82F6);
        color: white;
        border-radius: 12px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6);
        color: white;
    }

    /* 디바이더 스타일 */
    hr {
        margin: 2rem 0;
        border-top: 2px solid #f1f3f9;
        opacity: 0.5;
    }

    /* 데이터프레임 스타일 보정 */
    .stDataFrame {
        border-radius: 15px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

# 데이터 디렉토리
DATA_DIR = r'E:\fastcampus\icb6\project1\data'

# 서울 주요 자치구 법정동 코드
SEOUL_SIGUNGU_CODES = {
    '종로구': '11110', '중구': '11140', '용산구': '11170', '성동구': '11200',
    '광진구': '11215', '동대문구': '11230', '중랑구': '11260', '성북구': '11290',
    '강북구': '11305', '도봉구': '11320', '노원구': '11350', '은평구': '11380',
    '서대문구': '11410', '마포구': '11440', '양천구': '11470', '강서구': '11500',
    '구로구': '11530', '금천구': '11545', '영등포구': '11560', '동작구': '11590',
    '관악구': '11620', '서초구': '11650', '강남구': '11680', '송파구': '11710',
    '강동구': '11740'
}

# --- 컬럼 한글 매핑 사전 ---
COLUMN_MAP = {
    'dealAmount': '거래금액(만원)',
    'dealYear': '거래연도',
    'dealMonth': '거래월',
    'dealDay': '거래일',
    'sggNm': '자치구',
    'umdNm': '법정동',
    'buildingAr': '건물면적(㎡)',
    'buildYear': '건축년도',
    'buildingUse': '건물용도',
    'floor': '층',
    'sggCd': '지역코드',
    'landCd': '지번코드',
    'jibun': '지번'
}

def fetch_molit_data(lawd_cd, deal_ymd):
    """국토교통부 실거래가 API 연동 함수"""
    service_key = os.getenv("MOLIT_API_KEY")
    if not service_key:
        st.error(".env 파일에 MOLIT_API_KEY가 설정되어 있지 않습니다.")
        return None
        
    url = "http://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"
    params = {
        'serviceKey': service_key,
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd,
        'numOfRows': 1000, 
        'pageNo': 1
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        header = root.find('header')
        result_msg = header.find('resultMsg').text
        if result_msg not in ['NORMAL SERVICE.', 'OK']:
            st.warning(f"API 호출 결과: {result_msg}")
            return None
            
        items = root.findall('.//item')
        data_list = []
        for item in items:
            row = {child.tag: child.text for child in item}
            data_list.append(row)
            
        return pd.DataFrame(data_list) if data_list else None
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return None

def main():
    st.title("🏙️ 서울 상업용 부동산 분석 대시보드")
    
    st.header("국토교통부 실거래가 인터랙티브 데이터 분석")
    
    # 조회 설정 박스
    with st.expander("🔍 조회 설정", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            gu_options = ["서울특별시 전체"] + list(SEOUL_SIGUNGU_CODES.keys())
            selected_gus = st.multiselect("분석할 자치구 선택", gu_options, default=["종로구"])
        with col2:
            fetch_mode = st.radio("조회 모드", ["월별", "년단위"], index=1, horizontal=True)
        with col3:
            year_options = sorted(range(2021, 2027), reverse=True)
            year = st.selectbox("연도 선택", year_options, index=0)
        
        if fetch_mode == "월별":
            month = st.selectbox("월 선택", range(1, 13))
            deal_ymd_list = [f"{year}{month:02d}"]
        else:
            deal_ymd_list = [f"{year}{m:02d}" for m in range(1, 13)]
        
        fetch_btn = st.button("실거래가 데이터 수집 시작")

    if fetch_btn:
        if not selected_gus:
            st.warning("최소 하나 이상의 자치구를 선택해주세요.")
        else:
            all_dfs = []
            target_gus = SEOUL_SIGUNGU_CODES if "서울특별시 전체" in selected_gus else {gu: SEOUL_SIGUNGU_CODES[gu] for gu in selected_gus if gu in SEOUL_SIGUNGU_CODES}
            
            total_iterations = len(target_gus) * len(deal_ymd_list)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            current_iter = 0
            for gu_name, gu_code in target_gus.items():
                for ymd in deal_ymd_list:
                    current_iter += 1
                    status_text.text(f"데이터 수집 중... ({gu_name} - {ymd})")
                    df_temp = fetch_molit_data(gu_code, ymd)
                    if df_temp is not None:
                        # 데이터 전처리
                        if 'dealAmount' in df_temp.columns:
                            df_temp['dealAmount'] = df_temp['dealAmount'].str.replace(',', '').astype(float)
                        if 'buildingAr' in df_temp.columns:
                            df_temp['buildingAr'] = pd.to_numeric(df_temp['buildingAr'], errors='coerce')
                        if 'floor' in df_temp.columns:
                            df_temp['floor'] = pd.to_numeric(df_temp['floor'], errors='coerce')
                        all_dfs.append(df_temp)
                    progress_bar.progress(current_iter / total_iterations)
            
            if all_dfs:
                combined_df = pd.concat(all_dfs, ignore_index=True)
                
                # 다중 선택 레이블 생성
                if "서울특별시 전체" in selected_gus:
                    label = "서울특별시 전체"
                else:
                    label = ", ".join(selected_gus) if len(selected_gus) <= 2 else f"{selected_gus[0]} 외 {len(selected_gus)-1}개 지역"
                
                st.session_state['molit_df'] = combined_df
                st.session_state['selected_gu_label'] = label
                st.success(f"{label} 데이터 총 {len(combined_df)}건을 수집했습니다.")
            else:
                st.session_state['molit_df'] = None
                st.info("조회된 실거래 데이터가 없습니다.")

    if 'molit_df' in st.session_state and st.session_state['molit_df'] is not None:
        # 원본 데이터 복사 및 한글 컬럼명 적용
        df_display = st.session_state['molit_df'].copy()
        current_gu_label = st.session_state.get('selected_gu_label', '선택된 지역')
        
        st.divider()
        st.subheader("📍 상세 필터링")
        
        # 필터링용 동 필드 (한글 적용 전 original 필드 사용)
        dong_field = 'umdNm' if 'umdNm' in df_display.columns else ('법정동' if '법정동' in df_display.columns else None)
        
        if dong_field:
            all_dongs = sorted(df_display[dong_field].unique())
            selected_dongs = st.multiselect("분석할 상세 지역(동) 선택", all_dongs, default=all_dongs)
            df_display = df_display[df_display[dong_field].isin(selected_dongs)]
            
            # 한글 컬럼명으로 전체 변경
            df_display = df_display.rename(columns=COLUMN_MAP)
        else:
            df_display = df_display.rename(columns=COLUMN_MAP)
            st.warning("동 정보를 찾을 수 없습니다.")
        
        st.info(f"선택된 조건에 해당하는 실거래 데이터 **{len(df_display)}** 건이 분석되었습니다.")

        st.divider()
        # 자치구별 비교 (한글 컬럼명 기준)
        if current_gu_label == "서울특별시 전체":
            st.subheader("🏢 자치구별 거래 현황 비교")
            gu_comp_col1, gu_comp_col2 = st.columns(2)
            
            with gu_comp_col1:
                gu_counts = df_display['자치구'].value_counts().reset_index()
                gu_counts.columns = ['자치구', '거래건수']
                fig = px.bar(gu_counts, x='거래건수', y='자치구', orientation='h', 
                             title="자치구별 총 거래건수", color='거래건수', color_continuous_scale='Viridis')
                st.plotly_chart(fig, use_container_width=True)
                
            with gu_comp_col2:
                gu_avg_price = df_display.groupby('자치구')['거래금액(만원)'].mean().sort_values(ascending=False).reset_index()
                gu_avg_price.columns = ['자치구', '평균 거래금액']
                fig = px.bar(gu_avg_price, x='평균 거래금액', y='자치구', orientation='h',
                             title="자치구별 평균 거래금액 (만원)", color='평균 거래금액', color_continuous_scale='YlOrRd')
                st.plotly_chart(fig, use_container_width=True)
            st.divider()

        v_col1, v_col2 = st.columns(2)
        with v_col1:
            st.subheader("📅 거래량 추이")
            if '거래연도' in df_display.columns and '거래월' in df_display.columns:
                df_display['년월'] = df_display['거래연도'].astype(str) + "-" + df_display['거래월'].astype(str).str.zfill(2)
                trend = df_display.groupby('년월').size().reset_index(name='거래건수').sort_values('년월')
                fig = px.line(trend, x='년월', y='거래건수', markers=True, 
                             title=f"{current_gu_label} 연월별 거래량 추이", line_shape='spline')
                fig.update_traces(line_color='#4F46E5')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("시계열 분석 데이터 부족")

        with v_col2:
            st.subheader("🏘️ 지역별 거래 분포 (상위 15개)")
            # 서울 전체 분석 시 (구+동) 조합 필드 생성
            if current_gu_label == "서울특별시 전체":
                df_display['지역명'] = df_display['자치구'] + " " + df_display['법정동']
                dist_col = '지역명'
            else:
                dist_col = '법정동'
                
            if dist_col in df_display.columns:
                dist_data = df_display[dist_col].value_counts().head(15).reset_index()
                dist_data.columns = ['지역', '거래수']
                fig = px.bar(dist_data, x='거래수', y='지역', orientation='h',
                             title=f"{current_gu_label} 주요 지역별 거래 분포", color='거래수', color_continuous_scale='Spectral')
                st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("📈 거래가격 정밀 분석 (Price Analysis)")
        
        eda_col1, eda_col2 = st.columns(2)
        with eda_col1:
            st.markdown("#### 1. 가격 분포 및 밀도 (Histogram)")
            fig = px.histogram(df_display, x='거래금액(만원)', marginal="rug", 
                               title="거래 가격 분포 상세", nbins=50, color_discrete_sequence=['#4F46E5'])
            fig.update_layout(xaxis_title="거래 금액 (만원)", yaxis_title="건수")
            st.plotly_chart(fig, use_container_width=True)

        with eda_col2:
            st.markdown("#### 2. 지역별 가격 비교 및 이상치 (Box Plot)")
            fig = px.box(df_display, x='자치구', y='거래금액(만원)', points="all",
                         title="자치구별 거래 가격 분포 및 이상치 확인", color='자치구')
            st.plotly_chart(fig, use_container_width=True)

        eda_col3, eda_col4 = st.columns(2)
        with eda_col3:
            st.markdown("#### 3. 가격 밀집도 상세 분석 (Violin Plot)")
            fig = px.violin(df_display, y='거래금액(만원)', x='자치구', color='자치구', box=True,
                            title="자치구별 가격 밀집 데이터 분산")
            st.plotly_chart(fig, use_container_width=True)

        with eda_col4:
            st.markdown("#### 4. 면적 대비 가격 분석 (Scatter Plot)")
            if '건물면적(㎡)' in df_display.columns:
                # 층 정보가 있으면 색상으로 구분
                hue_col = '층' if '층' in df_display.columns else None
                fig = px.scatter(df_display, x='건물면적(㎡)', y='거래금액(만원)', color=hue_col,
                                 hover_data=['법정동', '건축년도', '건물용도'], 
                                 title="건물 면적 vs 거래 가격 상관관계",
                                 color_continuous_scale='Bluered')
                fig.update_layout(xaxis_title="건물 면적 (㎡)", yaxis_title="거래 금액 (만원)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("면적 데이터 부족")

        eda_col5, eda_col6 = st.columns(2)
        with eda_col5:
            st.markdown("#### 5. 누적분포함수 그래프 (ECDF Plot)")
            fig = px.ecdf(df_display, x='거래금액(만원)', title="가격 누적 분포 현황 (ECDF)")
            fig.update_traces(line_color='#EF4444')
            fig.update_layout(xaxis_title="거래 금액 (만원)", yaxis_title="누적 비율")
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("💎 거래 금액 하이라이트 (TOP 10)")
        
        top_col1, top_col2 = st.columns(2)
        
        # 표시할 한글 컬럼 리스트
        final_display_cols = ['자치구', '법정동', '건축년도', '건물용도', '거래금액(만원)', '건물면적(㎡)']
        available_cols = [c for c in final_display_cols if c in df_display.columns]

        with top_col1:
            st.markdown("#### 🚀 최고가 거래 TOP 10")
            top_10 = df_display.nlargest(10, '거래금액(만원)')
            st.table(top_10[available_cols])

        with top_col2:
            st.markdown("#### 📉 최저가 거래 TOP 10")
            bottom_10 = df_display.nsmallest(10, '거래금액(만원)')
            st.table(bottom_10[available_cols])

        st.divider()
        st.subheader("📄 전체 상세 거래 내역")
        st.dataframe(df_display, use_container_width=True)
        
        csv = df_display.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(label="분석 완료 데이터 다운로드", data=csv, 
                           file_name=f"analysis_{current_gu_label}_{year}.csv", mime='text/csv')

if __name__ == "__main__":
    main()
