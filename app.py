import streamlit as st
import pandas as pd

st.set_page_config(page_title="スワップ&バッファ シミュレーター", layout="wide")
st.title("つみたて外貨：確率ギャップモデル（期待値）シミュレーター")

# ===========================
# Sidebar Inputs (Japanese + help)
# ===========================
st.sidebar.header("起点・目標（編集可）")

m0 = st.sidebar.number_input(
    "起点：必要証拠金 M0（円）",
    value=44450,
    step=100,
    help="現在の『取引必要証拠金』など、口座で拘束されている証拠金の合計（円）を想定します。"
)
e0 = st.sidebar.number_input(
    "起点：純資産 E0（円）",
    value=70800,
    step=100,
    help="現在の『円時価評価額（純資産）』を想定します。評価損益・スワップを含む口座の純資産（円）です。"
)

target_margin_pct = st.sidebar.number_input(
    "目標維持率（%）",
    value=160.0,
    step=1.0,
    format="%.1f",
    help="半年後に『最低でもこの維持率を満たしたい』という目標値です。例：160%。"
)
target_margin = target_margin_pct / 100.0

months = st.sidebar.number_input(
    "積立期間（月）",
    value=6,
    min_value=1,
    max_value=24,
    step=1,
    help="月額を何か月積むか。デフォルトは6か月です。"
)

st.sidebar.subheader("レート（円）")
gbp_rate = st.sidebar.number_input("GBP/JPY", value=210.04, step=0.01, format="%.2f",
                                   help="計算用の為替レート。ここを変えると通貨数量とスワップ概算が変わります。")
mxn_rate = st.sidebar.number_input("MXN/JPY", value=9.03, step=0.01, format="%.2f",
                                   help="計算用の為替レート。")
try_rate = st.sidebar.number_input("TRY/JPY", value=3.46, step=0.01, format="%.2f",
                                   help="計算用の為替レート。")

st.sidebar.subheader("日次スワップ（円）")
gbp_swap_day = st.sidebar.number_input("GBP（1万通貨あたり/日）", value=178, step=1,
                                       help="1万通貨あたりの1日スワップ（円）。")
mxn_swap_day = st.sidebar.number_input("MXN（10万通貨あたり/日）", value=150, step=1,
                                       help="MXNは10万通貨あたりの1日スワップ（円）。他通貨と単位が違います。")
try_swap_day = st.sidebar.number_input("TRY（1万通貨あたり/日）", value=28, step=1,
                                       help="1万通貨あたりの1日スワップ（円）。")

st.sidebar.subheader("ギャップ幅（例：0.08＝8%）")
gbp_gap = st.sidebar.number_input("GBP ギャップ幅", value=0.08, step=0.01, format="%.2f",
                                  help="ギャップ（急変）時にどれだけ逆行すると仮定するか。例：0.08=8%。")
mxn_gap = st.sidebar.number_input("MXN ギャップ幅", value=0.12, step=0.01, format="%.2f",
                                  help="例：0.12=12%。")
try_gap = st.sidebar.number_input("TRY ギャップ幅", value=0.20, step=0.01, format="%.2f",
                                  help="例：0.20=20%。")

st.sidebar.subheader("ギャップ確率（期間内に発生）")
gbp_p = st.sidebar.number_input("GBP 確率", value=0.05, step=0.01, format="%.2f",
                                help="期間内（months）にギャップが起きる確率の仮定。例：0.05=5%。")
mxn_p = st.sidebar.number_input("MXN 確率", value=0.10, step=0.01, format="%.2f",
                                help="例：0.10=10%。")
try_p = st.sidebar.number_input("TRY 確率", value=0.30, step=0.01, format="%.2f",
                                help="例：0.30=30%。")

st.sidebar.subheader("平均保有月数（換算）")
avg_hold_year = st.sidebar.number_input("年スワップ用（例：6.5）", value=6.5, step=0.5, format="%.1f",
                                        help="年スワップ概算の平均保有月数。過去の計算互換のためのパラメータ。")
avg_hold_period = st.sidebar.number_input("期間スワップ用（例：3.5）", value=3.5, step=0.5, format="%.1f",
                                          help="期間（months）に対応する平均保有月数。6か月なら3.5が自然。")

# ===========================
# Explanations
# ===========================
st.subheader("用語と計算の説明（このアプリの前提）")
st.markdown(
    """
- **ベース追加バッファ**：ストレス（ギャップ損失）を考えない場合でも、半年後に目標維持率を満たすために必要な追加現金。  
  \\(B_{base} = t(M_0 + C) - (E_0 + C)\\)（マイナスなら0円）  
  - \\(t\\)：目標維持率（例：1.60）  
  - \\(M_0\\)：起点の必要証拠金  
  - \\(E_0\\)：起点の純資産  
  - \\(C\\)：期間中の積立合計（=月額合計×月数）

- **期待ストレス損失（期待値）**：ギャップ幅×確率を用いた「期待損失」。  
  \\(Loss = \\sum(月額×月数×レバ×ギャップ幅×確率)\\)

- **追加バッファ合計**：\\(B_{base} + Loss\\)。  
  ※これは“損失”ではなく、**目標維持率を満たすために口座に置いておく必要がある現金**の目安。

- **スワップ（期間・概算）**：日次スワップが一定と仮定し、月額から購入通貨数量を推定して概算。  
  年スワップを計算後、\\(期間 = 年×(avg\\_hold\\_period/avg\\_hold\\_year)\\)で按分。

- **期待損益（概算）**：\\(スワップ（期間） − 期待ストレス損失\\)  
  ※これは期待値ベースの概算で、実際の相場の順序（いつ下がるか）やスプレッド拡大等は反映しません。
"""
)

st.info(
    "注意：このモデルは“確率つきギャップの期待値”です。"
    " 実際にギャップが起きた場合の瞬間的な評価損やスプレッド拡大は、期待値より厳しく出ることがあります。"
)

# ===========================
# Pattern input
# ===========================
st.subheader("パターン入力")
st.caption("列: name, GBP月額(1x), TRY月額(1x), MXN月額_1x, MXN月額_2x, MXN月額_3x  ※月額は円")

default = pd.DataFrame([
    {"name":"P2", "GBP":7000, "TRY":4000, "MXN_1x":0, "MXN_2x":0, "MXN_3x":5000},
    {"name":"CaseB", "GBP":6000, "TRY":4000, "MXN_1x":0, "MXN_2x":1000, "MXN_3x":5000},
])

patterns = st.data_editor(default, num_rows="dynamic", use_container_width=True)

# ===========================
# Core calculations
# ===========================
def expected_stress_loss(row) -> float:
    gbp = row["GBP"]
    tryy = row["TRY"]
    mxn1 = row["MXN_1x"]
    mxn2 = row["MXN_2x"]
    mxn3 = row["MXN_3x"]

    loss_gbp = gbp * months * 1 * gbp_gap * gbp_p
    loss_try = tryy * months * 1 * try_gap * try_p
    loss_mxn = (
        mxn1 * months * 1 * mxn_gap * mxn_p +
        mxn2 * months * 2 * mxn_gap * mxn_p +
        mxn3 * months * 3 * mxn_gap * mxn_p
    )
    return loss_gbp + loss_try + loss_mxn

def annual_swap_estimate(row) -> float:
    gbp = row["GBP"]
    tryy = row["TRY"]
    mxn1 = row["MXN_1x"]
    mxn2 = row["MXN_2x"]
    mxn3 = row["MXN_3x"]

    # monthly purchased units
    gbp_units = (gbp * 1) / gbp_rate
    try_units = (tryy * 1) / try_rate
    mxn_units = (mxn1*1 + mxn2*2 + mxn3*3) / mxn_rate  # leveraged MXN units

    gbp_annual = (gbp_units / 10_000) * gbp_swap_day * 365 * avg_hold_year
    try_annual = (try_units / 10_000) * try_swap_day * 365 * avg_hold_year
    mxn_annual = (mxn_units / 100_000) * mxn_swap_day * 365 * avg_hold_year  # MXN is per 100k

    return gbp_annual + try_annual + mxn_annual

def period_swap_from_annual(annual: float) -> float:
    return annual * (avg_hold_period / avg_hold_year)

rows = []
for _, r in patterns.iterrows():
    monthly_total = float(r["GBP"] + r["TRY"] + r["MXN_1x"] + r["MXN_2x"] + r["MXN_3x"])
    contrib_total = monthly_total * months  # C

    # base buffer (stress-free)
    base_buffer = target_margin * (m0 + contrib_total) - (e0 + contrib_total)
    if base_buffer < 0:
        base_buffer = 0.0

    exp_loss = expected_stress_loss(r)
    add_buffer = base_buffer + exp_loss

    annual_swap = annual_swap_estimate(r)
    period_swap = period_swap_from_annual(annual_swap)

    ratio_swap_buffer = (period_swap / add_buffer) if add_buffer > 0 else 0.0
    expected_pnl = period_swap - exp_loss
    ratio_pnl_buffer = (expected_pnl / add_buffer) if add_buffer > 0 else 0.0

    rows.append({
        "パターン": r["name"],
        "月額合計（円）": int(monthly_total),
        "ベース追加バッファ（円）": round(base_buffer),
        "期待ストレス損失（円）": round(exp_loss),
        "追加バッファ合計（円）": round(add_buffer),
        "スワップ（期間・概算 円）": round(period_swap),
        "期待損益（概算 円）": round(expected_pnl),
        "スワップ/追加バッファ（%）": round(ratio_swap_buffer * 100, 2),
        "期待損益/追加バッファ（%）": round(ratio_pnl_buffer * 100, 2),
    })

out = pd.DataFrame(rows).sort_values("スワップ/追加バッファ（%）", ascending=False)

st.subheader("結果")
st.dataframe(out, use_container_width=True)

st.caption("注：『期待損益』は期待値ベース（スワップ−期待ストレス損失）。実際の損益は相場の順序・スプレッド拡大等で変動します。")
