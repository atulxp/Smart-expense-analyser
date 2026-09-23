"""Smart Expense Analyzer Streamlit application."""

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pdfplumber
import streamlit as st
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

import config
from src.analytics.evaluation import comparison_metrics, evaluate_seed_dataset
from src.memory.human_feedback import append_human_feedback, unique_feedback_entity_count
from src.memory.merchant_memory import ALLOWED_CATEGORIES, normalize_entity_key, save_memory_mapping
from src.memory.review_queue import build_review_queue
from src.nlp.categorizer import categorize_dataframe

st.set_page_config(page_title="Smart Expense Analyzer", page_icon="💰", layout="wide")


def extract_text_from_pdf(pdf_file):
    try:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
        return text if text.strip() else None
    except Exception as exc:
        st.error(f"Error extracting PDF: {exc}")
        return None


def parse_transactions(text):
    transactions = []
    lines = text.split("\n")
    date_pattern = r"(\d{1,2}\s*[A-Za-z]{3}\s*,?\s*\d{4}|\d{1,2}[-./]\d{1,2}[-./]\d{2,4}|\d{4}[-./]\d{1,2}[-./]\d{1,2})"
    amount_pattern = r"[₹Rs$]\.??\s*([\d,]+(?:\.?\d{1,2})?)"
    for index, line in enumerate(lines):
        date_match = re.search(date_pattern, line)
        if not date_match:
            continue
        block = [line.strip()]
        for next_index in range(index + 1, min(index + 26, len(lines))):
            candidate = lines[next_index].strip()
            if not candidate:
                continue
            if re.search(date_pattern, candidate):
                break
            block.append(candidate)
        block_text = " ".join(block)
        lowered = block_text.lower()
        if any(skip in lowered for skip in ["statement", "page ", "total ", "balance", "account", "note:"]):
            continue
        amount_match = re.search(amount_pattern, block_text)
        description = None
        transaction_type = "Expense"
        paid_match = re.search(r"paid\s*to\s*([A-Za-z][^₹\d]*?)(?:\s+₹|\s+Rs|\s+\$|UPI|Status|$)", block_text, re.IGNORECASE)
        received_match = re.search(r"received\s*from\s*([A-Za-z][^₹\d]*?)(?:\s+₹|\s+Rs|\s+\$|UPI|Status|$)", block_text, re.IGNORECASE)
        if paid_match:
            description = paid_match.group(1).strip()
        elif received_match:
            description = received_match.group(1).strip()
            transaction_type = "Income"
        if not description:
            for candidate in block:
                if any(token in candidate.lower() for token in ["upi", "transactionid", "paidby", "paidto", "receivedfrom", "status", "note"]):
                    continue
                if re.search(date_pattern, candidate) or re.match(r"^[₹Rs$\d,.]+$", candidate):
                    continue
                if len(candidate) > 3:
                    description = candidate
                    break
        if amount_match and description and len(description.strip()) > 2:
            description = re.sub(r"\s+(?:status|completed|pending|upi|transactionid).*", "", description.strip(), flags=re.IGNORECASE)
            transactions.append({"Date": date_match.group(1).strip(), "Description": description, "Amount": amount_match.group(1).strip(), "Type": transaction_type})
    return transactions


def clean_data(df):
    if "Type" in df.columns:
        df = df[df["Type"] == "Expense"].copy()
    df = df.dropna(subset=["Description"])
    df = df[df["Description"].str.strip() != ""]
    df["Amount"] = pd.to_numeric(df["Amount"].astype(str).str.replace(",", "", regex=False), errors="coerce")
    df = df.dropna(subset=["Amount"])
    formats = ["%d%b,%Y", "%d%b %Y", "%d %b, %Y", "%d %B, %Y", "%d %b %Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y", "%Y/%m/%d"]
    def parse_date(value):
        for date_format in formats:
            try:
                return pd.to_datetime(value, format=date_format)
            except (ValueError, TypeError):
                pass
        return pd.NaT
    df["Date"] = df["Date"].apply(parse_date)
    df = df.dropna(subset=["Date"])
    if "Type" in df.columns:
        df = df.drop(columns=["Type"])
    return df.sort_values("Date", ascending=False).reset_index(drop=True)


def _entity_transactions(df_clean, entity):
    matching = df_clean.apply(lambda row: normalize_entity_key(row["Description"], row.get("Merchant")) == entity, axis=1)
    return df_clean.loc[matching].sort_values("Date", ascending=False).copy()


def _render_review_section(df_clean):
    st.markdown("---")
    st.subheader("🧾 Merchant / Entity Review")
    st.caption("Only an explicit human confirmation creates memory. Changing a selectbox does not save anything.")
    feedback_count = unique_feedback_entity_count()
    st.write(f"Human feedback collected: {feedback_count} entities")
    st.write(f"Required for retraining: {config.FEEDBACK_RETRAIN_MINIMUM} entities")
    st.write("Status: " + ("READY FOR BATCH RETRAINING" if feedback_count >= config.FEEDBACK_RETRAIN_MINIMUM else "NOT READY"))
    review_queue = build_review_queue(df_clean)
    pending_queue = review_queue[review_queue["review_status"] == "PENDING"]
    st.write(f"Pending review candidates: {len(pending_queue)}")
    for queue_index, queue_row in pending_queue.iterrows():
        entity = queue_row["normalized_entity"]
        safe_key = f"{queue_index}_{hashlib.sha1(entity.encode('utf-8')).hexdigest()[:12]}"
        entity_rows = _entity_transactions(df_clean, entity)
        with st.expander(f"{entity} ({int(queue_row['transaction_count'])} transactions)"):
            st.write(f"Entity type: {queue_row['entity_type']}")
            st.write(f"Current category: {queue_row['current_category']}")
            with st.expander(f"Transactions ({len(entity_rows)})", expanded=False):
                columns = [column for column in ["Date", "Time", "Amount", "Description", "Final_Category", "Categorization_Method"] if column in entity_rows.columns]
                display = entity_rows[columns].copy()
                if "Date" in display.columns:
                    display["Date"] = display["Date"].dt.strftime("%Y-%m-%d")
                if "Amount" in display.columns:
                    display["Amount"] = display["Amount"].map(lambda value: f"₹{value:,.2f}")
                st.dataframe(display, use_container_width=True, hide_index=True)
            with st.form(key=f"review_form_{safe_key}"):
                selected_category = st.selectbox("Confirm category", ["Keep Unknown", *sorted(ALLOWED_CATEGORIES - {"Unknown"})], key=f"memory_category_{safe_key}")
                submitted = st.form_submit_button("Save human confirmation")
            if submitted:
                category = "Unknown" if selected_category == "Keep Unknown" else selected_category
                example = str(queue_row["representative_description"]).split(" | ")[0]
                save_memory_mapping(entity, category, entity_type=queue_row["entity_type"], example=example)
                append_human_feedback(example, queue_row["entity_type"], category, normalized_entity=entity)
                updated = df_clean.copy()
                matching = updated.apply(lambda row: normalize_entity_key(row["Description"], row.get("Merchant")) == entity, axis=1)
                updated.loc[matching, "Memory_Category"] = category
                updated.loc[matching, "Final_Category"] = category
                updated.loc[matching, "Category"] = category
                updated.loc[matching, "Categorization_Method"] = "MERCHANT_MEMORY"
                st.session_state["processed_transactions"] = updated
                st.rerun()


def _render_processed_dashboard(df_clean):
    st.success(f"✅ Processed {len(df_clean)} transactions")
    st.subheader("📊 Cleaned Data Preview")
    display_df = df_clean.copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    display_df["Amount"] = display_df["Amount"].map(lambda value: f"₹{value:,.2f}")
    st.dataframe(display_df, use_container_width=True, hide_index=False)
    st.markdown("---")
    st.subheader("📈 Summary Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("💵 Total Spending", f"₹{df_clean['Amount'].sum():,.2f}")
    col2.metric("📊 Total Transactions", len(df_clean))
    col3.metric("📉 Average Amount", f"₹{df_clean['Amount'].mean():,.2f}")
    category_summary = df_clean.groupby("Category")["Amount"].agg(["sum", "count"]).reset_index()
    category_summary.columns = ["Category", "Total Amount", "Transaction Count"]
    category_summary["Total Amount"] = category_summary["Total Amount"].map(lambda value: f"₹{value:,.2f}")
    st.subheader("🏷️ Spending by Category")
    st.dataframe(category_summary, use_container_width=True, hide_index=False)
    st.markdown("---")
    st.subheader("🧠 TWSMA Text Analytics")
    metrics = comparison_metrics(df_clean)
    metric_cols = st.columns(7)
    metric_cols[0].metric("Automatically classified", metrics["ml_transactions"])
    metric_cols[1].metric("P2P", metrics["final_p2p_count"])
    metric_cols[2].metric("Unknown", metrics["final_unknown_count"])
    metric_cols[3].metric("Baseline Unknown", metrics["baseline_unknown_count"])
    metric_cols[4].metric("Person entities", metrics["person_entities"])
    metric_cols[5].metric("Merchant/Service", metrics["merchant_entities"])
    metric_cols[6].metric("Unresolved %", f"{metrics['final_misc_rate']:.1%}")
    st.bar_chart(pd.DataFrame({"Baseline": df_clean["Baseline_Category"].value_counts(), "Final": df_clean["Final_Category"].value_counts()}).fillna(0))
    st.bar_chart(df_clean["Categorization_Method"].value_counts().rename_axis("Method").to_frame("Transactions"))
    with st.expander("🔬 NLP Processing Details"):
        from src.nlp.categorizer import get_classifier
        classifier = get_classifier()
        st.write(f"Reviewed real-data training rows: {getattr(classifier, 'training_size', 'unavailable')}")
        st.write(f"ML confidence threshold: {config.ML_CONFIDENCE_THRESHOLD:.2f}")
        st.dataframe(df_clean[["Description", "Preprocessed_Text", "Merchant", "Transaction_Entity_Type", "NLP_Category", "Category_Confidence", "Categorization_Method", "Web_Enriched"]], use_container_width=True, hide_index=True)
    with st.expander("📏 Model Evaluation"):
        evaluation = evaluate_seed_dataset(config.TRAINING_DATA_PATH)
        st.warning(evaluation["warning"])
        if "accuracy" in evaluation:
            st.write({key.title(): f"{evaluation[key]:.3f}" for key in ["accuracy", "precision", "recall", "f1"]})
    with st.expander("📋 Transaction-level Explainability"):
        columns = ["Date", "Description", "Merchant", "Transaction_Entity_Type", "Baseline_Category", "NLP_Category", "Final_Category", "Category_Confidence", "Categorization_Method", "Web_Enriched"]
        explain = df_clean[columns].copy()
        explain["Date"] = explain["Date"].dt.strftime("%Y-%m-%d")
        st.dataframe(explain, use_container_width=True, hide_index=True)
    _render_review_section(df_clean)
    st.markdown("---")
    st.subheader("🤖 ML Insights")
    df_ml = df_clean.sort_values("Date").copy()
    df_ml["Days"] = (df_ml["Date"] - df_ml["Date"].min()).dt.days
    if len(df_ml) > 5:
        model = LinearRegression().fit(df_ml[["Days"]], df_ml["Amount"])
        future_days = np.arange(df_ml["Days"].max() + 1, df_ml["Days"].max() + 8).reshape(-1, 1)
        st.metric("🔮 Predicted Spending (Next 7 Days)", f"₹{model.predict(future_days).sum():,.2f}")
    else:
        st.info("Not enough data for prediction")
    anomalies = df_clean.sort_values("Date").copy()
    if len(anomalies) > 15:
        anomalies["Amount_log"] = np.log1p(anomalies["Amount"])
        anomalies["RollingMean"] = anomalies["Amount"].rolling(window=5, min_periods=1).mean()
        anomalies["Deviation"] = anomalies["Amount"] - anomalies["RollingMean"]
        anomalies["Anomaly"] = IsolationForest(contamination=0.02, random_state=42).fit_predict(anomalies[["Amount_log", "Deviation"]].fillna(0))
        anomalies = anomalies[(anomalies["Anomaly"] == -1) & (anomalies["Amount"] > anomalies["Amount"].mean())]
        st.metric("⚠️ Unusual Transactions Detected", len(anomalies))
        if not anomalies.empty:
            st.dataframe(anomalies[["Date", "Description", "Amount"]], use_container_width=True, hide_index=True)
    else:
        st.info("Not enough data for anomaly detection")
    csv_data = df_clean.copy()
    csv_data["Date"] = csv_data["Date"].dt.strftime("%Y-%m-%d")
    st.download_button("📥 Download as CSV", data=csv_data.to_csv(index=False), file_name="expenses_cleaned.csv", mime="text/csv", use_container_width=True)


def main():
    if "pdf_processed" not in st.session_state:
        st.session_state["pdf_processed"] = False
    if "processed_transactions" not in st.session_state:
        st.session_state["processed_transactions"] = None
    st.title("💰 Smart Expense Analyzer")
    st.markdown("---")
    st.subheader("📄 Upload PDF File")
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], help="Upload your expense PDF (bank statement, GPay, Paytm, etc.)")
    process_button = st.button("🔍 Process PDF", use_container_width=True)
    if process_button:
        if uploaded_file is None:
            st.warning("⚠️ Please upload a PDF file first!")
        else:
            with st.spinner("Processing PDF..."):
                raw_text = extract_text_from_pdf(uploaded_file)
                transactions = parse_transactions(raw_text or "") if raw_text else []
                if not transactions:
                    st.error("❌ No transactions found in the PDF.")
                else:
                    df_clean = categorize_dataframe(clean_data(pd.DataFrame(transactions)))
                    df_clean["Amount"] = pd.to_numeric(df_clean["Amount"], errors="coerce")
                    df_clean = df_clean.dropna(subset=["Amount"])
                    st.session_state["processed_transactions"] = df_clean.copy()
                    st.session_state["pdf_processed"] = True
                    st.session_state["uploaded_file_name"] = uploaded_file.name
                    st.session_state["raw_pdf_text"] = raw_text
    if st.session_state["pdf_processed"] and st.session_state["processed_transactions"] is not None:
        _render_processed_dashboard(st.session_state["processed_transactions"])
    else:
        st.info("Upload a PDF and click Process PDF to begin.")


if __name__ == "__main__":
    main()
