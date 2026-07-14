"""
utils/pdf.py
------------
Generates a professional PDF valuation report using fpdf2.
Returns raw PDF bytes, or b"" if fpdf2 is not installed.
"""

from datetime import datetime


def generate_report(data: dict) -> bytes:
    """
    Build and return a PDF valuation report as raw bytes.

    Expected keys in `data`
    -----------------------
    brand, ram, storage, battery, camera, screen, fiveg,
    age, condition, predicted, low, high, vfm, verdict,
    category, listed (optional), depreciation (optional list of (age, price))
    """
    try:
        from fpdf import FPDF
    except ImportError:
        return b""

    # ---------------------------------------------------------------------------
    # Custom subclass — header and footer
    # ---------------------------------------------------------------------------
    class PDF(FPDF):
        def header(self):
            # Dark background
            self.set_fill_color(13, 17, 23)
            self.rect(0, 0, 210, 297, "F")
            # Gold top bar
            self.set_fill_color(201, 162, 75)
            self.rect(0, 0, 210, 4, "F")
            # Title
            self.set_font("Helvetica", "B", 18)
            self.set_text_color(201, 162, 75)
            self.set_y(12)
            self.cell(0, 8, "PHONE VALUATION REPORT", align="C")
            # Sub-title
            self.set_font("Helvetica", "", 9)
            self.set_text_color(125, 133, 144)
            self.ln(7)
            self.cell(0, 5, "The Appraisal Desk  ·  AI-Powered Mobile Price Intelligence", align="C")
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(125, 133, 144)
            self.cell(
                0, 5,
                f"Generated {datetime.now().strftime('%d %b %Y  %H:%M')}  |  Page {self.page_no()}",
                align="C",
            )

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------
    def section(title: str):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(201, 162, 75)
        pdf.set_fill_color(33, 38, 45)
        pdf.cell(0, 7, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def row(label: str, value: str, color=(230, 237, 243)):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(125, 133, 144)
        pdf.cell(70, 6, label)
        pdf.set_text_color(*color)
        pdf.cell(0, 6, str(value), new_x="LMARGIN", new_y="NEXT")

    # ---------------------------------------------------------------------------
    # Build document
    # ---------------------------------------------------------------------------
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    predicted = data.get("predicted", 0)
    low       = data.get("low",       0)
    high      = data.get("high",      0)
    listed    = data.get("listed",    0)
    vfm       = data.get("vfm",       "N/A")
    verdict   = data.get("verdict",   "")
    category  = data.get("category",  "")

    # Colour for verdict stamp
    if "Good" in verdict or "Great" in verdict:
        verdict_color = (63, 184, 118)
    elif "Overpriced" in verdict or "Avoid" in verdict:
        verdict_color = (226, 87, 76)
    else:
        verdict_color = (201, 162, 75)

    # --- Appraised value ---
    section("APPRAISED VALUE")
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(201, 162, 75)
    pdf.cell(0, 14, f"Rs. {predicted:,.0f}", new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(125, 133, 144)
    pdf.cell(
        0, 6,
        f"Expected range:  Rs. {low:,.0f}  –  Rs. {high:,.0f}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )

    if verdict:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*verdict_color)
        pdf.cell(0, 8, verdict, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # --- Specification sheet ---
    section("SPECIFICATION SHEET")
    specs = [
        ("Brand",       data.get("brand", "")),
        ("RAM",         f"{data.get('ram', '')} GB"),
        ("Storage",     f"{data.get('storage', '')} GB"),
        ("Battery",     f"{data.get('battery', '')} mAh"),
        ("Camera",      f"{data.get('camera', '')} MP"),
        ("Screen Size", f"{data.get('screen', '')} in"),
        ("5G Support",  data.get("fiveg", "")),
        ("Phone Age",   f"{data.get('age', '')} years"),
        ("Condition",   data.get("condition", "")),
    ]
    for label, val in specs:
        row(label, val)
    pdf.ln(5)

    # --- Price verdict (only when listed price is provided) ---
    if listed and listed > 0:
        section("PRICE VERDICT")
        row("Listed / Asking Price", f"Rs. {listed:,.0f}")
        row("Model Estimate",        f"Rs. {predicted:,.0f}")
        diff = listed - predicted
        row(
            "Difference",
            f"{'+'if diff >= 0 else ''}Rs. {diff:,.0f}",
            (226, 87, 76) if diff > 0 else (63, 184, 118),
        )
        row("Category", category, verdict_color)
        pdf.ln(5)

    # --- Scores ---
    section("SCORES")
    row("Value for Money Score", f"{vfm} / 100")
    pdf.ln(5)

    # --- Depreciation table ---
    depreciation = data.get("depreciation", [])
    if depreciation:
        section("DEPRECIATION FORECAST")
        for yr, price in depreciation:
            row(f"Age {yr:.1f} yr", f"Rs. {price:,.0f}")
        pdf.ln(5)

    # --- Disclaimer ---
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(80, 86, 96)
    pdf.multi_cell(
        0, 5,
        "Disclaimer: This report is generated by an AI model trained on synthetic data. "
        "Prices are indicative only and may differ from actual market values. "
        "Always verify with current marketplace listings before making purchase decisions.",
    )

    try:
        return bytes(pdf.output())
    except Exception as exc:
        print(f"[pdf] output error: {exc}")
        return b""
