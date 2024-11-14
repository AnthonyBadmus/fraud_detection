import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from typing import List
from pydantic import BaseModel
import io

st.set_page_config(layout="wide")

# Path to the default CSV file
sample_transaction_data = "sample_transactions.csv"  

# Define the Transaction class
class Transaction(BaseModel):
    id: str
    amount: float
    payment_channel: str
    device_type: str
    transaction_time: datetime
    location: str
    high_value_tx_count: int
    account_creation_date: datetime
    is_verified: bool
    transaction_time_weekday: str

# Define Fraud Rule for evaluation
class FraudRule:
    def __init__(self, rule_id, description, action, condition):
        self.rule_id = rule_id
        self.description = description
        self.action = action
        self.condition = condition

    def evaluate(self, transaction: Transaction):
        if self.condition(transaction):
            return self.action, self.description
        return None, None

# Initialize fraud detection rules
def create_fraud_rules():
    return [
        FraudRule("R1", "High transaction amount", "review", lambda t: t.amount > 500_000),
        FraudRule("R2", "Web channel transaction", "reject", lambda t: t.payment_channel == "web"),
        FraudRule("R3", "Transaction from iOS device", "review", lambda t: t.device_type == "iOS"),
        FraudRule("R4", "Late-night transaction", "review", lambda t: t.transaction_time.hour < 5 or t.transaction_time.hour >= 23),
        FraudRule("R5", "Transaction from Lagos, Nigeria", "reject", lambda t: t.location == "Lagos, Nigeria"),
        FraudRule("R6", "Frequent high-value transactions", "review", lambda t: t.high_value_tx_count > 5),
        FraudRule("R7", "Account created recently", "review", lambda t: (datetime.now() - t.account_creation_date).days <= 30),
        FraudRule("R8", "Unverified account", "reject", lambda t: not t.is_verified),
        FraudRule("R9", "Transaction on weekend", "reject", lambda t: t.transaction_time_weekday in ["Saturday", "Sunday"]),
    ]

# Load data from the default CSV
def load_default_data():
    data = pd.read_csv(sample_transaction_data)
    data["transaction_time"] = pd.to_datetime(data["transaction_time"])
    data["account_creation_date"] = pd.to_datetime(data["account_creation_date"])
    return data

# Load data from uploaded file (CSV or XLSX)
def load_uploaded_data(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        data = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file)
    else:
        st.error("Unsupported file type. Please upload a CSV or XLSX file.")
        return pd.DataFrame()
    
    data["transaction_time"] = pd.to_datetime(data["transaction_time"])
    data["account_creation_date"] = pd.to_datetime(data["account_creation_date"])
    return data

# Convert data to Transaction objects
def convert_to_transactions(data):
    transactions = [
        Transaction(**row) for row in data.to_dict(orient="records")
    ]
    return transactions

# Evaluate transactions for fraud
def evaluate_transactions(transactions: List[Transaction], rules: List[FraudRule]):
    results = []
    for tx in transactions:
        tx_results = []
        for rule in rules:
            action, description = rule.evaluate(tx)
            if action:
                tx_results.append({"action": action, "reason": description})
        status = "flagged" if tx_results else "clear"
        results.append({
            "id": tx.id,
            "status": status,
            "details": tx_results,
            "weekday": tx.transaction_time_weekday,
            "location": tx.location  # Added location info
        })
    return results

# Streamlit app layout
st.title("Fraud Detection Dashboard")

# File upload
uploaded_file = st.file_uploader("Upload transaction CSV or XLSX file", type=["csv", "xlsx"])
if uploaded_file:
    data = load_uploaded_data(uploaded_file)
else:
    st.write("Loading data from default CSV...")
    data = load_default_data()

# Convert to Transaction objects
transactions = convert_to_transactions(data)

# Initialize fraud detection rules
fraud_rules = create_fraud_rules()

# Evaluate transactions
fraud_results = evaluate_transactions(transactions, fraud_rules)

# Convert results to DataFrame
results_df = pd.DataFrame(fraud_results)

# Scorecards
total_transactions = len(results_df)
total_flagged = len(results_df[results_df["status"] == "flagged"])
total_cleared = len(results_df[results_df["status"] == "clear"])
total_review = len([detail for details in results_df["details"] for detail in details if detail["action"] == "review"])
total_reject = len([detail for details in results_df["details"] for detail in details if detail["action"] == "reject"])

# Display scorecards
st.subheader("Summary")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Transactions", total_transactions)
col2.metric("Total Flagged", total_flagged)
col3.metric("Total Cleared", total_cleared)
col4.metric("Total Reviews", total_review)
col5.metric("Total Rejections", total_reject)

# Visualization: Reasons for Flagged Transactions
st.subheader("Reasons for Flagged Transactions")
reasons = []
for result in results_df["details"]:
    for reason in result:
        reasons.append(reason["reason"])

reasons_df = pd.DataFrame(reasons, columns=['reason'])
reason_counts = reasons_df['reason'].value_counts().reset_index()
reason_counts.columns = ['reason', 'count']

reason_chart = alt.Chart(reason_counts).mark_bar().encode(
    x=alt.X('reason', title='Fraud Reason', sort='-y'),
    y=alt.Y('count', title='Count'),
    color='reason'
)
st.altair_chart(reason_chart, use_container_width=True)

# Visualization: Reasons for Rejected Transactions
st.subheader("Reasons for Rejected Transactions")
reasons_rejected = []
for result in results_df[results_df["status"] == "flagged"]["details"]:
    for reason in result:
        if reason["action"] == "reject":
            reasons_rejected.append(reason["reason"])

reasons_rejected_df = pd.DataFrame(reasons_rejected, columns=['reason'])
reason_rejected_counts = reasons_rejected_df['reason'].value_counts().reset_index()
reason_rejected_counts.columns = ['reason', 'count']

reason_rejected_chart = alt.Chart(reason_rejected_counts).mark_bar().encode(
    x=alt.X('reason', title='Fraud Reason', sort='-y'),
    y=alt.Y('count', title='Count'),
    color='reason'
)
st.altair_chart(reason_rejected_chart, use_container_width=True)

# Visualization: Flagged Transactions by Location (Pie Chart) and Rejected Transactions by Location (Pie Chart)
st.subheader("Transaction Analysis by Location")

# Create two columns for side-by-side display
col1, col2 = st.columns(2)

# Flagged Transactions by Location
with col1:
    st.subheader("Flagged Transactions by Location")
    location_counts = results_df[results_df["status"] == "flagged"]['location'].value_counts().reset_index()
    location_counts.columns = ['location', 'count']

    location_chart = alt.Chart(location_counts).mark_arc().encode(
        theta="count:Q",
        color="location:N",
        tooltip=["location:N", "count:Q"]
    )
    st.altair_chart(location_chart, use_container_width=True)

# Rejected Transactions by Location
with col2:
    st.subheader("Rejected Transactions by Location")
    rejected_location_counts = results_df[results_df["status"] == "flagged"][results_df["details"].apply(lambda x: any(item['action'] == "reject" for item in x))]['location'].value_counts().reset_index()
    rejected_location_counts.columns = ['location', 'count']

    rejected_location_chart = alt.Chart(rejected_location_counts).mark_arc().encode(
        theta="count:Q",
        color="location:N",
        tooltip=["location:N", "count:Q"]
    )
    st.altair_chart(rejected_location_chart, use_container_width=True)

# Add table with detailed evaluations
st.subheader("Fraud Evaluation Table")
evaluation_table = pd.DataFrame({
    "Transaction ID": results_df["id"],
    "Status": results_df["status"],
    "Evaluation Details": results_df["details"].apply(lambda x: ', '.join([f"{item['action']} ({item['reason']})" for item in x]) if x else 'None')
})
st.dataframe(evaluation_table)






# import streamlit as st
# import pandas as pd
# from datetime import datetime
# from pydantic import BaseModel, validator
# from typing import List, Dict
# import altair as alt

# # Transaction and FraudRule classes, and the fraud detection logic
# class Transaction(BaseModel):
#     id: str
#     amount: float
#     payment_channel: str
#     device_type: str
#     transaction_time: datetime
#     location: str
#     high_value_tx_count: int
#     account_creation_date: datetime
#     is_verified: bool
#     transaction_time_weekday: str

#     @validator('transaction_time_weekday', pre=True, always=True)
#     def set_transaction_time_weekday(cls, v, values):
#         return values['transaction_time'].strftime('%A')

# class FraudRule:
#     def __init__(self, rule_id, description, action, condition):
#         self.rule_id = rule_id
#         self.description = description
#         self.action = action
#         self.condition = condition

#     def evaluate(self, transaction):
#         if self.condition(transaction):
#             return self.action, self.description
#         return None, None

# class FraudDetector:
#     def __init__(self):
#         self.rules = self.create_rules()

#     def create_rules(self):
#         return [
#             FraudRule("R1", "High transaction amount", "review", lambda t: t.amount > 500_000),
#             FraudRule("R2", "Web channel transaction", "reject", lambda t: t.payment_channel == "web"),
#             FraudRule("R3", "Transaction from iOS device", "review", lambda t: t.device_type == "iOS"),
#             FraudRule("R4", "Late-night transaction", "review", lambda t: t.transaction_time.hour >= 23 or t.transaction_time.hour <= 5),
#             FraudRule("R5", "Transaction from Lagos, Nigeria", "reject", lambda t: t.location == "Lagos, Nigeria"),
#             FraudRule("R6", "Frequent high-value transactions", "review", lambda t: t.high_value_tx_count > 5),
#             FraudRule("R7", "Account created recently", "review", lambda t: (datetime.now() - t.account_creation_date).days <= 30),
#             FraudRule("R8", "Unverified account", "reject", lambda t: not t.is_verified),
#             FraudRule("R9", "Transaction during weekend", "reject", lambda t: t.transaction_time.weekday() >= 5)
#         ]

#     def check_fraud(self, transaction: Transaction):
#         actions = []
#         for rule in self.rules:
#             action, description = rule.evaluate(transaction)
#             if action:
#                 actions.append({"action": action, "reason": description})
#         return actions

# # Initialize fraud detector
# fraud_detector = FraudDetector()

# # Streamlit app code
# st.title("Fraud Detection System")
# st.header("Upload Transaction Data")

# # File uploader for CSV file
# uploaded_file = st.file_uploader("Upload a CSV file containing transaction data", type=["csv"])

# # Google Sheets integration (optional)
# google_sheet_url = st.text_input("Alternatively, enter Google Sheets URL (shared as CSV)")

# # Load data from CSV or Google Sheets
# data = None
# if uploaded_file is not None:
#     data = pd.read_csv(uploaded_file)
# elif google_sheet_url:
#     data = pd.read_csv(google_sheet_url)

# # Process data if it’s available
# if data is not None:
#     try:
#         transactions = []
#         results = []
        
#         for index, row in data.iterrows():
#             transaction = Transaction(
#                 id=str(row['id']),
#                 amount=float(row['amount']),
#                 payment_channel=row['payment_channel'],
#                 device_type=row['device_type'],
#                 transaction_time=pd.to_datetime(row['transaction_time']),
#                 location=row['location'],
#                 high_value_tx_count=int(row['high_value_tx_count']),
#                 account_creation_date=pd.to_datetime(row['account_creation_date']),
#                 is_verified=bool(row['is_verified']),
#                 transaction_time_weekday=''  # This will be set by validator
#             )
#             fraud_results = fraud_detector.check_fraud(transaction)
#             result = {
#                 "transaction_id": transaction.id,
#                 "status": "flagged" if fraud_results else "clear",
#                 "weekday": transaction.transaction_time_weekday,
#                 "details": fraud_results
#             }
#             results.append(result)
#             transactions.append(transaction.dict())
        
#         results_df = pd.DataFrame(results)
        
#         # Display the results in a table
#         st.subheader("Fraud Detection Results")
#         st.write(results_df)
        
#         # Chart: Status of Transactions (Flagged vs Clear)
#         status_counts = results_df['status'].value_counts().reset_index()
#         status_counts.columns = ['status', 'count']
        
#         st.subheader("Transaction Status Overview")
#         status_chart = alt.Chart(status_counts).mark_bar().encode(
#             x=alt.X('status', title='Transaction Status'),
#             y=alt.Y('count', title='Count'),
#             color='status'
#         )
#         st.altair_chart(status_chart, use_container_width=True)
        
#         # Chart: Reasons for Flagged Transactions
#         reasons = [reason['reason'] for result in results_df['details'] if result for reason in result]
#         reasons_df = pd.DataFrame(reasons, columns=['reason'])
#         reason_counts = reasons_df['reason'].value_counts().reset_index()
#         reason_counts.columns = ['reason', 'count']
        
#         st.subheader("Reasons for Flagged Transactions")
#         reason_chart = alt.Chart(reason_counts).mark_bar().encode(
#             x=alt.X('reason', title='Fraud Reason', sort='-y'),
#             y=alt.Y('count', title='Count'),
#             color='reason'
#         )
#         st.altair_chart(reason_chart, use_container_width=True)

#         # Chart: Weekday Analysis
#         weekday_counts = results_df.groupby(['weekday', 'status']).size().reset_index(name='count')
#         st.subheader("Transaction Status by Weekday")
#         weekday_chart = alt.Chart(weekday_counts).mark_bar().encode(
#             x=alt.X('weekday', sort=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], title='Day of Week'),
#             y=alt.Y('count', title='Count'),
#             color='status'
#         )
#         st.altair_chart(weekday_chart, use_container_width=True)
        
#     except Exception as e:
#         st.error(f"An error occurred: {e}")
# else:
#     st.info("Please upload a CSV file or provide a valid Google Sheets URL.")
