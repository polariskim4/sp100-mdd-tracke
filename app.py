import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
import io
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="S&P 100 실시간 MDD 분석", page_icon="📈", layout="wide")

# 2. 실시간 S&P 100 티커 리스트 가져오기 (403 Forbidden 및 HTML 파싱 오류 방지)
@st.cache_data(ttl=86400)
def get_sp100_tickers():
    url = "https://en.wikipedia.org/wiki/S%26P_100"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        html_data = io.StringIO(response.text)
        tables = pd.read_html(html_data)
        
        df = next((table for table in tables if 'Symbol' in table.columns), None)
        
        if df is not None:
            # 점(.)을 하이픈(-)으로 변환 (예: BRK.B -> BRK-B)
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
    # 주가 데이터 일괄 다운로드 (속도 최적화)
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    
    results = []
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
            # 점수 계산: 소수점 첫째 자리로 통일
            score = round(abs(mdd) - rec, 1) 
            
            # 시가총액 정보 가져오기 (Fast Info 우선 사용)
            t_obj = yf.Ticker(t)
            mkt_cap = 0
            try:
                mkt_cap = t_obj.fast_info.get('market_cap', 0)
                if not mkt_cap: # fast_info 실패 시 일반 info 시도
                    mkt_cap = t_obj.info.get('marketCap', 0)
            except:
                pass
            
            mkt_cap_bn = round(mkt_cap / 1e9, 1) if mkt_cap else 0

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, 
                "현재가": current_val, 
                "MDD": mdd, 
                "회복률": rec, 
                "수익률": chg, 
                "점수": score, # 소수점 한 자리 반영
                "시총($B)": mkt_cap_bn
            })
        except: continue
    return pd.DataFrame(results)

# 4. 메인 UI
st.title("📈 실시간 S&P 100 우량주 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tab1, tab2, tab3 = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def render_tab(years):
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
                "점수": st.column_config.NumberColumn(format="%.1f"), # 출력 포맷 고정
                "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
            }
        )

with tab1: render_tab(1)
with tab2: render_tab(2)
with tab3: render_tab(3)
