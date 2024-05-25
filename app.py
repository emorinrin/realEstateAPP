import os
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import folium_static

# Streamlit Secretsから環境変数を読み込む
DB_PATH = st.secrets["STEP3-1_bady"]["DB"]
DB_TABLE_NAME = 'room_ver2'  # テーブル名

# データベースを初期化する関数
def initialize_db(db_path):
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS room_ver2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                名称 TEXT,
                アドレス TEXT,
                階数 TEXT,
                家賃 REAL,
                間取り TEXT,
                物件詳細URL TEXT,
                緯度 REAL,
                経度 REAL,
                区 TEXT
            )
        ''')
        conn.close()

# データベースを初期化
initialize_db(DB_PATH)

# セッション状態の初期化
if 'show_all' not in st.session_state:
    st.session_state['show_all'] = False  # 初期状態は地図上の物件のみを表示

# 地図上以外の物件も表示するボタンの状態を切り替える関数
def toggle_show_all():
    st.session_state['show_all'] = not st.session_state['show_all']

# SQLiteデータベースからデータを読み込む関数
def load_data_from_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        query = f"SELECT * FROM {DB_TABLE_NAME}"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading data from database: {e}")
        return pd.DataFrame()  # 空のデータフレームを返す

# データフレームの前処理を行う関数
def preprocess_dataframe(df):
    # '家賃' 列を浮動小数点数に変換し、NaN値を取り除く
    df['家賃'] = pd.to_numeric(df['家賃'], errors='coerce')
    df = df.dropna(subset=['家賃'])
    return df

def make_clickable(url, name):
    return f'<a target="_blank" href="{url}">{name}</a>'

# 地図を作成し、マーカーを追加する関数
def create_map(filtered_df):
    # 地図の初期設定
    map_center = [filtered_df['緯度'].mean(), filtered_df['経度'].mean()]
    m = folium.Map(location=map_center, zoom_start=1
