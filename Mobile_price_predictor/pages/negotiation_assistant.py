"""
pages/negotiation_assistant.py
-------------------------------
Gemini-powered negotiation strategy advisor.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from utils.style  import get_custom_css
from utils.helper import BRANDS

st.set_page_config(
    page_title="Negotiation Assistant",
    page_icon="🤝",
    layout="wide",
)
st.markdown(get_custom_css(), unsafe_allow_html=True)

st.markdown('<div class="eyebrow">AI · POWERED BY GEMINI</div>', unsafe_allow_html=True)
st.title("🤝 Negotiation Assistant")
st.caption("Tell me the deal — get a strategy, a counter-offer script, and red flags to watch for.")

# ── Sidebar — API key ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 Gemini API Key")
    api_key = st.text_input(
        "Enter your Gemini API key",
        type="password",
        help="Get a free key at https://aistudio.google.com/",
    )
    st.caption("Your key is never stored — session only.")
    st.markdown("---")
    st.markdown("**Tips for best results:**")
    st.markdown("- Paste the predicted price from the Predictor page")
    st.markdown("- Mention the seller's platform (OLX, Flipkart, etc.)")
    st.markdown("- Say if the purchase is urgent")

# ── Deal input form ───────────────────────────────────────────────────────────
st.markdown('<div class="ticket">', unsafe_allow_html=True)
st.markdown('<div class="ticket-label">DEAL DETAILS</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    brand     = st.selectbox("Brand", BRANDS)
    condition = st.radio("Condition", ["New", "Used"], horizontal=True)
with c2:
    asking_price = st.number_input("Seller's Asking Price (₹)", 0, 300_000, 25_000, 500)
    model_price  = st.number_input(
        "AI Predicted Fair Price (₹)", 0, 300_000, 22_000, 500,
        help="Copy from the Predictor page",
    )
with c3:
    ram     = st.selectbox("RAM (GB)",     [2, 3, 4, 6, 8, 12, 16], index=4)
    storage = st.selectbox("Storage (GB)", [32, 64, 128, 256, 512],   index=2)

extra_notes = st.text_area(
    "Any extra context?",
    placeholder=(
        "e.g. The seller says it's 6 months old, has a cracked back cover, "
        "still has 6 months warranty, selling on OLX…"
    ),
)
role = st.radio("I am the…", ["Buyer", "Seller"], horizontal=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Chat state ────────────────────────────────────────────────────────────────
if "nego_messages" not in st.session_state:
    st.session_state.nego_messages = []


def _build_system_prompt() -> str:
    diff     = asking_price - model_price
    diff_pct = (diff / model_price * 100) if model_price > 0 else 0
    verdict  = (
        "OVERPRICED"    if diff_pct > 10
        else "UNDERPRICED" if diff_pct < -10
        else "FAIRLY PRICED"
    )
    return f"""You are an expert mobile phone deal negotiation advisor for the Indian market.

DEAL CONTEXT:
- Phone: {brand} | {condition} | {ram}GB RAM | {storage}GB Storage
- Seller asking: ₹{asking_price:,}
- AI fair market estimate: ₹{model_price:,}
- Price difference: {'+'if diff >= 0 else ''}₹{diff:,} ({diff_pct:+.1f}%) → {verdict}
- User role: {role}
- Extra notes: {extra_notes or 'None provided'}

YOUR JOB:
1. Give a clear verdict on whether this is a good deal.
2. Provide a specific counter-offer price with reasoning.
3. Give a ready-to-use negotiation message/script the user can send.
4. List 3–5 red flags to watch for or questions to ask the seller.
5. State a "walk away" price threshold.

Keep responses conversational, practical, and specific to Indian market norms.
Use ₹ for prices. Be direct — don't hedge everything."""


def _call_gemini(messages: list, key: str) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        gemini = genai.GenerativeModel(
            model_name="gemini-2.0-flash-lite",
            system_instruction=_build_system_prompt(),
        )
        history = [
            {"role": m["role"], "parts": [m["content"]]}
            for m in messages[:-1]
        ]
        chat = gemini.start_chat(history=history)
        resp = chat.send_message(messages[-1]["content"])
        return resp.text
    except Exception as exc:
        return (
            f"❌ Gemini error: {exc}\n\n"
            "Make sure your API key is valid and you have quota remaining."
        )


# ── Action buttons ────────────────────────────────────────────────────────────
btn_col, clr_col = st.columns([3, 1])
with btn_col:
    analyse_btn = st.button("🔍 Analyse This Deal", use_container_width=True)
with clr_col:
    if st.button("🗑 Clear Chat", use_container_width=True):
        st.session_state.nego_messages = []
        st.rerun()

if analyse_btn:
    if not api_key:
        st.error("Please enter your Gemini API key in the sidebar.")
    elif asking_price == 0 and model_price == 0:
        st.error("Please enter at least the asking price.")
    else:
        opening = (
            f"Analyse this {brand} deal: asking ₹{asking_price:,}, "
            f"AI estimate ₹{model_price:,}. I am the {role.lower()}. "
            f"{extra_notes or ''}"
        )
        st.session_state.nego_messages.append({"role": "user", "content": opening})
        with st.spinner("Consulting the negotiation desk…"):
            reply = _call_gemini(st.session_state.nego_messages, api_key)
        st.session_state.nego_messages.append({"role": "model", "content": reply})

# Display conversation
for msg in st.session_state.nego_messages:
    role_key = "user" if msg["role"] == "user" else "assistant"
    st.chat_message(role_key).write(msg["content"])

# Follow-up input
if st.session_state.nego_messages:
    follow_up = st.chat_input("Ask a follow-up question…")
    if follow_up:
        if not api_key:
            st.error("Please enter your Gemini API key in the sidebar.")
        else:
            st.session_state.nego_messages.append({"role": "user", "content": follow_up})
            with st.spinner("Thinking…"):
                reply = _call_gemini(st.session_state.nego_messages, api_key)
            st.session_state.nego_messages.append({"role": "model", "content": reply})
            st.rerun()
else:
    st.info(
        "Fill in the deal details above and click **Analyse This Deal** "
        "to get your negotiation strategy."
    )
