import streamlit as st
from datetime import datetime, timedelta, date
from io import BytesIO
from pathlib import Path
import base64
import json
import sqlite3
import os
from typing import Optional
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
# Database (SQLite) — persistent invoice history
# --------------------------------------------------------------------------------------
# NOTE: Streamlit Cloud's filesystem is ephemeral; the DB is wiped on redeploy or when
# the container recycles. To keep data long-term either:
#   * set st.secrets["DB_PATH"] to a path on a mounted persistent volume, or
#   * use the sidebar Backup/Restore controls.
try:
    _cfg_path = st.secrets.get("DB_PATH", None)  # may raise if no secrets file
except Exception:
    _cfg_path = None
DB_PATH = Path(_cfg_path or os.environ.get("DB_PATH", "/tmp/erdv_invoices.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _db_init() -> None:
    with _db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
              id            INTEGER PRIMARY KEY AUTOINCREMENT,
              invoice_no    TEXT UNIQUE NOT NULL,
              company       TEXT,
              company_addr  TEXT,
              client        TEXT,
              client_addr   TEXT,
              invoice_date  TEXT,
              due_date      TEXT,
              tax_rate      REAL,
              subtotal      REAL,
              tax           REAL,
              total         REAL,
              notes         TEXT,
              entries_json  TEXT,
              logo_blob     BLOB,
              created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
              updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


_db_init()


def db_save_invoice(payload: dict) -> int:
    """Insert or update an invoice by invoice_no. Returns row id."""
    with _db_connect() as conn:
        cur = conn.execute(
            "SELECT id FROM invoices WHERE invoice_no = ?", (payload["invoice_no"],)
        )
        row = cur.fetchone()
        now = datetime.utcnow().isoformat()
        if row:
            conn.execute(
                """
                UPDATE invoices SET
                  company=?, company_addr=?, client=?, client_addr=?,
                  invoice_date=?, due_date=?, tax_rate=?, subtotal=?, tax=?, total=?,
                  notes=?, entries_json=?, logo_blob=?, updated_at=?
                WHERE id=?
                """,
                (
                    payload["company"], payload["company_addr"], payload["client"], payload["client_addr"],
                    payload["invoice_date"], payload["due_date"], payload["tax_rate"],
                    payload["subtotal"], payload["tax"], payload["total"],
                    payload["notes"], payload["entries_json"], payload["logo_blob"], now, row["id"],
                ),
            )
            conn.commit()
            return int(row["id"])
        cur = conn.execute(
            """
            INSERT INTO invoices
              (invoice_no, company, company_addr, client, client_addr, invoice_date, due_date,
               tax_rate, subtotal, tax, total, notes, entries_json, logo_blob, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["invoice_no"], payload["company"], payload["company_addr"],
                payload["client"], payload["client_addr"], payload["invoice_date"], payload["due_date"],
                payload["tax_rate"], payload["subtotal"], payload["tax"], payload["total"],
                payload["notes"], payload["entries_json"], payload["logo_blob"], now, now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def db_list_invoices() -> list:
    with _db_connect() as conn:
        cur = conn.execute(
            """
            SELECT id, invoice_no, company, client, invoice_date, due_date,
                   subtotal, tax, total, created_at, updated_at
            FROM invoices
            ORDER BY datetime(updated_at) DESC
            """
        )
        return [dict(r) for r in cur.fetchall()]


def db_get_invoice(invoice_id: int) -> Optional[dict]:
    with _db_connect() as conn:
        cur = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def db_delete_invoice(invoice_id: int) -> None:
    with _db_connect() as conn:
        conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        conn.commit()


def db_backup_bytes() -> bytes:
    try:
        return DB_PATH.read_bytes()
    except Exception:
        return b""


def db_restore_from_bytes(data: bytes) -> None:
    DB_PATH.write_bytes(data)
    _db_init()

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
if "loaded_from_id" not in st.session_state:
    st.session_state.loaded_from_id = None
if "prefill" not in st.session_state:
    # Values loaded from DB history override defaults on next rerun
    st.session_state.prefill = {}


def _apply_loaded_invoice(row: dict) -> None:
    """Load a saved invoice into session_state so the UI reflects it on next rerun."""
    entries = json.loads(row.get("entries_json") or "[]")
    max_id = 0
    for e in entries:
        try:
            max_id = max(max_id, int(e.get("id") or 0))
        except Exception:
            pass
    st.session_state.entries = entries
    st.session_state.counter = max_id
    st.session_state.loaded_from_id = int(row["id"])
    st.session_state.prefill = {
        "invoice_no": row.get("invoice_no") or "",
        "company": row.get("company") or "",
        "company_addr": row.get("company_addr") or "",
        "client": row.get("client") or "",
        "client_addr": row.get("client_addr") or "",
        "invoice_date": row.get("invoice_date") or "",
        "due_date": row.get("due_date") or "",
        "notes": row.get("notes") or "",
        "tax_rate": float(row.get("tax_rate") or 14.975),
    }
    if row.get("logo_blob"):
        st.session_state.logo = bytes(row["logo_blob"])

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
    _default_tax = float(st.session_state.prefill.get("tax_rate", 14.975))
    tax_rate = st.number_input(
        "Tax rate (%)", min_value=0.0, max_value=100.0, value=_default_tax, step=0.1
    )

    st.markdown("### ⚡ Actions")
    if st.button("New invoice (clear form)", use_container_width=True):
        st.session_state.entries = []
        st.session_state.counter = 0
        st.session_state.loaded_from_id = None
        st.session_state.prefill = {}
        st.rerun()
    if st.button("Clear line items only", use_container_width=True):
        st.session_state.entries = []
        st.rerun()

    st.markdown("### 💾 Database")
    st.caption(f"Storage: `{DB_PATH}`")
    _all = db_list_invoices()
    st.caption(f"{len(_all)} saved invoice(s)")
    st.download_button(
        "Backup DB (.sqlite)",
        data=db_backup_bytes() or b"",
        file_name="erdv_invoices.sqlite",
        mime="application/octet-stream",
        use_container_width=True,
        disabled=(len(_all) == 0),
    )
    restore = st.file_uploader("Restore from backup", type=["sqlite", "db"])
    if restore is not None:
        db_restore_from_bytes(restore.read())
        st.success("Database restored. Reloading…")
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
tab_details, tab_items, tab_preview, tab_history = st.tabs(
    ["📇 Company & Client", "➕ Line items", "👀 Preview & Export", "📚 History"]
)


def _parse_date(s: str, fallback):
    try:
        if not s:
            return fallback
        return datetime.fromisoformat(s).date() if len(s) > 10 else datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return fallback


pf = st.session_state.prefill

with tab_details:
    if st.session_state.loaded_from_id:
        st.info(f"✏️ Editing saved invoice ID #{st.session_state.loaded_from_id}. Changes will update it in place when you save.")
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Invoice details")
    a, b = st.columns(2)
    with a:
        company = st.text_input("Your company", pf.get("company") or "Groupe eRDV inc.")
        company_addr = st.text_area(
            "Company address",
            pf.get("company_addr") or "Saint-Jean-sur-Richelieu, QC, Canada",
            height=80,
        )
    with b:
        client = st.text_input("Client name", pf.get("client") or "Soho Square Solutions")
        client_addr = st.text_area(
            "Client address", pf.get("client_addr") or "", height=80, placeholder="Optional"
        )

    c, d, e = st.columns(3)
    with c:
        invoice_no = st.text_input(
            "Invoice #",
            pf.get("invoice_no") or f'INV-{datetime.now().strftime("%Y%m%d")}-001',
        )
    with d:
        invoice_date = st.date_input(
            "Invoice date", _parse_date(pf.get("invoice_date", ""), datetime.now().date())
        )
    with e:
        due_date = st.date_input(
            "Due date",
            _parse_date(pf.get("due_date", ""), (datetime.now() + timedelta(days=15)).date()),
        )

    notes = st.text_area(
        "Notes / payment terms",
        pf.get("notes") or "Payment due within 15 days. Thank you for your business.",
        height=80,
    )
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
        colA, colB = st.columns([1, 1])
        with colA:
            st.download_button(
                "⬇️  Download PDF invoice",
                data=build_pdf(),
                file_name=f"{invoice_no}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with colB:
            if st.button("💾  Save invoice to history", use_container_width=True):
                try:
                    payload = {
                        "invoice_no": invoice_no.strip(),
                        "company": company,
                        "company_addr": company_addr,
                        "client": client,
                        "client_addr": client_addr,
                        "invoice_date": invoice_date.isoformat(),
                        "due_date": due_date.isoformat(),
                        "tax_rate": float(tax_rate),
                        "subtotal": float(subtotal),
                        "tax": float(tax),
                        "total": float(total),
                        "notes": notes,
                        "entries_json": json.dumps(st.session_state.entries),
                        "logo_blob": bytes(st.session_state.logo) if st.session_state.logo else None,
                    }
                    row_id = db_save_invoice(payload)
                    st.session_state.loaded_from_id = row_id
                    st.success(f"Saved invoice `{invoice_no}` to history (ID #{row_id}).")
                except sqlite3.IntegrityError as ex:
                    st.error(f"Could not save: {ex}")
                except Exception as ex:
                    st.error(f"Save failed: {ex}")


# --------------------------------------------------------------------------------------
# History tab
# --------------------------------------------------------------------------------------
with tab_history:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Saved invoices")
    all_invoices = db_list_invoices()
    if not all_invoices:
        st.info("No saved invoices yet. Create one, then click “Save invoice to history” on the Preview tab.")
    else:
        # Filter row
        q = st.text_input("Search (client, company, invoice #)", "")
        def _match(inv):
            if not q:
                return True
            ql = q.lower()
            return any(
                ql in (str(inv.get(k) or "").lower())
                for k in ("invoice_no", "client", "company")
            )
        filtered = [i for i in all_invoices if _match(i)]
        st.caption(f"Showing {len(filtered)} of {len(all_invoices)} invoice(s)")

        for inv in filtered:
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2.2, 2, 1.4, 1.4, 1.4])
                with c1:
                    st.markdown(f"**{inv['invoice_no']}**")
                    st.caption(inv.get("company") or "")
                with c2:
                    st.markdown(f"**{inv.get('client') or ''}**")
                    st.caption(f"{inv.get('invoice_date') or ''} → due {inv.get('due_date') or ''}")
                with c3:
                    st.markdown("Total")
                    st.markdown(f"**${(inv.get('total') or 0):,.2f}**")
                with c4:
                    if st.button("📂 Load", key=f"load{inv['id']}", use_container_width=True):
                        row = db_get_invoice(int(inv["id"]))
                        if row:
                            _apply_loaded_invoice(row)
                            st.success(f"Loaded `{row['invoice_no']}`. Switch to ‘Company & Client’ or ‘Preview’ to review.")
                            st.rerun()
                with c5:
                    if st.button("🗑 Delete", key=f"del{inv['id']}", use_container_width=True):
                        db_delete_invoice(int(inv["id"]))
                        if st.session_state.loaded_from_id == int(inv["id"]):
                            st.session_state.loaded_from_id = None
                        st.rerun()
                st.divider()
    st.markdown("</div>", unsafe_allow_html=True)
