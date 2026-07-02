import streamlit as st
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage

st.set_page_config(page_title='Groupe eRDV Invoice Studio', page_icon='📄', layout='wide', initial_sidebar_state='expanded')

st.markdown('''
<style>
:root { --bg:#f6f7fb; --surface:rgba(255,255,255,.78); --text:#0f172a; --muted:#64748b; --line:rgba(15,23,42,.08); --primary:#123a73; --primary2:#2b6cb0; --shadow:0 20px 50px rgba(15,23,42,.10); --radius:22px; }
[data-theme="dark"] { --bg:#0b1220; --surface:rgba(15,23,42,.72); --text:#e5e7eb; --muted:#94a3b8; --line:rgba(148,163,184,.16); --primary:#8ab4ff; --primary2:#60a5fa; --shadow:0 20px 50px rgba(0,0,0,.35); }
html, body, [class*="stApp"] { background: linear-gradient(180deg, var(--bg), var(--bg)); color: var(--text); }
.block-container { padding-top: 1.2rem; padding-bottom: 2.2rem; max-width: 1280px; }
.hero { background: linear-gradient(135deg, rgba(18,58,115,.96), rgba(43,108,176,.92)); color: white; border-radius: 28px; padding: 1.25rem 1.35rem; box-shadow: var(--shadow); display:flex; gap:1rem; align-items:center; justify-content:space-between; flex-wrap:wrap; }
.hero h1 { margin:0; font-size: clamp(1.6rem, 2vw, 2.4rem); line-height:1.05; }
.hero p { margin:.35rem 0 0; opacity:.9; max-width: 62ch; }
.brand { display:flex; align-items:center; gap:.9rem; }
.brand .mark { width: 62px; height: 62px; border-radius: 16px; background: rgba(255,255,255,.14); display:grid; place-items:center; font-weight:800; font-size:1.2rem; }
.kpi { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem; box-shadow: var(--shadow); }
.kpi .label { color: var(--muted); font-size: .86rem; }
.kpi .value { font-size: 1.6rem; font-weight: 750; margin-top: .2rem; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); padding: 1rem; }
div[data-testid="stButton"] > button, .stDownloadButton button { border-radius: 14px !important; border: 1px solid transparent !important; padding: .72rem 1rem !important; font-weight: 650 !important; background: linear-gradient(135deg, var(--primary), var(--primary2)) !important; color: white !important; }
input, textarea, select { border-radius: 14px !important; }
hr { border-color: var(--line); }
</style>
''', unsafe_allow_html=True)

if 'entries' not in st.session_state: st.session_state.entries=[]
if 'counter' not in st.session_state: st.session_state.counter=0
if 'theme' not in st.session_state: st.session_state.theme='light'
if 'logo' not in st.session_state: st.session_state.logo=b''

with st.sidebar:
    st.markdown('### Workspace')
    theme = st.radio('Theme', ['Light','Dark'], horizontal=True, index=0 if st.session_state.theme=='light' else 1)
    st.session_state.theme = 'dark' if theme=='Dark' else 'light'
    upload = st.file_uploader('Logo', type=['png','jpg','jpeg'])
    if upload is not None: st.session_state.logo = upload.read()
    st.caption('Modern layout, cleaner spacing, faster invoice workflow.')

st.markdown('<div class="hero"><div class="brand"><div class="mark">eRDV</div><div><h1>Groupe eRDV Invoice Studio</h1><p>Create polished invoices faster with live totals, clean previews, and branded PDF export.</p></div></div><div style="text-align:right"><div style="font-size:.86rem;opacity:.85">Modern invoice workflow</div><div style="font-size:1.02rem;font-weight:700">Streamlit-ready</div></div></div>', unsafe_allow_html=True)

subtotal = sum(x['qty']*x['rate'] for x in st.session_state.entries)
tax_rate = 14.975
tax = subtotal * tax_rate / 100
total = subtotal + tax
c1,c2,c3 = st.columns(3)
for col, label, val in [(c1,'Line items',len(st.session_state.entries)),(c2,'Subtotal',f'${subtotal:,.2f}'),(c3,'Total due',f'${total:,.2f}')]:
    with col: st.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{val}</div></div>', unsafe_allow_html=True)

left, right = st.columns([1.05, 1])
with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader('Invoice details')
    with st.form('entry_form', clear_on_submit=True):
        desc = st.text_input('Description', placeholder='Consulting Senior Developer')
        qty = st.number_input('Hours / quantity', min_value=0.0, value=8.0, step=0.5)
        rate = st.number_input('Rate', min_value=0.0, value=80.0, step=5.0)
        submitted = st.form_submit_button('Add line item', use_container_width=True)
        if submitted and desc.strip():
            st.session_state.counter += 1
            st.session_state.entries.append({'id': st.session_state.counter, 'desc': desc.strip(), 'qty': qty, 'rate': rate})
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel" style="margin-top:1rem;">', unsafe_allow_html=True)
    st.subheader('Company and client')
    company = st.text_input('Company name', 'Groupe eRDV inc.')
    client = st.text_input('Client name', 'Soho Square Solutions')
    invoice_no = st.text_input('Invoice number', f'INV-{datetime.now().strftime("%Y%m%d")}-001')
    invoice_date = st.date_input('Invoice date', datetime.now())
    due_date = st.date_input('Due date', datetime.now() + timedelta(days=15))
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader('Live preview')
    if st.session_state.entries:
        for e in st.session_state.entries:
            a,b,c = st.columns([5,2,1])
            with a:
                st.write(f"**{e['desc']}**")
                st.caption(f"{e['qty']:.2f} × ${e['rate']:.2f}")
            with b: st.metric('Amount', f"${e['qty']*e['rate']:,.2f}")
            with c:
                if st.button('✕', key=f"rm{e['id']}"):
                    st.session_state.entries = [x for x in st.session_state.entries if x['id'] != e['id']]
                    st.rerun()
            st.divider()
        st.markdown(f"**Subtotal:** ${subtotal:,.2f}  
**Tax:** ${tax:,.2f}  
**Total:** ${total:,.2f}")
    else:
        st.info('Add your first line item to see the invoice update instantly.')
    st.markdown('</div>', unsafe_allow_html=True)

    def build_pdf():
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=48, leftMargin=48, topMargin=54, bottomMargin=36)
        styles = getSampleStyleSheet()
        title = ParagraphStyle('title', parent=styles['Heading1'], fontSize=20, leading=24, textColor=colors.HexColor('#123a73'))
        body = ParagraphStyle('body', parent=styles['Normal'], fontSize=10, leading=13, textColor=colors.HexColor('#334155'))
        elements = []
        if st.session_state.logo:
            try:
                elements.append(RLImage(BytesIO(st.session_state.logo), width=1.5*inch, height=0.6*inch))
            except Exception:
                pass
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(company, title))
        elements.append(Paragraph(f'Invoice to: {client}', body))
        elements.append(Paragraph(f'Invoice #: {invoice_no}', body))
        elements.append(Paragraph(f'Date: {invoice_date} | Due: {due_date}', body))
        elements.append(Spacer(1, 14))
        data = [['Description', 'Qty', 'Rate', 'Amount']]
        for e in st.session_state.entries:
            data.append([e['desc'], f"{e['qty']:.2f}", f"${e['rate']:.2f}", f"${e['qty']*e['rate']:.2f}"])
        data += [['', '', 'Subtotal', f'${subtotal:.2f}'], ['', '', f'Tax ({tax_rate}%)', f'${tax:.2f}'], ['', '', 'Total', f'${total:.2f}']]
        table = Table(data, colWidths=[3.25*inch, 0.8*inch, 1.0*inch, 1.1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#123a73')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d7dee9')),
            ('BACKGROUND', (0,1), (-1,-4), colors.HexColor('#f8fbff')),
            ('FONTNAME', (2,-3), (-1,-1), 'Helvetica-Bold'),
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
            ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    st.download_button('Download PDF invoice', data=build_pdf(), file_name=f'{invoice_no}.pdf', mime='application/pdf', use_container_width=True)
