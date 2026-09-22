"""
GPay/Paytm Style Test Data Generator
Generates sample PDF files with multi-line transactions (GPay/Paytm format)
"""

from datetime import datetime, timedelta
import random


def generate_gpay_style_transactions():
    """Generate sample GPay/Paytm style transaction data"""
    
    merchants = {
        'Expense': [
            'Swiggy Food Delivery',
            'Zomato Restaurant',
            'Uber Ride',
            'OLA Cabs',
            'Amazon Marketplace',
            'Flipkart Online',
            'Netflix Subscription',
            'Spotify Premium',
            'Electricity Bill',
            'Water Supply',
            'Internet Provider',
            'Mobile Recharge',
            'Book My Show Tickets',
            'Local Grocery Store',
            'Pizza Hut Delivery'
        ],
        'Income': [
            'Salary Deposit',
            'Freelance Project Payment',
            'Refund from Amazon',
            'Cashback Reward'
        ]
    }
    
    transactions = []
    start_date = datetime(2025, 10, 1)
    
    # Generate 30 transactions (mix of expenses and income, but mostly expenses)
    for i in range(30):
        date = start_date + timedelta(days=i)
        txn_type = random.choice(['Expense'] * 8 + ['Income'])  # 80% expenses, 20% income
        merchant = random.choice(merchants[txn_type])
        amount = random.uniform(50, 5000)
        
        transactions.append({
            'date': date.strftime('%d %b, %Y'),  # GPay format: "02 Oct, 2025"
            'merchant': merchant,
            'amount': f'{amount:.2f}',
            'type': txn_type
        })
    
    return transactions\n\n\ndef create_gpay_style_text_file():\n    \"\"\"Create a sample text file with GPay/Paytm style transaction data\"\"\"\n    \n    transactions = generate_gpay_style_transactions()\n    \n    content = \"\"\"\nGoogle Pay Statement - October 2025\n====================================\n\nAccount: user@example.com\nStatement Period: 01-Oct-2025 to 30-Oct-2025\n\n\"\"\"\n    \n    for txn in transactions:\n        if txn['type'] == 'Expense':\n            content += f\"\"\"\n{txn['date']}\nPaid to: {txn['merchant']}\nAmount: ₹{txn['amount']}\nStatus: Completed\n\"\"\"\n        else:\n            content += f\"\"\"\n{txn['date']}\nReceived from: {txn['merchant']}\nAmount: ₹{txn['amount']}\nStatus: Completed\n\"\"\"\n    \n    content += \"\"\"\n\n====================================\nStatement Summary\nTotal Transactions: \"\"\" + str(len(transactions)) + \"\"\"\nDate Range: 01-Oct-2025 to 30-Oct-2025\nEND OF STATEMENT\n\"\"\"\n    \n    # Save to file\n    with open('sample_gpay_statement.txt', 'w') as f:\n        f.write(content)\n    \n    print(\"✅ GPay style text file created: sample_gpay_statement.txt\")\n    print(\"\\nSample Transactions:\")\n    for i, txn in enumerate(transactions[:5], 1):\n        print(f\"{i}. {txn['date']} | {txn['type']:8} | {txn['merchant']:30} | ₹{txn['amount']}\")\n    print(f\"... and {len(transactions) - 5} more transactions\\n\")\n\n\ndef create_gpay_style_pdf():\n    \"\"\"Create a sample PDF with GPay/Paytm style transaction data\"\"\"\n    \n    try:\n        from reportlab.lib.pagesizes import A4\n        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle\n        from reportlab.lib.units import inch\n        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak\n        from reportlab.lib import colors\n        \n        transactions = generate_gpay_style_transactions()\n        \n        pdf_filename = 'sample_gpay_statement.pdf'\n        doc = SimpleDocTemplate(pdf_filename, pagesize=A4, topMargin=0.5*inch)\n        \n        elements = []\n        styles = getSampleStyleSheet()\n        \n        # Custom styles\n        title_style = ParagraphStyle(\n            'CustomTitle',\n            parent=styles['Heading1'],\n            fontSize=14,\n            textColor=colors.HexColor('#1f77b4'),\n            spaceAfter=6\n        )\n        \n        txn_date_style = ParagraphStyle(\n            'TxnDate',\n            parent=styles['Normal'],\n            fontSize=10,\n            textColor=colors.HexColor('#333333'),\n            spaceAfter=2,\n            fontName='Helvetica-Bold'\n        )\n        \n        txn_detail_style = ParagraphStyle(\n            'TxnDetail',\n            parent=styles['Normal'],\n            fontSize=9,\n            textColor=colors.HexColor('#666666'),\n            spaceAfter=1,\n            leftIndent=10\n        )\n        \n        # Title\n        title = Paragraph(\"Google Pay Statement - October 2025\", title_style)\n        elements.append(title)\n        elements.append(Spacer(1, 0.1*inch))\n        \n        # Header info\n        header = Paragraph(\n            \"<b>Account:</b> user@example.com<br/>\"\n            \"<b>Period:</b> 01-Oct-2025 to 30-Oct-2025\",\n            styles['Normal']\n        )\n        elements.append(header)\n        elements.append(Spacer(1, 0.2*inch))\n        \n        # Transactions\n        for i, txn in enumerate(transactions):\n            if i > 0 and i % 15 == 0:  # Page break after 15 transactions\n                elements.append(PageBreak())\n            \n            date_para = Paragraph(txn['date'], txn_date_style)\n            elements.append(date_para)\n            \n            if txn['type'] == 'Expense':\n                elements.append(Paragraph(\n                    f\"<b>Paid to:</b> {txn['merchant']}\",\n                    txn_detail_style\n                ))\n            else:\n                elements.append(Paragraph(\n                    f\"<b>Received from:</b> {txn['merchant']}\",\n                    txn_detail_style\n                ))\n            \n            elements.append(Paragraph(\n                f\"<b>Amount:</b> ₹{txn['amount']}\",\n                txn_detail_style\n            ))\n            \n            elements.append(Paragraph(\n                \"<b>Status:</b> Completed\",\n                txn_detail_style\n            ))\n            \n            elements.append(Spacer(1, 0.15*inch))\n        \n        # Summary\n        elements.append(Spacer(1, 0.2*inch))\n        summary = Paragraph(\n            f\"<b>Statement Summary</b><br/>\"\n            f\"Total Transactions: {len(transactions)}<br/>\"\n            f\"Statement Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>\"\n            f\"END OF STATEMENT\",\n            styles['Normal']\n        )\n        elements.append(summary)\n        \n        # Build PDF\n        doc.build(elements)\n        \n        print(f\"✅ GPay style PDF created: {pdf_filename}\")\n        print(f\"\\nTransaction Count: {len(transactions)}\")\n        print(\"Sample Transactions:\")\n        for i, txn in enumerate(transactions[:5], 1):\n            print(f\"{i}. {txn['date']} | {txn['type']:8} | {txn['merchant']:30} | ₹{txn['amount']}\")\n        print(f\"... and {len(transactions) - 5} more transactions\\n\")\n        \n    except ImportError:\n        print(\"⚠️ reportlab not installed. Creating text file instead...\")\n        print(\"To generate PDF: pip install reportlab\\n\")\n        create_gpay_style_text_file()\n\n\nif __name__ == \"__main__\":\n    print(\"=\" * 60)\n    print(\"GPay/Paytm Style Test Data Generator\")\n    print(\"=\" * 60 + \"\\n\")\n    \n    print(\"Generating GPay/Paytm style test data...\\n\")\n    \n    try:\n        create_gpay_style_pdf()\n    except Exception as e:\n        print(f\"Note: {e}\")\n        create_gpay_style_text_file()\n    \n    print(\"Test data generation complete!\")\n    print(\"\\nNext steps:\")\n    print(\"1. The Streamlit app is running at http://localhost:8501\")\n    print(\"2. Upload the generated PDF file\")\n    print(\"3. Click 'Process PDF' to see the multi-line transaction parsing\\n\")\n