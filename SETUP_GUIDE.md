# 📋 Smart Expense Analyzer - Complete Setup Guide

## 📁 Project Files Overview

Your Smart Expense Analyzer project includes:

```
course project/
├── app.py                      # 🎯 Main Streamlit application (the app you run)
├── config.py                   # ⚙️ Configuration file (customize categories, patterns)
├── requirements.txt            # 📦 Python dependencies
├── generate_test_data.py       # 🧪 Test data generator
├── sample_expenses.csv         # 📊 Sample output format reference
├── README.md                   # 📚 Full documentation
├── QUICK_START.md             # 🚀 Quick start guide
├── SETUP_GUIDE.md             # 📋 This file
└── expenses_cleaned.csv       # 💾 Output file (generated after processing)
```

---

## ✅ Step-by-Step Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- A terminal/command prompt

### Step 1: Navigate to Project Directory
```bash
cd /Users/atulkumar/Desktop/college/sem\ 6/dwm/course\ project
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- **streamlit** - Web app framework
- **pdfplumber** - PDF text extraction
- **pandas** - Data manipulation
- **python-dateutil** - Date parsing

### Step 4: Run the Application
```bash
streamlit run app.py
```

Your app will open automatically at `http://localhost:8501`

---

## 🧪 Testing the App

### Option 1: Generate Test Data (Quickest)
```bash
python generate_test_data.py
```

This creates a sample PDF with mock expenses. Then:
1. Upload the generated PDF in the app
2. Click "Process PDF"
3. See the results!

### Option 2: Use Your Own PDF
1. Prepare a PDF with transaction data
2. Upload in the app
3. Click "Process PDF"

### Option 3: Add Custom PDF Format
Edit `config.py` to add your date/amount formats:
```python
SUPPORTED_DATE_FORMATS = [
    '%d-%m-%Y',  # Your format here
    # ...
]
```

---

## 🎯 Main Features

### 1. **Extract Text from PDF** ✅
- Handles multi-page PDFs
- Supports various PDF formats
- Raw text display for debugging

### 2. **Parse Transactions** ✅
- Regex-based extraction
- Identifies: Date, Amount, Description
- Flexible format support

### 3. **Clean Data** ✅
- Converts amounts to numeric
- Standardizes date formats
- Removes invalid entries
- Sorts by date

### 4. **Categorize Transactions** ✅
- Keyword-based categorization
- 6 default categories (Food, Travel, Shopping, etc.)
- Easy to customize

### 5. **Display Results** ✅
- Interactive DataFrame
- Summary statistics
- Category breakdown charts
- CSV download

---

## 🔧 Customization Guide

### Add New Category
Edit `config.py`:
```python
CATEGORIES = {
    'Your_Category': {
        'keywords': ['keyword1', 'keyword2', 'keyword3'],
        'color': '#FF6B6B'
    },
    # ... rest of categories
}
```

### Adjust Regex Patterns
Edit `config.py`:
```python
# Add date format
DATE_PATTERN = r'your_regex_pattern'

# Add amount format
AMOUNT_PATTERN = r'your_regex_pattern'
```

### Change Currency Symbol
Edit `config.py`:
```python
CURRENCY_SYMBOL = "€"  # or $ or ₹
```

### Modify Date Formats
Edit `config.py`:
```python
SUPPORTED_DATE_FORMATS = [
    '%d-%m-%Y',   # DD-MM-YYYY
    '%d/%m/%Y',   # DD/MM/YYYY
    # Add your formats
]
```

---

## 📝 Code Architecture

### Main Functions in `app.py`

#### 1. `extract_text_from_pdf(pdf_file)`
```python
# Extracts text from PDF pages
text = extract_text_from_pdf(uploaded_file)
```
**Returns:** String with concatenated text from all pages

#### 2. `parse_transactions(text)`
```python
# Parses transaction data from text
transactions = parse_transactions(raw_text)
# Returns: [{'Date': '01-03-2024', 'Description': '...', 'Amount': '450'}, ...]
```

#### 3. `categorize_transaction(description)`
```python
# Assigns category based on keywords
category = categorize_transaction("SWIGGY FOOD")
# Returns: 'Food'
```

#### 4. `clean_data(df)`
```python
# Cleans and standardizes data
df_clean = clean_data(df)
```
**Operations:**
- Remove empty rows
- Convert Amount → numeric
- Standardize dates
- Sort by date

#### 5. `main()`
```python
# Streamlit UI and workflow
main()
```
**Workflow:**
1. File upload UI
2. Extract text
3. Parse transactions
4. Clean data
5. Categorize
6. Display results

---

## 📊 Data Flow

```
PDF File
   ↓
Extract Text (pdfplumber)
   ↓
Parse with Regex (Date, Amount, Description)
   ↓
Convert to DataFrame
   ↓
Clean Data (numeric, standardize dates)
   ↓
Categorize (keyword matching)
   ↓
Display & Save Results
   ↓
CSV Export
```

---

## 🐛 Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'streamlit'`
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: `No text could be extracted from the PDF`
**Solution:** Your PDF might be image-based (scanned). Try:
- Using a different PDF
- Installing OCR (for scanned PDFs): `pip install pytesseract`

### Issue: No transactions found
**Solution:** Check your PDF format:
- Date must be in one of the supported formats
- Amounts must contain numbers
- Use the debug text viewer to see what's extracted

### Issue: Wrong category assignment
**Solution:** Update keywords in `config.py`
```python
CATEGORIES = {
    'Food': {
        'keywords': ['swiggy', 'your_merchant', ...]
    }
}
```

### Issue: App won't start
**Solution:** Check Python version
```bash
python --version  # Should be 3.8+
```

---

## 📦 Dependency Details

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | 1.28.1 | Web app framework |
| pdfplumber | 0.10.3 | PDF text extraction |
| pandas | 2.1.3 | Data manipulation |
| python-dateutil | 2.8.2 | Date parsing |

---

## 🎨 UI Components

### File Uploader
```python
uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'])
```

### Process Button
```python
if st.button("🔍 Process PDF", use_container_width=True):
    # Processing logic
```

### Data Display
```python
st.dataframe(df, use_container_width=True)
```

### Metrics
```python
st.metric("Total Spending", f"₹{total:,.2f}")
```

### Charts
```python
st.pie_chart(category_data)
```

### Download Button
```python
st.download_button(
    label="Download CSV",
    data=csv_data,
    file_name="expenses_cleaned.csv"
)
```

---

## 📈 Sample Output

### Cleaned DataFrame
| Date | Description | Amount | Category |
|------|------------|--------|----------|
| 2024-03-20 | SWIGGY FOOD DELIVERY | ₹450.00 | Food |
| 2024-03-19 | UBER TRIP | ₹320.50 | Travel |
| 2024-03-18 | AMAZON.IN PURCHASE | ₹1999.00 | Shopping |

### Summary Statistics
- Total Spending: ₹15,234.50
- Total Transactions: 15
- Average Amount: ₹1,015.63

### Category Breakdown
- Food: ₹2,850.00 (5 transactions)
- Travel: ₹2,100.00 (4 transactions)
- Shopping: ₹5,000.00 (3 transactions)
- etc.

---

## 🚀 Running in Production

For production deployment:

1. **Use a proper hosting service** (Streamlit Cloud, Heroku, etc.)
2. **Set up environment variables**:
   ```bash
   export STREAMLIT_SERVER_PORT=8501
   export STREAMLIT_SERVER_HEADLESS=true
   ```

3. **Create `.streamlit/config.toml`**:
   ```toml
   [server]
   port = 8501
   headless = true
   
   [theme]
   primaryColor = "#1f77b4"
   ```

4. **Deploy**:
   ```bash
   streamlit run app.py --logger.level=error
   ```

---

## 📚 Advanced Usage

### Add Custom PDF Parsing
Modify `parse_transactions()` in `app.py`:
```python
def parse_transactions(text):
    # Add your custom parsing logic
    # Use regex or NLP for better extraction
    pass
```

### Add Database Integration
Save to database instead of CSV:
```python
import sqlite3
conn = sqlite3.connect('expenses.db')
df_clean.to_sql('transactions', conn, if_exists='append')
```

### Add Email Notifications
```python
import smtplib
# Send summary email after processing
```

### Add Analytics Dashboard
Extend Streamlit app with more tabs:
```python
tab1, tab2, tab3 = st.tabs(["Data", "Analytics", "Settings"])
with tab1:
    # Display data
with tab2:
    # Show analytics
```

---

## ✨ Tips & Best Practices

1. **Use well-formatted PDFs** - Machine-readable (not scanned) PDFs work best
2. **Consistent formatting** - Use same date/amount formats throughout PDF
3. **Include merchant names** - Helps with categorization
4. **Test with sample data** - Use `generate_test_data.py` first
5. **Check debug output** - Review raw extracted text for issues
6. **Backup cleaned data** - Keep `expenses_cleaned.csv` for records

---

## 📞 Support & Debugging

### Enable Verbose Logging
```bash
streamlit run app.py --logger.level=debug
```

### View All Extracted Text
Use the "Raw Extracted Text" expander in the app's debug section

### Check Application Logs
Streamlit logs appear in your terminal where app.py is running

### Profile Performance
```bash
streamlit run app.py --profile=true
```

---

## 🔗 Useful Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [pdfplumber GitHub](https://github.com/jsvine/pdfplumber)
- [Pandas Documentation](https://pandas.pydata.org)
- [Python Regex Guide](https://docs.python.org/3/library/re.html)

---

## 📝 Project Summary

**What this app does:**
✅ Extracts transaction data from PDFs
✅ Parses and cleans the data
✅ Automatically categorizes expenses
✅ Provides summary statistics
✅ Exports to CSV for further analysis

**Technologies used:**
- Python 3.8+
- Streamlit (Web UI)
- pdfplumber (PDF extraction)
- Pandas (Data processing)
- Regular expressions (Text parsing)

**Key capabilities:**
- Multi-page PDF support
- Flexible date/amount format detection
- Intelligent categorization
- Data validation and cleaning
- Interactive visualization
- CSV export

---

## ✅ Verification Checklist

Before using the app, verify:

- [ ] Python 3.8+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Can run `streamlit run app.py` without errors
- [ ] App opens in browser at localhost:8501
- [ ] File uploader accepts PDF files
- [ ] Process button is clickable
- [ ] Test data generation works (optional)

---

Happy analyzing! 💰✨

For questions or issues, review the README.md and QUICK_START.md files.
