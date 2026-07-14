"""
utils/style.py
--------------
Streamlit custom CSS and stamp helper.
"""


def get_custom_css() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
    --bg:       #0D1117;
    --surface:  #161B22;
    --surface2: #21262D;
    --gold:     #C9A24B;
    --gold-lt:  #E3C47A;
    --green:    #3FB876;
    --red:      #E2574C;
    --blue:     #58A6FF;
    --text:     #E6EDF3;
    --muted:    #7D8590;
    --border:   #30363D;
}

/* ---- base ---- */
.stApp {
    background: linear-gradient(135deg, #0D1117 0%, #0A0F1A 100%);
    color: var(--text);
    font-family: 'Inter', sans-serif;
}
section[data-testid="stSidebar"] {
    background: #080C12;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMarkdown { color: var(--text); }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; }

/* ---- eyebrow ---- */
.eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 0.25rem;
}

/* ---- ticket (card) ---- */
.ticket {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.4rem 1.6rem 1.6rem;
    position: relative;
    margin-bottom: 1rem;
}
.ticket::before {
    content: "";
    position: absolute;
    left: 0; right: 0; top: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--gold), transparent);
    border-radius: 12px 12px 0 0;
}
.ticket-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    color: var(--muted);
    text-transform: uppercase;
    margin: 1rem 0 0.3rem;
    border-bottom: 1px dashed var(--border);
    padding-bottom: 0.3rem;
}
.ticket-perf { border-top: 1px dashed var(--border); margin: 1rem 0; }

/* ---- price display ---- */
.price-mono {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 2.6rem;
    color: var(--gold);
    line-height: 1;
    margin: 0.4rem 0 0.1rem;
}
.price-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--muted);
    margin: 0.25rem 0;
}

/* ---- verdict stamp ---- */
.stamp {
    display: inline-block;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 800;
    font-size: 1.1rem;
    letter-spacing: 0.08em;
    padding: 0.5rem 1.4rem;
    border-radius: 6px;
    transform: rotate(-2deg);
    margin-top: 0.8rem;
}
.stamp-green { background: rgba(63,184,118,0.12); color: var(--green); border: 2px solid var(--green); }
.stamp-red   { background: rgba(226,87,76,0.12);  color: var(--red);   border: 2px solid var(--red); }
.stamp-gold  { background: rgba(201,162,75,0.12); color: var(--gold);  border: 2px solid var(--gold); }
.stamp-blue  { background: rgba(88,166,255,0.12); color: var(--blue);  border: 2px solid var(--blue); }

/* ---- vfm pill ---- */
.vfm-pill {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    background: var(--surface2);
    border: 1px solid var(--border);
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    color: var(--muted);
    margin-top: 0.4rem;
}

/* ---- metric card ---- */
.metric-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.metric-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--gold);
}
.metric-lbl {
    font-size: 0.72rem;
    color: var(--muted);
    margin-top: 0.2rem;
    font-family: 'Inter', sans-serif;
}

/* ---- buttons ---- */
div.stButton > button {
    background: var(--gold);
    color: #0D1117;
    border: none;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    transition: all 0.15s ease;
    width: 100%;
}
div.stButton > button:hover {
    background: var(--gold-lt);
    transform: translateY(-1px);
}

/* ---- feature tag ---- */
.feature-tag {
    display: inline-block;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--muted);
    margin: 2px;
}

/* ---- alert row ---- */
.alert-row {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.7rem 1rem;
    margin: 0.4rem 0;
    display: flex;
    justify-content: space-between;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
}
</style>
"""


def stamp_class(category: str) -> str:
    """
    Map a price_category label to the appropriate CSS stamp class.

    Labels from helper.price_category:
        "Great Deal 🔥"         → green
        "Good Deal 👍"          → green
        "Fair Price ✅"         → gold
        "Overpriced ❌"         → red
        "Suspicious Listing 🚨" → blue (warning)
    """
    cat = category.lower()
    if "great deal" in cat or "good deal" in cat:
        return "stamp-green"
    if "overpriced" in cat:
        return "stamp-red"
    if "suspicious" in cat:
        return "stamp-blue"
    return "stamp-gold"   # fair price or unknown
