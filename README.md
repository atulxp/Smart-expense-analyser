# 💰 Smart Expense Analyzer

A Streamlit web application that extracts, parses, and analyzes expense transactions from PDF files.

## Features

✅ **PDF Text Extraction** - Automatically extracts text from PDF bank statements and receipts  
✅ **Transaction Parsing** - Identifies and extracts transaction data (date, amount, description)  
✅ **Data Cleaning** - Standardizes dates, converts amounts to numeric values, removes invalid rows  
✅ **Smart Categorization** - Automatically categorizes transactions (Food, Travel, Shopping, etc.)  
✅ **Summary Statistics** - Displays total spending, transaction count, and average amount  
✅ **Category Analysis** - Visualizes spending breakdown by category  
✅ **CSV Export** - Downloads cleaned dataset for further analysis  

## Requirements

- Python 3.8+
- Libraries listed in `requirements.txt`

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /path/to/course\ project
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the Streamlit app:**
   ```bash
   streamlit run app.py
   ```

2. **Upload a PDF file** containing expense transactions

3. **Click "Process PDF"** to:
   - Extract text from the PDF
   - Parse transaction data
   - Clean and standardize the data
   - Categorize transactions
   - Generate summary statistics

4. **View and download** the cleaned data as CSV

## File Structure

```
course project/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── README.md                # This file
└── expenses_cleaned.csv     # Output (generated after processing)
```

## Code Architecture

### Key Functions

**`extract_text_from_pdf(pdf_file)`**
- Extracts text from all pages of a PDF
- Returns concatenated text from all pages

**`parse_transactions(text)`**
- Identifies transaction lines using regex patterns
- Extracts date, amount, and description
- Returns list of transaction dictionaries

**`categorize_transaction(description)`**
- Categorizes based on keywords
- Supported categories: Food, Travel, Shopping, Entertainment, Utilities, Health, Others

**`clean_data(df)`**
- Converts amounts to numeric values
- Standardizes date formats
- Removes invalid/empty rows
- Sorts by date

### Regex Patterns

**Date Pattern:** `(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})`
- Matches: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, etc.

**Amount Pattern:** `[₹$]?\s*(\d+,)*\d+\.?\d*`
- Matches: ₹1000, $50, 999.99, 1,000, etc.

## Category Rules

| Category | Keywords |
|----------|----------|
| Food | swiggy, zomato, restaurant, cafe, pizza, burger |
| Travel | uber, ola, taxi, bus, flight, train, petrol, fuel |
| Shopping | amazon, flipkart, mall, store, shop, clothing |
| Entertainment | movie, cinema, netflix, spotify, gaming |
| Utilities | electricity, water, internet, phone, gas, bill |
| Health | hospital, pharmacy, doctor, medicine, clinic |
| Others | Default category |

## Expected PDF Format

For best results, use PDFs with transactions in this format:
```
Date        Description                Amount
01-03-2024  SWIGGY TECH PAYMENTS      ₹450.00
02-03-2024  UBER TRIP-BANGALORE       ₹320.50
03-03-2024  AMAZON.IN ONLINE PURCHASE ₹1999.00
```

## Output

The app generates:
1. **Console Display**: DataFrames and charts in Streamlit UI
2. **CSV File**: `expenses_cleaned.csv` with cleaned transaction data
3. **Summary Stats**: Total spending, category breakdown, averages

## Typical Workflow

1. Upload bank statement PDF
2. View raw extracted text (debugging)
3. Process and parse transactions
4. View cleaned data preview
5. Analyze summary statistics and category breakdown
6. Download CSV for further analysis

## Error Handling

- ⚠️ Invalid PDF files → User-friendly error message
- ⚠️ No text extracted → Warning with suggestion
- ⚠️ No transactions found → Warning about format
- ⚠️ Invalid data after cleaning → Warning about data quality

## Customization

### Add New Categories
Edit the `categorize_transaction()` function:
```python
categories = {
    'NewCategory': ['keyword1', 'keyword2'],
    # ...
}
```

### Change Date Formats
Modify the `formats` list in the `parse_date()` function inside `clean_data()`

### Adjust Regex Patterns
Update `date_pattern` and `amount_pattern` in `parse_transactions()` function

## Troubleshooting

**Issue:** No transactions found
- **Solution:** Check if your PDF format matches expected structure. Use the debug text viewer to inspect extracted text.

**Issue:** Dates not recognized
- **Solution:** Ensure dates are in one of the supported formats (DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD)

**Issue:** Amounts not extracted correctly
- **Solution:** Check that amounts have digits (with optional commas/decimals). Currency symbols are optional.

## Future Enhancements

- 🔄 OCR support for scanned PDFs (pytesseract)
- 📅 Date range filtering
- 💾 Multiple file uploads for batch processing
- 🤖 ML-based category prediction
- 📊 Advanced analytics and trends
- 💬 Natural language processing for better description parsing

## License

This project is for educational purposes.

## Author

Built for TWSMA Course Project.

---

**Happy Expense Tracking!** 💰✨

## TWSMA Text Analytics Extension

The original PDF parser, cleaning flow, financial summaries, forecasting, anomaly detection, keyword categorization, and CSV export remain in `app.py`. The new text analytics layer is modular:

```
Transaction description
   -> preprocessing (IDs/noise removed, merchant words preserved)
   -> merchant/entity extraction
   -> TF-IDF unigrams and bigrams
   -> Logistic Regression category + confidence
   -> optional cached web enrichment for low-confidence merchants
   -> keyword fallback, P2P, or Unknown
```

### Modules and data

- `src/nlp/preprocessing.py` normalizes text and retains payment metadata.
- `src/nlp/entity_extraction.py` extracts known merchants, conservative unknown candidates, location, and payment method.
- `src/nlp/classifier.py` trains a reusable TF-IDF plus Logistic Regression classifier.
- `src/nlp/categorizer.py` provides the central hybrid categorization service and dataframe enrichment.
- `src/web/merchant_enrichment.py` provides optional, timeout-protected DuckDuckGo Instant Answer enrichment. It is cached and only makes live requests when `WEB_ENRICHMENT_LIVE=1`; the app works offline by default.
- `src/analytics/evaluation.py` calculates real baseline-versus-final Unknown rates and stratified transaction-level and unseen-merchant holdout evaluations.
- `data/real_transaction_samples.csv` contains 163 deduplicated, manually reviewed descriptions from the supplied PDFs. `Suggested_Category` is advisory; only `Final_Label` is used for training. It is intentionally not a production ground truth set.

The app shows `Baseline_Category`, `NLP_Category`, `Final_Category`, `Category_Confidence`, `Categorization_Method`, `Merchant`, `Transaction_Entity_Type`, and `Web_Enriched` for inspection. `ML_CONFIDENCE_THRESHOLD` is configured in `config.py` and defaults to `0.60`. PERSON entities are evidence only; explicit transfer evidence is required for `P2P`. Low-confidence results abstain as `Unknown` or use the existing keyword categorizer.

The TWSMA dashboard reports total transactions, NLP/keyword/web method counts, P2P, Unknown, entity types, confidence, and baseline/final category distributions calculated from the processed statement. It does not claim an improvement unless the uploaded data demonstrates one.

### Installation and tests

```bash
pip install -r requirements.txt
streamlit run app.py
pytest -q
```

The web layer is optional and can be left disabled for offline demonstrations. No API key is required. The reviewed dataset and holdout are still small, so the evaluation is an academic diagnostic rather than a generalization benchmark. No spaCy, transformer model, social-media feed, or external banking integration is required.

## TWSMA Evaluation

The baseline is the existing keyword categorizer. Each description then passes through entity detection, which distinguishes `PERSON`, `MERCHANT`, `SERVICE`, and `UNKNOWN`. PERSON detection does not itself imply P2P; positive transfer evidence is required. Without it, the system abstains as `Unknown`.

The NLP classifier combines word TF-IDF unigrams/bigrams and character TF-IDF 3-5 grams with Logistic Regression. The confidence threshold remains `0.60`. A high-confidence ML prediction cannot overwrite an existing non-Misc baseline category unless the predicted category also has explicit textual evidence. This protects strong keyword decisions while allowing merchant/service transactions previously classified as Unknown to improve.

Low-confidence merchant/service candidates may use optional cached web enrichment. Web access is not required, has a timeout, and failed lookups fall back to the keyword system. The final fallback order is therefore entity evidence, NLP, optional web enrichment, keyword categorization, and Unknown.

The real-data evaluation uses 923 transactions from the supported PDF fixtures and a separate manually reviewed set of 163 unique descriptions. `Suggested_Category` is not treated as ground truth; only `Final_Label` is used for training and holdout evaluation. The current transaction-level 20% holdout reports 81.8% accuracy, 0.623 macro F1, and 0.776 weighted F1. The grouped unseen-merchant evaluation reports 60.6% accuracy, 0.468 macro F1, and 0.543 weighted F1. These are academic diagnostic results, not production performance claims.

Phase 1 separates `P2P` from `Unknown`. `P2P` requires positive evidence such as a person-like entity together with transfer language or a preserved transfer payment method. A person-like description without that evidence is `Unknown`, not automatically P2P. The supplied PDFs did not reliably preserve transfer wording or VPA handles, so the current full-fixture run produces no positive P2P decisions; this is an abstention-policy result, not fabricated certainty.

The transaction-level holdout and the grouped unseen-merchant evaluation are both reported in `reports/model_evaluation.json`. The grouped evaluation keeps normalized merchant groups together between train and test and is the more conservative estimate of merchant generalization. Confidence bands are also reported to check whether higher model confidence corresponds to correctness.

The final reports are saved in `reports/non_misc_changes.csv`, `reports/p2p_unknown_diagnostic.csv`, `reports/final_comparison.csv`, and `reports/model_evaluation.json`. The non-Misc review records evidence-based assessments where prior review data is available. Conservative baseline protection prevents unsupported ML disagreements from overwriting explicit keyword categories.
