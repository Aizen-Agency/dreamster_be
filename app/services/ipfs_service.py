import requests
import os
import json

class IPFS_Service:
    def __init__(self):
        self.api_url = os.getenv("PINATA_API_BASE_URL")
        self.secret_key = os.getenv("PINATA_SECRET_KEY")
        self.bearer_token = os.getenv("PINATA_TOKEN")
        self.api_key = os.getenv("PINATA_API_KEY")

    def upload_track_metadata(self, metadata):
        print(self.bearer_token)
        requestUrl = f"{self.api_url}/pinning/pinJSONToIPFS"
        
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "pinataContent": metadata,
            "pinataOptions": {
                "cidVersion": 1
            },
            "pinataMetadata": {
                "name": f"track-metadata-{metadata.get('name', 'untitled')}",
                "keyvalues": {
                    "type": "music-nft",
                    "artist": metadata.get("artist_username", "unknown")
                }
            }
        }
        
        response = requests.post(requestUrl, json=payload, headers=headers)
        response.raise_for_status()
        
        return response.json().get("IpfsHash")

    def get_track_metadata(self, cid):
        requestUrl = f"{self.api_url}/v3/files/public?cid={cid}"
        
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        response = requests.get(requestUrl, headers=headers)
        response.raise_for_status()
        
        return response.json()

    def get_all_track_metadata(self):
        requestUrl = f"{self.api_url}/data/pinList"
        
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        response = requests.get(requestUrl, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def pin_by_hash(self, hash_to_pin, name=None):
        requestUrl = f"{self.api_url}/pinning/pinByHash"
        
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "hashToPin": hash_to_pin,
            "pinataMetadata": {
                "name": name or f"pinned-content-{hash_to_pin[:10]}"
            }
        }
        
        response = requests.post(requestUrl, json=payload, headers=headers)
        response.raise_for_status()
        
        return response.json()