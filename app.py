"""
Smart Expense Analyzer - Streamlit Web App
Extracts and analyzes transactions from PDF files
"""

import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import IsolationForest
import numpy as np
import config
from src.analytics.evaluation import comparison_metrics, evaluate_seed_dataset
from src.nlp.categorizer import categorize_dataframe


st.set_page_config(
    page_title="Smart Expense Analyzer",
    page_icon="💰",
    layout="wide"
)


def extract_text_from_pdf(pdf_file):
    """Extract text from all pages of a PDF file."""
    try:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text
        
        return text if text.strip() else None
    except Exception as e:
        st.error(f"Error extracting PDF: {str(e)}")
        return None


def parse_transactions(text):
    """Parse transactions - handles no-space format from GPay PDFs."""
    transactions = []
    lines = text.split('\n')
    
    # Date patterns - handle both spaced ("02 Oct, 2025") and no-space ("02Oct,2025") formats
    date_pattern = r'(\d{1,2}\s*[A-Za-z]{3}\s*,?\s*\d{4}|\d{1,2}[-./]\d{1,2}[-./]\d{2,4}|\d{4}[-./]\d{1,2}[-./]\d{1,2})'
    
    # Amount pattern - handle ₹77, $77, Rs. 77, etc.
    amount_pattern = r'[₹Rs\$]\.?\s*([\d,]+(?:\.?\d{1,2})?)'
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line or len(line) < 2:
            i += 1
            continue
        
        # Check if this line contains a date
        date_match = re.search(date_pattern, line)
        
        if date_match:
            date_str = date_match.group(1).strip()
            description = None
            amount_str = None
            txn_type = 'Expense'
            
            # Collect next 25 lines for the transaction block
            transaction_block = [line]
            for j in range(i + 1, min(i + 26, len(lines))):
                block_line = lines[j].strip()
                if not block_line:
                    continue
                if re.search(date_pattern, block_line):
                    break
                transaction_block.append(block_line)
            
            block_text = ' '.join(transaction_block)
            block_text_lower = block_text.lower()
            
            # Skip non-transaction blocks
            if any(skip in block_text_lower for skip in ['statement', 'page ', 'total ', 'balance', 'account', 'note:']):
                i += 1
                continue
            
            # Extract amount - look for ₹ or Rs followed by numbers
            amt_match = re.search(amount_pattern, block_text)
            if amt_match:
                amount_str = amt_match.group(1).strip()
            
            # Extract description - look for "Paid to" or "Received from" patterns
            # Handle both spaced and no-space versions
            if 'paidto' in block_text_lower or ('paid' in block_text_lower and 'to' in block_text_lower):
                # Extract text after "Paid to" or "PaidTo"
                match = re.search(r'paid\s*to\s*([A-Za-z][^₹\d]*?)(?:\s+₹|\s+Rs|\s+\$|UPI|Status|$)', block_text, re.IGNORECASE)
                if match:
                    desc = match.group(1).strip()
                    if desc and len(desc) > 2:
                        description = desc
                        txn_type = 'Expense'
            
            elif 'receivedfrom' in block_text_lower or ('received' in block_text_lower and 'from' in block_text_lower):
                # Extract text after "Received from" or "ReceivedFrom"
                match = re.search(r'received\s*from\s*([A-Za-z][^₹\d]*?)(?:\s+₹|\s+Rs|\s+\$|UPI|Status|$)', block_text, re.IGNORECASE)
                if match:
                    desc = match.group(1).strip()
                    if desc and len(desc) > 2:
                        description = desc
                        txn_type = 'Income'
            
            # Fallback: find the transaction details line
            if not description:
                for block_line in transaction_block:
                    block_line_lower = block_line.lower()
                    # Skip lines with specific keywords
                    if any(x in block_line_lower for x in ['upi', 'transactionid', 'paidby', 'paidto', 'receivedfrom', 'status', 'note']):
                        continue
                    # Skip date lines and amount-only lines
                    if re.search(date_pattern, block_line) or re.match(r'^[₹Rs\$\d,\.]+$', block_line):
                        continue
                    if len(block_line) > 3:
                        description = block_line
                        break
            
            # Add transaction if we have sufficient data
            if date_str and amount_str and description:
                description = description.strip()
                # Clean up description
                description = re.sub(r'\s+(?:status|completed|pending|upi|transactionid).*', '', description, flags=re.IGNORECASE)
                description = re.sub(r'\s{2,}', ' ', description)  # Replace multiple spaces with single space
                
                if len(description) > 2:
                    transactions.append({
                        'Date': date_str,
                        'Description': description,
                        'Amount': amount_str,
                        'Type': txn_type
                    })
        
        i += 1
    
    return transactions


def categorize_transaction(description):
    """Categorize transaction based on keywords and person-name fallback."""
    description_lower = description.lower()
    
    categories = {
        'Food': ['swiggy', 'zomato', 'restaurant', 'food', 'cafe'],
        'Travel': ['uber', 'ola', 'rapido', 'travel'],
        'Shopping': ['amazon', 'flipkart', 'store', 'mart', 'shop'],
        'Utilities': ['electricity', 'bill', 'recharge', 'mobile', 'dth'],
        'Entertainment': ['netflix', 'prime', 'movie'],
        'Health': ['pharmacy', 'hospital', 'medical'],
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in description_lower:
                return category
    
    # Unmatched descriptions are explicit Unknown abstentions.
    stripped = re.sub(r'[^A-Za-z\s]', '', description).strip()
    words = stripped.split()
    if stripped and len(words) >= 2 and len(words) <= 5 and all(word.isalpha() for word in words):
        return 'Unknown'
    
    return 'Unknown'


def clean_data(df):
    """Clean and standardize data."""
    if 'Type' in df.columns:
        df = df[df['Type'] == 'Expense'].copy()
    
    df = df.dropna(subset=['Description'])
    df = df[df['Description'].str.strip() != '']
    
    df['Amount'] = df['Amount'].str.replace(',', '')
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    df = df.dropna(subset=['Amount'])
    
    def parse_date(date_str):
        formats = [
            '%d%b,%Y',     # 02Oct,2025 (no spaces - GPay format)
            '%d%b %Y',     # 02Oct 2025 (no space before year)
            '%d %b, %Y',   # 02 Oct, 2025 (with spaces)
            '%d %B, %Y',   # 02 October, 2025
            '%d %b %Y',    # 02 Oct 2025
            '%d-%m-%Y',    # 02-10-2025
            '%d/%m/%Y',    # 02/10/2025
            '%Y-%m-%d',    # 2025-10-02
            '%d-%m-%y',    # 02-10-25
            '%d/%m/%y',    # 02/10/25
            '%Y/%m/%d',    # 2025/10/02
        ]
        for fmt in formats:
            try:
                return pd.to_datetime(date_str, format=fmt)
            except (ValueError, TypeError):
                continue
        return pd.NaT
    
    df['Date'] = df['Date'].apply(parse_date)
    df = df.dropna(subset=['Date'])
    
    if 'Type' in df.columns:
        df = df.drop('Type', axis=1)
    
    df = df.sort_values('Date', ascending=False).reset_index(drop=True)
    
    return df


def main():
    """Main Streamlit application"""
    st.title("💰 Smart Expense Analyzer")
    st.markdown("---")
    
    st.subheader("📄 Upload PDF File")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload your expense PDF (bank statement, GPay, Paytm, etc.)"
    )
    
    if st.button("🔍 Process PDF", use_container_width=True):
        if uploaded_file is None:
            st.warning("⚠️ Please upload a PDF file first!")
            return
        
        with st.spinner("Processing PDF..."):
            st.info("📖 Extracting text from PDF...")
            raw_text = extract_text_from_pdf(uploaded_file)
            
            if not raw_text:
                st.error("❌ No text could be extracted from the PDF")
                return
            
            with st.expander("🔍 Raw Extracted Text (Debug)"):
                st.text(raw_text[:2000] + "..." if len(raw_text) > 2000 else raw_text)
            
            st.info("🔎 Parsing transaction data...")
            transactions = parse_transactions(raw_text)
            
            if not transactions:
                st.warning("⚠️ No transactions found in the PDF.")
                return
            
            st.success(f"✅ Found {len(transactions)} transactions!")
            
            st.info("🧹 Cleaning data...")
            df = pd.DataFrame(transactions)
            df_clean = clean_data(df)
            
            if df_clean.empty:
                st.warning("⚠️ No valid transactions after cleaning.")
                return
            
            st.info("🏷️ Categorizing transactions with the TWSMA pipeline...")
            df_clean = categorize_dataframe(df_clean)
            df_clean['Amount'] = pd.to_numeric(df_clean['Amount'], errors='coerce')
            df_clean = df_clean.dropna(subset=['Amount'])
            
            st.markdown("---")
            st.subheader("📊 Cleaned Data Preview")
            
            display_df = df_clean.copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
            display_df['Amount'] = display_df['Amount'].apply(lambda x: f"₹{x:,.2f}")
            
            st.dataframe(display_df, use_container_width=True, hide_index=False)
            
            st.markdown("---")
            st.subheader("📈 Summary Statistics")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💵 Total Spending", f"₹{df_clean['Amount'].sum():,.2f}")
            
            with col2:
                st.metric("📊 Total Transactions", len(df_clean))
            
            with col3:
                st.metric("📉 Average Amount", f"₹{df_clean['Amount'].mean():,.2f}")
            
            st.subheader("🏷️ Spending by Category")
            
            category_summary = df_clean.groupby('Category')['Amount'].agg(['sum', 'count']).reset_index()
            category_summary.columns = ['Category', 'Total Amount', 'Transaction Count']
            category_summary = category_summary.sort_values('Total Amount', ascending=False)
            
            display_category = category_summary.copy()
            display_category['Total Amount'] = display_category['Total Amount'].apply(lambda x: f"₹{x:,.2f}")
            
            st.dataframe(display_category, use_container_width=True, hide_index=False)

            st.markdown("---")
            st.subheader("🧠 TWSMA Text Analytics")
            st.caption("Transaction text → preprocessing → entity evidence → TF-IDF → classification → final category")
            twsma_metrics = comparison_metrics(df_clean)
            metric_cols = st.columns(7)
            metric_cols[0].metric("Automatically classified", twsma_metrics['ml_transactions'])
            metric_cols[1].metric("P2P", twsma_metrics['final_p2p_count'])
            metric_cols[2].metric("Unknown", twsma_metrics['final_unknown_count'])
            metric_cols[3].metric("Baseline Unknown", twsma_metrics['baseline_unknown_count'])
            metric_cols[4].metric("Person entities", twsma_metrics['person_entities'])
            metric_cols[5].metric("Merchant/Service", twsma_metrics['merchant_entities'])
            metric_cols[6].metric("Unresolved %", f"{twsma_metrics['final_misc_rate']:.1%}")

            comparison = pd.DataFrame({
                'Baseline': df_clean['Baseline_Category'].value_counts(),
                'Final': df_clean['Final_Category'].value_counts(),
            }).fillna(0)
            st.write("**Baseline versus enhanced category distribution**")
            st.bar_chart(comparison)
            method_counts = df_clean['Categorization_Method'].value_counts().rename_axis('Method').to_frame('Transactions')
            st.write("**Categorization methods**")
            st.bar_chart(method_counts)

            with st.expander("🔬 NLP Processing Details"):
                from src.nlp.categorizer import get_classifier
                classifier = get_classifier()
                st.write(f"Reviewed real-data training rows: {getattr(classifier, 'training_size', 'unavailable')}")
                st.write(f"ML confidence threshold: {config.ML_CONFIDENCE_THRESHOLD:.2f}")
                st.dataframe(df_clean[['Description', 'Preprocessed_Text', 'Merchant', 'Transaction_Entity_Type', 'NLP_Category', 'Category_Confidence', 'Categorization_Method', 'Web_Enriched']], use_container_width=True, hide_index=True)

            with st.expander("📏 Model Evaluation"):
                evaluation = evaluate_seed_dataset(config.TRAINING_DATA_PATH)
                st.warning(evaluation['warning'])
                if 'accuracy' in evaluation:
                    st.write({key.title(): f"{evaluation[key]:.3f}" for key in ['accuracy', 'precision', 'recall', 'f1']})

            with st.expander("📋 Transaction-level Explainability"):
                explain_cols = ['Date', 'Description', 'Merchant', 'Transaction_Entity_Type', 'Baseline_Category', 'NLP_Category', 'Final_Category', 'Category_Confidence', 'Categorization_Method', 'Web_Enriched']
                explain_df = df_clean[explain_cols].copy()
                explain_df['Date'] = explain_df['Date'].dt.strftime('%Y-%m-%d')
                st.dataframe(explain_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("🤖 ML Insights")
            st.write("This section uses a simple regression model to forecast spending and an isolation forest to flag unusual amounts.")
            
            # =========================
            # 1. SPENDING PREDICTION
            # =========================
            df_ml = df_clean.copy()
            df_ml = df_ml.sort_values('Date')
            df_ml['Days'] = (df_ml['Date'] - df_ml['Date'].min()).dt.days
            X = df_ml[['Days']]
            y = df_ml['Amount']
            
            if len(df_ml) > 5:
                model = LinearRegression()
                model.fit(X, y)
                future_days = np.arange(df_ml['Days'].max() + 1, df_ml['Days'].max() + 8).reshape(-1, 1)
                predictions = model.predict(future_days)
                predicted_spending = predictions.sum()
                st.metric("🔮 Predicted Spending (Next 7 Days)", f"₹{predicted_spending:,.2f}")
            else:
                st.info("Not enough data for prediction")
            
            # =========================
            # 2. ANOMALY DETECTION
            # =========================
            df_clean['Anomaly'] = 1
            if len(df_clean) > 15:
                df_anomaly = df_clean.copy()
                df_anomaly = df_anomaly.sort_values('Date')
                df_anomaly['Amount_log'] = np.log1p(df_anomaly['Amount'])
                df_anomaly['RollingMean'] = df_anomaly['Amount'].rolling(window=5, min_periods=1).mean()
                df_anomaly['Deviation'] = df_anomaly['Amount'] - df_anomaly['RollingMean']
                features = df_anomaly[['Amount_log', 'Deviation']].fillna(0)

                iso = IsolationForest(
                    contamination=0.02,
                    random_state=42
                )
                df_anomaly['anomaly'] = iso.fit_predict(features)

                # merge anomaly labels back into the main cleaned dataframe
                df_clean['Anomaly'] = df_anomaly['anomaly']

                anomalies = df_anomaly[df_anomaly['anomaly'] == -1]
                anomalies = anomalies[anomalies['Amount'] > df_anomaly['Amount'].mean()]

                st.metric("⚠️ Unusual Transactions Detected", len(anomalies))
                if not anomalies.empty:
                    st.write("### 🚨 Suspicious Transactions")
                    display_anomaly = anomalies[['Date', 'Description', 'Amount']].copy()
                    display_anomaly['Date'] = display_anomaly['Date'].dt.strftime('%Y-%m-%d')
                    display_anomaly['Amount'] = display_anomaly['Amount'].apply(lambda x: f"₹{x:,.2f}")
                    st.dataframe(display_anomaly, use_container_width=True)
            else:
                st.info("Not enough data for anomaly detection")
            
            st.markdown("---")
            st.subheader("💾 Download Cleaned Data")
            
            csv_data = df_clean.copy()
            csv_data['Date'] = csv_data['Date'].dt.strftime('%Y-%m-%d')
            csv_buffer = csv_data.to_csv(index=False)
            
            st.download_button(
                label="📥 Download as CSV",
                data=csv_buffer,
                file_name="expenses_cleaned.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            output_path = Path("expenses_cleaned.csv")
            csv_data.to_csv(output_path, index=False)
            st.success(f"✅ Dataset saved to {output_path}")


if __name__ == "__main__":
    main()
