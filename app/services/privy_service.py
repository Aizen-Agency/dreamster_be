import requests
import os
import base64
from uuid import UUID
from app.extensions.extension import db
from app.models.wallets import Wallet

class PrivyService:
    def __init__(self):
        self.app_id = os.getenv("PRIVY_APP_ID")
        self.secret_key = os.getenv("PRIVY_SECRET_KEY")
        self.base_url = "https://api.privy.io/v1"
    
    def create_wallet_address(self, email: str, user_id: str, token: str):
        print(f"Creating wallet address for {email}, {self.app_id}, {self.secret_key}")
        request_url = f"{self.base_url}/wallets_with_recovery"
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
            "Origin": "http://localhost:5000" if app.config['ENV'] == 'development' else "https://dreamster-be-364c1455b1f3.herokuapp.com"
        }
        response = requests.post(request_url, json=payload, headers=headers)
        response_data = response.json()
        
        if 'wallets' in response_data and len(response_data['wallets']) > 0:
            wallet_data = response_data['wallets'][0]
            wallet = Wallet(
                id=wallet_data['id'],
                user_id=user_id,
                address=wallet_data['address'],
                chain_type=wallet_data['chain_type'],
                recovery_user_id=response_data.get('recovery_user_id')
            )
            db.session.add(wallet)
            db.session.commit()
        
        return response_data

    def get_wallet_address(self, email):
        request_url = f"{self.base_url}/wallets/email:{email}"
        headers = {
            "privy-app-id": self.app_id,
            "Authorization": f"Basic {base64.b64encode(f'{self.app_id}:{self.secret_key}'.encode()).decode()}",
            "Content-Type": "application/json",
            "Origin": "http://localhost:5000" if app.config['ENV'] == 'development' else "https://dreamster-be-364c1455b1f3.herokuapp.com"
        }
        response = requests.get(request_url, headers=headers)
        return response.json()