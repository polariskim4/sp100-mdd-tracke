import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
import io
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="S&P 100 실시간 MDD 분석", page_icon="📈", layout="wide")

# 2. 실시간 S&P 100 티커 리스트 가져오기 (User-Agent 추가로 403 방지)
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
    # 시총 조회를 위한 전체 Tickers 객체 생성 (속도 향상)
    tickers_obj = yf.Tickers(' '.join(tickers))
    
    for t in tickers:
        try:
            close_series = data['Close'][t].dropna()
            if len(close_series) < 10: continue
            
            high_val = data['High'][t].max()
            low_val = data['Low'][t].min()
            current_val = close_series.iloc[-1]
            
            mdd = ((current_val - high_val) / high_val) * 100
            rec = ((current_val - low_val) / low_val) * 100
            chg = ((current_val - close_series.iloc[0]) / close_series.iloc[0]) * 100
            score = round(abs(mdd) - rec, 1) # 점수 소수점 첫째자리 통일
            
            # --- 시가총액 수집 강화 로직 ---
            mkt_cap = 0
            t_info = tickers_obj.tickers[t].info
            
            # marketCap 키값을 먼저 찾고, 없으면 다른 유사 키값 시도
            mkt_cap = t_info.get('marketCap') or t_info.get('totalAssets') or 0
            
            # 여전히 0이라면 fast_info로 마지막 시도
            if not mkt_cap:
                try:
                    mkt_cap = tickers_obj.tickers[t].fast_info.get('market_cap', 0)
                except:
                    mkt_cap = 0
            # ---------------------------

            mkt_cap_bn = round(mkt_cap / 1e9, 1) if mkt_cap else 0

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, "현재가": current_val, "MDD": mdd, 
                "회복률": rec, "수익률": chg, "점수": score, "시총($B)": mkt_cap_bn
            })
        except: continue
    return pd.DataFrame(results)

# 4. 메인 UI 및 출력
st.title("📈 실시간 S&P 100 우량주 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tab1, tab2, tab3 = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def render_tab(years):
    with st.spinner(f"{years}년 데이터 및 시가총액 분석 중..."):
        df = fetch_analysis(years)
        if not df.empty:
            st.dataframe(
                df.sort_values("점수", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "현재가": st.column_config.NumberColumn(format="$%.2f"),
                    "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                    "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                    "수익률": st.column_config.NumberColumn(format="%.1f%%"),
                    "점수": st.column_config.NumberColumn(format="%.1f"),
                    "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
                }
            )

with tab1: render_tab(1)
with tab2: render_tab(2)
with tab3: render_tab(3)
