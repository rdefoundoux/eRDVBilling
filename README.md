# 📄 Groupe eRDV Invoice Generator

A professional, modern invoice generation application built with Streamlit for consulting services.

## 🌟 Features

- **Professional Design**: Beautiful gradient UI with modern styling
- **Company & Client Management**: Easy input forms for business information
- **Work Entry System**: Add multiple work entries with descriptions, hours, and rates
- **Automatic Calculations**: Real-time calculation of subtotals, taxes, and totals
- **PDF Generation**: Export professional invoices as PDF documents
- **Responsive Layout**: Two-column design for easy data entry and preview
- **Session Management**: Maintains state across interactions

## 🚀 Quick Start

### Local Deployment

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   streamlit run invoice_generator_app.py
   ```

3. **Access the app**: Open your browser to `http://localhost:8501`

### Streamlit Cloud Deployment

1. **Push to GitHub**:
   - Create a new GitHub repository
   - Push these files to your repository:
     - `invoice_generator_app.py`
     - `requirements.txt`
     - `README.md`

2. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account
   - Click "New app"
   - Select your repository, branch, and main file (`invoice_generator_app.py`)
   - Click "Deploy"

## 📖 How to Use

1. **Company Information**: Enter your company details in the Company Information section
2. **Client Information**: Fill in your client's information
3. **Invoice Details**: Set invoice number, date, payment terms, and due date
4. **Work Entry Settings**: Configure default hourly rate, hours per day, and tax rate
5. **Add Work Entries**: Add individual work entries with descriptions, days worked, hours per day, and rates
6. **Preview**: View the invoice preview in real-time on the right side
7. **Download**: Click "Download PDF Invoice" to generate and download the professional PDF

## 🛠️ Technical Details

### Built With
- **Streamlit**: Web application framework
- **ReportLab**: PDF generation library
- **Python 3.8+**: Programming language

### File Structure
```
├── invoice_generator_app.py   # Main application file
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🎨 Customization

### Colors
The app uses a purple gradient theme (`#667eea` to `#764ba2`). To customize:
- Modify the CSS in the `st.markdown()` section
- Update the color values in the PDF generation function

### Default Values
Edit the default values in the input fields:
- Company information
- Default hourly rate
- Default hours per day
- Tax rate

## 📝 Features in Detail

### Work Entries
- Add unlimited work entries
- Each entry includes:
  - Description
  - Days worked
  - Hours per day
  - Hourly rate
- Automatic calculation of total hours and amount

### Calculations
- **Subtotal**: Sum of all work entry amounts
- **Tax**: Configurable tax rate applied to subtotal
- **Total**: Subtotal + Tax

### PDF Export
Generated PDFs include:
- Company header with branding
- Client billing information
- Invoice details (number, date, terms, due date)
- Itemized work entries table
- Professional formatting with colors and styling

## 🔧 Troubleshooting

### Common Issues

1. **Module not found error**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Port already in use**:
   ```bash
   streamlit run invoice_generator_app.py --server.port 8502
   ```

3. **PDF generation fails**: Ensure reportlab is properly installed

## 📄 License

This project is created for Groupe eRDV inc.

## 👨‍💻 Support

For issues or questions, please contact your development team.

## 🔄 Version History

- **v1.0.0** (2025-12-29)
  - Initial release
  - Core invoice generation functionality
  - PDF export capability
  - Modern UI with gradient design

---

**Made with ❤️ for Groupe eRDV**
