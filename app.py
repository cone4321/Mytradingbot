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
