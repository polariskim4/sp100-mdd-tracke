import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
import io
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="S&P 100 실시간 MDD 분석", page_icon="📈", layout="wide")

# 2. 실시간 S&P 100 티커 리스트 가져오기
@st.cache_data(ttl=86400)
def get_sp100_tickers():
    url = "https://en.wikipedia.org/wiki/S%26P_100"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html_data = io.StringIO(response.text)
        tables = pd.read_html(html_data)
        df = next((table for table in tables if 'Symbol' in table.columns), None)
        if df is not None:
            return sorted(df['Symbol'].str.replace('.', '-', regex=False).tolist())
        else:
            raise ValueError("Table not found")
    except Exception as e:
        st.error(f"리스트 갱신 실패: {e}")
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "UNH", "LLY"]

# 3. 데이터 분석 함수
@st.cache_data(ttl=3600)
def fetch_analysis(years):
    tickers = get_sp100_tickers()
    # 주가 데이터 일괄 다운로드
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    
    results = []
    
    for t in tickers:
        try:
            close_series = data['Close'][t].dropna()
            if len(close_series) < 10: continue
            
            high_val = data['High'][t].max()
            low_val = data['Low'][t].min()
            current_val = close_series.iloc[-1]
            
            # 지표 계산
            mdd = ((current_val - high_val) / high_val) * 100
            rec = ((current_val - low_val) / low_val) * 100
            chg = ((current_val - close_series.iloc[0]) / close_series.iloc[0]) * 100
            score = round(abs(mdd) - rec, 1) 

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, 
                "현재가": current_val, 
                "고가/저가": f"${high_val:.2f} / ${low_val:.2f}", # 신규 추가
                "MDD": mdd, 
                "회복률": rec, 
                "수익률": chg, 
                "점수": score
            })
        except: continue
    return pd.DataFrame(results)

# 4. 메인 UI 및 출력
st.title("📈 실시간 S&P 100 우량주 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tab1, tab2, tab3 = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def render_tab(years):
    with st.spinner(f"{years}년 데이터 분석 중..."):
        df = fetch_analysis(years)
        if not df.empty:
            # 칼럼 순서 명시적 지정 (현재가 옆에 고가/저가 배치)
            display_cols = ["신호", "티커", "현재가", "고가/저가", "MDD", "회복률", "수익률", "점수"]
            
            st.dataframe(
                df[display_cols].sort_values("점수", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "현재가": st.column_config.NumberColumn(format="$%.2f"),
                    "고가/저가": st.column_config.TextColumn("기간 내 고가 / 저가"), # 텍스트 형식으로 출력
                    "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                    "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                    "수익률": st.column_config.NumberColumn(format="%.1f%%"),
                    "점수": st.column_config.NumberColumn(format="%.1f"),
                }
            )

with tab1: render_tab(1)
with tab2: render_tab(2)
with tab3: render_tab(3)
