import requests
import os
import base64
from uuid import UUID

class PrivyService:
    def __init__(self, app_id: str, secret_key: str):
        self.app_id = app_id
        self.secret_key = secret_key
        self.base_url = "https://api.privy.io/v1"
    
    def create_wallet_address(self, email: str, first_name: str, last_name: str, user_id: str):
        print(f"Creating wallet address for {email}, {first_name}, {last_name}, {self.app_id}, {self.secret_key}")
        request_url = f"{self.base_url}/wallets_with_recovery"
        # payload = {"chain_type": "ethereum", "email": email, "first_name": first_name, "last_name": last_name}
        payload = {
    "wallets": [
        {
            "chain_type": "ethereum",
            "policy_ids": []
        },
    ],
    "primary_signer": {"subject_id": str(user_id) if isinstance(user_id, UUID) else user_id},
    "recovery_user": {"linked_accounts": [
            {
                "type": "email",
                "address": email
            }
        ]}
}

        headers = {
            "privy-app-id": self.app_id,
            "Authorization": f"Basic {base64.b64encode(f'{self.app_id}:{self.secret_key}'.encode()).decode()}",
            "Content-Type": "application/json",
            "Origin": "http://localhost:5000"
        }
        response = requests.post(request_url, json=payload, headers=headers)
        return response.json()

    def get_wallet_address(self, email):
        request_url = f"{self.base_url}/wallets/email:{email}"
        headers = {
            "privy-app-id": self.app_id,
            "Authorization": f"Basic {base64.b64encode(f'{self.app_id}:{self.secret_key}'.encode()).decode()}",
            "Content-Type": "application/json",
            "Origin": "http://localhost:5000"
        }
        response = requests.get(request_url, headers=headers)
        return response.json()