# 🚀 Quick Start Guide

## Setup & Run (5 minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run the App
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501` in your browser.

---

## How to Use

### 1. **Prepare a PDF File**
Your PDF should contain transaction data with:
- **Date** (in format: DD-MM-YYYY, DD/MM/YYYY, or YYYY-MM-DD)
- **Amount** (numbers, with optional ₹ or $ symbols)
- **Description** (merchant name or transaction details)

**Example PDF Content:**
```
Transaction Summary
Date        Description              Amount
01-03-2024  SWIGGY FOOD DELIVERY    ₹450.00
02-03-2024  UBER TRIP                ₹320.50
03-03-2024  AMAZON.IN PURCHASE       ₹1999.00
```

### 2. **Upload PDF in the App**
- Click on "Choose a PDF file"
- Select your expense PDF

### 3. **Click "Process PDF" Button**
The app will:
1. Extract text from the PDF
2. Parse transaction data
3. Clean and standardize the data
4. Categorize the transactions
5. Show you a preview and summary

### 4. **Review the Results**
- **Raw Extracted Text**: Expand to see what text was extracted (for debugging)
- **Data Preview**: Table showing all parsed and cleaned transactions
- **Summary Statistics**: Total spending, transaction count, average amount
- **Category Analysis**: Spending breakdown by category + pie chart

### 5. **Download the CSV**
Click "📥 Download as CSV" to get `expenses_cleaned.csv`

---

## Testing with Sample Data

### Option 1: Generate a Test PDF

Create a file named `test_transactions.txt` with content like:

```
Bank Statement - March 2024
=================================

Date        | Merchant                | Amount
------------|------------------------|----------
01-03-2024  | SWIGGY FOOD DELIVERY   | ₹450.00
02-03-2024  | UBER TRIP              | ₹320.50
03-03-2024  | AMAZON.IN PURCHASE     | ₹1999.00
04-03-2024  | ZOMATO FOOD ORDER      | ₹280.75
05-03-2024  | OLA CABS RIDE          | ₹145.00
06-03-2024  | FLIPKART SHOPPING      | ₹599.00
07-03-2024  | NETFLIX SUBSCRIPTION   | ₹199.00
08-03-2024  | ELECTRICITY BILL       | ₹2500.00
```

Then convert it to PDF (using online tools or libraries like `reportlab`).

### Option 2: Use Provided Sample Data

Check `sample_expenses.csv` in the project directory to see the expected output format.

---

## What Gets Extracted?

The app identifies and extracts:

### ✅ **Dates**
- Formats: `DD-MM-YYYY`, `DD/MM/YYYY`, `YYYY-MM-DD`
- Examples: `01-03-2024`, `3/1/24`, `2024-03-01`

### ✅ **Amounts**
- Formats: `1000`, `1,000`, `1000.50`, `₹1000`, `$50`
- Automatically converted to numeric values

### ✅ **Descriptions**
- Extracted as remaining text after date and amount
- Used for categorization

### ✅ **Categories** (Auto-assigned)
- **Food**: swiggy, zomato, restaurant, cafe, etc.
- **Travel**: uber, ola, taxi, flight, fuel, etc.
- **Shopping**: amazon, flipkart, mall, store, etc.
- **Entertainment**: movie, netflix, spotify, gaming, etc.
- **Utilities**: electricity, water, internet, phone, etc.
- **Health**: hospital, doctor, pharmacy, medicine, etc.
- **Others**: Default category

---

## Output Files

### 1. **expenses_cleaned.csv**
Saved automatically in the project directory with columns:
- `Date` (standardized to YYYY-MM-DD)
- `Description` (cleaned transaction text)
- `Amount` (numeric value)
- `Category` (auto-assigned)

### 2. **Display in Streamlit**
- DataFrame table
- Summary statistics
- Pie chart showing category distribution
- Download button for CSV

---

## Troubleshooting

**Q: No transactions are extracted**
- A: Check your PDF format. Dates must be in one of the supported formats (DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD)
- Use the "Raw Extracted Text" debug view to see what text is being extracted

**Q: Amounts are not recognized**
- A: Ensure amounts contain digits (1000, 999.99, 1,000). Currency symbols are optional.

**Q: Dates are not standardized**
- A: Use one of these formats: DD-MM-YYYY, DD/MM/YYYY, or YYYY-MM-DD

**Q: Categories are wrong**
- A: Edit the `categorize_transaction()` function in `app.py` to add custom keywords

**Q: PDF text extraction fails**
- A: Try a different PDF. Some scanned/image-based PDFs may not have extractable text. Consider using OCR tools.

---

## Code Structure

### Main Files
- **app.py** - Complete Streamlit application with all functions
- **requirements.txt** - Python dependencies
- **README.md** - Full documentation
- **sample_expenses.csv** - Sample output format

### Main Functions in app.py

1. **`extract_text_from_pdf(pdf_file)`**
   - Extracts text from all PDF pages
   - Returns concatenated text

2. **`parse_transactions(text)`**
   - Identifies transaction lines
   - Extracts date, description, amount
   - Returns list of dictionaries

3. **`categorize_transaction(description)`**
   - Assigns category based on keywords
   - Returns category name

4. **`clean_data(df)`**
   - Converts amounts to numeric
   - Standardizes dates
   - Removes invalid rows

5. **`main()`**
   - Streamlit UI and workflow
   - Orchestrates all functions

---

## Tips for Best Results

1. **Use clear, formatted PDFs** - Machine-readable text works better than scans
2. **Consistent date format** - Use DD-MM-YYYY or YYYY-MM-DD throughout
3. **Include merchant names** - Helps with categorization
4. **Clean amounts** - Numbers with optional decimals and commas
5. **Bank statements work best** - Standard format with clear transaction lines

---

## Customization Examples

### Add a New Category
In `categorize_transaction()` function:
```python
'Groceries': ['dmart', 'big basket', 'supermarket', 'grocery'],
```

### Change Date Format
In `parse_date()` inside `clean_data()`:
```python
formats = ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%B %d, %Y']
```

### Adjust Amount Format
Modify `amount_pattern` in `parse_transactions()`:
```python
amount_pattern = r'[₹$€]?\s*(\d+[.,])*\d+\.?\d{0,2}'
```

---

## Next Steps

- ✅ Test with your own PDF
- 🔧 Customize categories if needed
- 💾 Export cleaned data for analysis
- 📊 Use the CSV in Excel, Power BI, or Python for further analysis

Happy analyzing! 💰✨
