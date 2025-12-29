import streamlit as st
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas
import io

# Page configuration
st.set_page_config(
    page_title="Groupe eRDV Invoice Generator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #667eea;
    }
    .invoice-header {
        background: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .work-entry {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin-bottom: 10px;
    }
    h1, h2, h3 {
        color: white !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
    }
    .stButton>button:hover {
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'work_entries' not in st.session_state:
    st.session_state.work_entries = []
if 'entry_counter' not in st.session_state:
    st.session_state.entry_counter = 0

# Helper functions
def add_work_entry(description, days, hours_per_day, rate):
    st.session_state.entry_counter += 1
    entry = {
        'id': st.session_state.entry_counter,
        'description': description,
        'days': days,
        'hours_per_day': hours_per_day,
        'rate': rate
    }
    st.session_state.work_entries.append(entry)

def remove_work_entry(entry_id):
    st.session_state.work_entries = [e for e in st.session_state.work_entries if e['id'] != entry_id]

def calculate_amount(days, hours_per_day, rate):
    return days * hours_per_day * rate

def calculate_totals(entries, tax_rate):
    subtotal = sum(calculate_amount(e['days'], e['hours_per_day'], e['rate']) for e in entries)
    tax = subtotal * (tax_rate / 100)
    total = subtotal + tax
    return subtotal, tax, total

def generate_pdf(company_info, client_info, invoice_data, work_entries, subtotal, tax, total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)

    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
    )

    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
    )

    # Company Header
    company_text = f"""
    <b><font size=18 color='#667eea'>{company_info['name']}</font></b><br/>
    {company_info['address']}<br/>
    {company_info['city']}<br/>
    {company_info['country']}
    """
    elements.append(Paragraph(company_text, header_style))
    elements.append(Spacer(1, 20))

    # Invoice Title
    elements.append(Paragraph("<b>INVOICE</b>", title_style))
    elements.append(Spacer(1, 12))

    # Invoice details and Client info side by side
    invoice_client_data = [
        ['Bill To:', '', 'Invoice Details:', ''],
        [f"{client_info['name']}", '', f"Invoice #: {invoice_data['number']}", ''],
        [f"{client_info['address']}", '', f"Date: {invoice_data['date']}", ''],
        [f"{client_info['city']}", '', f"Terms: {invoice_data['terms']}", ''],
        [f"{client_info['country']}", '', f"Due Date: {invoice_data['due_date']}", ''],
    ]

    invoice_client_table = Table(invoice_client_data, colWidths=[2.5*inch, 0.5*inch, 2*inch, 1*inch])
    invoice_client_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ]))
    elements.append(invoice_client_table)
    elements.append(Spacer(1, 30))

    # Work entries table
    table_data = [['#', 'Description', 'Qty', 'Rate', 'Amount']]
    for idx, entry in enumerate(work_entries, 1):
        qty = entry['days'] * entry['hours_per_day']
        amount = calculate_amount(entry['days'], entry['hours_per_day'], entry['rate'])
        table_data.append([
            str(idx),
            entry['description'],
            f"{qty:.2f}",
            f"${entry['rate']:.2f}",
            f"${amount:.2f}"
        ])

    work_table = Table(table_data, colWidths=[0.5*inch, 3*inch, 1*inch, 1*inch, 1.5*inch])
    work_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(work_table)
    elements.append(Spacer(1, 20))

    # Totals
    totals_data = [
        ['', '', '', 'Subtotal:', f'${subtotal:.2f}'],
        ['', '', '', f'Tax ({invoice_data["tax_rate"]}%):', f'${tax:.2f}'],
        ['', '', '', 'Total:', f'${total:.2f}'],
    ]

    totals_table = Table(totals_data, colWidths=[0.5*inch, 3*inch, 1*inch, 1*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (3, -1), (-1, -1), 14),
        ('TEXTCOLOR', (3, -1), (-1, -1), colors.HexColor('#667eea')),
        ('LINEABOVE', (3, -1), (-1, -1), 2, colors.HexColor('#667eea')),
    ]))
    elements.append(totals_table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Main App
st.title("📄 Groupe eRDV Invoice Generator")
st.markdown("### Professional Invoice Creation Tool")

# Create two columns for input and preview
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("## 📝 Invoice Information")

    # Company Information
    with st.expander("🏢 Company Information", expanded=True):
        company_name = st.text_input("Company Name", value="Groupe eRDV inc.")
        company_address = st.text_input("Address", value="Saint-Jean-sur-Richelieu")
        company_city = st.text_input("City/Province/Postal Code", value="Quebec J2X 5W5")
        company_country = st.text_input("Country", value="Canada")

    # Client Information
    with st.expander("👤 Client Information", expanded=True):
        client_name = st.text_input("Client Name", value="Soho Square Solutions")
        client_address = st.text_input("Client Address", value="1 University Ave")
        client_city = st.text_input("Client City/Province/Postal Code", value="Toronto M5J 2P1")
        client_country = st.text_input("Client Country", value="Canada")

    # Invoice Details
    with st.expander("📅 Invoice Details", expanded=True):
        invoice_cols = st.columns(2)
        with invoice_cols[0]:
            invoice_number = st.text_input("Invoice Number", value="INV-001")
            invoice_date = st.date_input("Invoice Date", value=datetime.now())
        with invoice_cols[1]:
            payment_terms = st.selectbox("Payment Terms", ["Net 15", "Net 30", "Net 45", "Due on Receipt"])
            due_date = st.date_input("Due Date", value=datetime.now() + timedelta(days=15))

    # Work Entry Settings
    with st.expander("⚙️ Work Entry Settings", expanded=True):
        default_rate = st.number_input("Default Hourly Rate ($)", min_value=0.0, value=80.0, step=5.0)
        default_hours = st.number_input("Default Hours per Day", min_value=0.0, value=8.0, step=0.5)
        tax_rate = st.number_input("Tax Rate (%)", min_value=0.0, value=14.975, step=0.1)

    # Add Work Entry
    st.markdown("### ➕ Add Work Entry")
    with st.form("add_entry_form", clear_on_submit=True):
        entry_description = st.text_input("Description", value="Consulting Senior Developer")
        entry_cols = st.columns(3)
        with entry_cols[0]:
            entry_days = st.number_input("Days Worked", min_value=0.0, value=1.0, step=0.5)
        with entry_cols[1]:
            entry_hours = st.number_input("Hours/Day", min_value=0.0, value=default_hours, step=0.5)
        with entry_cols[2]:
            entry_rate = st.number_input("Hourly Rate ($)", min_value=0.0, value=default_rate, step=5.0)

        submit_entry = st.form_submit_button("➕ Add Entry", use_container_width=True)
        if submit_entry:
            add_work_entry(entry_description, entry_days, entry_hours, entry_rate)
            st.success(f"Added: {entry_description}")
            st.rerun()

with col2:
    st.markdown("## 👁️ Invoice Preview")

    # Display work entries
    if st.session_state.work_entries:
        st.markdown("### Work Entries")
        for entry in st.session_state.work_entries:
            with st.container():
                entry_col1, entry_col2, entry_col3 = st.columns([3, 2, 1])
                with entry_col1:
                    st.markdown(f"**{entry['description']}**")
                with entry_col2:
                    qty = entry['days'] * entry['hours_per_day']
                    amount = calculate_amount(entry['days'], entry['hours_per_day'], entry['rate'])
                    st.markdown(f"Qty: {qty:.2f} hrs @ ${entry['rate']:.2f}")
                with entry_col3:
                    if st.button("🗑️", key=f"remove_{entry['id']}"):
                        remove_work_entry(entry['id'])
                        st.rerun()
                st.markdown(f"<div style='background:#f8f9fa;padding:10px;border-radius:5px;border-left:4px solid #667eea;margin-bottom:10px;'>Amount: <b>${amount:.2f}</b></div>", unsafe_allow_html=True)

        # Calculate totals
        subtotal, tax, total = calculate_totals(st.session_state.work_entries, tax_rate)

        # Display totals
        st.markdown("### 💰 Summary")
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        with summary_col1:
            st.metric("Subtotal", f"${subtotal:.2f}")
        with summary_col2:
            st.metric(f"Tax ({tax_rate}%)", f"${tax:.2f}")
        with summary_col3:
            st.metric("Total", f"${total:.2f}")

        # Generate PDF button
        st.markdown("---")
        if st.button("📥 Download PDF Invoice", use_container_width=True, type="primary"):
            company_info = {
                'name': company_name,
                'address': company_address,
                'city': company_city,
                'country': company_country
            }
            client_info = {
                'name': client_name,
                'address': client_address,
                'city': client_city,
                'country': client_country
            }
            invoice_data = {
                'number': invoice_number,
                'date': invoice_date.strftime('%Y-%m-%d'),
                'terms': payment_terms,
                'due_date': due_date.strftime('%Y-%m-%d'),
                'tax_rate': tax_rate
            }

            pdf_buffer = generate_pdf(company_info, client_info, invoice_data, 
                                     st.session_state.work_entries, subtotal, tax, total)

            st.download_button(
                label="💾 Download Invoice PDF",
                data=pdf_buffer,
                file_name=f"Invoice_{invoice_number}_{invoice_date.strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.info("👈 Add work entries to generate an invoice")

# Sidebar
with st.sidebar:
    st.markdown("## ℹ️ About")
    st.markdown("""
    **Groupe eRDV Invoice Generator**

    A professional invoice generation tool for consulting services.

    ### Features:
    - ✅ Custom company & client info
    - ✅ Multiple work entries
    - ✅ Automatic tax calculation
    - ✅ PDF generation
    - ✅ Professional design

    ### How to Use:
    1. Fill in company and client information
    2. Set invoice details and payment terms
    3. Add work entries with hours and rates
    4. Review the invoice preview
    5. Download as PDF
    """)

    st.markdown("---")
    if st.button("🗑️ Clear All Entries", use_container_width=True):
        st.session_state.work_entries = []
        st.session_state.entry_counter = 0
        st.rerun()

    st.markdown("---")
    st.markdown("**Made with ❤️ for Groupe eRDV**")
