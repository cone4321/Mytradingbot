import streamlit as st
import yfinance as yf
import math
import requests

# --- 화면 기본 설정 ---
st.set_page_config(page_title="나의 투자 시그널 봇", page_icon="📈")
st.title("📈 나의 실전 분할매수 시그널 봇")

st.markdown("""
**매일 밤 미장 개장 전, 내 상태를 입력하고 오늘의 주문 가격을 확인하세요!**
""")

# --- 1. 현재 상태 입력 (UI) ---
st.header("1. 현재 상태 입력")
col1, col2 = st.columns(2)
with col1:
    ticker = st.text_input("종목명", value="SOXL")
    max_days = st.number_input("최대 매수일 (Day)", value=25)
    current_day = st.number_input("현재 진행일 (처음 진입 시 0)", value=0, min_value=0, max_value=max_days)
    avg_price = st.number_input("현재 내 평단가 ($)", value=0.0)
with col2:
    total_cash = st.number_input("초기 총 투자금 ($)", value=10000.0)
    target_profit = st.number_input("목표 수익률 (%)", value=14.0) / 100.0
    loc_pct = st.number_input("시가 대비 LOC 허용치 (%)", value=5.0) / 100.0
    held_shares = st.number_input("현재 보유 수량 (주)", value=0)

# --- 2. 시그널 생성 로직 ---
if st.button("🚀 오늘의 액션 플랜 생성", use_container_width=True):
    with st.spinner('가격을 불러오는 중...'):
        try:
            # [수정] 야후 파이낸스 차단(Rate Limit) 방지를 위해 크롬 브라우저인 척 위장
            session = requests.Session()
            session.headers.update(
                {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'}
            )
            
            stock = yf.Ticker(ticker, session=session)
            hist = stock.history(period="1d")
            
            if hist.empty:
                st.error("가격을 불러오지 못했습니다. 종목명을 확인하거나 잠시 후 다시 시도해 주세요.")
            else:
                current_price = float(hist['Close'].iloc[-1])
                st.success(f"현재 {ticker} 기준가 (전일 종가 또는 현재가): **${current_price:.2f}**")

                # 하루치 예산 및 1세션 주식 수 계산
                budget_per_day = total_cash / max_days
                session_size = max(1, math.floor(budget_per_day / current_price))
                
                st.header("🔔 오늘의 행동 지침 (Action Plan)")
                
                if current_day == 0:
                    st.info(f"**[새로운 사이클 시작 - Day 1]**\n\n👉 장 시작 직후 **시장가(Market)**로 **{session_size}주** 매수하세요.")
                
                elif current_day >= max_days:
                    st.error(f"**[최대 매수일 도달 - 타임스탑 강제 청산]**\n\n👉 목표 수익에 도달하지 못했습니다. 오늘 장 중 전량(**{held_shares}주**) **시장가 매도** 하세요.")
                
                else:
                    target_price = avg_price * (1.0 + target_profit)
                    half_1 = session_size // 2
                    half_2 = session_size - half_1
                    loc_target = current_price * (1.0 + loc_pct)
                    
                    st.warning(f"**[추가 매수 및 익절 세팅 - Day {current_day + 1}]**")
                    st.write(f"**🔴 1. 익절 매도 (GTC 지정가):**\n👉 **${target_price:.2f}** 에 보유 수량 전량(**{held_shares}주**) '매도' 걸어두기")
                    st.write(f"**🔵 2. 추가 매수 1 (종가 지정가/LOC):**\n👉 나의 평단가 **${avg_price:.2f}** 에 **{half_1}주** '매수' 걸어두기")
                    st.write(f"**🔵 3. 추가 매수 2 (종가 지정가/LOC):**\n👉 현재가 + {loc_pct*100}% 인 **${loc_target:.2f}** 이하 조건으로 **{half_2}주** '매수' 걸어두기")
        except Exception as e:
            st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
