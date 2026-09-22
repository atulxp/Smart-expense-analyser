"""
Configuration file for Smart Expense Analyzer
Customize categories, regex patterns, and other settings here
"""

# =================== PATHS AND TWSMA SETTINGS ===================
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
NLP_ENABLED = True
ML_CONFIDENCE_THRESHOLD = 0.60
WEB_ENRICHMENT_ENABLED = True
WEB_ENRICHMENT_TIMEOUT = 5
MODEL_PATH = BASE_DIR / 'models' / 'expense_classifier.joblib'
VECTORIZER_PATH = BASE_DIR / 'models' / 'tfidf_vectorizer.joblib'
REAL_TRAINING_DATA_PATH = BASE_DIR / 'data' / 'real_transaction_samples.csv'
TRAINING_DATA_PATH = REAL_TRAINING_DATA_PATH if REAL_TRAINING_DATA_PATH.exists() else BASE_DIR / 'data' / 'training_transactions.csv'
REAL_LABEL_MINIMUM = 150

# =================== CATEGORY DEFINITIONS ===================
CATEGORIES = {
    'Food': {
        'keywords': ['swiggy', 'zomato', 'restaurant', 'cafe', 'pizza', 'burger', 'food', 'delivery'],
        'color': '#FF6B6B'
    },
    'Travel': {
        'keywords': ['uber', 'ola', 'taxi', 'bus', 'flight', 'train', 'petrol', 'fuel', 'airline'],
        'color': '#4ECDC4'
    },
    'Shopping': {
        'keywords': ['amazon', 'flipkart', 'mall', 'store', 'shop', 'clothing', 'apparel', 'market'],
        'color': '#95E1D3'
    },
    'Entertainment': {
        'keywords': ['movie', 'cinema', 'netflix', 'spotify', 'gaming', 'game', 'theatre', 'show'],
        'color': '#F38181'
    },
    'Utilities': {
        'keywords': ['electricity', 'water', 'internet', 'phone', 'gas', 'bill', 'broadband', 'mobile'],
        'color': '#AA96DA'
    },
    'Health': {
        'keywords': ['hospital', 'pharmacy', 'doctor', 'medicine', 'health', 'clinic', 'dental', 'medical'],
        'color': '#FCBAD3'
    },
    'Others': {
        'keywords': [],
        'color': '#C8C8C8'
    }
}

# =================== REGEX PATTERNS ===================
# Date pattern - matches: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, DD-MM-YY, etc.
DATE_PATTERN = r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})'

# Amount pattern - matches: 1000, 1,000, 1000.50, ₹1000, $50, €100, etc.
AMOUNT_PATTERN = r'[₹$€]?\s*(\d+,)*\d+\.?\d*'

# =================== DATE FORMATS ===================
# Supported date formats for parsing
SUPPORTED_DATE_FORMATS = [
    '%d-%m-%Y',  # 01-03-2024
    '%d/%m/%Y',  # 01/03/2024
    '%Y-%m-%d',  # 2024-03-01
    '%d-%m-%y',  # 01-03-24
    '%d/%m/%y',  # 01/03/24
    '%Y/%m/%d',  # 2024/03/01
    '%B %d, %Y', # March 01, 2024
    '%b %d, %Y', # Mar 01, 2024
]

# =================== STREAMLIT UI SETTINGS ===================
APP_TITLE = "Smart Expense Analyzer"
APP_ICON = "💰"
APP_LAYOUT = "wide"

# Page titles and messages
TITLES = {
    'main': "💰 Smart Expense Analyzer",
    'upload': "📄 Upload PDF File",
    'data_preview': "📊 Cleaned Data Preview",
    'summary': "📈 Summary Statistics",
    'category': "🏷️ Spending by Category",
    'download': "💾 Download Cleaned Data",
}

MESSAGES = {
    'no_file': "⚠️ Please upload a PDF file first!",
    'extracting': "📖 Extracting text from PDF...",
    'extraction_failed': "❌ No text could be extracted from the PDF",
    'parsing': "🔎 Parsing transaction data...",
    'parsing_success': "✅ Found {count} transactions!",
    'parsing_failed': "⚠️ No transactions found in the PDF. Try a different format.",
    'cleaning': "🧹 Cleaning data...",
    'cleaning_failed': "⚠️ No valid transactions after cleaning the data.",
    'categorizing': "🏷️ Categorizing transactions...",
    'success': "✅ Dataset saved to {path}",
}

# =================== DATA CLEANING SETTINGS ===================
# Minimum required fields for a valid transaction
REQUIRED_FIELDS = ['Date', 'Amount', 'Description']

# Should we drop transactions with missing descriptions?
DROP_EMPTY_DESCRIPTIONS = True

# Numeric conversion - decimal places
DECIMAL_PLACES = 2

# =================== OUTPUT SETTINGS ===================
# Output CSV filename
OUTPUT_CSV = "expenses_cleaned.csv"

# CSV export options
CSV_OPTIONS = {
    'index': False,
    'encoding': 'utf-8'
}

# =================== METRICS & FORMATTING ===================
# Currency symbol
CURRENCY_SYMBOL = "₹"

# Number formatting
AMOUNT_FORMAT = "{:,.2f}"
PERCENTAGE_FORMAT = "{:.1f}%"

# =================== ADVANCED SETTINGS ===================
# Maximum transactions to display initially
MAX_DISPLAY_ROWS = 100

# Enable debug mode (shows raw extracted text)
DEBUG_MODE = True

# Minimum amount threshold (skip transactions below this)
MIN_AMOUNT = 0

# Maximum amount threshold (skip transactions above this, 0 = no limit)
MAX_AMOUNT = 0

# =================== CATEGORY FUNCTION ===================
def get_category(description: str) -> str:
    """
    Get category for a transaction description
    Uses CATEGORIES configuration above
    
    Args:
        description: Transaction description
    
    Returns:
        str: Category name
    """
    if not isinstance(description, str) or not description.strip():
        return 'Unknown'

    description_lower = description.lower()
    
    for category, config in CATEGORIES.items():
        if category == 'Others':
            continue
        
        for keyword in config['keywords']:
            if keyword in description_lower:
                return category
    
    return 'Unknown'


# =================== HELPER FUNCTIONS ===================
def get_category_color(category: str) -> str:
    """Get color for a category"""
    return CATEGORIES.get(category, {}).get('color', '#C8C8C8')


def get_all_categories() -> list:
    """Get list of all categories"""
    return list(CATEGORIES.keys())


def format_amount(amount: float) -> str:
    """Format amount with currency symbol"""
    return f"{CURRENCY_SYMBOL}{AMOUNT_FORMAT.format(amount)}"


# =================== CUSTOMIZATION EXAMPLES ===================
"""
TO ADD A NEW CATEGORY:
1. Add to CATEGORIES dictionary:
   'Groceries': {
       'keywords': ['dmart', 'big basket', 'supermarket', 'grocery'],
       'color': '#FFD93D'
   }

TO CHANGE DATE FORMATS:
1. Modify SUPPORTED_DATE_FORMATS list with your desired formats

TO ADD KEYWORDS TO EXISTING CATEGORY:
1. Update the 'keywords' list in the CATEGORIES dictionary

TO CHANGE CURRENCY SYMBOL:
1. Update CURRENCY_SYMBOL variable

TO ADJUST REGEX PATTERNS:
1. Update DATE_PATTERN and AMOUNT_PATTERN variables

EXAMPLE CUSTOM PATTERN (includes more date formats):
DATE_PATTERN = r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
"""

if __name__ == "__main__":
    # Print configuration summary
    print("Smart Expense Analyzer - Configuration Summary")
    print("=" * 50)
    print(f"\nCategories defined: {len(CATEGORIES)}")
    for category, config in CATEGORIES.items():
        print(f"  - {category}: {len(config['keywords'])} keywords")
    
    print(f"\nSupported date formats: {len(SUPPORTED_DATE_FORMATS)}")
    print(f"Currency symbol: {CURRENCY_SYMBOL}")
    print(f"Output file: {OUTPUT_CSV}")
    print(f"\nSample amount format: {format_amount(1999.99)}")
