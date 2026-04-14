import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime
import time

# 1. 페이지 설정
st.set_page_config(page_title="S&P 100 섹터별 MDD 분석", layout="wide")

SECTOR_MAP = {
    "Technology": "💻 기술", "Consumer Cyclical": "🛍️ 임의소비",
    "Communication Services": "📱 통신", "Healthcare": "🏥 헬스케어",
    "Financial Services": "🏦 금융", "Industrials": "🏭 산업재",
    "Consumer Defensive": "🛒 필수소비", "Utilities": "⚡ 유틸리티",
    "Real Estate": "🏢 부동산", "Energy": "🛢️ 에너지", "Basic Materials": "🧱 소재"
}

def get_sp100_tickers():
    return [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "TSLA", "UNH", "LLY",
        "JPM", "XOM", "V", "MA", "AVGO", "PG", "HD", "COST", "JNJ", "ABBV",
        "CRM", "WMT", "BAC", "CVX", "MRK", "ADBE", "PEP", "KO", "TMO", "WFC"
    ]

# 2. 데이터 수집 함수 (재시도 로직 및 에러 핸들링 강화)
@st.cache_data(ttl=3600)
def fetch_sp100_data(years):
    tickers = get_sp100_tickers()
    data = pd.DataFrame()
    
    # 최대 2회 재시도 (서버 응답 지연 대비)
    for _ in range(2):
        try:
            data = yf.download(tickers, period=f"{years}y", interval="1d", progress=False, group_by='ticker')
            if not data.empty:
                break
            time.sleep(1)
        except:
            time.sleep(1)
            continue
            
    if data.empty:
        return pd.DataFrame()

    tickers_obj = yf.Tickers(' '.join(tickers))
    results = []
    
    for t in tickers:
        try:
            # 기간에 따른 데이터 추출 방식 보정
            df_t = data[t].dropna()
            if df_t.empty or len(df_t) < 5: continue
            
            cur = df_t['Close'].iloc[-1]
            high = df_t['High'].max()
            low = df_t['Low'].min()
            
            mdd = ((cur - high) / high) * 100
            rec = ((cur - low) / low) * 100
            score = round(abs(mdd) - rec, 1)

            # 섹터 정보 안전하게 가져오기
            try:
                info = tickers_obj.tickers[t].info
                s_raw = info.get('sector', '기타')
                mkt_cap = (info.get('marketCap') or 0) / 1e9
            except:
                s_raw, mkt_cap = "기타", 0.0

            results.append({
                "신호": "🔥 적극매수" if score >= 20 else "🟢 매수" if score >= 10 else "🟡 진입",
                "티커": t, "섹터": SECTOR_MAP.get(s_raw, s_raw), "현재가": cur,
                "MDD": mdd, "회복률": rec, "점수": score, "시총($B)": mkt_cap
            })
        except: continue
    return pd.DataFrame(results)

# 3. UI 구성
st.title("📊 실시간 S&P 100 우량주 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tabs = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

for i, tab in enumerate(tabs):
    years = i + 1
    with tab:
        with st.spinner(f"{years}년 데이터를 정밀 분석 중입니다..."):
            res_df = fetch_sp100_data(years)
            if not res_df.empty:
                st.dataframe(
                    res_df.sort_values("점수", ascending=False),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "현재가": st.column_config.NumberColumn(format="$%.2f"),
                        "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                        "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                        "점수": st.column_config.NumberColumn(format="%.1f"),
                        "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
                    }
                )
            else:
                st.warning(f"{years}년 데이터를 불러오지 못했습니다. 우측 상단 메뉴에서 [Clear Cache] 후 새로고침해 주세요.")
