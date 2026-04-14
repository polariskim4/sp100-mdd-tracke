import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="실시간 S&P 100 분석", page_icon="📈", layout="wide")

# 2. 실시간 S&P 100 티커 리스트 가져오기 (403 에러 방지 헤더 추가)
@st.cache_data(ttl=86400)
def get_sp100_tickers():
    url = "https://en.wikipedia.org/wiki/S%26P_100"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers)
        tables = pd.read_html(response.text)
        df = tables[2]
        tickers = df['Symbol'].str.replace('.', '-', regex=False).tolist()
        return sorted(tickers)
    except Exception as e:
        st.error(f"리스트 업데이트 실패: {e}")
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "UNH", "LLY"]

# 3. 데이터 로딩 및 분석
@st.cache_data(ttl=3600)
def fetch_data(years):
    tickers = get_sp100_tickers()
    # 전체 주가 데이터 다운로드
    data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False)
    
    results = []
    for t in tickers:
        try:
            close = data['Close'][t].dropna()
            if close.empty: continue
            
            high = data['High'][t].max()
            low = data['Low'][t].min()
            current = close.iloc[-1]
            
            mdd = ((current - high) / high) * 100
            rec = ((current - low) / low) * 100
            chg = ((current - close.iloc[0]) / close.iloc[0]) * 100
            score = abs(mdd) - rec
            
            # 시가총액 정보 가져오기 (안정성 강화)
            t_obj = yf.Ticker(t)
            mkt_cap = 0
            # fast_info가 안될 경우 info로 시도
            try:
                mkt_cap = t_obj.fast_info.get('market_cap', 0)
                if mkt_cap == 0:
                    mkt_cap = t_obj.info.get('marketCap', 0)
            except:
                pass
            
            mkt_cap_bn = round(mkt_cap / 1e9, 1) if mkt_cap else 0

            # 신호 결정
            if score >= 20: sig = "🔥 적극매수"
            elif 10 <= score < 20: sig = "🟢 매수"
            else: sig = "🟡 진입"

            results.append({
                "신호": sig, "티커": t, "현재가": current, 
                "MDD": mdd, "회복률": rec, "수익률": chg, 
                "점수": round(score, 1), "시총($B)": mkt_cap_bn
            })
        except: continue
    return pd.DataFrame(results)

# 4. UI 출력
st.title("📈 실시간 S&P 100 우량주 MDD 분석")
ny_time = datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"최종 업데이트 (NY): {ny_time} | Wikipedia 실시간 구성 종목 반영")

tab1, tab2, tab3 = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

def show_tab(years):
    with st.spinner(f"{years}년치 분석 중..."):
        df = fetch_data(years)
        if not df.empty:
            st.dataframe(
                df.sort_values("점수", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "현재가": st.column_config.NumberColumn(format="$%.2f"),
                    "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                    "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                    "수익률": st.column_config.NumberColumn(format="%.1f%%"),
                    "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
                }
            )

with tab1: show_tab(1)
with tab2: show_tab(2)
with tab3: show_tab(3)
