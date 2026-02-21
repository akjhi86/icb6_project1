"""
서울 저가 커피 브랜드 카페 입지 분석 대시보드
Streamlit 버전 - dashboard_data.json 기반
"""

import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ──────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="서울 카페 입지 분석",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# 데이터 로드
# ──────────────────────────────────────────────
@st.cache_data
def load_data():
    """dashboard_data.json 및 p_v2/detailed_analysis.json 로드 (캐시)"""
    json_path = os.path.join(os.path.dirname(__file__), "dashboard_data.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 신규 상세 지표 로드
    detailed_json_path = os.path.join(os.path.dirname(__file__), "detailed_analysis.json")
    detailed_data = {}
    if os.path.exists(detailed_json_path):
        with open(detailed_json_path, "r", encoding="utf-8") as f:
            detailed_data = json.load(f)

    # 행정동 DataFrame
    df_dong = pd.DataFrame(data["dong_data"])
    
    # 상세 지표 병합
    def get_detailed_metric(row, metric):
        name = row['dong_name'].replace('·', '').replace('.', '').replace('•', '').strip()
        return detailed_data.get(name, {}).get(metric, 0)

    if detailed_data:
        metrics_to_add = [
            'opportunity_score', 'penetration_rate', 'peak_sales_ratio', 
            'weekday_sales_ratio', 'avg_op_days', 'closure_rate', 'competition_intensity',
            'penetration_score', 'commercial_index'
        ]
        for m in metrics_to_add:
            df_dong[m] = df_dong.apply(lambda r: get_detailed_metric(r, m), axis=1)

    # 브랜드 컬럼 분리
    brands_df = pd.json_normalize(df_dong["brands"])
    brands_df.columns = [f"cnt_{c}" for c in brands_df.columns]
    df_dong = pd.concat([df_dong.drop(columns=["brands"]), brands_df], axis=1)

    # 지도 포인트 DataFrame
    df_map = pd.DataFrame(data["map_points"])
    
    # 지도 포인트에 행정동 이름 머지 (필터링용)
    if not df_map.empty and 'dong_name' not in df_map.columns:
        df_map = pd.merge(
            df_map, 
            df_dong[['dong_code', 'dong_name']], 
            on='dong_code', 
            how='left'
        )

    # 추천 DataFrame
    df_rec = pd.DataFrame(data["recommend_top"])

    return data, df_dong, df_map, df_rec

data, df_dong, df_map, df_rec = load_data()

BRANDS      = data["brands"]
BRAND_COLORS = data["brand_colors"]
BRAND_STATS  = data["brand_stats"]

# ──────────────────────────────────────────────
# 테마 및 가이드 설정
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎨 테마 설정")
    theme_mode = st.radio("테마 선택", ["Light", "Dark"], horizontal=True, label_visibility="collapsed")
    st.divider()

is_light = (theme_mode == "Light")

# 테마별 색상 정의
THEME = {
    "bg": "#f8f9fa" if is_light else "#0d1117",
    "surface": "#ffffff" if is_light else "#161b22",
    "surface2": "#f1f3f5" if is_light else "#21262d",
    "border": "#dee2e6" if is_light else "#30363d",
    "text": "#212529" if is_light else "#e6edf3",
    "text_sub": "#495057" if is_light else "#8b949e",
    "accent": "#005cc5" if is_light else "#58a6ff",
    "shadow": "rgba(0, 0, 0, 0.08)" if is_light else "rgba(0, 0, 0, 0.4)",
}

# 라이트 모드 시인성 확보를 위한 브랜드 색상
ADJUSTED_BRAND_COLORS = {}
for b, c in data["brand_colors"].items():
    if is_light:
        # 주요 브랜드 시인성 보정
        manual_colors = {
            "더벤티": "#d12d2d", "매머드커피": "#09a39a", "메가커피": "#b18e00",
            "빽다방": "#2e8b57", "컴포즈커피": "#8a63d2", "이디야": "#1e40af", "바나프레소": "#ef4444"
        }
        ADJUSTED_BRAND_COLORS[b] = manual_colors.get(b, c)
    else:
        ADJUSTED_BRAND_COLORS[b] = c

# ──────────────────────────────────────────────
# 커스텀 CSS
# ──────────────────────────────────────────────
st.markdown(f"""
<style>
/* 전체 배경 */
[data-testid="stAppViewContainer"] {{ background: {THEME["bg"]}; color: {THEME["text"]}; }}
[data-testid="stSidebar"] {{ background: {THEME["surface"]}; border-right: 1px solid {THEME["border"]}; }}
[data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}

/* 텍스트 색상 강제 적용 */
h1, h2, h3, h4, h5, h6, p, span, label, div {{ color: {THEME["text"]}; }}
.stMarkdown p {{ color: {THEME["text"]}; }}

/* 헤더 */
.main-header {{
    background: {THEME["surface"]};
    background-image: linear-gradient(135deg, {THEME["surface"]}, {THEME["bg"]});
    border: 1px solid {THEME["border"]};
    border-radius: 12px;
    padding: 24px 32px;
    margin-bottom: 24px;
    box-shadow: 0 4px 15px {THEME["shadow"]};
    text-align: center;
}}
.main-header h1 {{
    font-size: 1.8rem; font-weight: 900;
    background: linear-gradient(90deg, {THEME["accent"]}, #8a63d2);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0;
}}
.main-header p {{ color: {THEME["text_sub"]}; margin: 8px 0 0; font-size: .9rem; font-weight: 500; }}

/* 브랜드 카드 */
.brand-card {{
    background: {THEME["surface"]};
    border: 1px solid {THEME["border"]};
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 8px {THEME["shadow"]};
}}
.brand-name {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 8px; }}
.brand-val  {{ font-size: 1.8rem; font-weight: 900; }}
.brand-sub  {{ font-size: .72rem; color: {THEME["text_sub"]}; }}

/* 메트릭 카드 */
[data-testid="metric-container"] {{
    background: {THEME["surface"]} !important;
    border: 1px solid {THEME["border"]} !important;
    border-radius: 10px !important;
    padding: 14px !important;
    box-shadow: 0 2px 6px {THEME["shadow"]} !important;
}}

/* 점수 설명 카드 */
.stp-card {{
    background: {THEME["surface"]};
    border-radius: 10px;
    padding: 16px;
    border: 1px solid {THEME["border"]};
    border-left: 4px solid var(--stp-color, {THEME["accent"]});
    box-shadow: 0 2px 8px {THEME["shadow"]};
}}
.stp-name  {{ font-size: .9rem; font-weight: 800; margin-bottom: 10px; }}
.stp-formula {{
    font-family: 'Roboto Mono', monospace;
    font-size: .75rem;
    font-weight: 700;
    background: {THEME["surface2"]};
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 10px;
    line-height: 1.6;
    white-space: pre-line;
    color: {THEME["text"]};
    border: 1px dashed {THEME["border"]};
}}
.stp-note {{ font-size: .72rem; color: {THEME["text_sub"]}; line-height: 1.6; font-weight: 500; }}

/* 지도 툴팁 스타일 수정 */
.deckgl-tooltip {{
    background: {THEME["surface"]} !important;
    color: {THEME["text"]} !important;
    border: 1px solid {THEME["border"]} !important;
    font-weight: 500;
}}

/* 탭 바 텍스트 강화 */
[data-testid="stMarkdownContainer"] p {{
    font-weight: 500;
}}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Plotly 공통 레이아웃
# ──────────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor=THEME["surface"],
    plot_bgcolor=THEME["surface"],
    font=dict(color=THEME["text"], family="Noto Sans KR"),
    margin=dict(l=10, r=10, t=30, b=10),
)
GRID_STYLE = dict(gridcolor=THEME["border"], zerolinecolor=THEME["border"])

# ──────────────────────────────────────────────
# 헤더
# ──────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>☕ 서울 저가 커피 브랜드 입지 분석</h1>
  <p>행정동별 브랜드 현황 · 매출 분석 · 입지 추천 | 더벤티 · 매머드커피 · 메가커피 · 빽다방 · 컴포즈커피</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────────
with st.sidebar:
    st.divider()

    st.markdown("### 🔍 필터")
    selected_tab = st.radio(
        "분석 메뉴",
        ["📊 브랜드 개요", "🗺️ 지도", "🏙️ 행정동 분석", "📊 분석 시각화", "⭐ 입지 추천"],
        label_visibility="collapsed",
    )
    st.divider()

    if selected_tab == "🏙️ 행정동 분석":
        all_dongs = sorted(df_dong["dong_name"].unique())
        dong_search = st.selectbox("🏙️ 행정동 선택", ["전체"] + all_dongs)
        brand_filter = st.selectbox("브랜드 필터", ["전체"] + BRANDS)
        sort_by = st.selectbox(
            "정렬 기준",
            ["total_brand_count", "attractiveness_score", "monthly_sales", "opportunity_score", "penetration_rate", "peak_sales_ratio", "closure_rate"],
            format_func=lambda x: {
                "total_brand_count": "총 브랜드 수",
                "attractiveness_score": "매력도 점수",
                "monthly_sales": "월 매출",
                "opportunity_score": "기회 지수 (종사자/저가카페)",
                "penetration_rate": "저가 브랜드 침투율",
                "peak_sales_ratio": "피크 시간 매출 비중",
                "closure_rate": "폐업률",
            }[x],
        )

    elif selected_tab == "⭐ 입지 추천":
        rec_brand = st.selectbox("브랜드 선택", ["전체"] + BRANDS)
        rec_sort = st.selectbox(
            "정렬 기준",
            ["attractiveness_score", "demand_score", "cost_score"],
            format_func=lambda x: {
                "attractiveness_score": "매력도 점수",
                "demand_score": "수요 점수",
                "cost_score": "비용 점수",
            }[x],
        )
        all_dongs = sorted(df_dong["dong_name"].unique())
        rec_search = st.selectbox("🏙️ 행정동 선택", ["전체"] + all_dongs)

    elif selected_tab == "🗺️ 지도":
        map_brands = st.multiselect(
            "표시할 브랜드",
            BRANDS,
            default=BRANDS,
        )
        all_dongs = sorted(df_dong["dong_name"].unique())
        map_dongs = st.multiselect(
            "📍 행정동 선택",
            all_dongs,
            placeholder="동 이름을 선택하세요 (미선택 시 전체)",
            help="선택한 행정동의 매장만 지도에 표시합니다."
        )

    st.divider()
    st.caption(f"행정동 {len(df_dong)}개 · 매장 {len(df_map):,}개")

    # 점수 계산 방법 설명 (항상 접근 가능)
    with st.expander("❓ 점수 계산 방법"):
        st.markdown("""
**Min-Max 정규화(0~1)** 후 3가지 점수를 가중 합산합니다.

| 점수 | 공식 | 의미 |
|---|---|---|
| 📈 **수요** | (정규화_매출×0.5 + 정규화_종사자×0.5)×100 | 높을수록 ↑ |
| ⚔️ **경쟁** | (1 − 정규화_카페수)×100 | 카페 적을수록 ↑ |
| 💰 **비용** | (1 − 정규화_부동산가)×100 | 임대료 낮을수록 ↑ |
| ⭐ **매력도** | 수요×0.4 + 경쟁×0.3 + 비용×0.3 | 종합 입지 지수 |
        """)

# ══════════════════════════════════════════════
# 탭 1: 브랜드 개요
# ══════════════════════════════════════════════
if selected_tab == "📊 브랜드 개요":

    # 브랜드 카드 (5개)
    cols = st.columns(5)
    for i, brand in enumerate(BRANDS):
        if i >= 5: break # 상위 5개만 카드로 표시하거나 레이아웃 조정 필요할 수 있음
        s = BRAND_STATS[brand]
        color = ADJUSTED_BRAND_COLORS[brand]
        with cols[i]:
            avg = s.get('avg_monthly_sales', 0)
            avg_str = f"{avg:,}만" if avg else '-'
            st.markdown(f"""
            <div class="brand-card" style="border-top:3px solid {color}">
              <div class="brand-name" style="color:{color}">{brand}</div>
              <div class="brand-val">{s['total_stores']:,}</div>
              <div class="brand-sub">총 매장 수</div>
              <hr style="border-color:#30363d;margin:8px 0">
              <div style="font-size:1.1rem;font-weight:700">{s['dong_count']}</div>
              <div class="brand-sub">진출 행정동</div>
              <hr style="border-color:#30363d;margin:8px 0">
              <div style="font-size:1.1rem;font-weight:700;color:{color}">{avg_str}</div>
              <div class="brand-sub">점포당 평균월매출</div>
            </div>
            """, unsafe_allow_html=True)


    st.markdown("<br>", unsafe_allow_html=True)

    # 차트 행 1
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### 브랜드별 총 매장 수")
        fig = go.Figure(go.Bar(
            x=BRANDS,
            y=[BRAND_STATS[b]["total_stores"] for b in BRANDS],
            marker_color=[ADJUSTED_BRAND_COLORS[b] for b in BRANDS],
            text=[BRAND_STATS[b]["total_stores"] for b in BRANDS],
            textposition="outside",
        ))
        fig.update_layout(**PLOT_LAYOUT, height=300)
        fig.update_xaxes(**GRID_STYLE)
        fig.update_yaxes(**GRID_STYLE)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("##### 브랜드별 진출 행정동 수")
        fig = go.Figure(go.Pie(
            labels=BRANDS,
            values=[BRAND_STATS[b]["dong_count"] for b in BRANDS],
            marker_colors=[ADJUSTED_BRAND_COLORS[b] for b in BRANDS],
            hole=0.45,
            textinfo="label+percent",
        ))
        fig.update_layout(**PLOT_LAYOUT, height=300,
            legend=dict(orientation="h", y=-0.1),
        )
        st.plotly_chart(fig, use_container_width=True)

    # 차트 행 2: 상위 30개 동 누적 막대
    st.markdown("##### 행정동별 브랜드 분포 (총 브랜드 수 상위 30개 동)")
    top30 = df_dong[df_dong["total_brand_count"] > 0].nlargest(30, "total_brand_count")
    fig = go.Figure()
    for brand in BRANDS:
        col = f"cnt_{brand}"
        if col in top30.columns:
            fig.add_trace(go.Bar(
                name=brand,
                x=top30["dong_name"],
                y=top30[col],
                marker_color=ADJUSTED_BRAND_COLORS[brand],
            ))
    fig.update_layout(
        **PLOT_LAYOUT, barmode="stack", height=350,
        legend=dict(orientation="h", y=1.05),
    )
    fig.update_xaxes(tickangle=-40, **GRID_STYLE)
    fig.update_yaxes(**GRID_STYLE)
    st.plotly_chart(fig, use_container_width=True)

    # 차트 행 3: 연령대별 매출
    st.markdown("##### 연령대별 총 매출 합계")
    age_cols  = ["age_10","age_20","age_30","age_40","age_50","age_60"]
    age_labels = ["10대","20대","30대","40대","50대","60대+"]
    age_colors = ["#FF6B6B","#FFE66D","#4ECDC4","#58a6ff","#bc8cff","#A8E6CF"]
    age_totals = [df_dong[c].sum() / 1e8 for c in age_cols]

    fig = go.Figure(go.Bar(
        x=age_labels, y=age_totals,
        marker_color=age_colors,
        text=[f"{v:.0f}억" for v in age_totals],
        textposition="outside",
    ))
    fig.update_layout(**PLOT_LAYOUT, height=300)
    fig.update_xaxes(**GRID_STYLE)
    fig.update_yaxes(title="매출(억원)", **GRID_STYLE)
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════
# 탭 2: 지도
# ══════════════════════════════════════════════
elif selected_tab == "🗺️ 지도":
    st.markdown("##### 📍 저가 커피 브랜드 매장 위치")

    # 필터링 (브랜드 + 행정동)
    filtered_map = df_map[df_map["brand"].isin(map_brands)] if map_brands else df_map.iloc[0:0]
    
    if map_dongs:
        filtered_map = filtered_map[filtered_map["dong_name"].isin(map_dongs)]

    if filtered_map.empty:
        st.warning("표시할 브랜드를 사이드바에서 선택하세요.")
    else:
        # 색상 컬럼 추가 (hex → RGB)
        def hex_to_rgb(h):
            h = h.lstrip("#")
            return [int(h[i:i+2], 16) for i in (0, 2, 4)] + [200]

        filtered_map = filtered_map.copy()
        filtered_map["color"] = filtered_map["brand"].map(
            lambda b: hex_to_rgb(ADJUSTED_BRAND_COLORS.get(b, "#888888"))
        )

        import pydeck as pdk
        
        # 지도 중심 결정 (선택한 동이 하나라면 해당 동의 평균 위치로)
        if map_dongs and not filtered_map.empty:
            lat_center = filtered_map["lat"].mean()
            lng_center = filtered_map["lng"].mean()
            zoom_level = 13
        else:
            lat_center = 37.5665
            lng_center = 126.9780
            zoom_level = 10.5

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=filtered_map,
            get_position=["lng", "lat"],
            get_fill_color="color",
            get_radius=80,
            pickable=True,
            auto_highlight=True,
        )
        view = pdk.ViewState(latitude=lat_center, longitude=lng_center, zoom=zoom_level, pitch=0)
        tooltip = {"html": "<b>{brand}</b><br>{name}", "style": {"background": THEME["surface"], "color": THEME["text"]}}

        st.pydeck_chart(pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip=tooltip,
            map_style="light" if is_light else "dark",
        ))

        # 브랜드별 매장 수 요약
        st.markdown("---")
        summary_cols = st.columns(len(map_brands))
        brand_counts = filtered_map["brand"].value_counts()
        for i, brand in enumerate(map_brands):
            cnt = brand_counts.get(brand, 0)
            color = ADJUSTED_BRAND_COLORS[brand]
            with summary_cols[i]:
                st.markdown(f"""
                <div style="text-align:center;padding:12px;background:{THEME['surface']};
                     border:1px solid {THEME['border']};border-radius:10px;border-top:3px solid {color};
                     box-shadow:0 2px 6px {THEME['shadow']}">
                  <div style="color:{color};font-weight:700;font-size:1rem">{brand}</div>
                  <div style="font-size:1.6rem;font-weight:900;color:{THEME['text']}">{cnt}</div>
                </div>
                """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# 탭 3: 행정동 분석
# ══════════════════════════════════════════════
elif selected_tab == "🏙️ 행정동 분석":

    # 필터 적용
    df_view = df_dong.copy()
    if dong_search != "전체":
        df_view = df_view[df_view["dong_name"] == dong_search]
    if brand_filter != "전체":
        col = f"cnt_{brand_filter}"
        if col in df_view.columns:
            df_view = df_view[df_view[col] > 0]
    df_view = df_view.sort_values(sort_by, ascending=False, na_position="last")

    st.markdown(f"##### 행정동 분석 — {len(df_view)}개 동")

    # 표시 컬럼 선택
    display_cols = ["dong_name"] + [f"cnt_{b}" for b in BRANDS] + \
                   ["total_brand_count", "attractiveness_score", "monthly_sales", "total_workers"]
    display_cols = [c for c in display_cols if c in df_view.columns]

    rename_map = {"dong_name": "행정동"}
    for b in BRANDS:
        rename_map[f"cnt_{b}"] = b
    rename_map.update({
        "total_brand_count": "합계",
        "attractiveness_score": "매력도",
        "monthly_sales": "월매출(억)",
        "total_workers": "근로자",
    })

    show_df = df_view[display_cols].rename(columns=rename_map).head(200).copy()
    if "월매출(억)" in show_df.columns:
        show_df["월매출(억)"] = (show_df["월매출(억)"] / 1e8).round(1)
    if "매력도" in show_df.columns:
        show_df["매력도"] = show_df["매력도"].round(1)

    # 테이블 표시 (1단)
    selected_rows = st.dataframe(
        show_df,
        use_container_width=True,
        height=400,
        on_select="rerun",
        selection_mode="single-row",
    )

    # 선택 행 상세 (아래에 표시)
    sel_idx = selected_rows.selection.get("rows", []) if selected_rows else []
    if sel_idx:
        row_idx = df_view.index[sel_idx[0]]
        d = df_dong.loc[row_idx]

        st.markdown(f"#### {d['dong_name']}")

        m1, m2 = st.columns(2)
        m1.metric("매력도 점수", f"{d['attractiveness_score']:.1f}" if pd.notna(d.get('attractiveness_score')) else "-")
        m2.metric("수요 점수",   f"{d['demand_score']:.1f}"        if pd.notna(d.get('demand_score'))        else "-")
        m3, m4 = st.columns(2)
        m3.metric("경쟁 점수",   f"{d['competition_score']:.1f}"   if pd.notna(d.get('competition_score'))   else "-")
        m4.metric("비용 점수",   f"{d['cost_score']:.1f}"          if pd.notna(d.get('cost_score'))          else "-")

        st.markdown("---")
        st.markdown(f"**근로자** {int(d.get('total_workers',0)):,}명 (여성 {int(d.get('female_workers',0)):,}명)")
        st.markdown(f"**카페 수** {int(d.get('cafe_count',0))}개")
        st.markdown(f"**월 매출** {d.get('monthly_sales',0)/1e8:.1f}억원")

        # 브랜드 현황
        st.markdown("**브랜드별 매장 분포**")
        brand_counts_dong = []
        for brand in BRANDS:
            cnt = int(d.get(f"cnt_{brand}", 0))
            if cnt > 0:
                brand_counts_dong.append({"브랜드": brand, "매장수": cnt})
        
        if brand_counts_dong:
            df_brand_dong = pd.DataFrame(brand_counts_dong).sort_values("매장수", ascending=True)
            fig = px.bar(df_brand_dong, x="매장수", y="브랜드", orientation='h',
                         color="브랜드", color_discrete_map=ADJUSTED_BRAND_COLORS,
                         text_auto=True)
            # 매장 수에 따라 높이 유동적 조절
            chart_height = max(150, len(df_brand_dong) * 30)
            fig.update_layout(**PLOT_LAYOUT, height=chart_height, showlegend=False,
                              margin=dict(l=0, r=20, t=10, b=10))
            fig.update_xaxes(title=None, **GRID_STYLE)
            fig.update_yaxes(title=None, **GRID_STYLE)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("해당 지역에 진출한 브랜드가 없습니다.")

        # 연령대 차트
        st.markdown("**연령대별 매출**")
        age_vals = [d.get(c, 0) / 1e6 for c in ["age_10","age_20","age_30","age_40","age_50","age_60"]]
        fig = go.Figure(go.Bar(
            x=["10대","20대","30대","40대","50대","60대+"],
            y=age_vals,
            marker_color=["#FF6B6B","#FFE66D","#4ECDC4","#58a6ff","#bc8cff","#A8E6CF"],
        ))
        fig.update_layout(**PLOT_LAYOUT, height=220)
        fig.update_xaxes(**GRID_STYLE)
        fig.update_yaxes(title="백만원", **GRID_STYLE)
        st.plotly_chart(fig, use_container_width=True)

        # ── 상세 분석 지표 (Advanced Metrics) ──
        st.markdown("---")
        st.markdown("#### 📊 상세 분석 지표")
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            opp_score = d.get('opportunity_score', 0)
            st.metric("기회 지수", f"{opp_score:,.1f}", help="매장당 종사자 수. 높을수록 잠재 수요 대비 경쟁이 적음을 의미")
        with m2:
            pen_rate = d.get('penetration_rate', 0)
            st.metric("저가 브랜드 침투율", f"{pen_rate:.1f}%", help="전체 카페 수 대비 저가 브랜드 비중")
        with m3:
            peak_ratio = d.get('peak_sales_ratio', 0)
            st.metric("피크 시간 매출 비중", f"{peak_ratio:.1f}%", help="06~14시 매출이 전체에서 차지하는 비중")
        with m4:
            closure_rate = d.get('closure_rate', 0)
            st.metric("폐업률", f"{closure_rate:.1f}%", help="해당 지역 카페들의 전체 대비 폐업 매장 비율")
        
        m5, m6, m7, m8 = st.columns(4)
        with m5:
            weekday_ratio = d.get('weekday_sales_ratio', 0)
            st.metric("주중 매출 비중", f"{weekday_ratio:.1f}%")
        with m6:
            avg_op = d.get('avg_op_days', 0) / 365
            st.metric("평균 영업 기간", f"{avg_op:.1f}년")
        with m7:
            comp_intensity = d.get('competition_intensity', 0)
            st.metric("경쟁 강도", f"{comp_intensity:.1f}", help="종사자 100명당 카페 수")
        with m8:
            total_workers_val = d.get('total_workers', 0)
            st.metric("총 종사자 수", f"{total_workers_val:,.0f}명")

        # ── 점수 계산 방법 설명 ──
        st.markdown("---")
        st.markdown("#### 📐 가중치 및 평가 지수")
        st.caption("서울 행정동별 데이터를 **Min-Max 정규화(0~1)** 한 후 가중 합산한 결과입니다.")
        
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.markdown(f"""
            <div class="stp-card" style="--stp-color:#4ECDC4">
              <div class="stp-name" style="color:#4ECDC4">📈 수요 점수</div>
              <div class="stp-formula">(정규화_매출 × 0.5\\n+ 정규화_종사자 × 0.5)\\n× 100</div>
              <div class="stp-note">월매출 + 종사자수를 동등 반영. 높을수록 ↑</div>
            </div>
            """, unsafe_allow_html=True)
        with sc2:
            st.markdown(f"""
            <div class="stp-card" style="--stp-color:#FFE66D">
              <div class="stp-name" style="color:#FFE66D">⚔️ 경쟁 점수</div>
              <div class="stp-formula">(1 − 정규화_카페수)\\n× 100</div>
              <div class="stp-note">카페 수 적을수록 ↑ (반비례)</div>
            </div>
            """, unsafe_allow_html=True)
        with sc3:
            st.markdown(f"""
            <div class="stp-card" style="--stp-color:#A8E6CF">
              <div class="stp-name" style="color:#A8E6CF">💰 비용 점수</div>
              <div class="stp-formula">(1 − 정규화_부동산가)\\n× 100</div>
              <div class="stp-note">m² 당 부동산가 낮을수록 ↑ (반비례)</div>
            </div>
            """, unsafe_allow_html=True)
        with sc4:
            st.markdown(f"""
            <div class="stp-card" style="--stp-color:{THEME['accent']}">
              <div class="stp-name" style="color:{THEME['accent']}">⭐ 종합 매력도</div>
              <div class="stp-formula">수요 × 0.4\\n+ 경쟁 × 0.3\\n+ 비용 × 0.3</div>
              <div class="stp-note">유동인구 많고 · 경쟁 적고 · 임대료 저렴할수록 ↑</div>
            </div>
            """, unsafe_allow_html=True)

        sc5, sc6, sc7, sc8 = st.columns(4)
        with sc5:
            st.markdown(f"""
            <div class="stp-card" style="--stp-color:#FF6B6B">
              <div class="stp-name" style="color:#FF6B6B">🎯 기회 지수</div>
              <div class="stp-formula">총 종사자 수\\n÷ 저가 커피 매장 수</div>
              <div class="stp-note">잠재 고객 대비 경쟁 정도. 높을수록 유리</div>
            </div>
            """, unsafe_allow_html=True)
        with sc6:
            st.markdown(f"""
            <div class="stp-card" style="--stp-color:#bc8cff">
              <div class="stp-name" style="color:#bc8cff">📉 브랜드 침투율</div>
              <div class="stp-formula">(저가 브랜드 수\\n÷ 전체 카페 수) × 100</div>
              <div class="stp-note">저가 브랜드의 시장 점유율 (%)</div>
            </div>
            """, unsafe_allow_html=True)
        with sc7:
            st.markdown(f"""
            <div class="stp-card" style="--stp-color:#FF9F43">
              <div class="stp-name" style="color:#FF9F43">⏰ 피크 매출 비중</div>
              <div class="stp-formula">(06~14시 매출\\n÷ 총 매출) × 100</div>
              <div class="stp-note">출근/점심 시간대 수요 집중도 (%)</div>
            </div>
            """, unsafe_allow_html=True)
        with sc8:
            st.markdown(f"""
            <div class="stp-card" style="--stp-color:#10AC84">
              <div class="stp-name" style="color:#10AC84">⚠️ 폐업률</div>
              <div class="stp-formula">(폐업 매장 수\\n÷ 전체 매장 수) × 100</div>
              <div class="stp-note">지역 내 카페의 생존 안정성 (%)</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("👆 테이블에서 행을 클릭하면 상세 정보가 표시됩니다.")


# ══════════════════════════════════════════════
# 탭 3.5: 행정동분석_차트
# ══════════════════════════════════════════════
elif selected_tab == "📊 분석 시각화":
    st.markdown("##### 📊 데이터 기반 심층 분석 시각화")
    st.caption("서울시 행정동별 핵심 지표를 6가지 관점에서 분석하며, 각 브랜드별 현황을 비교합니다.")

    # ── 산식 및 설명 (Methodology) ──
    with st.expander("📐 지표 계산 산식 및 분석 방법론 확인", expanded=False):
        f1, f2, f3 = st.columns(3)
        with f1:
            st.markdown("""
            <div class="stp-card" style="--stp-color:#FF6B6B">
              <div class="stp-name" style="color:#FF6B6B">🎯 Opportunity Score</div>
              <div class="stp-formula">총 종사자 수 ÷ 저가카페 매장수</div>
              <div class="stp-note">공급(매장) 대비 수요(종사자) 불균형 지표. 높을수록 기회.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="stp-card" style="--stp-color:#4ECDC4">
              <div class="stp-name" style="color:#4ECDC4">⏰ 피크 시간 매출 비중</div>
              <div class="stp-formula">(06~14시 매출 ÷ 전체) × 100</div>
              <div class="stp-note">오피스 상권의 활동 집중도 파악 지표.</div>
            </div>
            """, unsafe_allow_html=True)
        with f2:
            st.markdown("""
            <div class="stp-card" style="--stp-color:#FFE66D">
              <div class="stp-name" style="color:#FFE66D">📈 저가 브랜드 점유율 (U)</div>
              <div class="stp-formula">저가 점유율 구간별 점수화</div>
              <div class="stp-note">0-3%:1점 | 3-15%:4점(최적) | 15%+:2점</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="stp-card" style="--stp-color:#58a6ff">
              <div class="stp-name" style="color:#58a6ff">📅 주중 매출 비중</div>
              <div class="stp-formula">주중 ÷ (주중 + 주말) × 100</div>
              <div class="stp-note">상권 성격(직장인 vs 주거/여가) 판별 지표.</div>
            </div>
            """, unsafe_allow_html=True)
        with f3:
            st.markdown("""
            <div class="stp-card" style="--stp-color:#bc8cff">
              <div class="stp-name" style="color:#bc8cff">⚔️ 지역별 경쟁 강도</div>
              <div class="stp-formula">반경 내 카페 수 ÷ 종사자 수</div>
              <div class="stp-note">종사자 대비 카페 밀집도. 낮을수록 유리.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="stp-card" style="--stp-color:#A8E6CF">
              <div class="stp-name" style="color:#A8E6CF">🔄 상권변화 지표</div>
              <div class="stp-formula">폐업률 & 매출 기반 분류</div>
              <div class="stp-note">다이나믹(4) / 확장(3) / 정체(2) / 축소(1)</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # 1. Opportunity Score (Brand Breakdown) & 2. 저가카페 점유율 점수
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("###### 1) Opportunity Score 및 지역별 브랜드 현황")
        top_opp = df_dong.nlargest(10, 'opportunity_score')
        
        # 브랜드별 데이터로 변환 (Stacked Bar용)
        # 상위 10개 지역에 존재하는 브랜드만 추출하여 레전드가 지저분해지는 것을 방지
        relevant_brands = [b for b in BRANDS if top_opp[f'cnt_{b}'].sum() > 0]
        brand_counts = []
        for brand in relevant_brands:
            brand_counts.append(go.Bar(
                name=brand, 
                x=top_opp['dong_name'], 
                y=top_opp[f'cnt_{brand}'],
                marker_color=ADJUSTED_BRAND_COLORS[brand]
            ))
        
        # 기회 점수 라인 차트 (Secondary Y axis)
        brand_counts.append(go.Scatter(
            name="Opportunity Score",
            x=top_opp['dong_name'],
            y=top_opp['opportunity_score'],
            yaxis="y2",
            line=dict(color="#FF6B6B", width=3, dash='dot'),
            mode="lines+markers+text",
            text=top_opp['opportunity_score'].round(0),
            textposition="top center"
        ))

        fig = go.Figure(data=brand_counts)
        fig.update_layout(
            **PLOT_LAYOUT, 
            height=350,
            barmode='stack',
            yaxis=dict(title="브랜드별 매장 수"),
            yaxis2=dict(title="기회 점수", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("###### 2) 저가카페 점유율 점수 분포 (U-Score)")
        score_counts = df_dong['penetration_score'].value_counts().sort_index()
        score_map = {1: "1점 (검증부족)", 4: "4점 (최적구간)", 2: "2점 (과밀경쟁)"}
        score_df = pd.DataFrame({
            '점수': [score_map.get(i, f"{i}점") for i in score_counts.index],
            '동 개수': score_counts.values
        })
        fig = px.bar(score_df, x='점수', y='동 개수', color='점수',
                     color_discrete_map={
                         "1점 (검증부족)": "#FF6B6B", 
                         "4점 (최적구간)": "#4ECDC4", 
                         "2점 (과밀경쟁)": "#FFE66D"
                     }, text_auto=True)
        fig.update_layout(**PLOT_LAYOUT, height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # 3. 피크 시간 & 4. 주중 매출 (브랜드 비교 요소 추가)
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("###### 3) 오피스 상권 집중도 (피크 시간 매출)")
        top_peak = df_dong.nlargest(10, 'peak_sales_ratio')
        fig = px.bar(top_peak, x='dong_name', y='peak_sales_ratio',
                     color='peak_sales_ratio', color_continuous_scale='Oranges',
                     text_auto='.1f')
        fig.update_layout(**PLOT_LAYOUT, height=300, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.markdown("###### 4) 평일 상권 집중도 (주중 매출 비중)")
        top_weekday = df_dong.nlargest(10, 'weekday_sales_ratio')
        fig = px.bar(top_weekday, x='dong_name', y='weekday_sales_ratio',
                     color='weekday_sales_ratio', color_continuous_scale='Blues',
                     text_auto='.1f')
        fig.update_layout(**PLOT_LAYOUT, height=300, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # 5. 경쟁 강도 & 6. 상권변화 (브랜드 비교 파이 차트)
    c5, c6 = st.columns(2)
    with c5:
        st.markdown("###### 5) 브랜드별 지역 점유율 비교 (전체)")
        total_counts = {b: df_dong[f"cnt_{b}"].sum() for b in BRANDS}
        share_df = pd.DataFrame({
            '브랜드': list(total_counts.keys()),
            '매장수': list(total_counts.values())
        })
        fig = px.pie(share_df, values='매장수', names='브랜드', 
                     color='브랜드', color_discrete_map=ADJUSTED_BRAND_COLORS,
                     hole=0.4)
        fig.update_layout(**PLOT_LAYOUT, height=350)
        st.plotly_chart(fig, use_container_width=True)

    with c6:
        st.markdown("###### 6) 상권변화 및 활력도 분포")
        change_map = {4: "다이나믹(4)", 3: "상권확장(3)", 2: "정체(2)", 1: "상권축소(1)"}
        change_counts = df_dong['commercial_index'].value_counts().sort_index(ascending=False)
        change_df = pd.DataFrame({
            '지표': [change_map.get(i, f"{i}") for i in change_counts.index],
            '동 개수': change_counts.values
        })
        fig = px.pie(change_df, values='동 개수', names='지표', hole=0.4,
                     color='지표', color_discrete_map={
                         "다이나믹(4)": "#4ECDC4", 
                         "상권확장(3)": "#58a6ff", 
                         "정체(2)": "#FFE66D", 
                         "상권축소(1)": "#FF6B6B"
                     })
        fig.update_layout(**PLOT_LAYOUT, height=350)
        st.plotly_chart(fig, use_container_width=True)

    # ──────────────────────────────────────────────
    # 📊 심층 통계 분석 (기존 차트 보강)
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("##### 🔬 다차원 분포 및 밀도 분석")
    
    c7, c8 = st.columns(2)
    with c7:
        st.markdown("###### 주요 지표 분포 (Box Plot)")
        box_df = df_dong.copy()
        box_df['월 매출(억)'] = box_df['monthly_sales'] / 1e8
        melt_df = box_df.melt(value_vars=['attractiveness_score', 'opportunity_score', '월 매출(억)'], 
                              var_name='지표', value_name='값')
        fig = px.box(melt_df, x='지표', y='값', color='지표', points="all")
        fig.update_layout(**PLOT_LAYOUT, height=380, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c8:
        st.markdown("###### 종사자-매출 밀도 Heatmap")
        dens_df = df_dong.copy()
        dens_df['sales_cr'] = dens_df['monthly_sales'] / 1e8
        fig = px.density_heatmap(dens_df, x='total_workers', y='sales_cr', 
                                 nbinsx=30, nbinsy=30, color_continuous_scale='Viridis',
                                 labels={'total_workers': '총 종사자 수', 'sales_cr': '월 매출(억)'},
                                 text_auto=True)
        fig.update_layout(**PLOT_LAYOUT, height=380, coloraxis_showscale=True)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("###### 카페 수와 매출의 상관관계 (Marginal Scatter)")
    scat_df = df_dong.copy()
    scat_df['sales_cr'] = scat_df['monthly_sales'] / 1e8
    fig = px.scatter(scat_df, x='cafe_count', y='sales_cr', 
                     marginal_x="box", marginal_y="violin",
                     hover_name='dong_name', color='attractiveness_score',
                     labels={'cafe_count': '행정동별 전체 카페 수', 'sales_cr': '월 매출(억)'},
                     opacity=0.7)
    fig.update_layout(**PLOT_LAYOUT, height=450)
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════
# 탭 4: 입지 추천
# ══════════════════════════════════════════════
elif selected_tab == "⭐ 입지 추천":

    # 필터
    df_r = df_rec.copy()
    if rec_brand != "전체":
        df_r = df_r[df_r["brand"] == rec_brand]
    if rec_search != "전체":
        df_r = df_r[df_r["dong_name"].str.contains(rec_search)]
    df_r = df_r.sort_values(rec_sort, ascending=False).head(60)

    st.markdown(f"##### ⭐ 입지 추천 — {len(df_r)}개 결과")
    st.caption("매력도 점수 기준 해당 브랜드가 **아직 진출하지 않은** 행정동을 추천합니다.")

    if df_r.empty:
        st.warning("조건에 맞는 추천 결과가 없습니다.")
    else:
        # 3열 카드 그리드
        for row_start in range(0, len(df_r), 3):
            cols = st.columns(3)
            for ci, idx in enumerate(range(row_start, min(row_start + 3, len(df_r)))):
                r = df_r.iloc[idx]
                color = BRAND_COLORS.get(r["brand"], "#888")
                score = r.get("attractiveness_score")
                score_color = "#4ECDC4" if score and score > 60 else "#FFE66D" if score and score > 40 else "#FF6B6B"

                with cols[ci]:
                    st.markdown(f"""
                    <div style="background:{THEME['surface']};border:1px solid {THEME['border']};border-radius:12px;
                         padding:18px;border-top:4px solid {color};margin-bottom:14px;box-shadow: 0 4px 10px {THEME['shadow']}">
                      <div style="font-size:.75rem;color:{THEME['text_sub']};font-weight:700">#{row_start+ci+1} 추천</div>
                      <div style="font-size:1.1rem;font-weight:800;margin:6px 0;color:{THEME['text']}">{r['dong_name']}</div>
                      <span style="background:{color}15;color:{ADJUSTED_BRAND_COLORS.get(r['brand'], color)};padding:3px 10px;
                            border-radius:12px;font-size:.78rem;font-weight:800;border:1px solid {color}30">{r['brand']}</span>
                      <span style="font-size:.75rem;color:{THEME['text_sub']};margin-left:8px;font-weight:600">미진출 지역</span>
                      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:16px">
                        <div style="background:{THEME['surface2']};border-radius:8px;padding:10px;border:1px solid {THEME['border']}">
                          <div style="font-size:.68rem;color:{THEME['text_sub']};font-weight:700">매력도</div>
                          <div style="font-size:1.2rem;font-weight:900;color:{score_color}">
                            {f"{score:.1f}" if score else "-"}
                          </div>
                        </div>
                        <div style="background:{THEME['surface2']};border-radius:8px;padding:10px;border:1px solid {THEME['border']}">
                          <div style="font-size:.68rem;color:{THEME['text_sub']};font-weight:700">수요</div>
                          <div style="font-size:1.2rem;font-weight:900;color:#00897b">
                            {f"{r['demand_score']:.1f}" if r.get('demand_score') else "-"}
                          </div>
                        </div>
                        <div style="background:{THEME['surface2']};border-radius:8px;padding:10px;border:1px solid {THEME['border']}">
                          <div style="font-size:.68rem;color:{THEME['text_sub']};font-weight:700">경쟁</div>
                          <div style="font-size:1.2rem;font-weight:900;color:#f57f17">
                            {f"{r['competition_score']:.1f}" if r.get('competition_score') else "-"}
                          </div>
                        </div>
                        <div style="background:{THEME['surface2']};border-radius:8px;padding:10px;border:1px solid {THEME['border']}">
                          <div style="font-size:.68rem;color:{THEME['text_sub']};font-weight:700">비용</div>
                          <div style="font-size:1.2rem;font-weight:900;color:#2e7d32">
                            {f"{r['cost_score']:.1f}" if r.get('cost_score') else "-"}
                          </div>
                        </div>
                      </div>
                      <div style="font-size:.8rem;color:{THEME['text']};margin-top:12px;font-weight:700;border-top:1px solid {THEME['border']};padding-top:8px">
                        근로자 {int(r.get('total_workers',0)):,}명 · 
                        카페 {int(r.get('cafe_count',0))}개 <br>
                        월평균 매출 <span style="color:#005cc5">{r.get('monthly_sales',0)/1e8:.1f}억 원</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
