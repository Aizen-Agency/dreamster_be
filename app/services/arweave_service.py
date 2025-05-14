import requests
import os
import json
from pybundlr import PyBundlr

class ArweaveService:
    def __init__(self):
        self.wallet_private_key = os.getenv("METAMASK_PRIVATE_KEY")
        self.bundlr = PyBundlr(
            "https://devnet.bundlr.network",
            "arweave",
            self.wallet_private_key
        )

    def upload_metadata(self, metadata):
        if isinstance(metadata, dict):
            metadata_json = json.dumps(metadata)
        else:
            metadata_json = metadata
            
        temp_file_path = "./files/temp_metadata.json"
        with open(temp_file_path, "w") as f:
            f.write(metadata_json)
            
        try:
            tx_id = self.bundlr.upload_file(temp_file_path)            
            return tx_id
        except Exception as e:
            print(f"Error uploading to Arweave: {str(e)}")
            raise
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    def get_arweave_url(self, tx_id):
        return f"https://arweave.net/{tx_id}"
    
    def fund_bundlr(self, amount):
        return self.bundlr.fund(amount)
    
    def get_balance(self):
        return self.bundlr.get_balance()
        
