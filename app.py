from datetime import datetime, date
from zoneinfo import ZoneInfo
import hmac

import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="冷蔵庫の期限メモ",
    page_icon="🥕",
    layout="centered"
)

st.title("🥕 冷蔵庫の期限メモ")

# パスワードを確認
if not st.session_state.get("authenticated", False):
    with st.form("login"):
        password = st.text_input(
            "アプリのパスワード",
            type="password"
        )
        login = st.form_submit_button("開く")

    if login:
        expected = st.secrets["APP_PASSWORD"]

        if expected and hmac.compare_digest(
            password.encode(),
            expected.encode()
        ):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")

    st.stop()

if st.button("ログアウト"):
    st.session_state.clear()
    st.rerun()

# クラウドの保存先に接続
db = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
)

today = datetime.now(ZoneInfo("Asia/Tokyo")).date()

# 食材の登録
with st.expander("＋ 食材を登録", expanded=True):
    with st.form("add_food", clear_on_submit=True):
        name = st.text_input(
            "食材名",
            placeholder="牛乳、卵、ヨーグルトなど",
            max_chars=80
        )

        quantity = st.text_input(
            "数量",
            placeholder="1本、3個など",
            max_chars=40
        )

        deadline_type = st.selectbox(
            "期限の種類",
            ["賞味期限", "消費期限"]
        )

        deadline = st.date_input(
            "パッケージに書かれた期限",
            value=today
        )

        place = st.selectbox(
            "保存場所",
            ["冷蔵", "冷凍", "常温"]
        )

        submitted = st.form_submit_button(
            "登録する",
            use_container_width=True
        )

    if submitted:
        if not name.strip():
            st.warning("食材名を入力してください。")
        else:
            try:
                db.table("foods").insert({
                    "name": name.strip(),
                    "quantity": quantity.strip(),
                    "deadline_type": deadline_type,
                    "deadline": deadline.isoformat(),
                    "place": place
                }).execute()

                st.success("登録しました。")
            except Exception:
                st.error(
                    "保存できませんでした。"
                    "接続と設定を確認してください。"
                )

# 食材を期限順に取得
st.subheader("期限が近い順")

only_soon = st.checkbox(
    "3日以内の期限・期限超過だけを表示"
)

try:
    foods = (
        db.table("foods")
        .select("*")
        .order("deadline")
        .order("id")
        .execute()
        .data
    )
except Exception:
    st.error(
        "一覧を読み込めませんでした。"
        "接続と設定を確認してください。"
    )
    st.stop()

# 一覧を表示
shown = 0

for food in foods:
    remaining = (
        date.fromisoformat(food["deadline"]) - today
    ).days

    if only_soon and remaining > 3:
        continue

    shown += 1

    if remaining < 0:
        status = f"🔴 期限から{-remaining}日経過"
    elif remaining == 0:
        status = "🟠 今日が期限"
    elif remaining <= 3:
        status = f"🟡 あと{remaining}日"
    else:
        status = f"🟢 あと{remaining}日"

    with st.container(border=True):
        st.write(food["name"])

        st.caption(
            f"{food['quantity']} ｜ "
            f"{food['place']} ｜ "
            f"{food['deadline_type']}："
            f"{food['deadline']}"
        )

        st.write(status)

        if st.button(
            "食べ終わった・一覧から削除",
            key=f"delete_{food['id']}"
        ):
            try:
                (
                    db.table("foods")
                    .delete()
                    .eq("id", food["id"])
                    .execute()
                )
                st.rerun()
            except Exception:
                st.error(
                    "削除できませんでした。"
                    "もう一度お試しください。"
                )

if shown == 0:
    st.info("表示する食材がありません。")

st.caption(
    "期限の記録用です。日数表示は、"
    "食べられるかどうかの判定ではありません。"
)
