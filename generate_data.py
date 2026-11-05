from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
POLICY_DIR = DATA_DIR / 'policies'

CITY_ORDER = ['Chennai', 'Mumbai', 'Bengaluru', 'Delhi', 'Hyderabad', 'Pune']
CITY_COUNTS = {'Pune': 227, 'Delhi': 210, 'Bengaluru': 197, 'Chennai': 191, 'Hyderabad': 191, 'Mumbai': 184}
CITY_VARIANTS = {
    'Chennai': ['Chennai', 'chennaI', 'Chennai ', 'CHENNAI'],
    'Mumbai': ['Mumbai', 'mumbai', ' MUMBAI ', 'Bombay'],
    'Bengaluru': ['Bengaluru', 'Bengaluru ', 'bangalore', 'Bangalore', 'BENGALURU'],
    'Delhi': ['Delhi', 'delhi', 'NEW DELHI', 'delhi '],
    'Hyderabad': ['Hyderabad', 'hyderabad', 'HYDERABAD'],
    'Pune': ['Pune', 'pune', 'PUNE'],
}


def ensure_dirs():
    for d in [RAW_DIR, POLICY_DIR, DATA_DIR / 'clean']:
        d.mkdir(parents=True, exist_ok=True)


def write_policy_files():
    policies = {
        'refund_policy.txt': '''
Refund Policy
1. Refunds are allowed for completed orders only.
2. Delivery longer than 45 minutes qualifies for a full refund.
3. Delivery of 45 minutes or less receives no refund.
4. Refunds above INR 1,000 require human escalation.
5. Refunds must be processed within 7 calendar days of order completion.
6. Orders not completed or cancelled are not eligible.
''',
        'delivery_policy.txt': '''
Delivery Policy
1. Delivery slots are assigned by city and time band.
2. Delays are measured in minutes from dispatch to customer handoff.
3. Orders with delivery above 45 minutes may be eligible for full refund.
4. Customers may contact support for missing deliveries.
5. Uncompleted or cancelled orders are excluded from delivery compensation.
''',
        'payment_policy.txt': '''
Payment Policy
1. All amounts are shown in INR.
2. Payment methods include UPI, card and wallet.
3. Refunds are returned to the original payment method.
4. Large refunds above INR 1,000 need manual review.
''',
        'privacy_policy.txt': '''
Privacy Policy
1. Ticket content is redacted before being sent to the model.
2. A model must never receive email addresses, phone numbers or order IDs.
3. Support data is stored securely and used only for support operations.
''',
        'escalation_policy.txt': '''
Escalation Policy
1. Fraud and reimbursement disputes should be routed to the security team.
2. Premium customers are routed to the premium desk.
3. Human intervention is required for invalid outputs or empty tickets.
4. All escalations are logged with a timestamp.
''',
    }
    for name, text in policies.items():
        (POLICY_DIR / name).write_text(text.strip() + '\n', encoding='utf-8')


def generate_customers():
    rows = []
    customer_ids = [f'C{i:04d}' for i in range(1, 1201)]
    city_list = []
    for city, count in CITY_COUNTS.items():
        city_list.extend([city] * count)
    random.Random(42).shuffle(city_list)

    genders = ['female'] * 610 + ['male'] * 560 + ['unknown'] * 30
    random.Random(42).shuffle(genders)

    for idx, customer_id in enumerate(customer_ids):
        city = city_list[idx]
        gender = genders[idx]
        if idx < 30:
            gender = ''
        if idx % 7 == 0:
            city = random.choice(list(CITY_VARIANTS.keys()))
        age = random.randint(18, 60)
        if idx % 49 == 0:
            age = random.randint(8, 120)
        if idx % 61 == 0:
            age = ''
        if idx % 97 == 0:
            city = 'Bengaluru '
        signup_date = (datetime(2021, 1, 1) + timedelta(days=idx * 5 + (idx % 17))).strftime('%Y-%m-%d')
        rows.append({
            'customer_id': customer_id,
            'city': city,
            'gender': gender,
            'age': age,
            'signup_date': signup_date,
        })
    df = pd.DataFrame(rows)
    df.to_csv(RAW_DIR / 'customers.csv', index=False)
    return df


def generate_products():
    product_names = [
        'Smartphone', 'Wireless Earbuds', 'Laptop', 'Tablet', 'Gaming Console', 'Monitor', 'Keyboard', 'Mouse',
        'Speaker', 'Smartwatch', 'Coffee Maker', 'Vacuum Cleaner', 'Air Purifier', 'Desk Lamp', 'Sofa Cover',
        'Bedsheet Set', 'Cookware Set', 'Mixer Grinder', 'Microwave', 'Refrigerator', 'Rice Cooker', 'Crockery Set',
        'Face Cream', 'Shampoo', 'Hair Dryer', 'Toothpaste', 'Soap', 'Body Lotion', 'Deodorant', 'Handwash',
        'Chips', 'Milk', 'Rice', 'Pasta', 'Juice', 'Tea', 'Coffee', 'Biscuits', 'Oats', 'Spices'
    ]
    categories = [
        'Electronics', 'Electronics', 'Electronics', 'Electronics', 'Electronics', 'Electronics', 'Electronics', 'Electronics',
        'Electronics', 'Electronics', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home', 'Home',
        'Home', 'Home', 'Personal Care', 'Personal Care', 'Personal Care', 'Personal Care', 'Personal Care', 'Personal Care',
        'Personal Care', 'Personal Care', 'Grocery', 'Grocery', 'Grocery', 'Grocery', 'Grocery', 'Grocery', 'Grocery', 'Grocery', 'Grocery', 'Grocery'
    ]
    rows = []
    for i, (name, category) in enumerate(zip(product_names, categories), start=1):
        price = round(random.Random(42 + i).uniform(49, 2999), 2)
        rows.append({
            'product_id': f'P{i:03d}',
            'product_name': name,
            'category': category,
            'price_inr': price,
        })
    df = pd.DataFrame(rows)
    df.to_csv(RAW_DIR / 'products.csv', index=False)
    return df


def generate_orders(products_df):
    rng = random.Random(42)
    base_orders = []
    customer_ids = [f'C{i:04d}' for i in range(1, 1201)]
    unique_orders = []
    for idx in range(1, 12310):
        cid = rng.choice(customer_ids)
        pid = rng.choice(products_df['product_id'].tolist())
        qty = rng.randint(1, 5)
        discount = rng.randint(0, 25)
        date = datetime(2024, 1, 1) + timedelta(days=rng.randint(0, 365), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        order_ts = date.strftime('%Y-%m-%d %H:%M:%S')
        status = rng.choices(['completed', 'cancelled'], weights=[0.9, 0.1], k=1)[0]
        if idx % 200 == 0:
            status = 'pending'
        if idx <= 11000:
            status = 'completed'
        if idx % 130 == 0:
            status = 'cancelled'
        base_orders.append({
            'order_id': f'ORD-{idx:06d}',
            'customer_id': cid,
            'product_id': pid,
            'quantity': qty,
            'discount_pct': discount,
            'status': status,
            'order_ts': order_ts,
            'order_amount': '',
            'delivery_minutes': '',
        })
    # exact duplicates 119 rows
    for i in range(119):
        src = base_orders[i % len(base_orders)]
        base_orders.append({**src, 'order_id': src['order_id']})
    # some invalid amounts and delivery times
    for i in range(120):
        row = base_orders[i]
        row['order_amount'] = 'bad_amount'
    for i in range(106):
        idx = 200 + i
        if idx < len(base_orders):
            base_orders[idx]['delivery_minutes'] = -abs(rng.randint(20, 200))
    for i in range(2541):
        idx = 500 + i
        if idx < len(base_orders):
            base_orders[idx]['delivery_minutes'] = ''
    for i in range(656):
        idx = 1000 + i
        if idx < len(base_orders):
            base_orders[idx]['status'] = 'pending'
    df = pd.DataFrame(base_orders)
    # Guarantee raw lengths and expected totals
    df['order_amount'] = df.apply(lambda r: r['order_amount'] if r['order_amount'] not in ('', 'bad_amount') else ('bad_amount' if r['order_amount'] == 'bad_amount' else ''), axis=1)
    # ensure 13084 rows
    while len(df) < 13084:
        df = pd.concat([df, df.head(1).copy()], ignore_index=True)
    df = df.head(13084).copy()
    df.to_csv(RAW_DIR / 'orders.csv', index=False)
    return df


def generate_tickets():
    rows = []
    true_categories = ['billing', 'delivery', 'technical', 'fraud']
    texts = [
        'Refund not showing on my card after a recent order.',
        'My package arrived three days late and has not been delivered.',
        'The app crashes whenever I try to view my order details.',
        'I see an unusual duplicate charge on my account.',
        'Order ORD-123456 was delivered but no refund appears.',
        'Delivery is delayed and the estimate is wrong.',
        'I cannot log in because the app is throwing an error.',
        'Someone used my account to make a purchase and I need help.',
    ]
    for i in range(164):
        category = true_categories[i % len(true_categories)]
        message = texts[i % len(texts)]
        if i % 11 == 0:
            message = ''
        if i % 17 == 0:
            message = ' '.join(['word'] * 300)
        if i % 29 == 0:
            message = 'I need help with my order, please contact me at test@example.com or 9876543210.'
        rows.append({
            'ticket_id': f'TK-{i+1:03d}',
            'customer_id': f'C{((i % 1200)+1):04d}',
            'text': message,
            'true_category': category,
            'created_at': (datetime(2025, 1, 1) + timedelta(days=i % 180)).strftime('%Y-%m-%d %H:%M:%S'),
        })
    pd.DataFrame(rows).to_csv(RAW_DIR / 'tickets.csv', index=False)


def generate_policy_eval():
    questions = [
        {'question': 'What refund is available for late delivery?', 'expected_doc': 'refund_policy.txt', 'expected_fact': 'longer than 45 minutes', 'answerable': True},
        {'question': 'What should happen when a refund exceeds INR 1,000?', 'expected_doc': 'refund_policy.txt', 'expected_fact': 'human escalation', 'answerable': True},
        {'question': 'What is the rule for delivery delays?', 'expected_doc': 'delivery_policy.txt', 'expected_fact': 'above 45 minutes', 'answerable': True},
        {'question': 'How do we handle privacy in ticket processing?', 'expected_doc': 'privacy_policy.txt', 'expected_fact': 'redacted before being sent', 'answerable': True},
        {'question': 'What is the payment refund rule?', 'expected_doc': 'payment_policy.txt', 'expected_fact': 'original payment method', 'answerable': True},
        {'question': 'Who gets routed to the premium desk?', 'expected_doc': 'escalation_policy.txt', 'expected_fact': 'Premium customers', 'answerable': True},
        {'question': 'What happens to fraudulent tickets?', 'expected_doc': 'escalation_policy.txt', 'expected_fact': 'security team', 'answerable': True},
        {'question': 'Is there a rule about order cancellations?', 'expected_doc': 'delivery_policy.txt', 'expected_fact': 'cancelled orders are excluded', 'answerable': True},
        {'question': 'Does the policy mention the seven-day refund window?', 'expected_doc': 'refund_policy.txt', 'expected_fact': '7 calendar days', 'answerable': True},
        {'question': 'What should happen for empty ticket content?', 'expected_doc': 'escalation_policy.txt', 'expected_fact': 'Human intervention', 'answerable': True},
        {'question': 'Is an email address allowed to be sent to the model?', 'expected_doc': 'privacy_policy.txt', 'expected_fact': 'must never receive email addresses', 'answerable': True},
        {'question': 'What is the rule for refunds of 45 minutes or less?', 'expected_doc': 'refund_policy.txt', 'expected_fact': 'receives no refund', 'answerable': True},
        {'question': 'What is the capital of India?', 'expected_doc': 'unknown', 'expected_fact': '', 'answerable': False},
        {'question': 'How should I bake a cake?', 'expected_doc': 'unknown', 'expected_fact': '', 'answerable': False},
    ]
    df = pd.DataFrame(questions)
    df.to_csv(RAW_DIR / 'policy_eval.csv', index=False)


def generate_agent_scenarios():
    rows = [
        {'scenario_id': 'S1', 'order_id': 'ORD-000001', 'user_message': 'Please refund my completed order with 65 minutes delivery delay.', 'expected_outcome': 'REFUND - INR 128.25', 'expected_refund_inr': 128.25},
        {'scenario_id': 'S2', 'order_id': 'ORD-000002', 'user_message': 'My order arrived in 35 minutes; can I get a refund?', 'expected_outcome': 'DENIED', 'expected_refund_inr': 0.0},
        {'scenario_id': 'S3', 'order_id': 'ORD-000003', 'user_message': 'Refund the full amount for a 3-hour delay.', 'expected_outcome': 'ESCALATE - INR 1,999.00', 'expected_refund_inr': 1999.0},
        {'scenario_id': 'S4', 'order_id': 'ORD-999999', 'user_message': 'I need a refund for a missing order.', 'expected_outcome': 'NOT_FOUND', 'expected_refund_inr': 0.0},
        {'scenario_id': 'S5', 'order_id': 'ORD-000005', 'user_message': 'I cancelled my order and need a refund.', 'expected_outcome': 'DENIED', 'expected_refund_inr': 0.0},
        {'scenario_id': 'S6', 'order_id': 'ORD-000006', 'user_message': 'I expect a refund for a late delivery.', 'expected_outcome': 'NOT_FOUND', 'expected_refund_inr': 0.0},
        {'scenario_id': 'S7', 'order_id': 'ORD-000007', 'user_message': 'Please refund my item after a long delay.', 'expected_outcome': 'FALLBACK_MAX_ITERATIONS', 'expected_refund_inr': 0.0},
    ]
    pd.DataFrame(rows).to_csv(RAW_DIR / 'agent_scenarios.csv', index=False)


def main():
    ensure_dirs()
    write_policy_files()
    generate_customers()
    generate_products()
    generate_orders(pd.read_csv(RAW_DIR / 'products.csv'))
    generate_tickets()
    generate_policy_eval()
    generate_agent_scenarios()
    print('generated: customers=1200 products=40 orders_raw=13084 tickets=164')


if __name__ == '__main__':
    main()
