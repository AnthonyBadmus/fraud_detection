from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, time
from typing import List, Optional

app = FastAPI()

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
    transaction_time_weekday: datetime

class FraudRule:
    def __init__(self, rule_id, description, action, condition):
        self.rule_id = rule_id
        self.description = description
        self.action = action  # Either "review" or "reject"
        self.condition = condition

    def evaluate(self, transaction):
        if self.condition(transaction):
            return self.action, self.description
        return None, None

class FraudDetector:
    def __init__(self):
        self.rules = self.create_rules()

    def create_rules(self):
        return [
            # Transaction Amount Rule
            FraudRule(
                rule_id="R1",
                description="High transaction amount",
                action="review",
                condition=lambda t: t.amount > 500_000
            ),
            # Payment Channel Rule
            FraudRule(
                rule_id="R2",
                description="Web channel transaction",
                action="reject",
                condition=lambda t: t.payment_channel == "web"
            ),
            # Device Type Rule/p
            FraudRule(
                rule_id="R3",
                description="Transaction from iOS device",
                action="review",
                condition=lambda t: t.device_type == "iOS"
            ),
            # Transaction Time Rule
            FraudRule(
                rule_id="R4",
                description="Late-night transaction",
                action="review",
                condition=lambda t: time(23, 0) <= t.transaction_time.time() or t.transaction_time.time() <= time(5, 0)
            ),
            # Geographic Location Rule
            FraudRule(
                rule_id="R5",
                description="Transaction from Lagos, Nigeria",
                action="reject",
                condition=lambda t: t.location == "Lagos, Nigeria"
            ),
            # Transaction Frequency Rule
            FraudRule(
                rule_id="R6",
                description="Frequent high-value transactions",
                action="review",
                condition=lambda t: t.high_value_tx_count > 5
            ),
            # Account Status Rule
            FraudRule(
                rule_id="R7",
                description="Account created recently",
                action="review",
                condition=lambda t: (datetime.now() - t.account_creation_date).days <= 30
            ),
            # Identity Verification Rule
            FraudRule(
                rule_id="R8",
                description="Unverified account",
                action="reject",
                condition=lambda t: not t.is_verified
            ),
            # Time Off Period Rule
            FraudRule(
                rule_id="R9",
                description="Transaction during restricted period",
                action="reject",
                condition=lambda t: t.transaction_time.weekday() >= 6  #Sunday
            )
        ]

    def check_fraud(self, transaction: Transaction):
        actions = []
        for rule in self.rules:
            action, description = rule.evaluate(transaction)
            if action:
                actions.append({"action": action, "reason": description})
        return actions

# Initialize fraud detector
fraud_detector = FraudDetector()

@app.post("/check_transaction/")
async def check_transaction(transaction: Transaction):
    fraud_results = fraud_detector.check_fraud(transaction)
    if not fraud_results:
        return {"transaction_id": transaction.id, "status": "clear", "details": "No fraud detected"}
    return {"transaction_id": transaction.id, "status": "flagged", "details": fraud_results}



# JSON payload you could send as a POST request to the /check_transaction/
# {
#     "id": "TXN002",
#     "amount": 10000,
#     "payment_channel": "web",
#     "device_type": "Android",
#     "transaction_time": "2024-11-12T23:30:00",
#     "location": "Ibadan, Nigeria",
#     "high_value_tx_count": 1,
#     "account_creation_date": "2024-11-17T12:00:00",
#     "is_verified": true,
#     "transaction_time": "2024-11-17T12:00:00"
# }


#Response
# {
#     "transaction_id": "TXN001",
#     "status": "flagged",
#     "details": [
#         {
#             "action": "review",
#             "reason": "High transaction amount"
#         },
#         {
#             "action": "reject",
#             "reason": "Web channel transaction"
#         },
#         {
#             "action": "reject",
#             "reason": "Transaction from Lagos, Nigeria"
#         },
#         {
#             "action": "review",
#             "reason": "Frequent high-value transactions"
#         },
#         {
#             "action": "reject",
#             "reason": "Unverified account"
#         }
#     ]
# }
