import os
import json
import uuid
from web3 import Web3
from eth_account import Account
from app.models.track import Track
from app.models.user import User

# Connect to blockchain network (example using Infura for Ethereum)
INFURA_URL = os.environ.get('INFURA_URL', 'https://polygon-mumbai.infura.io/v3/YOUR_INFURA_KEY')
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Load contract ABI and address
with open('app/contracts/MusicNFT.json') as f:
    contract_json = json.load(f)
    
CONTRACT_ABI = contract_json['abi']
CONTRACT_ADDRESS = os.environ.get('NFT_CONTRACT_ADDRESS')

# Initialize contract
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# Private key for minting (should be securely stored, e.g., in AWS KMS)
MINTER_PRIVATE_KEY = os.environ.get('MINTER_PRIVATE_KEY')
minter_account = Account.from_key(MINTER_PRIVATE_KEY)

def mint_nft(user_id, track_id):
    """Mint an NFT for a purchased track"""
    try:
        # Get track and user data
        track = Track.query.get(uuid.UUID(track_id) if isinstance(track_id, str) else track_id)
        user = User.query.get(uuid.UUID(user_id) if isinstance(user_id, str) else user_id)
        
        if not track or not user:
            raise ValueError("Track or user not found")
        
        # Get user's wallet address
        recipient_address = user.wallet_address
        if not recipient_address:
            raise ValueError("User has no wallet address")
        
        # Prepare metadata for the NFT
        metadata = {
            "name": track.title,
            "description": track.description or f"NFT for {track.title}",
            "image": track.s3_url.replace("audio", "artwork"),  # Assuming artwork URL follows a pattern
            "attributes": [
                {"trait_type": "Artist", "value": track.artist.username},
                {"trait_type": "Genre", "value": track.genre.name if track.genre else "Unknown"},
                {"trait_type": "Exclusive", "value": str(track.exclusive)}
            ]
        }
        
        # Upload metadata to IPFS (simplified - in production use a proper IPFS service)
        metadata_uri = f"ipfs://QmExample/{track_id}.json"  # Placeholder
        
        # Prepare transaction for minting
        nonce = web3.eth.get_transaction_count(minter_account.address)
        
        # Estimate gas
        gas_estimate = contract.functions.mintNFT(
            recipient_address,
            metadata_uri
        ).estimate_gas({'from': minter_account.address})
        
        # Build transaction
        txn = contract.functions.mintNFT(
            recipient_address,
            metadata_uri
        ).build_transaction({
            'chainId': 80001,  # Mumbai testnet
            'gas': gas_estimate,
            'gasPrice': web3.to_wei('50', 'gwei'),
            'nonce': nonce,
        })
        
        # Sign transaction
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=MINTER_PRIVATE_KEY)
        
        # Send transaction
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for transaction receipt
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get token ID from event logs
        token_id = None
        for log in tx_receipt['logs']:
            try:
                parsed_log = contract.events.Transfer().process_log(log)
                token_id = parsed_log['args']['tokenId']
                break
            except:
                continue
        
        if not token_id:
            raise ValueError("Failed to retrieve token ID from transaction")
        
        return token_id
    
    except Exception as e:
        # Log error and return None
        print(f"Error minting NFT: {str(e)}")
        return None 