import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="서울시 업종별 고도화 분석 대시보드", layout="wide")

@st.cache_data
def load_data():
    file_path = "data/seoul_business_stats.csv"
    if not os.path.exists(file_path):
        st.error(f"데이터 파일을 찾을 수 없습니다: {file_path}")
        return None
    
    df = pd.read_csv(file_path)
    df['일자'] = pd.to_datetime(df['일자'])
    df['Year'] = df['일자'].dt.year
    df['Month'] = df['일자'].dt.month
    return df

st.title("🚀 서울시 업종별 데이터 심층 분석 대시보드")
st.markdown("분석 섹션별로 수치를 입력하여 실시간으로 변화하는 데이터를 확인해 보세요.")

data_raw = load_data()

if data_raw is not None:
    # 1. 연도별 전체 추이 섹션
    with st.expander("📅 1. 연도별 전체 창업/폐업 추이 분석", expanded=True):
        st.subheader("연도 범위 설정")
        col1, col2 = st.columns(2)
        with col1:
            start_y = st.number_input("시작 연도", min_value=int(data_raw['Year'].min()), max_value=int(data_raw['Year'].max()), value=1990, key="y_start")
        with col2:
            # 종료 연도 설정: 데이터의 최대 연도와 2025 중 큰 값을 max_value로 설정
            max_year_data = int(data_raw['Year'].max())
            max_bound = max(2025, max_year_data)
            # 기본값(value)은 2025로 하되, 데이터가 그보다 적으면 데이터 최대값으로 설정
            default_end = min(2025, max_year_data)
            
            end_y = st.number_input("종료 연도", 
                                    min_value=int(data_raw['Year'].min()), 
                                    max_value=max_bound, 
                                    value=default_end, 
                                    key="y_end")
        
        y_df_base = data_raw[(data_raw['Year'] >= start_y) & (data_raw['Year'] <= end_y)]
        yearly_total = y_df_base.groupby('Year')[['창업수', '폐업수']].sum().reset_index()
        
        # 호버 시 상위 10개 업종 정보를 보여주기 위한 사전 계산
        top10_info = []
        for year in yearly_total['Year']:
            year_data = y_df_base[y_df_base['Year'] == year]
            top10 = year_data.groupby('업종명')['창업수'].sum().nlargest(10)
            info_str = "<br>".join([f"{i+1}. {name} ({count:,}건)" for i, (name, count) in enumerate(top10.items())])
            top10_info.append(f"<b>[상위 10개 업종]</b><br>{info_str}")
        
        yearly_total['top10_details'] = top10_info

        fig1 = go.Figure()
        # 창업수 라인
        fig1.add_trace(go.Scatter(x=yearly_total['Year'], y=yearly_total['창업수'], name='창업수', mode='lines+markers',
                                  customdata=yearly_total['top10_details'],
                                  hovertemplate='<b>연도: %{x}</b><br>창업수: %{y:,}건<br>%{customdata}<extra></extra>'))
        # 폐업수 라인
        fig1.add_trace(go.Scatter(x=yearly_total['Year'], y=yearly_total['폐업수'], name='폐업수', mode='lines+markers',
                                  hovertemplate='<b>연도: %{x}</b><br>폐업수: %{y:,}건<extra></extra>'))
        
        fig1.update_layout(title='서울시 연도별 전체 창업/폐업 추이', xaxis_title='연도', yaxis_title='건수', template='plotly_white')
        st.plotly_chart(fig1, use_container_width=True)

    # 2. 업종별 비교 섹션
    with st.expander("📊 2. 주요 업종별 누적 현황 비교", expanded=True):
        st.subheader("업종 개수 및 검색어 필터")
        col1, col2 = st.columns(2)
        
        all_industries_list = sorted(list(data_raw['업종명'].unique()))
        
        with col1:
            top_n = st.number_input("표시할 상위 업종 수", min_value=5, max_value=100, value=30, step=5)
        with col2:
            # text_input 대신 multiselect를 활용하여 '미리보기' 및 '선택' 기능 제공
            filter_industries = st.multiselect("특정 업종 필터 (미리보기 및 선택 가능)", options=all_industries_list, help="입력하면 해당 업종들만 비교합니다. 비워두면 상위 N개를 보여줍니다.")
        
        industry_all = data_raw.groupby('업종명')[['창업수', '폐업수']].sum().reset_index()
        
        if filter_industries:
            industry_display = industry_all[industry_all['업종명'].isin(filter_industries)]
        else:
            industry_display = industry_all.sort_values(by='창업수', ascending=False).head(top_n)
        
        fig2 = px.bar(industry_display, x='업종명', y=['창업수', '폐업수'], barmode='group',
                      title=f"업종별 누적 현황 현황",
                      labels={'value': '누적 건수'})
        st.plotly_chart(fig2, use_container_width=True)

    # 3. 생존 지수 섹션
    with st.expander("🛡️ 3. 업종별 상대적 생존 지수 (안정성 분석)", expanded=True):
        st.subheader("생존 분석 파라미터 입력")
        col1, col2 = st.columns(2)
        with col1:
            min_startups = st.number_input("최소 창업 건수 문턱값 (최근 10년 기준)", min_value=100, max_value=50000, value=1000, step=100)
        with col2:
            survival_n = st.number_input("표시할 상위 안정 업종 수", min_value=5, max_value=50, value=20)
            
        recent_10 = data_raw[data_raw['Year'] >= (datetime.now().year - 10)].groupby('업종명')[['창업수', '폐업수']].sum().reset_index()
        recent_10 = recent_10[recent_10['창업수'] >= min_startups]
        recent_10['폐업비율'] = (recent_10['폐업수'] / recent_10['창업수']) * 100
        
        survival_top = recent_10.nsmallest(survival_n, '폐업비율')
        
        fig3 = px.bar(survival_top, x='업종명', y='폐업비율', color='폐업비율',
                      title=f"안정성이 높은 TOP {survival_n} 업종 (창업 {min_startups}건 이상)",
                      labels={'폐업비율': '창업 대비 폐업 비율 (%)'},
                      color_continuous_scale='RdYlGn_r')
        st.plotly_chart(fig3, use_container_width=True)

    # 4. 팬데믹 전후 비교 섹션
    with st.expander("🦠 4. 팬데믹 전후 비즈니스 트렌드 변화", expanded=True):
        st.subheader("비교 기간 설정")
        col1, col2 = st.columns(2)
        with col1:
            pre_years = st.multiselect("팬데믹 이전 연도 선택", options=range(2010, 2021), default=[2017, 2018, 2019])
        with col2:
            post_years = st.multiselect("팬데믹 이후 연도 선택", options=range(2021, 2026), default=[2021, 2022, 2023])
            
        if pre_years and post_years:
            pre_avg = data_raw[data_raw['Year'].isin(pre_years)].groupby('업종명')[['창업수', '폐업수']].mean().reset_index()
            post_avg = data_raw[data_raw['Year'].isin(post_years)].groupby('업종명')[['창업수', '폐업수']].mean().reset_index()
            
            p_merge = pd.merge(pre_avg, post_avg, on='업종명', suffixes=('_전', '_후'))
            p_merge['변화량'] = p_merge['창업수_후'] - p_merge['창업수_전']
            
            display_n = st.slider("표시할 변화량 상위 업종 수", 5, 30, 15)
            p_top = p_merge.sort_values(by='변화량', key=abs, ascending=False).head(display_n)
            
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(name='이전 평균', x=p_top['업종명'], y=p_top['창업수_전']))
            fig4.add_trace(go.Bar(name='이후 평균', x=p_top['업종명'], y=p_top['창업수_후']))
            fig4.update_layout(title=f"팬데믹 전후 연평균 창업수 변화 (상위 {display_n}개)", barmode='group')
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.warning("비교할 연도를 최소 하나 이상 선택해 주세요.")

    # 5. 계절성 및 시간별 패턴 섹션
    with st.expander("🌖 5. 시계열 창업/폐업 패턴 분석", expanded=True):
        st.subheader("분석 대상 업종 및 시간 단위 설정")
        col1, col2 = st.columns(2)
        with col1:
            all_unique = ["전체"] + sorted(list(data_raw['업종명'].unique()))
            target_ind = st.selectbox("업종 선택 (미리보기 지원)", all_unique, key="ind_select")
        with col2:
            time_unit = st.radio("시간 단위 선택", ("월별 (Month)", "년별 (Year)"), horizontal=True)
        
        if target_ind == "전체":
            m_df = data_raw
        else:
            m_df = data_raw[data_raw['업종명'] == target_ind]
            
        group_col = 'Month' if "월별" in time_unit else 'Year'
        unit_label = '월' if "월별" in time_unit else '연도'
        
        time_stats = m_df.groupby(group_col)[['창업수', '폐업수']].sum().reset_index()
        
        fig5 = px.bar(time_stats, x=group_col, y=['창업수', '폐업수'], barmode='group',
                      title=f"[{target_ind}] 기준 {unit_label} 누적 패턴",
                      labels={'value': '건수', group_col: unit_label})
        
        if group_col == 'Month':
            fig5.update_layout(xaxis=dict(tickmode='linear', tick0=1, dtick=1))
        
        st.plotly_chart(fig5, use_container_width=True)

else:
    st.info("데이터를 불러오는 데 실패했습니다.")
