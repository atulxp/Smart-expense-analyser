"""
Test Data Generator for Smart Expense Analyzer
Generates sample PDF files with expenses for testing
Requires: reportlab (pip install reportlab)
"""

import os
from datetime import datetime, timedelta
import random


def generate_sample_transactions():
    """Generate sample transaction data"""
    
    merchants = {
        'Food': [
            'SWIGGY FOOD DELIVERY',
            'ZOMATO RESTAURANT',
            'STARBUCKS CAFE',
            'MCDONALD\'S',
            'PIZZA HUT ORDER'
        ],
        'Travel': [
            'UBER TRIP TO OFFICE',
            'OLA CABS BENGALURU',
            'INDIGO FLIGHT BOOKING',
            'PETROL PUMP FUEL',
            'AUTO RICKSHAW FARE'
        ],
        'Shopping': [
            'AMAZON.IN ELECTRONIC',
            'FLIPKART CLOTHING',
            'MALL SHOPPING CENTER',
            'H&M APPAREL',
            'NIKE STORE BANGALORE'
        ],
        'Entertainment': [
            'NETFLIX SUBSCRIPTION',
            'NETFLIX MONTHLY',
            'SPOTIFY PREMIUM',
            'INOX MOVIE TICKET',
            'BOOK MY SHOW CINEMA'
        ],
        'Utilities': [
            'ELECTRICITY BILL PAYMENT',
            'WATER SUPPLY BILL',
            'INTERNET SERVICE PROVIDER',
            'MOBILE PHONE BILL',
            'GAS CYLINDER DELIVERY'
        ],
        'Health': [
            'APOLLO PHARMACY',
            'DOCTOR CONSULTATION',
            'MAX HEALTHCARE CLINIC',
            'MEDICINE PURCHASE',
            'LAB TEST FEES'
        ]
    }
    
    transactions = []
    start_date = datetime(2024, 3, 1)
    
    for i in range(20):
        date = start_date + timedelta(days=i)
        category = random.choice(list(merchants.keys()))
        merchant = random.choice(merchants[category])
        amount = random.uniform(100, 5000)
        
        transactions.append({
            'date': date.strftime('%d-%m-%Y'),
            'merchant': merchant,
            'amount': f'{amount:.2f}'
        })
    
    return sorted(transactions, key=lambda x: x['date'])


def create_sample_text_file():
    """Create a sample text file with transaction data"""
    
    transactions = generate_sample_transactions()
    
    content = """
BANK STATEMENT - MARCH 2024
===========================

Account: XXXX XXXX XXXX 1234
Statement Period: 01-Mar-2024 to 31-Mar-2024

TRANSACTIONS:
=============

Date        | Description                      | Amount (₹)
------------|----------------------------------|----------
"""
    
    for txn in transactions:
        content += f"{txn['date']} | {txn['merchant']:<30} | {txn['amount']:>10}\n"
    
    content += """
------------|----------------------------------|----------

Summary:
Total Transactions: """ + str(len(transactions)) + """
Date Range: 01-Mar-2024 to 20-Mar-2024

END OF STATEMENT
===============
"""
    
    # Save to file
    with open('sample_bank_statement.txt', 'w') as f:
        f.write(content)
    
    print("✅ Sample text file created: sample_bank_statement.txt")
    print("\nTransaction Details:")
    for i, txn in enumerate(transactions[:5], 1):
        print(f"{i}. {txn['date']} | {txn['merchant']:30} | ₹{txn['amount']}")
    print(f"... and {len(transactions) - 5} more transactions\n")


def create_sample_pdf():
    """Create a sample PDF with transaction data (requires reportlab)"""
    
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        
        # Generate transactions
        transactions = generate_sample_transactions()
        
        # Create PDF
        pdf_filename = 'sample_bank_statement.pdf'
        doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1f77b4')
        )
        
        # Title
        title = Paragraph("BANK STATEMENT - MARCH 2024", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Account info
        account_info = Paragraph(
            "<b>Account:</b> XXXX XXXX XXXX 1234<br/>"
            "<b>Statement Period:</b> 01-Mar-2024 to 20-Mar-2024",
            styles['Normal']
        )
        elements.append(account_info)
        elements.append(Spacer(1, 0.2*inch))
        
        # Transaction table
        table_data = [['Date', 'Description', 'Amount (₹)']]
        table_data.extend([
            [txn['date'], txn['merchant'], txn['amount']]
            for txn in transactions
        ])
        
        table = Table(table_data, colWidths=[1.2*inch, 3.5*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary
        summary = Paragraph(
            f"<b>Summary:</b><br/>"
            f"Total Transactions: {len(transactions)}<br/>"
            f"Statement Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
            f"END OF STATEMENT",
            styles['Normal']
        )
        elements.append(summary)
        
        # Build PDF
        doc.build(elements)
        
        print(f"✅ Sample PDF created: {pdf_filename}")
        print(f"\nTransaction Count: {len(transactions)}")
        print("Sample Transactions:")
        for i, txn in enumerate(transactions[:5], 1):
            print(f"{i}. {txn['date']} | {txn['merchant']:30} | ₹{txn['amount']}")
        print(f"... and {len(transactions) - 5} more transactions\n")
        
    except ImportError:
        print("⚠️  reportlab not installed. Creating text file instead...")
        print("To generate PDF: pip install reportlab\n")
        create_sample_text_file()


if __name__ == "__main__":
    print("=" * 60)
    print("Smart Expense Analyzer - Test Data Generator")
    print("=" * 60 + "\n")
    
    print("Generating test data...\n")
    
    # Create PDF if reportlab is available, else text file
    try:
        create_sample_pdf()
    except Exception as e:
        print(f"Note: {e}")
        create_sample_text_file()
    
    print("Test data generation complete!")
    print("\nNext steps:")
    print("1. Run: streamlit run app.py")
    print("2. Upload the generated PDF file")
    print("3. Click 'Process PDF' to see the results\n")
