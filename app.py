@st.cache_data(ttl=86400)
def get_stock_metadata():
    meta = {}
    # 한 번에 모든 데이터를 요청하기보다 하나씩 처리하되, 실패 시 대안을 찾습니다.
    for t in TICKERS:
        # 기본값 설정
        meta[t] = {"desc": t, "mkt_cap": 0} 
        try:
            ticker_obj = yf.Ticker(t)
            
            # 1. 시가총액 가져오기 (fast_info가 일반 info보다 훨씬 빠르고 안정적입니다)
            try:
                raw_mkt_cap = ticker_obj.fast_info.get('market_cap', 0)
            except:
                raw_mkt_cap = ticker_obj.info.get('marketCap', 0)
                
            mkt_cap_bn = round(raw_mkt_cap / 1_000_000_000, 1) if raw_mkt_cap else 0
            
            # 2. 기업명 가져오기 (실패 시 티커명을 그대로 사용)
            try:
                name = ticker_obj.info.get('longName', t)
            except:
                name = t # 정보가 없으면 AAPL 같이 티커라도 표시
                
            meta[t] = {"desc": name, "mkt_cap": mkt_cap_bn}
        except Exception as e:
            # 에러 발생 시 로그만 남기고 다음 종목으로 진행
            print(f"Error fetching {t}: {e}")
            continue
    return meta
