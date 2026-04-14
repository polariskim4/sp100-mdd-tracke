import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="S&P 100 MDD 분석기", page_icon="📈", layout="wide")

# 2. S&P 100 티커 리스트 (시총 상위 주요 100개 기업)
SP100_TICKERS = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "BRK-B", "TSLA", "UNH",
    "LLY", "JPM", "XOM", "V", "MA", "AVGO", "HD", "PG", "COST", "ORCL",
    "JNJ", "ABBV", "ADBE", "WMT", "CRM", "CVX", "BAC", "MRK", "AMD", "PEP",
    "ACN", "KO", "TMO", "LIN", "NFLX", "WFC", "CSCO", "DIS", "PM", "ABT",
    "INTU", "INTC", "DHR", "CAT", "VZ", "TXN", "AXP", "AMGN", "MS", "PFE",
    "UNP", "IBM", "HON", "LOW", "SPGI", "GE", "QCOM", "SYK", "NKE", "COP",
    "GS", "NEE", "RTX", "BA", "ELV", "T", "BLK", "ISRG", "TJX", "MDLZ",
    "VRTX", "SBUX", "REGN", "LMT", "BKNG", "MMC", "CB", "ADI", "MDT", "PLD",
    "ADP", "AMT", "CI", "MU", "GILD", "ETN", "C", "BMY", "BSX", "MO",
    "ZTS", "DUK", "PGR", "LRCX", "DE", "EOG", "ITW", "CVS", "CL", "MMC"
]
TICKERS = sorted(list(set(SP100_TICKERS)))

# 3. 기업 메타데이터 (회사명 및 시가총액)
@st.cache_data(ttl=86400)
def get_stock_metadata():
    meta = {}
    for t in TICKERS:
        meta[t] = {"desc": "-", "mkt_cap": 0}
        try:
            info = yf.Ticker(t).info
            name = info.get('longName', t)
            
            # 시가총액을 Billion($B) 단위로 변환
            raw_mkt_cap = info.get('marketCap', 0)
            mkt_cap_bn = round(raw_mkt_cap / 1_000_000_000, 1) if raw_mkt_cap else 0
            
            meta[t] = {"desc": name, "mkt_cap": mkt_cap_bn}
        except:
            pass
    return meta

# 4. 주가 데이터 분석
@st.cache_data(ttl=3600)
def fetch_stock_data(period_years):
    meta_dict = get_stock_metadata()
    results = []
    
    for t in TICKERS:
        try:
            df = yf.download(t, period=f"{period_years}y", interval="1d", progress=False)
            if df.empty or len(df) < 2: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

            cp = float(df['Close'].iloc[-1])
            start_p = float(df['Close'].iloc[0])
            high = float(df['High'].max())
            low = float(df['Low'].min())
            
            chg = round(((cp - start_p) / start_p) * 100, 2)
            mdd = round(((cp - high) / high) * 100, 2)
            rec = round(((cp - low) / low) * 100, 2)
            score = round(abs(mdd) - rec, 1)
            
            # 우량주는 레버리지보다 MDD 회복 속도가 중요하므로 신호 기준 유지 또는 조정 가능
            if score >= 20: sig = "🔥 적극매수"
            elif 10 <= score < 20: sig = "🟢 매수"
            else: sig = "🟡 진입"

            m = meta_dict.get(t, {"desc": "-", "mkt_cap": 0})

            results.append({
                "신호": sig,
                "티커": t,
                "기업명": m["desc"],
                "현재가": cp,
                "MDD": mdd,
                "회복률": rec,
                "기간변화": chg,
                "점수": score,
                "시가총액($B)": m["mkt_cap"]
            })
        except: continue
    return pd.DataFrame(results)

# 5. 메인 UI
st.title("📈 S&P 100 우량주 MDD 분석 리포트")
ny_tz = pytz.timezone('America/New_York')
ny_time = datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"Last Update (NY): {ny_time} | S&P 100 기업 대상")

tabs = st.tabs(["📅 1년 분석", "📅 2년 분석", "📅 3년 분석"])

def display_dashboard(years):
    data = fetch_stock_data(years)
    if data.empty:
        st.warning("데이터를 가져오는 중입니다. 잠시만 기다려 주세요.")
        return

    # 상단 필터
    c1, c2 = st.columns([1, 2])
    with c1:
        f_sig = st.multiselect("신호 필터", ["🔥 적극매수", "🟢 매수", "🟡 진입"], 
                               default=["🔥 적극매수", "🟢 매수"], key=f"sig_{years}")
    
    filtered = data[data['신호'].isin(f_sig)]

    # 데이터 프레임 출력
    st.dataframe(
        filtered.sort_values("점수", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "현재가": st.column_config.NumberColumn("현재가", format="$%.2f"),
            "MDD": st.column_config.NumberColumn("MDD", format="%.1f%%"),
            "회복률": st.column_config.NumberColumn("저점대비 회복", format="%.1f%%"),
            "기간변화": st.column_config.NumberColumn("기간 수익률", format="%.1f%%"),
            "시가총액($B)": st.column_config.NumberColumn("시총 (Billion)", format="$%.1f B"),
            "기업명": st.column_config.TextColumn("기업명 (Description)", width="large")
        }
    )

for i, tab in enumerate(tabs):
    with tab:
        display_dashboard(i+1)
