import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="실시간 S&P 100 MDD 분석", page_icon="📊", layout="wide")

# 2. 실시간 S&P 100 티커 리스트 가져오기 함수
@st.cache_data(ttl=86400) # 리스트는 하루에 한 번만 갱신
def get_sp100_tickers():
    try:
        # Wikipedia의 S&P 100 리스트 테이블을 읽어옵니다.
        url = "https://en.wikipedia.org/wiki/S%26P_100"
        tables = pd.read_html(url)
        df = tables[2] # 보통 3번째 테이블이 종목 리스트입니다.
        tickers = df['Symbol'].tolist()
        # 점(.)이 포함된 티커(예: BRK.B)를 yfinance 형식(BRK-B)으로 변환
        tickers = [t.replace('.', '-') for t in tickers]
        return sorted(tickers)
    except Exception as e:
        st.error(f"티커 리스트를 가져오는 중 오류 발생: {e}")
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"] # 실패 시 비상용 리스트

# 3. 데이터 로딩 및 분석 함수
@st.cache_data(ttl=3600)
def fetch_and_analyze(period_years):
    tickers = get_sp100_tickers()
    
    # 100개 종목의 주가 데이터를 한 번에 다운로드
    data_all = yf.download(tickers, period=f"{period_years}y", interval="1d", progress=False)
    
    results = []
    for t in tickers:
        try:
            # 해당 티커의 종가 데이터 (결측치 제거)
            df_close = data_all['Close'][t].dropna()
            df_high = data_all['High'][t].dropna()
            df_low = data_all['Low'][t].dropna()
            
            if len(df_close) < 10: continue

            cp = float(df_close.iloc[-1])
            start_p = float(df_close.iloc[0])
            max_high = float(df_high.max())
            min_low = float(df_low.min())

            mdd = round(((cp - max_high) / max_high) * 100, 2)
            rec = round(((cp - min_low) / min_low) * 100, 2)
            chg = round(((cp - start_p) / start_p) * 100, 2)
            score = round(abs(mdd) - rec, 1)

            # 시가총액 정보 가져오기 (실시간 순위 반영을 위해 표시)
            t_obj = yf.Ticker(t)
            mkt_cap = t_obj.fast_info.get('market_cap', 0)
            mkt_cap_bn = round(mkt_cap / 1_000_000_000, 1) if mkt_cap else 0

            # 신호 결정
            if score >= 20: sig = "🔥 적극매수"
            elif 10 <= score < 20: sig = "🟢 매수"
            else: sig = "🟡 진입"

            results.append({
                "신호": sig, "티커": t, "현재가": cp, 
                "MDD": mdd, "회복률": rec, "수익률": chg, 
                "점수": score, "시총($B)": mkt_cap_bn
            })
        except: continue
        
    return pd.DataFrame(results)

# 4. 메인 UI 및 출력
st.title("📊 실시간 S&P 100 우량주 MDD 분석")
ny_tz = pytz.timezone('America/New_York')
st.caption(f"최종 업데이트 (NY): {datetime.now(ny_tz).strftime('%Y-%m-%d %H:%M:%S')}")

tabs = st.tabs(["1년 분석", "2년 분석", "3년 분석"])

for i, tab in enumerate(tabs):
    with tab:
        years = i + 1
        with st.spinner(f"{years}년치 데이터를 분석 중입니다..."):
            df_res = fetch_and_analyze(years)
            
            if not df_res.empty:
                # 시가총액 순으로 정렬하거나 점수 순으로 정렬하여 표시
                st.dataframe(
                    df_res.sort_values("점수", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "현재가": st.column_config.NumberColumn(format="$%.2f"),
                        "MDD": st.column_config.NumberColumn(format="%.1f%%"),
                        "회복률": st.column_config.NumberColumn(format="%.1f%%"),
                        "수익률": st.column_config.NumberColumn(format="%.1f%%"),
                        "시총($B)": st.column_config.NumberColumn(format="$%.1f B")
                    }
                )
            else:
                st.warning("분석할 데이터를 가져오지 못했습니다.")
