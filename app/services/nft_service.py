from web3 import Web3
from web3.middleware import geth_poa_middleware
import os
import json
from app.models.track import Track
from app.services.arweave_service import ArweaveService
from app.extensions.extension import db
import logging
from app.datastore.DreamsterFactory import DreamsterFactory
from app.datastore.DreamsterNFT import DreamsterNFT
from app.datastore.DreamsterBondingCurve import DreamsterBondingCurve
from app.datastore.DreamsterYield import DreamsterYield

class NFTService:
    def __init__(self):
        # Initialize Web3 connection
        self.rpc_url = os.getenv("WEB3_PROVIDER_URI")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Load contract ABIs
        self.factory_abi = self._load_abi(DreamsterFactory)
        self.nft_abi = self._load_abi(DreamsterNFT)
        self.bonding_curve_abi = self._load_abi(DreamsterBondingCurve)
        self.yield_abi = self._load_abi(DreamsterYield)
        
        self.factory_address = os.getenv("DREAMSTER_FACTORY_ADDRESS")
        
        self.dreamster_private_key = os.getenv("DREAMSTER_PRIVATE_KEY")
        self.dreamster_address = os.getenv("DREAMSTER_ADDRESS")
        
        # Service dependencies
        self.arweave_service = ArweaveService()
        
        # Default addresses for revenue distribution
        self.dreamster_treasury = os.getenv("DREAMSTER_TREASURY_ADDRESS")
        self.platform_address = os.getenv("DREAMSTER_PLATFORM_ADDRESS")
        
        # Logging
        self.logger = logging.getLogger(__name__)

    def _load_abi(self, filename):
        try:
            with open(f'app/datastore/{filename}', 'r') as file:
                return json.load(file)
        except Exception as e:
            self.logger.error(f"Error loading ABI from {filename}: {str(e)}")
            raise

    def create_nft_collection(self, track_id):
        """
        Create a new NFT collection for a track
        
        Args:
            track_id: UUID of the track
            
        Returns:
            dict: Contract addresses and transaction hash
        """
        try:
            track = Track.query.get(track_id)
            if not track:
                raise ValueError(f"Track with ID {track_id} not found")
            
            metadata = {
                "name": track.title,
                "description": track.description,
                "artist": track.artist.username,
                "image": track.cover_art_url,
                "audio": track.audio_url,
                "attributes": [
                    {"trait_type": "Genre", "value": track.genre},
                    {"trait_type": "Duration", "value": str(track.duration)},
                    {"trait_type": "Release Date", "value": track.created_at.strftime("%Y-%m-%d")}
                ]
            }
            
            # Upload metadata to Arweave
            arweave_tx_id = self.arweave_service.upload_metadata(metadata)
            arweave_uri = self.arweave_service.get_arweave_url(arweave_tx_id)
            
            # Prepare NFT collection config
            nft_config = {
                "name": f"{track.title} by {track.artist.username}",
                "symbol": f"DREAM-{track.id.hex()[:4].upper()}",
                "arweaveUri": arweave_uri,
                "maxSupply": 100,  
                "launchDate": 0 
            }
            
            # Initialize factory contract
            factory_contract = self.w3.eth.contract(
                address=self.factory_address,
                abi=self.factory_abi
            )
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.dreamster_address)
            
            # Estimate gas for the transaction
            gas_estimate = factory_contract.functions.createNFTCollection(nft_config).estimate_gas({
                'from': self.dreamster_address,
                'nonce': nonce
            })
            
            # Build the transaction
            tx = factory_contract.functions.createNFTCollection(nft_config).build_transaction({
                'from': self.dreamster_address,
                'gas': int(gas_estimate * 1.2),  # Add 20% buffer
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.dreamster_private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Parse event logs to get contract addresses
            event_logs = factory_contract.events.NFTCollectionCreated().process_receipt(tx_receipt)
            if not event_logs:
                raise Exception("Failed to get NFT collection creation event logs")
            
            event_data = event_logs[0]['args']
            nft_address = event_data['nftContract']
            bonding_curve_address = event_data['bondingCurveContract']
            yield_address = event_data['yieldContract']
            
            # Update track in database
            track.nft_contract_address = nft_address
            track.bonding_curve_address = bonding_curve_address
            track.yield_contract_address = yield_address
            track.nft_status = "deployed"
            track.arweave_uri = arweave_uri
            db.session.commit()
            
            # Configure revenue addresses for the bonding curve
            self._configure_bonding_curve(bonding_curve_address, track.artist.wallet_address)
            
            return {
                'nft_address': nft_address,
                'bonding_curve_address': bonding_curve_address,
                'yield_address': yield_address,
                'tx_hash': tx_hash.hex()
            }
            
        except Exception as e:
            self.logger.error(f"Error creating NFT collection: {str(e)}")
            return None

    def _configure_bonding_curve(self, bonding_curve_address, artist_address):
        try:
            # Initialize bonding curve contract
            bonding_curve = self.w3.eth.contract(
                address=bonding_curve_address,
                abi=self.bonding_curve_abi
            )
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.dreamster_address)
            
            # Estimate gas for the transaction
            gas_estimate = bonding_curve.functions.setRevenueAddresses(
                artist_address,
                self.dreamster_address,
                self.dreamster_treasury
            ).estimate_gas({
                'from': self.dreamster_address,
                'nonce': nonce
            })
            
            # Build the transaction
            tx = bonding_curve.functions.setRevenueAddresses(
                artist_address,
                self.dreamster_address,
                self.dreamster_treasury
            ).build_transaction({
                'from': self.dreamster_address,
                'gas': int(gas_estimate * 1.2),  # Add 20% buffer
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.dreamster_private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring bonding curve: {str(e)}")
            return False

    def get_nft_price(self, track_id, amount=1):
        """
        Get the current price to buy NFTs for a track
        
        Args:
            track_id: UUID of the track
            amount: Number of NFTs to buy
            
        Returns:
            float: Price in ETH
        """
        try:
            track = Track.query.get(track_id)
            if not track or not track.bonding_curve_address:
                raise ValueError(f"Track with ID {track_id} not found or NFT not deployed")
            
            # Initialize bonding curve contract
            bonding_curve = self.w3.eth.contract(
                address=track.bonding_curve_address,
                abi=self.bonding_curve_abi
            )
            
            # Get price
            price_wei = bonding_curve.functions.getBuyPrice(amount).call()
            price_eth = self.w3.from_wei(price_wei, 'ether')
            
            return price_eth
            
        except Exception as e:
            self.logger.error(f"Error getting NFT price: {str(e)}")
            return None

    def get_nft_sell_price(self, track_id, amount=1):
        """
        Get the current price to sell NFTs for a track
        
        Args:
            track_id: UUID of the track
            amount: Number of NFTs to sell
            
        Returns:
            float: Price in ETH
        """
        try:
            track = Track.query.get(track_id)
            if not track or not track.bonding_curve_address:
                raise ValueError(f"Track with ID {track_id} not found or NFT not deployed")
            
            # Initialize bonding curve contract
            bonding_curve = self.w3.eth.contract(
                address=track.bonding_curve_address,
                abi=self.bonding_curve_abi
            )
            
            # Get price
            price_wei = bonding_curve.functions.getSellPrice(amount).call()
            price_eth = self.w3.from_wei(price_wei, 'ether')
            
            return price_eth
            
        except Exception as e:
            self.logger.error(f"Error getting NFT sell price: {str(e)}")
            return None

    def get_nft_supply(self, track_id):
        """
        Get the current supply of NFTs for a track
        
        Args:
            track_id: UUID of the track
            
        Returns:
            dict: Current supply and max supply
        """
        try:
            track = Track.query.get(track_id)
            if not track or not track.nft_contract_address or not track.bonding_curve_address:
                raise ValueError(f"Track with ID {track_id} not found or NFT not deployed")
            
            # Initialize contracts
            nft_contract = self.w3.eth.contract(
                address=track.nft_contract_address,
                abi=self.nft_abi
            )
            
            bonding_curve = self.w3.eth.contract(
                address=track.bonding_curve_address,
                abi=self.bonding_curve_abi
            )
            
            # Get current and max supply
            current_supply = nft_contract.functions.totalSupply(1).call()
            max_supply = bonding_curve.functions.getMaxSupply().call()
            
            return {
                'current_supply': current_supply,
                'max_supply': max_supply
            }
            
        except Exception as e:
            self.logger.error(f"Error getting NFT supply: {str(e)}")
            return None

    def get_nft_holders(self, track_id):
        """
        Get all holders of NFTs for a track
        
        Args:
            track_id: UUID of the track
            
        Returns:
            list: Addresses of NFT holders
        """
        try:
            track = Track.query.get(track_id)
            if not track or not track.nft_contract_address:
                raise ValueError(f"Track with ID {track_id} not found or NFT not deployed")
            
            # Initialize NFT contract
            nft_contract = self.w3.eth.contract(
                address=track.nft_contract_address,
                abi=self.nft_abi
            )
            
            # Get holders
            holders = nft_contract.functions.getHolders(1).call()
            
            return holders
            
        except Exception as e:
            self.logger.error(f"Error getting NFT holders: {str(e)}")
            return None

    def get_user_nft_balance(self, track_id, user_address):
        """
        Get the NFT balance of a user for a track
        
        Args:
            track_id: UUID of the track
            user_address: Ethereum address of the user
            
        Returns:
            int: Number of NFTs owned
        """
        try:
            track = Track.query.get(track_id)
            if not track or not track.nft_contract_address:
                raise ValueError(f"Track with ID {track_id} not found or NFT not deployed")
            
            # Initialize NFT contract
            nft_contract = self.w3.eth.contract(
                address=track.nft_contract_address,
                abi=self.nft_abi
            )
            
            # Get balance
            balance = nft_contract.functions.balanceOf(user_address, 1).call()
            
            return balance
            
        except Exception as e:
            self.logger.error(f"Error getting user NFT balance: {str(e)}")
            return None

    def get_claimable_yield(self, track_id, user_address):
        """
        Get the claimable yield for a user for a track
        
        Args:
            track_id: UUID of the track
            user_address: Ethereum address of the user
            
        Returns:
            float: Claimable yield in ETH
        """
        try:
            track = Track.query.get(track_id)
            if not track or not track.yield_contract_address:
                raise ValueError(f"Track with ID {track_id} not found or NFT not deployed")
            
            # Initialize yield contract
            yield_contract = self.w3.eth.contract(
                address=track.yield_contract_address,
                abi=self.yield_abi
            )
            
            # Get claimable yield
            yield_wei = yield_contract.functions.getClaimableYield(user_address).call()
            yield_eth = self.w3.from_wei(yield_wei, 'ether')
            
            return yield_eth
            
        except Exception as e:
            self.logger.error(f"Error getting claimable yield: {str(e)}")
            return None

    def claim_yield(self, track_id, user_address):
        """
        Claim yield for a user for a track
        
        Args:
            track_id: UUID of the track
            user_address: Ethereum address of the user
            
        Returns:
            dict: Transaction hash and amount claimed
        """
        try:
            track = Track.query.get(track_id)
            if not track or not track.yield_contract_address:
                raise ValueError(f"Track with ID {track_id} not found or NFT not deployed")
            
            # Initialize yield contract
            yield_contract = self.w3.eth.contract(
                address=track.yield_contract_address,
                abi=self.yield_abi
            )
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.dreamster_address)
            
            # Estimate gas for the transaction
            gas_estimate = yield_contract.functions.claimYield(user_address).estimate_gas({
                'from': self.dreamster_address,
                'nonce': nonce
            })
            
            # Build the transaction
            tx = yield_contract.functions.claimYield(user_address).build_transaction({
                'from': self.dreamster_address,
                'gas': int(gas_estimate * 1.2),  # Add 20% buffer
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.dreamster_private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Parse event logs to get claimed amount
            event_logs = yield_contract.events.YieldClaimed().process_receipt(tx_receipt)
            if not event_logs:
                raise Exception("Failed to get yield claimed event logs")
            
            event_data = event_logs[0]['args']
            amount_wei = event_data['amount']
            amount_eth = self.w3.from_wei(amount_wei, 'ether')
            
            return {
                'tx_hash': tx_hash.hex(),
                'amount': amount_eth
            }
            
        except Exception as e:
            self.logger.error(f"Error claiming yield: {str(e)}")
            return None

    def distribute_yield(self, track_id, amount_eth=None):
        """
        Distribute yield for a track
        
        Args:
            track_id: UUID of the track
            amount_eth: Amount of ETH to distribute (optional)
            
        Returns:
            dict: Transaction hash and amount distributed
        """
        try:
            track = Track.query.get(track_id)
            if not track or not track.yield_contract_address:
                raise ValueError(f"Track with ID {track_id} not found or NFT not deployed")
            
            # Initialize yield contract
            yield_contract = self.w3.eth.contract(
                address=track.yield_contract_address,
                abi=self.yield_abi
            )
            
            # Determine amount to distribute
            if amount_eth is None:
                # Get contract balance
                contract_balance_wei = self.w3.eth.get_balance(track.yield_contract_address)
                amount_wei = contract_balance_wei
            else:
                amount_wei = self.w3.to_wei(amount_eth, 'ether')
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.dreamster_address)
            
            # Estimate gas for the transaction
            gas_estimate = yield_contract.functions.distributeYield().estimate_gas({
                'from': self.dreamster_address,
                'value': amount_wei,
                'nonce': nonce
            })
            
            # Build the transaction
            tx = yield_contract.functions.distributeYield().build_transaction({
                'from': self.dreamster_address,
                'value': amount_wei,
                'gas': int(gas_estimate * 1.2),  # Add 20% buffer
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.dreamster_private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Parse event logs to get distributed amount
            event_logs = yield_contract.events.YieldReceived().process_receipt(tx_receipt)
            if not event_logs:
                raise Exception("Failed to get yield received event logs")
            
            event_data = event_logs[0]['args']
            distributed_wei = event_data['amount']
            distributed_eth = self.w3.from_wei(distributed_wei, 'ether')
            
            return {
                'tx_hash': tx_hash.hex(),
                'amount': distributed_eth
            }
            
        except Exception as e:
            self.logger.error(f"Error distributing yield: {str(e)}")
            return None

    def get_track_nft_info(self, track_id):
        """
        Get comprehensive NFT information for a track
        
        Args:
            track_id: UUID of the track
            
        Returns:
            dict: NFT information
        """
        try:
            track = Track.query.get(track_id)
            if not track:
                raise ValueError(f"Track with ID {track_id} not found")
            
            if not track.nft_contract_address:
                return {
                    'deployed': False,
                    'track_id': str(track_id),
                    'track_title': track.title,
                    'artist': track.artist.username
                }
            
            # Get supply info
            supply_info = self.get_nft_supply(track_id)
            
            # Get current price
            current_price = self.get_nft_price(track_id)
            
            # Initialize contracts
            nft_contract = self.w3.eth.contract(
                address=track.nft_contract_address,
                abi=self.nft_abi
            )
            
            bonding_curve = self.w3.eth.contract(
                address=track.bonding_curve_address,
                abi=self.bonding_curve_abi
            )
            
            yield_contract = self.w3.eth.contract(
                address=track.yield_contract_address,
                abi=self.yield_abi
            )
            
            # Get additional info
            initial_price = bonding_curve.functions.getInitialPrice().call()
            launch_date = bonding_curve.functions.getLaunchDate().call()
            total_distributed = yield_contract.functions.getTotalDistributed().call()
            current_epoch = yield_contract.functions.getCurrentEpoch().call()
            
            return {
                'deployed': True,
                'track_id': str(track_id),
                'track_title': track.title,
                'artist': track.artist.username,
                'nft_address': track.nft_contract_address,
                'bonding_curve_address': track.bonding_curve_address,
                'yield_address': track.yield_contract_address,
                'arweave_uri': track.arweave_uri,
                'current_supply': supply_info['current_supply'],
                'max_supply': supply_info['max_supply'],
                'current_price_eth': current_price,
                'initial_price_wei': initial_price,
                'launch_date': launch_date,
                'total_yield_distributed_wei': total_distributed,
                'current_epoch': current_epoch
            }
            
        except Exception as e:
            self.logger.error(f"Error getting track NFT info: {str(e)}")
            return None
