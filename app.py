import streamlit as st
import yfinance as yf
import math
import pandas as pd
import os
from datetime import datetime
import time

# --- 화면 기본 설정 ---
st.set_page_config(page_title="나의 투자 시그널 봇", page_icon="📈", layout="wide")

# --- 데이터 저장 함수 (CSV 파일로 기록 보관) ---
HISTORY_FILE_1 = "trade_history_1.csv"
HISTORY_FILE_2 = "trade_history_2.csv"

def load_history(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame(columns=["날짜", "종목", "종류", "수량", "가격", "총액", "메모"])

def save_history(df, file_path):
    df.to_csv(file_path, index=False)

# --- 내 포트폴리오 상태 및 수익 계산 함수 ---
def calculate_portfolio_state(df):
    held_shares = 0
    total_cost = 0.0
    avg_price = 0.0
    current_day = 0
    realized_profit = 0.0
    
    profits = []
    cum_profits = []
    buy_dates = set()

    for index, row in df.iterrows():
        kind = row["종류"]
        qty = float(row["수량"]) if pd.notnull(row["수량"]) else 0.0
        
        # 가격 파싱 ("$50.00" -> 50.0)
        price_str = str(row["가격"]).replace('$', '').replace(',', '')
        price = float(price_str) if price_str.replace('.', '', 1).isdigit() else 0.0
            
        profit = 0.0
        
        if kind == "매수":
            held_shares += qty
            total_cost += qty * price
            if held_shares > 0:
                avg_price = total_cost / held_shares
            buy_dates.add(row["날짜"])
            current_day = len(buy_dates)
        elif kind == "매도":
            profit = (price - avg_price) * qty
            realized_profit += profit
            held_shares -= qty
            if held_shares <= 0:  # 전량 매도시 사이클 초기화
                held_shares = 0
                total_cost = 0.0
                avg_price = 0.0
                current_day = 0
                buy_dates.clear()
            else:
                total_cost = avg_price * held_shares
        
        profits.append(profit)
        cum_profits.append(realized_profit)
        
    return held_shares, avg_price, current_day, profits, cum_profits

# ==========================================
# --- 세션 분리형 UI 렌더링 함수 ---
# ==========================================
def render_signal_ui(session_id, calc_shares, calc_avg, calc_day):
    st.subheader(f"🔹 매매 세션 {session_id} - 현재 상태")
    c1, c2 = st.columns(2)
    with c1:
        ticker = st.text_input("종목명", value="SOXL", key=f"ticker_{session_id}")
        max_days = st.number_input("최대 매수일 (Day)", value=25, key=f"max_days_{session_id}")
        default_day = min(int(calc_day), int(max_days))
        current_day = st.number_input("현재 진행일 (처음 진입 시 0)", value=default_day, min_value=0, max_value=int(max_days), key=f"current_day_{session_id}")
        avg_price = st.number_input("현재 내 평단가 ($)", value=float(calc_avg), format="%.2f", key=f"avg_price_{session_id}")
    with c2:
        total_cash = st.number_input("초기 총 투자금 ($)", value=10000.0, key=f"total_cash_{session_id}")
        target_profit = st.number_input("목표 수익률 (%)", value=14.0, key=f"target_profit_{session_id}") / 100.0
        loc_pct = st.number_input("시가 대비 LOC 허용치 (%)", value=5.0, key=f"loc_pct_{session_id}") / 100.0
        held_shares = st.number_input("현재 보유 수량 (주)", value=int(calc_shares), key=f"held_shares_{session_id}")

    if st.button(f"🚀 세션 {session_id} 액션 플랜 생성", use_container_width=True, key=f"btn_action_{session_id}"):
        with st.spinner('가격을 불러오는 중...'):
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                
                if hist.empty:
                    st.error("가격을 불러오지 못했습니다. 종목명을 확인하거나 잠시 후 다시 시도해 주세요.")
                else:
                    current_price = float(hist['Close'].iloc[-1])
                    st.success(f"현재 {ticker} 기준가 (전일 종가 또는 현재가): **${current_price:.2f}**")

                    budget_per_day = total_cash / max_days
                    session_size = max(1, math.floor(budget_per_day / current_price))
                    
                    st.markdown(f"### 🔔 세션 {session_id} 오늘의 행동 지침")
                    
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

def render_record_ui(session_id, file_path, history_df, calc_shares, calc_avg, profits_list, cum_profits_list):
    st.subheader(f"📝 세션 {session_id} 매매 기록 남기기")
    with st.form(f"record_form_{session_id}"):
        c1, c2 = st.columns(2)
        with c1:
            r_date = st.date_input("체결 날짜", datetime.today(), key=f"r_date_{session_id}")
            r_ticker = st.text_input("종목명", value="SOXL", key=f"r_ticker_{session_id}")
            r_type = st.selectbox("매매 종류", ["매수", "매도", "배당/기타"], key=f"r_type_{session_id}")
        with c2:
            r_qty = st.number_input("체결 수량 (주)", min_value=0, value=0, key=f"r_qty_{session_id}")
            r_price = st.number_input("체결 가격 ($)", min_value=0.0, format="%.2f", key=f"r_price_{session_id}")
            r_memo = st.text_input("메모 (선택)", key=f"r_memo_{session_id}")
        
        if st.form_submit_button("저장하기", use_container_width=True):
            new_record = pd.DataFrame([{
                "날짜": r_date.strftime("%Y-%m-%d"),
                "종목": r_ticker.upper(),
                "종류": r_type,
                "수량": r_qty,
                "가격": f"${r_price:.2f}",
                "총액": f"${r_qty * r_price:.2f}",
                "메모": r_memo
            }])
            curr_df = load_history(file_path)
            curr_df = pd.concat([curr_df, new_record], ignore_index=True)
            save_history(curr_df, file_path)
            st.success(f"✅ 세션 {session_id} 매매 기록이 성공적으로 저장되었습니다.")
            time.sleep(0.5)
            st.rerun()

    st.divider()
    st.subheader(f"📋 세션 {session_id} 전체 매매 내역")
    
    if not history_df.empty:
        total_cum = cum_profits_list[-1] if cum_profits_list else 0.0
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 누적 수익", f"${total_cum:,.2f}")
        m2.metric("📦 보유 수량", f"{int(calc_shares)} 주")
        m3.metric("📊 평단가", f"${calc_avg:,.2f}")
        
        display_df = history_df.copy()
        display_df["수익금"] = [f"${p:,.2f}" if p != 0 else "-" for p in profits_list]
        display_df["누적수익"] = [f"${cp:,.2f}" for cp in cum_profits_list]
        
        st.dataframe(display_df.iloc[::-1].reset_index(drop=True), use_container_width=True)
        
        with st.expander(f"세션 {session_id} 위험 구역 (Danger Zone)"):
            if st.button("모든 기록 영구 삭제", type="primary", key=f"del_{session_id}"):
                if os.path.exists(file_path):
                    os.remove(file_path)
                st.success("모든 기록이 삭제되었습니다.")
                st.rerun()
    else:
        st.info("아직 저장된 매매 기록이 없습니다.")

# --- 세션 상태 (로그인 여부) 초기화 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ==========================================
# --- 0. 로그인 화면 ---
# ==========================================
if not st.session_state['logged_in']:
    st.title("🔒 로그인")
    with st.form("login_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submit_button = st.form_submit_button("로그인", use_container_width=True)
        
        if submit_button:
            # 💡 이곳에서 원하는 아이디와 비밀번호를 설정하세요!
            if username == "admin" and password == "1234": 
                st.session_state['logged_in'] = True
                st.rerun() # 로그인 성공 시 화면 새로고침
            else:
                st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
    st.stop() # 로그인이 안 되면 여기서 앱 실행을 멈춤

# ==========================================
# --- 1. 메인 화면 (로그인 성공 시) ---
# ==========================================
col_title, col_logout = st.columns([4, 1])
with col_title:
    st.title("📈 나의 실전 분할매수 봇")
with col_logout:
    st.write("") # 버튼 위치를 맞추기 위한 여백
    if st.button("로그아웃"):
        st.session_state['logged_in'] = False
        st.rerun()

st.markdown("**매일 밤 오늘의 행동 지침을 확인하고, 실제 체결된 내역을 기록하세요!**")

# --- 데이터 불러오기 및 현재 상태 계산 ---
hist_df1 = load_history(HISTORY_FILE_1)
sh1, avg1, day1, p_list1, cum_p1 = calculate_portfolio_state(hist_df1)

hist_df2 = load_history(HISTORY_FILE_2)
sh2, avg2, day2, p_list2, cum_p2 = calculate_portfolio_state(hist_df2)

# --- 탭(Tab)으로 화면 분리 ---
tab1, tab2 = st.tabs(["🚀 오늘의 시그널", "📁 매매 기록"])

with tab1:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        render_signal_ui(1, sh1, avg1, day1)
    with col_s2:
        render_signal_ui(2, sh2, avg2, day2)

with tab2:
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        render_record_ui(1, HISTORY_FILE_1, hist_df1, sh1, avg1, p_list1, cum_p1)
    with col_r2:
        render_record_ui(2, HISTORY_FILE_2, hist_df2, sh2, avg2, p_list2, cum_p2)
