"""
Generates synthetic customer baselines and multi-month transaction histories
with seeded anomalies for PS06 Fraud Desk Risk Engine.
"""

import json
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CUSTOMERS = [
    {
        "customer_id": "CUST-101",
        "name": "Alexander Hayes",
        "account_type": "Standard Checking",
        "account_number": "ACC-88120491",
        "baseline_avg_amount": 78.50,
        "baseline_std_amount": 32.10,
        "baseline_max_normal": 220.00,
        "baseline_active_hours": [7, 22],
        "known_payees": ["Whole Foods Market", "Metro Transit", "ConEd Utility", "Netflix", "Amazon.com", "Starbucks", "Trader Joe's", "Shell Gas Station"],
        "common_channels": ["POS", "Mobile", "Web"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-102",
        "name": "Brianna Taylor",
        "account_type": "Student Account",
        "account_number": "ACC-44910283",
        "baseline_avg_amount": 34.20,
        "baseline_std_amount": 18.50,
        "baseline_max_normal": 110.00,
        "baseline_active_hours": [9, 23],
        "known_payees": ["Campus Dining", "University Bookstore", "Spotify", "Uber", "Target", "Venmo"],
        "common_channels": ["Mobile", "POS"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-103",
        "name": "Carlos Mendez",
        "account_type": "Small Business",
        "account_number": "ACC-33918274",
        "baseline_avg_amount": 420.00,
        "baseline_std_amount": 160.00,
        "baseline_max_normal": 1200.00,
        "baseline_active_hours": [6, 20],
        "known_payees": ["Sysco Food Services", "Office Depot", "Square Terminal Pay", "Waste Management", "Local Produce Wholesale"],
        "common_channels": ["Web", "POS", "Wire"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-104",
        "name": "Elena Rostova",
        "account_type": "Personal Checking",
        "account_number": "ACC-77291048",
        "baseline_avg_amount": 115.00,
        "baseline_std_amount": 45.00,
        "baseline_max_normal": 380.00,
        "baseline_active_hours": [8, 21],
        "known_payees": ["Kroger Grocery", "City Water Board", "Walgreens", "Nordstrom", "Delta Air Lines", "Chevron"],
        "common_channels": ["POS", "Mobile", "Web"],
        "anomaly_type": "LARGE_TRANSFER_OUTLIER"  # Outlier wire of $14,500
    },
    {
        "customer_id": "CUST-105",
        "name": "Fiona Gallagher",
        "account_type": "Premium Wealth",
        "account_number": "ACC-99281034",
        "baseline_avg_amount": 850.00,
        "baseline_std_amount": 340.00,
        "baseline_max_normal": 2800.00,
        "baseline_active_hours": [7, 22],
        "known_payees": ["Sotheby's Realty", "Equinox Fitness", "Vanguard Investments", "Ritz-Carlton Club", "Apple Store"],
        "common_channels": ["Web", "Mobile", "Wire"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-106",
        "name": "George Washington",
        "account_type": "Standard Checking",
        "account_number": "ACC-11029384",
        "baseline_avg_amount": 92.00,
        "baseline_std_amount": 41.00,
        "baseline_max_normal": 260.00,
        "baseline_active_hours": [8, 22],
        "known_payees": ["Home Depot", "Costco Wholesale", "Verizon Wireless", "Liberty Mutual", "Publix"],
        "common_channels": ["POS", "Mobile"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-107",
        "name": "Hannah Abbott",
        "account_type": "Freelance Designer",
        "account_number": "ACC-55918230",
        "baseline_avg_amount": 145.00,
        "baseline_std_amount": 65.00,
        "baseline_max_normal": 450.00,
        "baseline_active_hours": [9, 23],
        "known_payees": ["Adobe Creative Cloud", "Figma Subscription", "Apple Store", "WeWork Coworking", "Uber Eats"],
        "common_channels": ["Web", "Mobile"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-108",
        "name": "Ian Sterling",
        "account_type": "High Net Worth",
        "account_number": "ACC-66192847",
        "baseline_avg_amount": 1250.00,
        "baseline_std_amount": 480.00,
        "baseline_max_normal": 3500.00,
        "baseline_active_hours": [8, 21],
        "known_payees": ["Morgan Stanley Wealth", "BMW Financial", "Hermes Paris", "Aman Resorts", "Delta Private Jets"],
        "common_channels": ["Web", "Wire"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-109",
        "name": "Marcus Vance",
        "account_type": "Tech Contractor",
        "account_number": "ACC-22910385",
        "baseline_avg_amount": 130.00,
        "baseline_std_amount": 55.00,
        "baseline_max_normal": 420.00,
        "baseline_active_hours": [8, 22],
        "known_payees": ["AWS Cloud Services", "GitHub Enterprise", "Chipotle", "Best Buy", "Blue Bottle Coffee"],
        "common_channels": ["Web", "Mobile", "POS"],
        "anomaly_type": "NEW_PAYEE_BURST"  # 3 rapid payments to new payee "NovaDex Crypto Gateway"
    },
    {
        "customer_id": "CUST-110",
        "name": "Julia Roberts",
        "account_type": "Personal Checking",
        "account_number": "ACC-88392019",
        "baseline_avg_amount": 88.00,
        "baseline_std_amount": 38.00,
        "baseline_max_normal": 240.00,
        "baseline_active_hours": [7, 21],
        "known_payees": ["Safeway", "CVS Pharmacy", "Wegmans", "AT&T", "Shell"],
        "common_channels": ["POS", "Mobile"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-111",
        "name": "Kevin Zhang",
        "account_type": "Tech Professional",
        "account_number": "ACC-33190284",
        "baseline_avg_amount": 160.00,
        "baseline_std_amount": 70.00,
        "baseline_max_normal": 480.00,
        "baseline_active_hours": [8, 23],
        "known_payees": ["Google Fiber", "DoorDash", "Costco", "Steam Games", "Lyft"],
        "common_channels": ["Mobile", "Web", "POS"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-112",
        "name": "Aisha Patel",
        "account_type": "Senior Consultant",
        "account_number": "ACC-55291049",
        "baseline_avg_amount": 185.00,
        "baseline_std_amount": 75.00,
        "baseline_max_normal": 550.00,
        "baseline_active_hours": [8, 21],  # 8 AM to 9 PM strictly
        "known_payees": ["Marriott Hotels", "United Airlines", "Hertz Car Rental", "Starbucks", "Nordstrom"],
        "common_channels": ["Mobile", "POS", "Web"],
        "anomaly_type": "ODD_HOURS_ACTIVITY"  # Transacting at 03:15 AM and 04:20 AM for $1,800 and $2,250
    },
    {
        "customer_id": "CUST-113",
        "name": "Liam O'Connor",
        "account_type": "Small Business",
        "account_number": "ACC-77491028",
        "baseline_avg_amount": 380.00,
        "baseline_std_amount": 140.00,
        "baseline_max_normal": 950.00,
        "baseline_active_hours": [7, 19],
        "known_payees": ["Grainger Industrial", "FedEx Express", "Fastenal Co", "State Farm Business"],
        "common_channels": ["Web", "POS"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-114",
        "name": "Maya Lin",
        "account_type": "Student Account",
        "account_number": "ACC-11928374",
        "baseline_avg_amount": 28.50,
        "baseline_std_amount": 14.00,
        "baseline_max_normal": 90.00,
        "baseline_active_hours": [9, 23],
        "known_payees": ["Campus Coffee", "Chegg Textbooks", "Subway", "Amazon Prime", "Venmo"],
        "common_channels": ["Mobile", "POS"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-115",
        "name": "David Chen",
        "account_type": "Retail Store Owner",
        "account_number": "ACC-66391029",
        "baseline_avg_amount": 290.00,
        "baseline_std_amount": 110.00,
        "baseline_max_normal": 750.00,
        "baseline_active_hours": [8, 20],
        "known_payees": ["Local Goods Distribution", "Stripe Merchant Fees", "Square Terminal Pay", "Waste Pro"],
        "common_channels": ["POS", "Mobile", "Web"],
        "anomaly_type": "PATTERN_CHANNEL_BREAK"  # Sudden high-risk International Wire transfers never seen before
    },
    {
        "customer_id": "CUST-116",
        "name": "Noah Smith",
        "account_type": "Standard Checking",
        "account_number": "ACC-44102938",
        "baseline_avg_amount": 72.00,
        "baseline_std_amount": 29.00,
        "baseline_max_normal": 190.00,
        "baseline_active_hours": [7, 22],
        "known_payees": ["Walmart Supercenter", "Duke Energy", "McDonald's", "Walgreens"],
        "common_channels": ["POS", "ATM", "Mobile"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-117",
        "name": "Olivia Brown",
        "account_type": "Retail Professional",
        "account_number": "ACC-99102948",
        "baseline_avg_amount": 105.00,
        "baseline_std_amount": 42.00,
        "baseline_max_normal": 310.00,
        "baseline_active_hours": [8, 22],
        "known_payees": ["Macy's", "Target", "Sephora", "Trader Joe's", "Lyft"],
        "common_channels": ["POS", "Mobile"],
        "anomaly_type": "CLEAN"
    },
    {
        "customer_id": "CUST-118",
        "name": "Sophia Morales",
        "account_type": "Medical Specialist",
        "account_number": "ACC-33019284",
        "baseline_avg_amount": 210.00,
        "baseline_std_amount": 85.00,
        "baseline_max_normal": 650.00,
        "baseline_active_hours": [7, 21],
        "known_payees": ["MedSupply Direct", "AMA Membership", "Whole Foods", "Starbucks", "Tesla Supercharger"],
        "common_channels": ["Web", "Mobile", "POS"],
        "anomaly_type": "MULTI_VECTOR_ANOMALY"  # Large outlier ($9,850) + New Payee "Apex Offshore Settlement" + Odd Hours (02:40 AM)
    },
    {
        "customer_id": "CUST-198",
        "name": "Zoe Kensington",
        "account_type": "Recently Opened Checking",
        "account_number": "ACC-00481923",
        "baseline_avg_amount": 42.50,
        "baseline_std_amount": 12.00,
        "baseline_max_normal": 85.00,
        "baseline_active_hours": [9, 18],
        "known_payees": ["Corner Cafe", "Campus Bookstore"],
        "common_channels": ["Mobile", "POS"],
        "anomaly_type": "SPARSE_HISTORY"  # Edge case: fewer than 5 transactions (< 5 txns)
    },
    {
        "customer_id": "CUST-199",
        "name": "Lucas Vance",
        "account_type": "New Checking Account",
        "account_number": "ACC-00192834",
        "baseline_avg_amount": 0.0,
        "baseline_std_amount": 0.0,
        "baseline_max_normal": 0.0,
        "baseline_active_hours": [8, 22],
        "known_payees": [],
        "common_channels": ["Mobile"],
        "anomaly_type": "EMPTY_HISTORY"  # Edge case: zero transactions
    }
]

CATEGORIES = {
    "Whole Foods Market": "Groceries",
    "Trader Joe's": "Groceries",
    "Kroger Grocery": "Groceries",
    "Safeway": "Groceries",
    "Wegmans": "Groceries",
    "Publix": "Groceries",
    "Walmart Supercenter": "Groceries",
    "Costco": "Wholesale",
    "Costco Wholesale": "Wholesale",
    "Starbucks": "Food & Beverage",
    "Blue Bottle Coffee": "Food & Beverage",
    "Campus Coffee": "Food & Beverage",
    "Chipotle": "Food & Beverage",
    "McDonald's": "Food & Beverage",
    "Subway": "Food & Beverage",
    "DoorDash": "Food & Beverage",
    "Uber Eats": "Food & Beverage",
    "Campus Dining": "Food & Beverage",
    "ConEd Utility": "Utilities",
    "City Water Board": "Utilities",
    "Duke Energy": "Utilities",
    "AT&T": "Telecom",
    "Verizon Wireless": "Telecom",
    "Google Fiber": "Telecom",
    "Netflix": "Entertainment",
    "Spotify": "Entertainment",
    "Steam Games": "Entertainment",
    "Adobe Creative Cloud": "Software",
    "Figma Subscription": "Software",
    "AWS Cloud Services": "Cloud Services",
    "GitHub Enterprise": "Cloud Services",
    "Metro Transit": "Transportation",
    "Uber": "Transportation",
    "Lyft": "Transportation",
    "Shell Gas Station": "Gasoline",
    "Shell": "Gasoline",
    "Chevron": "Gasoline",
    "Delta Air Lines": "Travel",
    "United Airlines": "Travel",
    "Marriott Hotels": "Travel",
    "Hertz Car Rental": "Travel",
    "Ritz-Carlton Club": "Travel",
    "Aman Resorts": "Travel",
    "Delta Private Jets": "Travel",
    "Amazon.com": "Shopping",
    "Amazon Prime": "Shopping",
    "Target": "Shopping",
    "Nordstrom": "Luxury Shopping",
    "Macy's": "Shopping",
    "Sephora": "Beauty",
    "Apple Store": "Electronics",
    "Best Buy": "Electronics",
    "Home Depot": "Home Improvement",
    "CVS Pharmacy": "Pharmacy",
    "Walgreens": "Pharmacy",
    "Sysco Food Services": "Business Supplies",
    "Office Depot": "Business Supplies",
    "Square Terminal Pay": "Payment Processing",
    "Stripe Merchant Fees": "Payment Processing",
    "Waste Management": "Sanitation",
    "Waste Pro": "Sanitation",
    "Local Produce Wholesale": "Wholesale",
    "Grainger Industrial": "Industrial",
    "FedEx Express": "Shipping",
    "Fastenal Co": "Industrial",
    "State Farm Business": "Insurance",
    "Liberty Mutual": "Insurance",
    "Sotheby's Realty": "Real Estate",
    "Equinox Fitness": "Fitness",
    "Vanguard Investments": "Financial Services",
    "Morgan Stanley Wealth": "Financial Services",
    "BMW Financial": "Automotive",
    "Hermes Paris": "Luxury Goods",
    "Chegg Textbooks": "Education",
    "University Bookstore": "Education",
    "Venmo": "P2P Transfer",
    "Local Goods Distribution": "Wholesale",
    "MedSupply Direct": "Medical Supplies",
    "AMA Membership": "Professional",
    "Tesla Supercharger": "Automotive"
}

def generate_dataset():
    all_transactions = []
    customer_records = []
    
    start_date = datetime(2026, 3, 1, 9, 0, 0)
    end_date = datetime(2026, 8, 31, 21, 0, 0)
    days_span = (end_date - start_date).days
    
    txn_counter = 1000
    
    for cust in CUSTOMERS:
        c_id = cust["customer_id"]
        c_type = cust["anomaly_type"]
        
        if c_type == "EMPTY_HISTORY":
            customer_records.append({
                "customer_id": c_id,
                "name": cust["name"],
                "account_type": cust["account_type"],
                "account_number": cust["account_number"],
                "baseline_avg_amount": 0.0,
                "baseline_std_amount": 0.0,
                "baseline_max_normal": 0.0,
                "baseline_active_hours": cust["baseline_active_hours"],
                "known_payees": cust["known_payees"],
                "common_channels": cust["common_channels"],
                "total_transactions": 0,
                "total_volume": 0.0
            })
            continue

        num_txns = 2 if c_type == "SPARSE_HISTORY" else random.randint(65, 95)
        txns_cust = []
        
        # Generate baseline normal transactions across the 6-month period
        for _ in range(num_txns):
            txn_counter += 1
            txn_id = f"TXN-{txn_counter}"
            
            # Normal date and normal active hour
            random_day = random.randint(0, days_span - 3)
            h_start, h_end = cust["baseline_active_hours"]
            hour = random.randint(h_start, h_end)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            
            t_date = start_date + timedelta(days=random_day, hours=hour - 9, minutes=minute, seconds=second)
            
            # Normal amount based on Gaussian distribution
            amt = max(5.0, round(random.gauss(cust["baseline_avg_amount"], cust["baseline_std_amount"]), 2))
            # Cap at baseline max normal for routine transactions
            amt = min(amt, cust["baseline_max_normal"])
            
            payee = random.choice(cust["known_payees"])
            category = CATEGORIES.get(payee, "General")
            channel = random.choice(cust["common_channels"])
            
            description = f"Payment to {payee}"
            
            txns_cust.append({
                "transaction_id": txn_id,
                "customer_id": c_id,
                "timestamp": t_date.strftime("%Y-%m-%dT%H:%M:%S"),
                "description": description,
                "payee": payee,
                "amount": amt,
                "channel": channel,
                "category": category,
                "is_anomaly": False
            })

        # Inject seeded anomalies near the end of the history (August 2026)
        if c_type == "LARGE_TRANSFER_OUTLIER":
            # CUST-104: Elena Rostova - Large Outlier Transfer
            txn_counter += 1
            outlier_time = datetime(2026, 8, 28, 14, 22, 15)
            txns_cust.append({
                "transaction_id": f"TXN-{txn_counter}",
                "customer_id": c_id,
                "timestamp": outlier_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "description": "High-Value Outbound Wire Transfer",
                "payee": "Bavaria Real Estate Holding",
                "amount": 14500.00,
                "channel": "Wire",
                "category": "Real Estate / Wire",
                "is_anomaly": True
            })

        elif c_type == "NEW_PAYEE_BURST":
            # CUST-109: Marcus Vance - Burst to newly added payee within 6 hours
            burst_time = datetime(2026, 8, 29, 11, 15, 0)
            burst_payee = "NovaDex Crypto Settlement"
            burst_amts = [2450.00, 3200.00, 4150.00]
            for idx, b_amt in enumerate(burst_amts):
                txn_counter += 1
                b_date = burst_time + timedelta(hours=idx * 2, minutes=random.randint(5, 25))
                txns_cust.append({
                    "transaction_id": f"TXN-{txn_counter}",
                    "customer_id": c_id,
                    "timestamp": b_date.strftime("%Y-%m-%dT%H:%M:%S"),
                    "description": f"Express Crypto Settlement Tranche #{idx+1}",
                    "payee": burst_payee,
                    "amount": b_amt,
                    "channel": "Web",
                    "category": "Cryptocurrency",
                    "is_anomaly": True
                })

        elif c_type == "ODD_HOURS_ACTIVITY":
            # CUST-112: Aisha Patel - High value transactions in the dead of night (03:15 AM & 04:20 AM)
            odd_time_1 = datetime(2026, 8, 30, 3, 15, 22)
            odd_time_2 = datetime(2026, 8, 30, 4, 20, 45)
            
            txn_counter += 1
            txns_cust.append({
                "transaction_id": f"TXN-{txn_counter}",
                "customer_id": c_id,
                "timestamp": odd_time_1.strftime("%Y-%m-%dT%H:%M:%S"),
                "description": "Overnight Immediate Mobile Transfer",
                "payee": "QuickCash Remittance Services",
                "amount": 1850.00,
                "channel": "Mobile",
                "category": "Remittance",
                "is_anomaly": True
            })
            
            txn_counter += 1
            txns_cust.append({
                "transaction_id": f"TXN-{txn_counter}",
                "customer_id": c_id,
                "timestamp": odd_time_2.strftime("%Y-%m-%dT%H:%M:%S"),
                "description": "Overnight Immediate Mobile Transfer",
                "payee": "QuickCash Remittance Services",
                "amount": 2250.00,
                "channel": "Mobile",
                "category": "Remittance",
                "is_anomaly": True
            })

        elif c_type == "PATTERN_CHANNEL_BREAK":
            # CUST-115: David Chen - Unprecedented high-volume international wires
            for idx in range(3):
                txn_counter += 1
                wire_time = datetime(2026, 8, 27 + idx, 10, 30, 0)
                txns_cust.append({
                    "transaction_id": f"TXN-{txn_counter}",
                    "customer_id": c_id,
                    "timestamp": wire_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "description": f"International Commercial SWIFT Wire #{idx+1}",
                    "payee": "Global Trade Logistics HK",
                    "amount": 4800.00 + (idx * 600),
                    "channel": "Wire",
                    "category": "International Wire",
                    "is_anomaly": True
                })

        elif c_type == "MULTI_VECTOR_ANOMALY":
            # CUST-118: Sophia Morales - Outlier ($9,850) + New Payee + Odd Hours (02:40 AM)
            txn_counter += 1
            multi_time = datetime(2026, 8, 30, 2, 40, 10)
            txns_cust.append({
                "transaction_id": f"TXN-{txn_counter}",
                "customer_id": c_id,
                "timestamp": multi_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "description": "Urgent Offshore Capital Liquidation",
                "payee": "Apex Offshore Settlement Ltd",
                "amount": 9850.00,
                "channel": "Wire",
                "category": "Offshore Transfer",
                "is_anomaly": True
            })

        # Sort transactions chronologically
        txns_cust.sort(key=lambda x: x["timestamp"])
        
        # Calculate actual historical totals
        total_vol = sum(t["amount"] for t in txns_cust)
        customer_records.append({
            "customer_id": c_id,
            "name": cust["name"],
            "account_type": cust["account_type"],
            "account_number": cust["account_number"],
            "baseline_avg_amount": cust["baseline_avg_amount"],
            "baseline_std_amount": cust["baseline_std_amount"],
            "baseline_max_normal": cust["baseline_max_normal"],
            "baseline_active_hours": cust["baseline_active_hours"],
            "known_payees": cust["known_payees"],
            "common_channels": cust["common_channels"],
            "total_transactions": len(txns_cust),
            "total_volume": round(total_vol, 2),
            "provenance": "HISTORICAL_TRANSACTIONS_ONLY"
        })
        
        all_transactions.extend(txns_cust)

    # Save customers.json
    customers_file = DATA_DIR / "customers.json"
    with open(customers_file, "w", encoding="utf-8") as f:
        json.dump(customer_records, f, indent=2)
    print(f"[OK] Generated {len(customer_records)} customers in {customers_file}")

    # Save transactions.csv
    transactions_file = DATA_DIR / "transactions.csv"
    with open(transactions_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["transaction_id", "customer_id", "timestamp", "description", "payee", "amount", "channel", "category"])
        for t in all_transactions:
            writer.writerow([
                t["transaction_id"],
                t["customer_id"],
                t["timestamp"],
                t["description"],
                t["payee"],
                f"{t['amount']:.2f}",
                t["channel"],
                t.get("category", "General")
            ])
    print(f"[OK] Generated {len(all_transactions)} transactions in {transactions_file}")

    # Generate sample_test_inputs.json for easy automated evaluation and judge testing
    generate_test_fixtures(customer_records, all_transactions)

def generate_test_fixtures(customers, transactions):
    fixtures = {
        "test_cases": [
            {
                "case_id": "TEST_CASE_1_LARGE_OUTLIER",
                "customer_id": "CUST-104",
                "customer_name": "Elena Rostova",
                "description": "Customer with normal average spend of $115 triggers statistical outlier on sudden $14,500 international wire.",
                "expected_verdict": "ATTENTION_REQUIRED",
                "expected_triggered_rules": ["RULE_LARGE_TRANSFER", "RULE_PATTERN_BREAK"],
                "sample_transaction_ids": ["TXN-1318"]
            },
            {
                "case_id": "TEST_CASE_2_NEW_PAYEE_BURST",
                "customer_id": "CUST-109",
                "customer_name": "Marcus Vance",
                "description": "Customer performs rapid successive payments to previously unseen crypto payee within 48 hours.",
                "expected_verdict": "ATTENTION_REQUIRED",
                "expected_triggered_rules": ["RULE_NEW_PAYEE_BURST"],
                "sample_transaction_ids": ["TXN-1718", "TXN-1719", "TXN-1720"]
            },
            {
                "case_id": "TEST_CASE_3_ODD_HOURS",
                "customer_id": "CUST-112",
                "customer_name": "Aisha Patel",
                "description": "High-value transactions executed at 03:15 AM and 04:20 AM, outside customer's baseline active window (08:00 - 21:00).",
                "expected_verdict": "ATTENTION_REQUIRED",
                "expected_triggered_rules": ["RULE_ODD_HOURS"],
                "sample_transaction_ids": ["TXN-1941", "TXN-1942"]
            },
            {
                "case_id": "TEST_CASE_4_PATTERN_BREAK",
                "customer_id": "CUST-115",
                "customer_name": "David Chen",
                "description": "Sudden unprecedented high-value international wire payments on a domestic retail account.",
                "expected_verdict": "ATTENTION_REQUIRED",
                "expected_triggered_rules": ["RULE_PATTERN_BREAK"],
                "sample_transaction_ids": ["TXN-2165", "TXN-2166", "TXN-2167"]
            },
            {
                "case_id": "TEST_CASE_5_MULTI_VECTOR_ANOMALY",
                "customer_id": "CUST-118",
                "customer_name": "Sophia Morales",
                "description": "Outlier transfer ($9,850) + New Payee + Odd Hours (02:40 AM) triggering multiple rules simultaneously.",
                "expected_verdict": "ATTENTION_REQUIRED",
                "expected_triggered_rules": ["RULE_LARGE_TRANSFER", "RULE_ODD_HOURS", "RULE_NEW_PAYEE_BURST", "RULE_PATTERN_BREAK"]
            },
            {
                "case_id": "TEST_CASE_6_CLEAN_CUSTOMER",
                "customer_id": "CUST-101",
                "customer_name": "Alexander Hayes",
                "description": "Routine personal checking account with 80+ standard transactions adhering strictly to baseline profile.",
                "expected_verdict": "NOTHING_FLAGGED",
                "expected_triggered_rules": []
            },
            {
                "case_id": "TEST_CASE_7_EMPTY_HISTORY",
                "customer_id": "CUST-199",
                "customer_name": "Lucas Vance",
                "description": "New account with zero transactions. Explicitly returns INSUFFICIENT_EVIDENCE.",
                "expected_verdict": "INSUFFICIENT_EVIDENCE",
                "expected_triggered_rules": []
            },
            {
                "case_id": "TEST_CASE_8_SPARSE_HISTORY",
                "customer_id": "CUST-198",
                "customer_name": "Zoe Kensington",
                "description": "Recently opened account with only 2 transactions (< 5 minimum reliable history). Returns INSUFFICIENT_EVIDENCE.",
                "expected_verdict": "INSUFFICIENT_EVIDENCE",
                "expected_triggered_rules": []
            }
        ]
    }
    
    fixtures_file = DATA_DIR / "sample_test_inputs.json"
    with open(fixtures_file, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2)
    print(f"[OK] Generated test fixtures in {fixtures_file}")

if __name__ == "__main__":
    generate_dataset()
