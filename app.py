"""BTC 5m Predictor: live dashboard.  Run with:  streamlit run app.py"""
from datetime import datetime, timezone

import plotly.graph_objects as go
import streamlit as st

from predictor import INTERVAL_MINUTES, fetch_snapshot

st.set_page_config(page_title="BTC 5m Predictor", page_icon="⚡", layout="wide")

st.markdown(
    """
<style>
.stApp { background: radial-gradient(1200px 600px at 50% -10%, #1b1440 0%, #0b0b16 55%); }
#MainMenu, footer, header { visibility: hidden; }
.hero { text-align:center; padding: 2.5rem 0 1rem; }
.hero h1 { font-size: 3.4rem; font-weight: 800; margin: 0;
  background: linear-gradient(90deg,#f7931a,#ffcf70 45%,#a78bfa); -webkit-background-clip:text;
  -webkit-text-fill-color: transparent; }
.hero p { color:#9aa0b8; font-size:1.15rem; margin-top:.6rem; }
.pills { display:flex; gap:.5rem; justify-content:center; flex-wrap:wrap; margin-top:1rem; }
.pill { border:1px solid #2b2b4a; background:#14142a; color:#b9bdd6; border-radius:999px;
  padding:.25rem .8rem; font-size:.8rem; }
.card { background: linear-gradient(160deg,#16162e,#101022); border:1px solid #2b2b4a;
  border-radius:18px; padding:1.3rem 1.5rem; height:100%; }
.label { color:#8a8fb0; font-size:.78rem; letter-spacing:.12em; text-transform:uppercase; }
.big { font-size:clamp(1.7rem,2.6vw,2.8rem); white-space:nowrap; font-weight:800; color:#fff; line-height:1.1; }
.up { color:#22e39b; text-shadow:0 0 24px #22e39b66; }
.down { color:#ff5470; text-shadow:0 0 24px #ff547066; }
.sub { color:#9aa0b8; font-size:.9rem; }
.live { display:inline-block; width:9px; height:9px; border-radius:50%; background:#22e39b;
  box-shadow:0 0 10px #22e39b; margin-right:.4rem; animation:pulse 1.4s infinite; }
@keyframes pulse { 50% { opacity:.25; } }
.disc { color:#6c7190; font-size:.78rem; text-align:center; padding:2rem 0 1rem; }
</style>
<div class="hero">
  <h1>⚡ BTC 5-Minute Predictor</h1>
  <p>Live UP / DOWN call for the current 5-minute window, built from real Binance market microstructure.</p>
  <div class="pills">
    <span class="pill">Order-book imbalance</span><span class="pill">Trade pressure</span>
    <span class="pill">VWAP deviation</span><span class="pill">Volume spikes</span>
    <span class="pill">Volatility</span><span class="pill">Tick momentum</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []      # resolved predictions
    st.session_state.pending = None    # prediction for the running window


def update_scoreboard(snap):
    """Lock in the call for each window, then grade it once the window closes."""
    pending = st.session_state.pending
    if pending and snap.interval_start > pending["start"]:
        went_up = snap.open_price >= pending["open"]
        pending["actual"] = "UP" if went_up else "DOWN"
        pending["hit"] = pending["actual"] == pending["direction"]
        st.session_state.history.insert(0, pending)
        st.session_state.history = st.session_state.history[:50]
        pending = None
    if pending is None or snap.interval_start > pending["start"]:
        pending = {"start": snap.interval_start, "open": snap.open_price}
    pending["direction"] = snap.direction  # keeps updating; the last call before close counts
    pending["confidence"] = snap.confidence
    st.session_state.pending = pending


def gauge(score):
    fig = go.Figure(go.Indicator(
        mode="gauge", value=score * 100,
        gauge={
            "axis": {"range": [-100, 100], "tickcolor": "#555", "tickfont": {"color": "#777"}},
            "bar": {"color": "#22e39b" if score >= 0 else "#ff5470", "thickness": 0.35},
            "bgcolor": "#0e0e1c", "borderwidth": 0,
            "steps": [{"range": [-100, 0], "color": "#2a1320"}, {"range": [0, 100], "color": "#10281f"}],
        },
    ))
    fig.update_layout(height=180, margin=dict(l=20, r=20, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def sparkline(snap):
    up = snap.closes[-1] >= snap.open_price
    color = "#22e39b" if up else "#ff5470"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=snap.times, y=snap.closes, mode="lines", line=dict(color=color, width=2.5),
                             fill="tozeroy", fillcolor="rgba(34,227,155,.07)" if up else "rgba(255,84,112,.07)"))
    fig.add_hline(y=snap.open_price, line_dash="dot", line_color="#8a8fb0",
                  annotation_text="window open", annotation_font_color="#8a8fb0")
    lo, hi = min(snap.closes), max(snap.closes)
    pad = (hi - lo) * 0.15 or 1
    fig.update_layout(height=230, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      xaxis=dict(showgrid=False, color="#666"),
                      yaxis=dict(range=[lo - pad, hi + pad], gridcolor="#1e1e38", color="#666"))
    return fig


@st.fragment(run_every=2)
def live_panel():
    try:
        snap = fetch_snapshot()
    except Exception as e:  # network hiccup / rate limit: keep the page alive
        st.warning(f"Waiting for Binance… ({type(e).__name__})")
        return
    update_scoreboard(snap)

    secs = max(0, int((snap.interval_end - datetime.now(timezone.utc)).total_seconds()))
    cls = "up" if snap.direction == "UP" else "down"
    arrow = "🚀" if snap.direction == "UP" else "📉"

    c1, c2, c3 = st.columns([1.1, 1.3, 1])
    with c1:
        st.markdown(f"""<div class="card"><div class="label"><span class="live"></span>BTC / USDT · Binance</div>
        <div class="big">${snap.price:,.2f}</div>
        <div class="sub">{snap.momentum_pct:+.3f}% since window open · ${snap.open_price:,.2f}</div>
        <br><div class="label">Window closes in</div>
        <div class="big" style="font-size:2rem">{secs // 60}:{secs % 60:02d}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="card"><div class="label">Prediction · next {INTERVAL_MINUTES} min</div>
        <div class="big {cls}">{arrow} {snap.direction}</div>
        <div class="sub">Signal strength {snap.confidence}/99 (not a win probability)</div></div>""",
                    unsafe_allow_html=True)
        st.plotly_chart(gauge(snap.score), width="stretch", config={"displayModeBar": False})
    with c3:
        h = st.session_state.history
        hits = sum(x["hit"] for x in h)
        rate = f"{hits / len(h) * 100:.0f}%" if h else "—"
        st.markdown(f"""<div class="card"><div class="label">Live track record</div>
        <div class="big">{rate}</div><div class="sub">{hits} / {len(h)} windows called correctly this session</div>
        <br><div class="label">Recent calls</div>
        <div style="font-size:1.3rem;letter-spacing:.2em">{''.join('🟢' if x['hit'] else '🔴' for x in h[:12]) or '<span class="sub">collecting…</span>'}</div>
        </div>""", unsafe_allow_html=True)

    st.plotly_chart(sparkline(snap), width="stretch", config={"displayModeBar": False})

    m = st.columns(5)
    m[0].metric("Order book imbalance", f"{snap.imbalance:+.2f}")
    m[1].metric("Trade pressure", f"{snap.pressure:+.2f}")
    m[2].metric("VWAP deviation", f"{snap.vwap_dev:+.3f}%")
    m[3].metric("Volume spike", f"{snap.volume_spike:.1f}×")
    m[4].metric("Volatility (1m σ)", f"{snap.volatility:.3f}%")


live_panel()

st.markdown(
    '<div class="disc">Experimental, for research and education only. 5-minute price moves are extremely noisy '
    "and often close to random. Not financial advice.</div>",
    unsafe_allow_html=True,
)
