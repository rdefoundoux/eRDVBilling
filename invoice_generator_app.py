import streamlit as st
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import base64
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage

# --------------------------------------------------------------------------------------
# Page + assets
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Groupe eRDV Invoice Studio",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOGO_PATH = Path(__file__).parent / "assets" / "logo.jpeg"

@st.cache_data(show_spinner=False)
def _load_default_logo() -> bytes:
    try:
        return LOGO_PATH.read_bytes()
    except Exception:
        return b""

DEFAULT_LOGO_BYTES = _load_default_logo()

def _logo_data_uri(data: bytes) -> str:
    if not data:
        return ""
    b64 = base64.b64encode(data).decode("ascii")
    # jpeg works for both jpg/png in most browsers via image/*; use image/jpeg as safe default
    return f"data:image/jpeg;base64,{b64}"

# --------------------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------------------
if "entries" not in st.session_state:
    st.session_state.entries = []
if "counter" not in st.session_state:
    st.session_state.counter = 0
if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "logo" not in st.session_state:
    st.session_state.logo = DEFAULT_LOGO_BYTES

# --------------------------------------------------------------------------------------
# Theme CSS (dark mode driven by a wrapper class we inject on every rerun)
# --------------------------------------------------------------------------------------
def inject_css(theme: str) -> None:
    is_dark = theme == "dark"
    palette = {
        "bg": "#0b1220" if is_dark else "#f6f7fb",
        "bg2": "#0e162a" if is_dark else "#eef1f8",
        "surface": "rgba(15,23,42,.72)" if is_dark else "rgba(255,255,255,.85)",
        "surface_solid": "#0f1a30" if is_dark else "#ffffff",
        "text": "#e5e7eb" if is_dark else "#0f172a",
        "muted": "#94a3b8" if is_dark else "#64748b",
        "line": "rgba(148,163,184,.16)" if is_dark else "rgba(15,23,42,.08)",
        "primary": "#3b82f6" if is_dark else "#123a73",
        "primary2": "#60a5fa" if is_dark else "#2b6cb0",
        "accent": "#22d3ee" if is_dark else "#0ea5e9",
        "shadow": "0 20px 50px rgba(0,0,0,.35)" if is_dark else "0 20px 50px rgba(15,23,42,.10)",
    }
    css = f"""
    <style>
    :root {{
      --bg: {palette['bg']};
      --bg2: {palette['bg2']};
      --surface: {palette['surface']};
      --surface-solid: {palette['surface_solid']};
      --text: {palette['text']};
      --muted: {palette['muted']};
      --line: {palette['line']};
      --primary: {palette['primary']};
      --primary2: {palette['primary2']};
      --accent: {palette['accent']};
      --shadow: {palette['shadow']};
      --radius: 20px;
    }}
    /* Force background + text across Streamlit chrome */
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
      background: radial-gradient(1200px 600px at 10% -10%, var(--bg2), var(--bg) 60%) !important;
      color: var(--text) !important;
    }}
    [data-testid="stHeader"] {{ background: transparent !important; }}
    [data-testid="stSidebar"] > div {{
      background: var(--surface) !important;
      backdrop-filter: blur(14px);
      border-right: 1px solid var(--line);
    }}
    [data-testid="stSidebar"] * {{ color: var(--text) !important; }}
    .block-container {{
      padding-top: 1rem; padding-bottom: 3rem; max-width: 1280px;
    }}
    /* Typography color for main body */
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
      color: var(--text);
    }}
    .stMarkdown p, .stMarkdown li {{ color: var(--text); }}
    .stCaption, .st-emotion-cache-1pbsqtx, small {{ color: var(--muted) !important; }}
    /* Hero */
    .hero {{
      background: linear-gradient(135deg, rgba(18,58,115,.96), rgba(43,108,176,.92));
      color: #ffffff;
      border-radius: 26px;
      padding: 1.25rem 1.5rem;
      box-shadow: var(--shadow);
      display: flex; gap: 1.25rem; align-items: center; justify-content: space-between; flex-wrap: wrap;
      border: 1px solid rgba(255,255,255,.08);
    }}
    .hero .left {{ display:flex; align-items:center; gap: 1rem; }}
    .hero .logo-wrap {{
      width: 74px; height: 74px; border-radius: 18px;
      background: rgba(255,255,255,.96);
      display: grid; place-items: center;
      padding: 8px;
      box-shadow: 0 8px 20px rgba(0,0,0,.15);
    }}
    .hero .logo-wrap img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
    .hero h1 {{ margin: 0; font-size: clamp(1.5rem, 2vw, 2.1rem); line-height: 1.1; color:#fff; }}
    .hero p {{ margin: .25rem 0 0; opacity: .92; max-width: 62ch; color:#fff; }}
    .hero .pill {{
      display:inline-flex; align-items:center; gap:.4rem;
      padding: .32rem .7rem; border-radius: 999px;
      background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.18);
      font-size:.78rem; font-weight:600; color:#fff;
    }}
    /* KPI cards */
    .kpi {{
      background: var(--surface); border: 1px solid var(--line);
      border-radius: var(--radius); padding: 1rem 1.1rem; box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .kpi .label {{ color: var(--muted); font-size: .82rem; letter-spacing:.02em; text-transform: uppercase; }}
    .kpi .value {{ font-size: 1.7rem; font-weight: 750; margin-top: .25rem; color: var(--text); }}
    .kpi .delta {{ font-size:.78rem; color: var(--accent); margin-top:.15rem; }}
    /* Panel */
    .panel {{
      background: var(--surface); border: 1px solid var(--line);
      border-radius: var(--radius); box-shadow: var(--shadow);
      padding: 1.1rem 1.15rem; backdrop-filter: blur(10px);
    }}
    .panel h3 {{ margin-top: 0; }}
    /* Line-item row */
    .row {{
      display:flex; align-items:center; justify-content: space-between; gap:.75rem;
      padding: .65rem .8rem; margin-bottom:.4rem;
      border: 1px solid var(--line); border-radius: 14px;
      background: var(--surface-solid);
    }}
    .row .desc {{ font-weight: 650; }}
    .row .meta {{ color: var(--muted); font-size:.82rem; }}
    .row .amt {{ font-weight: 700; }}
    /* Totals */
    .totals {{
      margin-top:.8rem; padding: .9rem 1rem;
      background: linear-gradient(135deg, rgba(59,130,246,.10), rgba(14,165,233,.10));
      border: 1px solid var(--line); border-radius: 16px;
    }}
    .totals .r {{ display:flex; justify-content: space-between; padding:.15rem 0; }}
    .totals .r.total {{ font-size:1.15rem; font-weight:800; border-top:1px dashed var(--line); margin-top:.4rem; padding-top:.5rem; color: var(--text); }}
    /* Buttons */
    div[data-testid="stButton"] > button, .stDownloadButton button {{
      border-radius: 12px !important;
      border: 1px solid transparent !important;
      padding: .7rem 1rem !important;
      font-weight: 650 !important;
      background: linear-gradient(135deg, var(--primary), var(--primary2)) !important;
      color: #ffffff !important;
      box-shadow: 0 6px 16px rgba(43,108,176,.25);
      transition: transform .05s ease, box-shadow .2s ease;
    }}
    div[data-testid="stButton"] > button:hover, .stDownloadButton button:hover {{
      transform: translateY(-1px);
      box-shadow: 0 10px 24px rgba(43,108,176,.35);
    }}
    /* Inputs */
    .stTextInput input, .stNumberInput input, .stDateInput input, textarea, select {{
      border-radius: 12px !important;
      background: var(--surface-solid) !important;
      color: var(--text) !important;
      border: 1px solid var(--line) !important;
    }}
    .stTextInput label, .stNumberInput label, .stDateInput label, .stSelectbox label, .stFileUploader label, .stRadio label {{
      color: var(--muted) !important; font-weight: 600 !important;
    }}
    /* Radio pill look */
    div[role="radiogroup"] > label {{
      background: var(--surface-solid);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: .35rem .8rem;
      margin-right: .35rem;
    }}
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ gap: .35rem; }}
    .stTabs [data-baseweb="tab"] {{
      background: var(--surface-solid);
      border: 1px solid var(--line);
      border-radius: 12px 12px 0 0;
      padding: .55rem .9rem;
    }}
    .stTabs [aria-selected="true"] {{
      background: linear-gradient(135deg, var(--primary), var(--primary2)) !important;
      color: #fff !important;
      border-color: transparent !important;
    }}
    hr {{ border-color: var(--line); }}
    /* Alerts */
    .stAlert {{ background: var(--surface-solid) !important; color: var(--text) !important; border:1px solid var(--line); border-radius: 14px; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

inject_css(st.session_state.theme)

# --------------------------------------------------------------------------------------
# Sidebar — workspace controls
# --------------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Workspace")
    theme = st.radio(
        "Theme",
        ["Light", "Dark"],
        horizontal=True,
        index=0 if st.session_state.theme == "light" else 1,
    )
    new_theme = "dark" if theme == "Dark" else "light"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    st.markdown("### 🖼 Branding")
    upload = st.file_uploader("Replace logo (optional)", type=["png", "jpg", "jpeg"])
    if upload is not None:
        st.session_state.logo = upload.read()
    if st.session_state.logo:
        st.image(st.session_state.logo, caption="Current logo", use_container_width=True)
    if st.button("Reset to default logo", use_container_width=True):
        st.session_state.logo = DEFAULT_LOGO_BYTES
        st.rerun()

    st.markdown("### 💰 Tax")
    tax_rate = st.number_input("Tax rate (%)", min_value=0.0, max_value=100.0, value=14.975, step=0.1)

    st.markdown("### ⚡ Actions")
    if st.button("Clear all line items", use_container_width=True):
        st.session_state.entries = []
        st.rerun()

    st.caption("Modern layout · cleaner spacing · faster invoice workflow.")

# --------------------------------------------------------------------------------------
# Hero
# --------------------------------------------------------------------------------------
logo_uri = _logo_data_uri(st.session_state.logo)
logo_html = f'<img src="{logo_uri}" alt="Groupe eRDV logo"/>' if logo_uri else '<div style="font-weight:800;color:#123a73">eRDV</div>'
st.markdown(
    f"""
    <div class="hero">
      <div class="left">
        <div class="logo-wrap">{logo_html}</div>
        <div>
          <h1>Groupe eRDV Invoice Studio</h1>
          <p>Craft polished invoices in seconds — live totals, clean previews, and branded PDF export.</p>
        </div>
      </div>
      <div style="text-align:right;">
        <span class="pill">✨ Modern workflow</span>
        <div style="margin-top:.5rem; font-size:.82rem; opacity:.9;">Streamlit-powered · {datetime.now().strftime('%b %d, %Y')}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

# --------------------------------------------------------------------------------------
# KPIs
# --------------------------------------------------------------------------------------
subtotal = sum(x["qty"] * x["rate"] for x in st.session_state.entries)
tax = subtotal * tax_rate / 100
total = subtotal + tax

k1, k2, k3, k4 = st.columns(4)
kpis = [
    (k1, "Line items", str(len(st.session_state.entries)), ""),
    (k2, "Subtotal", f"${subtotal:,.2f}", ""),
    (k3, f"Tax ({tax_rate:g}%)", f"${tax:,.2f}", ""),
    (k4, "Total due", f"${total:,.2f}", "Auto-updated"),
]
for col, label, val, delta in kpis:
    with col:
        st.markdown(
            f'<div class="kpi"><div class="label">{label}</div><div class="value">{val}</div>'
            + (f'<div class="delta">{delta}</div>' if delta else "")
            + "</div>",
            unsafe_allow_html=True,
        )

st.write("")

# --------------------------------------------------------------------------------------
# Main tabs
# --------------------------------------------------------------------------------------
tab_details, tab_items, tab_preview = st.tabs(["📇 Company & Client", "➕ Line items", "👀 Preview & Export"])

with tab_details:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Invoice details")
    a, b = st.columns(2)
    with a:
        company = st.text_input("Your company", "Groupe eRDV inc.")
        company_addr = st.text_area("Company address", "Saint-Jean-sur-Richelieu, QC, Canada", height=80)
    with b:
        client = st.text_input("Client name", "Soho Square Solutions")
        client_addr = st.text_area("Client address", "", height=80, placeholder="Optional")

    c, d, e = st.columns(3)
    with c:
        invoice_no = st.text_input("Invoice #", f'INV-{datetime.now().strftime("%Y%m%d")}-001')
    with d:
        invoice_date = st.date_input("Invoice date", datetime.now())
    with e:
        due_date = st.date_input("Due date", datetime.now() + timedelta(days=15))

    notes = st.text_area("Notes / payment terms", "Payment due within 15 days. Thank you for your business.", height=80)
    st.markdown("</div>", unsafe_allow_html=True)

with tab_items:
    left, right = st.columns([1, 1.15])

    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Add a line item")
        with st.form("entry_form", clear_on_submit=True):
            desc = st.text_input("Description", placeholder="e.g. Consulting — Senior Developer")
            f1, f2 = st.columns(2)
            with f1:
                days = st.number_input(
                    "Days worked",
                    min_value=0.0, value=1.0, step=0.5,
                    help="Half days supported (e.g. 0.5, 1.5, 2.5).",
                )
            with f2:
                hours_per_day = st.number_input(
                    "Hours per day",
                    min_value=0.0, value=8.0, step=0.5,
                    help="How many hours you worked in a full day.",
                )
            rate = st.number_input("Rate per hour ($)", min_value=0.0, value=80.0, step=5.0)

            total_hours = days * hours_per_day
            line_amount = total_hours * rate
            st.markdown(
                f'<div class="totals" style="margin-top:.4rem;">'
                f'<div class="r"><span>Total hours</span><span><b>{total_hours:.2f}</b> h</span></div>'
                f'<div class="r"><span>Line amount</span><span><b>${line_amount:,.2f}</b></span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            submitted = st.form_submit_button("➕  Add line item", use_container_width=True)
            if submitted and desc.strip():
                st.session_state.counter += 1
                st.session_state.entries.append(
                    {
                        "id": st.session_state.counter,
                        "desc": desc.strip(),
                        "days": days,
                        "hours_per_day": hours_per_day,
                        "qty": total_hours,
                        "rate": rate,
                    }
                )
                st.rerun()
        st.caption("Tip: use 0.5 for a half day. Total hours = Days × Hours/day. Line amount = Total hours × Rate.")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Current line items")
        if not st.session_state.entries:
            st.info("No line items yet. Add your first one to see live totals.")
        else:
            for e in st.session_state.entries:
                amount = e["qty"] * e["rate"]
                days_val = e.get("days")
                hpd_val = e.get("hours_per_day")
                if days_val is not None and hpd_val is not None:
                    meta = (
                        f"{days_val:g} day{'s' if days_val != 1 else ''} × {hpd_val:g} h/day "
                        f"= {e['qty']:.2f} h × ${e['rate']:.2f}/h"
                    )
                else:
                    meta = f"{e['qty']:.2f} × ${e['rate']:.2f}"
                cols = st.columns([6, 2, 1])
                with cols[0]:
                    st.markdown(
                        f'<div class="row"><div><div class="desc">{e["desc"]}</div>'
                        f'<div class="meta">{meta}</div></div>'
                        f'<div class="amt">${amount:,.2f}</div></div>',
                        unsafe_allow_html=True,
                    )
                with cols[2]:
                    if st.button("🗑", key=f"rm{e['id']}", help="Remove this line"):
                        st.session_state.entries = [
                            x for x in st.session_state.entries if x["id"] != e["id"]
                        ]
                        st.rerun()

            st.markdown(
                f"""
                <div class="totals">
                  <div class="r"><span>Subtotal</span><span>${subtotal:,.2f}</span></div>
                  <div class="r"><span>Tax ({tax_rate:g}%)</span><span>${tax:,.2f}</span></div>
                  <div class="r total"><span>Total due</span><span>${total:,.2f}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

with tab_preview:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Preview")
    if not st.session_state.entries:
        st.info("Add line items to enable preview & PDF export.")
    else:
        pa, pb = st.columns([1, 1.6])
        with pa:
            if st.session_state.logo:
                st.image(st.session_state.logo, width=180)
            st.markdown(f"**{company}**")
            st.caption(company_addr)
        with pb:
            st.markdown(f"### Invoice `{invoice_no}`")
            st.markdown(f"**Bill to:** {client}")
            if client_addr:
                st.caption(client_addr)
            st.markdown(
                f"**Date:** {invoice_date.strftime('%b %d, %Y')}  \n"
                f"**Due:** {due_date.strftime('%b %d, %Y')}"
            )

        st.divider()
        for e in st.session_state.entries:
            amount = e["qty"] * e["rate"]
            days_val = e.get("days")
            hpd_val = e.get("hours_per_day")
            if days_val is not None and hpd_val is not None:
                meta = (
                    f"{days_val:g} day{'s' if days_val != 1 else ''} × {hpd_val:g} h/day "
                    f"= {e['qty']:.2f} h × ${e['rate']:.2f}/h"
                )
            else:
                meta = f"{e['qty']:.2f} × ${e['rate']:.2f}"
            st.markdown(
                f'<div class="row"><div><div class="desc">{e["desc"]}</div>'
                f'<div class="meta">{meta}</div></div>'
                f'<div class="amt">${amount:,.2f}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f"""
            <div class="totals">
              <div class="r"><span>Subtotal</span><span>${subtotal:,.2f}</span></div>
              <div class="r"><span>Tax ({tax_rate:g}%)</span><span>${tax:,.2f}</span></div>
              <div class="r total"><span>Total due</span><span>${total:,.2f}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if notes:
            st.caption(f"📝 {notes}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------ PDF builder ------------------------------
    def build_pdf() -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter, rightMargin=48, leftMargin=48, topMargin=54, bottomMargin=36
        )
        styles = getSampleStyleSheet()
        title = ParagraphStyle(
            "title", parent=styles["Heading1"], fontSize=20, leading=24,
            textColor=colors.HexColor("#123a73")
        )
        body = ParagraphStyle(
            "body", parent=styles["Normal"], fontSize=10, leading=13,
            textColor=colors.HexColor("#334155")
        )
        elements = []
        if st.session_state.logo:
            try:
                elements.append(RLImage(BytesIO(st.session_state.logo), width=1.6 * inch, height=0.65 * inch))
            except Exception:
                pass
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(company, title))
        if company_addr:
            elements.append(Paragraph(company_addr.replace("\n", "<br/>"), body))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>Invoice #:</b> {invoice_no}", body))
        elements.append(Paragraph(f"<b>Date:</b> {invoice_date} &nbsp;&nbsp; <b>Due:</b> {due_date}", body))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"<b>Bill to:</b> {client}", body))
        if client_addr:
            elements.append(Paragraph(client_addr.replace("\n", "<br/>"), body))
        elements.append(Spacer(1, 14))

        data = [["Description", "Days", "Hrs/day", "Total hrs", "Rate", "Amount"]]
        for e in st.session_state.entries:
            days_val = e.get("days")
            hpd_val = e.get("hours_per_day")
            days_str = f"{days_val:g}" if days_val is not None else "-"
            hpd_str = f"{hpd_val:g}" if hpd_val is not None else "-"
            data.append(
                [
                    e["desc"],
                    days_str,
                    hpd_str,
                    f"{e['qty']:.2f}",
                    f"${e['rate']:.2f}",
                    f"${e['qty']*e['rate']:.2f}",
                ]
            )
        data += [
            ["", "", "", "", "Subtotal", f"${subtotal:.2f}"],
            ["", "", "", "", f"Tax ({tax_rate:g}%)", f"${tax:.2f}"],
            ["", "", "", "", "Total", f"${total:.2f}"],
        ]
        table = Table(
            data,
            colWidths=[2.4 * inch, 0.55 * inch, 0.7 * inch, 0.75 * inch, 0.75 * inch, 1.0 * inch],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123a73")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d7dee9")),
                    ("BACKGROUND", (0, 1), (-1, -4), colors.HexColor("#f8fbff")),
                    ("FONTNAME", (4, -3), (-1, -1), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(table)

        if notes:
            elements.append(Spacer(1, 14))
            elements.append(Paragraph(f"<i>{notes}</i>", body))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    st.write("")
    if st.session_state.entries:
        st.download_button(
            "⬇️  Download PDF invoice",
            data=build_pdf(),
            file_name=f"{invoice_no}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
