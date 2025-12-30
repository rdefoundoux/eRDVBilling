import streamlit as st
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from reportlab.pdfgen import canvas
import io
import base64
from PIL import Image as PILImage

# Page configuration
st.set_page_config(
    page_title="Groupe eRDV Invoice Generator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for better styling
st.markdown("""
<style>
    /* Main background */
    .main {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #667eea 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #667eea 100%);
    }

    /* Card styling */
    .stExpander {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }

    /* Metric cards */
    div[data-testid="stMetricValue"] {
        font-size: 32px;
        color: #1e3c72;
        font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #555;
        font-weight: 600;
    }

    /* Headers */
    h1, h2, h3 {
        color: white !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 28px;
        font-weight: 600;
        font-size: 15px;
        transition: all 0.3s;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(30, 60, 114, 0.4);
    }

    /* Form inputs */
    .stTextInput>div>div>input, 
    .stNumberInput>div>div>input,
    .stSelectbox>div>div>select,
    .stDateInput>div>div>input {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 10px;
        transition: border-color 0.3s;
    }

    .stTextInput>div>div>input:focus, 
    .stNumberInput>div>div>input:focus {
        border-color: #2a5298;
        box-shadow: 0 0 0 2px rgba(42, 82, 152, 0.1);
    }

    /* Work entry cards */
    .work-entry {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        padding: 18px;
        border-radius: 10px;
        border-left: 5px solid #2a5298;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    /* Success/Info messages */
    .stSuccess {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        border-radius: 8px;
    }

    .stInfo {
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        border-radius: 8px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
    }

    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] li {
        color: white !important;
    }

    /* Logo container */
    .logo-container {
        text-align: center;
        padding: 20px;
        background: white;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    /* Divider */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #fff, transparent);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'work_entries' not in st.session_state:
    st.session_state.work_entries = []
if 'entry_counter' not in st.session_state:
    st.session_state.entry_counter = 0
if 'logo_data' not in st.session_state:
    st.session_state.logo_data = None
if 'invoice_history' not in st.session_state:
    st.session_state.invoice_history = []

# Helper functions
def load_logo(uploaded_file):
    """Load and process logo image"""
    if uploaded_file is not None:
        return uploaded_file.read()
    return None

def add_work_entry(description, days, hours_per_day, rate):
    """Add a new work entry"""
    st.session_state.entry_counter += 1
    entry = {
        'id': st.session_state.entry_counter,
        'description': description,
        'days': days,
        'hours_per_day': hours_per_day,
        'rate': rate,
        'timestamp': datetime.now()
    }
    st.session_state.work_entries.append(entry)

def remove_work_entry(entry_id):
    """Remove a work entry by ID"""
    st.session_state.work_entries = [e for e in st.session_state.work_entries if e['id'] != entry_id]

def calculate_amount(days, hours_per_day, rate):
    """Calculate total amount for an entry"""
    return days * hours_per_day * rate

def calculate_totals(entries, tax_rate):
    """Calculate subtotal, tax, and total"""
    subtotal = sum(calculate_amount(e['days'], e['hours_per_day'], e['rate']) for e in entries)
    tax = subtotal * (tax_rate / 100)
    total = subtotal + tax
    return subtotal, tax, total

def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:,.2f}"

def generate_pdf(company_info, client_info, invoice_data, work_entries, subtotal, tax, total, logo_data=None):
    """Generate professional PDF invoice with logo"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=50)

    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#1e3c72'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        leading=14,
    )

    company_name_style = ParagraphStyle(
        'CompanyName',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#1e3c72'),
        fontName='Helvetica-Bold',
        spaceAfter=8,
    )

    # Add logo if available
    if logo_data:
        try:
            logo_img = Image(io.BytesIO(logo_data), width=2*inch, height=0.8*inch)
            logo_table = Table([[logo_img]], colWidths=[2*inch])
            logo_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(logo_table)
            elements.append(Spacer(1, 10))
        except:
            pass

    # Company Header
    company_text = f"""
    <b><font size=14 color='#1e3c72'>{company_info['name']}</font></b><br/>
    <font size=9 color='#555555'>{company_info['address']}<br/>
    {company_info['city']}<br/>
    {company_info['country']}</font>
    """
    elements.append(Paragraph(company_text, header_style))
    elements.append(Spacer(1, 20))

    # Invoice Title
    elements.append(Paragraph("<b>INVOICE</b>", title_style))
    elements.append(Spacer(1, 20))

    # Invoice details and Client info
    invoice_client_data = [
        [Paragraph('<b><font size=10 color="#1e3c72">BILL TO:</font></b>', header_style), 
         '', 
         Paragraph('<b><font size=10 color="#1e3c72">INVOICE DETAILS:</font></b>', header_style), 
         ''],
        [Paragraph(f'<b>{client_info["name"]}</b>', header_style), '', 
         Paragraph(f'<b>Invoice #:</b> {invoice_data["number"]}', header_style), ''],
        [Paragraph(client_info['address'], header_style), '', 
         Paragraph(f'<b>Date:</b> {invoice_data["date"]}', header_style), ''],
        [Paragraph(client_info['city'], header_style), '', 
         Paragraph(f'<b>Terms:</b> {invoice_data["terms"]}', header_style), ''],
        [Paragraph(client_info['country'], header_style), '', 
         Paragraph(f'<b>Due Date:</b> {invoice_data["due_date"]}', header_style), ''],
    ]

    invoice_client_table = Table(invoice_client_data, colWidths=[2.5*inch, 0.5*inch, 2*inch, 1*inch])
    invoice_client_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(invoice_client_table)
    elements.append(Spacer(1, 30))

    # Work entries table
    table_data = [[
        Paragraph('<b>#</b>', header_style),
        Paragraph('<b>Description</b>', header_style),
        Paragraph('<b>Quantity</b>', header_style),
        Paragraph('<b>Rate</b>', header_style),
        Paragraph('<b>Amount</b>', header_style)
    ]]

    for idx, entry in enumerate(work_entries, 1):
        qty = entry['days'] * entry['hours_per_day']
        amount = calculate_amount(entry['days'], entry['hours_per_day'], entry['rate'])
        table_data.append([
            str(idx),
            entry['description'],
            f"{qty:.2f} hrs",
            format_currency(entry['rate']),
            format_currency(amount)
        ])

    work_table = Table(table_data, colWidths=[0.5*inch, 2.8*inch, 1.2*inch, 1*inch, 1.5*inch])
    work_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3c72')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 14),
        ('TOPPADDING', (0, 0), (-1, 0), 14),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
    ]))
    elements.append(work_table)
    elements.append(Spacer(1, 25))

    # Totals section
    totals_data = [
        ['', '', '', Paragraph('<b>Subtotal:</b>', header_style), Paragraph(format_currency(subtotal), header_style)],
        ['', '', '', Paragraph(f'<b>Tax ({invoice_data["tax_rate"]}%):</b>', header_style), Paragraph(format_currency(tax), header_style)],
        ['', '', '', '', ''],
        ['', '', '', Paragraph('<b><font size=12 color="#1e3c72">TOTAL DUE:</font></b>', header_style), 
         Paragraph(f'<b><font size=12 color="#1e3c72">{format_currency(total)}</font></b>', header_style)],
    ]

    totals_table = Table(totals_data, colWidths=[0.5*inch, 2.8*inch, 1.2*inch, 1*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (3, 3), (-1, 3), 2, colors.HexColor('#1e3c72')),
        ('LINEBELOW', (3, 3), (-1, 3), 2, colors.HexColor('#1e3c72')),
        ('TOPPADDING', (3, 3), (-1, 3), 12),
        ('BOTTOMPADDING', (3, 3), (-1, 3), 12),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 40))

    # Footer
    footer_text = f"""
    <para align=center>
    <font size=8 color='#888888'>
    <b>Thank you for your business!</b><br/>
    Please make payment by {invoice_data['due_date']}<br/>
    If you have any questions, please contact us.
    </font>
    </para>
    """
    elements.append(Paragraph(footer_text, header_style))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def save_to_history(invoice_number, client_name, total):
    """Save invoice to history"""
    st.session_state.invoice_history.append({
        'invoice_number': invoice_number,
        'client_name': client_name,
        'total': total,
        'date': datetime.now(),
        'entries_count': len(st.session_state.work_entries)
    })

# Main App Header
col_logo, col_title = st.columns([1, 4])
with col_logo:
    # Logo upload in main area
    logo_file = st.file_uploader("Upload Logo", type=['png', 'jpg', 'jpeg'], key='main_logo', label_visibility='collapsed')
    if logo_file:
        st.session_state.logo_data = load_logo(logo_file)
        st.image(logo_file, width=120)

with col_title:
    st.title("📄 Groupe eRDV Invoice Generator")
    st.markdown("### Professional Invoice Creation & Management System")

st.markdown("---")

# Create tabs for better organization
tab1, tab2, tab3 = st.tabs(["📝 Create Invoice", "📊 Invoice Preview", "📚 History"])

with tab1:
    # Create two columns for better layout
    col1, col2 = st.columns([1, 1])

    with col1:
        # Company Information
        with st.expander("🏢 Company Information", expanded=True):
            company_name = st.text_input("Company Name", value="Groupe eRDV inc.", key="comp_name")
            company_address = st.text_input("Address", value="Saint-Jean-sur-Richelieu", key="comp_addr")
            company_city = st.text_input("City/Province/Postal Code", value="Quebec J2X 5W5", key="comp_city")
            company_country = st.text_input("Country", value="Canada", key="comp_country")

        # Invoice Details
        with st.expander("📅 Invoice Details", expanded=True):
            invoice_cols = st.columns(2)
            with invoice_cols[0]:
                invoice_number = st.text_input("Invoice Number", value=f"INV-{datetime.now().strftime('%Y%m%d')}-001")
                invoice_date = st.date_input("Invoice Date", value=datetime.now())
            with invoice_cols[1]:
                payment_terms = st.selectbox("Payment Terms", ["Net 15", "Net 30", "Net 45", "Net 60", "Due on Receipt"])
                days_map = {"Net 15": 15, "Net 30": 30, "Net 45": 45, "Net 60": 60, "Due on Receipt": 0}
                due_date = st.date_input("Due Date", value=datetime.now() + timedelta(days=days_map.get(payment_terms, 15)))

    with col2:
        # Client Information
        with st.expander("👤 Client Information", expanded=True):
            client_name = st.text_input("Client Name", value="Soho Square Solutions", key="client_name")
            client_address = st.text_input("Client Address", value="1 University Ave", key="client_addr")
            client_city = st.text_input("Client City/Province/Postal Code", value="Toronto M5J 2P1", key="client_city")
            client_country = st.text_input("Client Country", value="Canada", key="client_country")

        # Work Entry Settings
        with st.expander("⚙️ Default Settings", expanded=True):
            settings_cols = st.columns(3)
            with settings_cols[0]:
                default_rate = st.number_input("Hourly Rate ($)", min_value=0.0, value=80.0, step=5.0)
            with settings_cols[1]:
                default_hours = st.number_input("Hours/Day", min_value=0.0, value=8.0, step=0.5)
            with settings_cols[2]:
                tax_rate = st.number_input("Tax Rate (%)", min_value=0.0, value=14.975, step=0.1)

    # Add Work Entry Section
    st.markdown("### ➕ Add Work Entry")
    with st.form("add_entry_form", clear_on_submit=True):
        entry_description = st.text_input("Description", value="Consulting Senior Developer", placeholder="Enter service description")
        entry_cols = st.columns(3)
        with entry_cols[0]:
            entry_days = st.number_input("Days Worked", min_value=0.0, value=1.0, step=0.5)
        with entry_cols[1]:
            entry_hours = st.number_input("Hours/Day", min_value=0.0, value=default_hours, step=0.5)
        with entry_cols[2]:
            entry_rate = st.number_input("Hourly Rate ($)", min_value=0.0, value=default_rate, step=5.0)

        col_submit, col_clear = st.columns([3, 1])
        with col_submit:
            submit_entry = st.form_submit_button("➕ Add Work Entry", use_container_width=True, type="primary")
        with col_clear:
            if st.form_submit_button("🗑️ Clear All", use_container_width=True):
                st.session_state.work_entries = []
                st.session_state.entry_counter = 0
                st.rerun()

        if submit_entry:
            add_work_entry(entry_description, entry_days, entry_hours, entry_rate)
            st.success(f"✅ Added: {entry_description}")
            st.rerun()

with tab2:
    st.markdown("## 👁️ Invoice Preview & Summary")

    # Display work entries
    if st.session_state.work_entries:
        st.markdown("### 📋 Work Entries")

        for entry in st.session_state.work_entries:
            qty = entry['days'] * entry['hours_per_day']
            amount = calculate_amount(entry['days'], entry['hours_per_day'], entry['rate'])

            entry_col1, entry_col2, entry_col3 = st.columns([4, 2, 1])
            with entry_col1:
                st.markdown(f"**{entry['description']}**")
                st.caption(f"Days: {entry['days']:.1f} | Hours/Day: {entry['hours_per_day']:.1f} | Rate: {format_currency(entry['rate'])}")
            with entry_col2:
                st.metric("Quantity", f"{qty:.2f} hrs")
            with entry_col3:
                st.metric("Amount", format_currency(amount))
                if st.button("🗑️", key=f"remove_{entry['id']}", help="Remove entry"):
                    remove_work_entry(entry['id'])
                    st.rerun()

            st.markdown("---")

        # Calculate totals
        subtotal, tax, total = calculate_totals(st.session_state.work_entries, tax_rate)

        # Display totals in metric cards
        st.markdown("### 💰 Financial Summary")
        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
        with summary_col1:
            st.metric("Entries", len(st.session_state.work_entries))
        with summary_col2:
            st.metric("Subtotal", format_currency(subtotal))
        with summary_col3:
            st.metric(f"Tax ({tax_rate}%)", format_currency(tax))
        with summary_col4:
            st.metric("💵 Total Due", format_currency(total), delta=None)

        # Generate PDF button
        st.markdown("---")
        col_download, col_save = st.columns([2, 1])

        with col_download:
            if st.button("📥 Generate & Download PDF Invoice", use_container_width=True, type="primary"):
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
                                         st.session_state.work_entries, subtotal, tax, total,
                                         st.session_state.logo_data)

                save_to_history(invoice_number, client_name, total)

                st.download_button(
                    label="💾 Download Invoice PDF",
                    data=pdf_buffer,
                    file_name=f"Invoice_{invoice_number}_{invoice_date.strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ Invoice generated successfully!")

        with col_save:
            if st.button("💾 Save Draft", use_container_width=True):
                save_to_history(invoice_number, client_name, total)
                st.success("✅ Draft saved!")
    else:
        st.info("👈 Add work entries in the 'Create Invoice' tab to generate an invoice")

with tab3:
    st.markdown("## 📚 Invoice History")

    if st.session_state.invoice_history:
        st.markdown(f"### Total Invoices: {len(st.session_state.invoice_history)}")

        # Create a summary table
        history_data = []
        for inv in reversed(st.session_state.invoice_history):
            history_data.append({
                'Invoice #': inv['invoice_number'],
                'Client': inv['client_name'],
                'Total': format_currency(inv['total']),
                'Entries': inv['entries_count'],
                'Date': inv['date'].strftime('%Y-%m-%d %H:%M')
            })

        st.dataframe(history_data, use_container_width=True)

        # Calculate total revenue
        total_revenue = sum(inv['total'] for inv in st.session_state.invoice_history)
        st.metric("💵 Total Revenue", format_currency(total_revenue))

        if st.button("🗑️ Clear History"):
            st.session_state.invoice_history = []
            st.rerun()
    else:
        st.info("No invoices in history yet. Generate your first invoice!")

# Sidebar
with st.sidebar:
    st.markdown("## ℹ️ About")

    # Display logo in sidebar if available
    if st.session_state.logo_data:
        st.image(st.session_state.logo_data, use_container_width=True)

    st.markdown("""
    **Groupe eRDV Invoice Generator v2.0**

    A professional invoice generation and management system.

    ### ✨ Features:
    - ✅ Custom branding with logo
    - ✅ Multi-tab interface
    - ✅ Invoice history tracking
    - ✅ Real-time calculations
    - ✅ Professional PDF generation
    - ✅ Responsive design
    - ✅ Auto-save drafts
    - ✅ Financial summaries

    ### 📊 Quick Stats:
    """)

    if st.session_state.work_entries:
        total_hours = sum(e['days'] * e['hours_per_day'] for e in st.session_state.work_entries)
        st.metric("Current Hours", f"{total_hours:.2f}")

    if st.session_state.invoice_history:
        st.metric("Invoices Created", len(st.session_state.invoice_history))

    st.markdown("---")
    st.markdown("""
    ### 💡 Tips:
    - Upload your company logo for branding
    - Use the History tab to track invoices
    - Customize default rates and settings
    - Export PDFs for professional delivery
    """)

    st.markdown("---")
    st.markdown("**Made with ❤️ for Groupe eRDV**")
    st.caption("v2.0 - Enhanced Edition")
