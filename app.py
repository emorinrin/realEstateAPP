import os
import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import folium_static

#CSS
st.set_page_config(
    page_title="HomeSeeker",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="auto",
)


# データベース接続の設定
DB_PATH = 'database.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# パスワードのハッシュ化関数
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def create_user():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')

def add_user(username, password):
    c.execute('INSERT INTO userstable(username, password) VALUES (?, ?)', (username, password))
    conn.commit()

def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    return data

# ブックマークのデータベース設定
def create_bookmark_table(username):
    user_db = f"bookmark/{username}.db"
    user_conn = sqlite3.connect(user_db)
    user_c = user_conn.cursor()
    user_c.execute('''CREATE TABLE IF NOT EXISTS bookmarks (
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
                    )''')
    user_conn.commit()
    user_conn.close()

def add_bookmark(username, bookmark):
    user_db = f"bookmark/{username}.db"
    user_conn = sqlite3.connect(user_db)
    user_c = user_conn.cursor()
    user_c.execute('''INSERT INTO bookmarks (名称, アドレス, 階数, 家賃, 間取り, 物件詳細URL, 緯度, 経度, 区)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                   (bookmark['名称'], bookmark['アドレス'], bookmark['階数'], bookmark['家賃'], 
                    bookmark['間取り'], bookmark['物件詳細URL'], bookmark['緯度'], 
                    bookmark['経度'], bookmark['区']))
    user_conn.commit()
    user_conn.close()

def load_bookmarks(username):
    user_db = f"bookmark/{username}.db"
    user_conn = sqlite3.connect(user_db)
    user_c = user_conn.cursor()
    user_c.execute('SELECT * FROM bookmarks')
    bookmarks = user_c.fetchall()
    user_conn.close()
    return bookmarks

# 賃貸物件データベースの設定
RENT_DB_PATH = 'DB/room.db'
RENT_DB_TABLE_NAME = 'room_ver2'

# データベースを初期化する関数
def initialize_db(db_path):
    try:
        if not os.path.exists(db_path):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
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
    except sqlite3.OperationalError as e:
        st.error(f"SQLite OperationalError: {e}")
    except Exception as e:
        st.error(f"Error initializing database: {e}")

# データベースを初期化
initialize_db(RENT_DB_PATH)

# セッション状態の初期化
if 'show_all' not in st.session_state:
    st.session_state['show_all'] = False

def toggle_show_all():
    st.session_state['show_all'] = not st.session_state['show_all']

# 賃貸物件データベースからデータを読み込む関数
def load_data_from_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT rowid as id, * FROM {RENT_DB_TABLE_NAME}"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading data from database: {e}")
        return pd.DataFrame()

# データフレームの前処理を行う関数
def preprocess_dataframe(df):
    # st.write("データフレームの列名: ", df.columns.tolist())
    # st.write("データフレームの内容: ", df.head())
    if '家賃' in df.columns:
        df['家賃'] = pd.to_numeric(df['家賃'], errors='coerce')
        df = df.dropna(subset=['家賃'])
    else:
        st.error("家賃の列がデータフレームに存在しません。")
    return df

def make_clickable(url, name):
    return f'<a target="_blank" href="{url}">{name}</a>'

def create_map(filtered_df):
    map_center = [filtered_df['緯度'].mean(), filtered_df['経度'].mean()]
    m = folium.Map(location=map_center, zoom_start=12)

    for idx, row in filtered_df.iterrows():
        if pd.notnull(row['緯度']) and pd.notnull(row['経度']):
            popup_html = f"""
            <b>名称:</b> {row['名称']}<br>
            <b>アドレス:</b> {row['アドレス']}<br>
            <b>家賃:</b> {row['家賃']}万円<br>
            <b>間取り:</b> {row['間取り']}<br>
            <a href="{row['物件詳細URL']}" target="_blank">物件詳細</a>
            """
            popup = folium.Popup(popup_html, max_width=400)
            folium.Marker([row['緯度'], row['経度']], popup=popup).add_to(m)

    return m

def display_search_results(filtered_df, username):
    filtered_df['物件番号'] = range(1, len(filtered_df) + 1)

    # チェックボックスを追加
    for idx, row in filtered_df.iterrows():
        st.header(f"{row['名称']}")
        st.write(f"住所：{row['アドレス']}")
        st.write(f"家賃：{row['家賃']}万円、階数{row['階数']}、間取り：{row['間取り']}")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(row['物件画像URL'])

        with col2:
            st.image(row['間取画像URL'], width=200)

        st.markdown("詳細リンク(%s)" % row['物件詳細URL'])
        if st.checkbox(f"お気に入り登録する", key=f"{username}_{row['id']}"):
            add_bookmark(username, row)

def rental_app(username):
    df = load_data_from_db(RENT_DB_PATH)
    df = preprocess_dataframe(df)

    st.title('賃貸物件検索')

    col1, col2 = st.columns([1, 2])

    with col1:
        area = st.radio('■ エリア選択', df['区'].unique())

    with col2:
        price_min, price_max = st.slider(
            '■ 家賃範囲 (万円)',
            min_value=float(1),
            max_value=float(df['家賃'].max()),
            value=(float(df['家賃'].min()), float(df['家賃'].max())),
            step=0.1,
            format='%.1f'
        )

    with col2:
        type_options = st.multiselect('■ 間取り選択', df['間取り'].unique(), default=df['間取り'].unique())

    filtered_df = df[(df['区'].isin([area])) & (df['間取り'].isin(type_options))]
    filtered_df = filtered_df[(filtered_df['家賃'] >= price_min) & (filtered_df['家賃'] <= price_max)]
    filtered_count = len(filtered_df)

    filtered_df['緯度'] = pd.to_numeric(filtered_df['緯度'], errors='coerce')
    filtered_df['経度'] = pd.to_numeric(filtered_df['経度'], errors='coerce')
    filtered_df2 = filtered_df.dropna(subset=['緯度', '経度'])

    col2_1, col2_2 = st.columns([1, 2])

    with col2_2:
        st.write(f"物件検索数: {filtered_count}件 / 全{len(df)}件")

    if col2_1.button('検索＆更新', key='search_button'):
        st.session_state['filtered_df'] = filtered_df
        st.session_state['filtered_df2'] = filtered_df2
        st.session_state['search_clicked'] = True

    if st.session_state.get('search_clicked', False):
        m = create_map(st.session_state.get('filtered_df2', filtered_df2))
        folium_static(m)

    show_all_option = st.radio(
        "表示オプションを選択してください:",
        ('地図上の検索物件のみ', 'すべての検索物件'),
        index=0 if not st.session_state.get('show_all', False) else 1,
        key='show_all_option'
    )

    st.session_state['show_all'] = (show_all_option == 'すべての検索物件')

    if st.session_state.get('search_clicked', False):
        if st.session_state['show_all']:
            display_search_results(st.session_state.get('filtered_df', filtered_df), username)
        else:
            display_search_results(st.session_state.get('filtered_df2', filtered_df2), username)

def main():
    st.title("HomeSeekers -賃貸検索アプリ-")

    menu = ["ホーム", "ログイン", "サインアップ", "ブックマーク"]
    choice = st.sidebar.selectbox("メニュー", menu)

    if choice == "ホーム":
        st.image("img/HomeSeekers.png")
        st.subheader("ホーム画面です")

    elif choice == "ログイン":
        st.subheader("ログイン画面です")

        username = st.sidebar.text_input("ユーザー名を入力してください")
        password = st.sidebar.text_input("パスワードを入力してください", type='password')
        if st.sidebar.checkbox("ログイン"):
            create_user()
            hashed_pswd = make_hashes(password)

            result = login_user(username, check_hashes(password, hashed_pswd))
            if result:
                st.success(f"{username}さんでログインしました")
                create_bookmark_table(username)
                rental_app(username)
            else:
                st.warning("ユーザー名かパスワードが間違っています")

    elif choice == "サインアップ":
        st.subheader("新しいアカウントを作成します")
        new_user = st.text_input("ユーザー名を入力してください")
        new_password = st.text_input("パスワードを入力してください", type='password')

        if st.button("サインアップ"):
            create_user()
            add_user(new_user, make_hashes(new_password))
            st.success("アカウントの作成に成功しました")
            st.info("ログイン画面からログインしてください")

    elif choice == "ブックマーク":
        st.subheader("ブックマークされた物件情報")
        username = st.sidebar.text_input("ユーザー名を入力してください")
        password = st.sidebar.text_input("パスワードを入力してください", type='password')
        if st.sidebar.checkbox("表示"):
            result = login_user(username, check_hashes(password, make_hashes(password)))
            if result:
                bookmarks = load_bookmarks(username)
                if bookmarks:
                    df_bookmarks = pd.DataFrame(bookmarks, columns=["id", "名称", "アドレス", "階数", "家賃", "間取り", "物件詳細URL",'緯度',
                    '経度', '区'])
                    # 重複データの削除
                    df_bookmarks = df_bookmarks.drop_duplicates(subset=["物件詳細URL"])
                    df_bookmarks = df_bookmarks.loc[:,["名称", "アドレス", "階数", "家賃", "間取り", "物件詳細URL"]]
                    st.dataframe(df_bookmarks,hide_index=True)
                else:
                    st.warning("ブックマークされた物件がありません")
            else:
                st.warning("ユーザー名かパスワードが間違っています")

if __name__ == '__main__':
    main()
