// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "../interfaces/IDreamsterBondingCurve.sol";
import "../interfaces/IDreamsterNFT.sol";
import "../interfaces/IDreamsterYield.sol";

/**
 * @title DreamsterBondingCurve
 * @notice Implementation of Dreamster's bonding curve contract with square root pricing
 */
contract DreamsterBondingCurve is IDreamsterBondingCurve, Ownable, Pausable, ReentrancyGuard {
    // Constants
    uint256 private constant PRECISION = 1e18;
    uint256 private constant LIQUIDITY_SHARE = 40; // 40% of sales go to liquidity pool
    uint256 private constant YIELD_SHARE = 20; // 20% of sales go to yield
    uint256 private constant ARTIST_SHARE = 25; // 25% of sales go to artist
    uint256 private constant DREAMSTER_SHARE = 10; // 10% of sales go to dreamster
    uint256 private constant TREASURY_SHARE = 5; // 5% of sales go to treasury
    uint256 private constant K = 1e16; // k = 0.01 with 18 decimals precision
    uint256 private constant MAX_SLIPPAGE = 500; // 5% max slippage
    uint256 private constant TOKEN_ID = 1; // Token ID for NFT operations

    // State variables
    address public nftContract;
    address public yieldContract;
    address public artistAddress;
    address public dreamsterAddress;
    address public treasuryAddress;
    uint256 public initialPrice;
    uint256 public liquidityPool;
    uint256 public maxGasPrice;
    uint256 public maxSupply;
    uint256 public launchDate;
    bool private _initialized;
    bool private _active;

    // Custom errors
    error NotInitialized();
    error AlreadyInitialized();
    error InvalidNFTContract();
    error InvalidInitialPrice();
    error InvalidMaxSupply();
    error InvalidAmount();
    error NotLaunched();
    error TradingInactive();
    error GasPriceTooHigh();
    error InsufficientPayment();
    error PriceExceedsMax();
    error ExceedsMaxSupply();
    error YieldTransferFailed();
    error ArtistTransferFailed();
    error DreamsterTransferFailed();
    error TreasuryTransferFailed();
    error RefundFailed();
    error TransferFailed();
    error YieldContractAlreadySet();
    error InvalidYieldContract();
    error InvalidAddress();
    error MinimumNFTsNotMet();
    error SlippageExceeded();

    // Additional events (Purchase, Sale, and YieldDistributed defined in interface)
    event ArtistPaid(uint256 amount);
    event DreamsterPaid(uint256 amount);
    event TreasuryPaid(uint256 amount);

    // Struct to hold revenue distribution info
    struct RevenueShares {
        uint256 liquidity;
        uint256 yield;
        uint256 artist;
        uint256 dreamster;
        uint256 treasury;
    }

    // Modifiers
    modifier whenInitialized() {
        if (!_initialized) revert NotInitialized();
        _;
    }

    modifier validateGasPrice() {
        if (tx.gasprice > maxGasPrice) revert GasPriceTooHigh();
        _;
    }

    constructor() {
        _transferOwnership(msg.sender);
    }

    /**
     * @inheritdoc IDreamsterBondingCurve
     */
    function initialize(
        address _nftContract,
        uint256 _maxSupply,
        uint256 _initialPrice,
        uint256 _launchDate
    ) external override {
        if (_initialized) revert AlreadyInitialized();
        if (_nftContract == address(0)) revert InvalidNFTContract();
        if (_initialPrice == 0) revert InvalidInitialPrice();
        if (_maxSupply == 0) revert InvalidMaxSupply();

        nftContract = _nftContract;
        initialPrice = _initialPrice;
        maxSupply = _maxSupply;
        launchDate = _launchDate;
        maxGasPrice = 100 gwei;
        _initialized = true;
        _active = true;
    }

    /**
     * @notice Sets the addresses for revenue distribution
     * @param _artistAddress Address to receive artist's share
     * @param _dreamsterAddress Address to receive Dreamster's share
     * @param _treasuryAddress Address to receive treasury's share
     */
    function setRevenueAddresses(
        address _artistAddress,
        address _dreamsterAddress,
        address _treasuryAddress
    ) external onlyOwner {
        if (_artistAddress == address(0) || _dreamsterAddress == address(0) || _treasuryAddress == address(0)) 
            revert InvalidAddress();
        
        artistAddress = _artistAddress;
        dreamsterAddress = _dreamsterAddress;
        treasuryAddress = _treasuryAddress;
    }

    /**
     * @inheritdoc IDreamsterBondingCurve
     */
    function setYieldContract(address _yieldContract) external override onlyOwner {
        if (yieldContract != address(0)) revert YieldContractAlreadySet();
        if (_yieldContract == address(0)) revert InvalidYieldContract();
        yieldContract = _yieldContract;
    }

    /**
     * @notice Allows owner to withdraw ETH from the contract
     * @param amount Amount of ETH to withdraw
     */
    function withdrawETH(uint256 amount) external onlyOwner {
        if (amount > address(this).balance) revert InsufficientPayment();
        (bool success, ) = msg.sender.call{value: amount}("");
        if (!success) revert TransferFailed();
    }

    /**
     * @inheritdoc IDreamsterBondingCurve
     */
    function buy(uint256 amount, uint256 maxPricePerNFT) 
        external 
        payable
        whenInitialized
        whenNotPaused
        nonReentrant
        validateGasPrice
        returns (uint256 nftsReceived, uint256 pricePaid, uint256 refund)
    {
        if (amount == 0) revert InvalidAmount();
        if (block.timestamp < launchDate) revert NotLaunched();
        if (!_active) revert TradingInactive();

        uint256 supply = IDreamsterNFT(nftContract).totalSupply(TOKEN_ID);
        if (supply + amount > maxSupply) revert ExceedsMaxSupply();

        // Calculate actual price and NFTs receivable
        uint256 totalPrice = _calculateBuyPrice(amount);
        uint256 nftsToMint = amount;

        // If price increased, calculate max NFTs we can buy with provided ETH
        if (totalPrice > msg.value) {
            nftsToMint = 0;
            totalPrice = 0;
            
            // Try each amount from amount down to 1
            for (uint256 i = amount; i > 0; i--) {
                uint256 tryPrice = _calculateBuyPrice(i);
                if (tryPrice <= msg.value) {
                    nftsToMint = i;
                    totalPrice = tryPrice;
                    break;
                }
            }

            // Revert if we can't buy any NFTs
            if (nftsToMint == 0) revert InsufficientPayment();
        }

        // Check for slippage
        if (totalPrice / nftsToMint > maxPricePerNFT) revert PriceExceedsMax();

        // Calculate revenue shares
        RevenueShares memory shares = RevenueShares({
            liquidity: (totalPrice * LIQUIDITY_SHARE) / 100,
            yield: (totalPrice * YIELD_SHARE) / 100,
            artist: (totalPrice * ARTIST_SHARE) / 100,
            dreamster: (totalPrice * DREAMSTER_SHARE) / 100,
            treasury: (totalPrice * TREASURY_SHARE) / 100
        });

        // Update state and mint NFTs first to prevent reentrancy
        liquidityPool += shares.liquidity;
        IDreamsterNFT(nftContract).mint(msg.sender, nftsToMint);

        // Distribute shares
        _distributeShares(shares);

        // Calculate and send refund
        refund = msg.value - totalPrice;
        if (refund > 0) {
            (bool refundSuccess, ) = msg.sender.call{value: refund}("");
            if (!refundSuccess) revert RefundFailed();
        }

        emit Purchase(msg.sender, nftsToMint, totalPrice, refund);
        return (nftsToMint, totalPrice, refund);
    }

    /**
     * @inheritdoc IDreamsterBondingCurve
     */
    function sell(uint256 amount, uint256 minEthToReceive) external whenInitialized nonReentrant returns (uint256 ethReceived) {
        if (amount == 0) revert InvalidAmount();
        if (!_active) revert TradingInactive();

        // Calculate theoretical and actual sell price
        uint256 theoreticalPrice = _calculateSellPrice(amount);
        if (theoreticalPrice == 0) revert InvalidAmount();
        
        // Check both liquidity pool and actual contract balance
        if (theoreticalPrice > liquidityPool || theoreticalPrice > address(this).balance) {
            revert InsufficientPayment();
        }

        // Check for slippage - must receive at least 95% of expected value
        if (theoreticalPrice < minEthToReceive) revert SlippageExceeded();

        // Update liquidity pool first
        liquidityPool -= theoreticalPrice;

        // Burn NFTs to prevent reentrancy
        IDreamsterNFT(nftContract).burn(msg.sender, amount, TOKEN_ID);

        // Send ETH to seller
        (bool success, ) = msg.sender.call{value: theoreticalPrice}("");
        if (!success) {
            // Revert liquidity pool update if transfer fails
            liquidityPool += theoreticalPrice;
            revert TransferFailed();
        }

        emit Sale(msg.sender, amount, theoreticalPrice);
        return theoreticalPrice;
    }

    /**
     * @notice Distributes revenue shares to all parties
     * @param shares Revenue shares to distribute
     */
    function _distributeShares(RevenueShares memory shares) internal {
        if (shares.yield > 0 && yieldContract != address(0)) {
            (bool yieldSuccess, ) = yieldContract.call{value: shares.yield}("");
            if (!yieldSuccess) revert YieldTransferFailed();
            emit YieldDistributed(shares.yield);
        }

        (bool artistSuccess, ) = artistAddress.call{value: shares.artist}("");
        if (!artistSuccess) revert ArtistTransferFailed();
        emit ArtistPaid(shares.artist);

        (bool dreamsterSuccess, ) = dreamsterAddress.call{value: shares.dreamster}("");
        if (!dreamsterSuccess) revert DreamsterTransferFailed();
        emit DreamsterPaid(shares.dreamster);

        (bool treasurySuccess, ) = treasuryAddress.call{value: shares.treasury}("");
        if (!treasurySuccess) revert TreasuryTransferFailed();
        emit TreasuryPaid(shares.treasury);
    }

    /**
     * @inheritdoc IDreamsterBondingCurve
     */
    function getBuyPrice(uint256 amount) external view override returns (uint256 price) {
        if (amount == 0) return 0;
        return _calculateBuyPrice(amount);
    }

    /**
     * @inheritdoc IDreamsterBondingCurve
     */
    function getSellPrice(uint256 amount) external view override returns (uint256 price) {
        if (amount == 0) return 0;
        return _calculateSellPrice(amount);
    }

    /**
     * @inheritdoc IDreamsterBondingCurve
     */
    function getMaxSupply() external view override returns (uint256) {
        return maxSupply;
    }

    /**
     * @inheritdoc IDreamsterBondingCurve
     */
    function getCurrentSupply() external view override returns (uint256) {
        return IDreamsterNFT(nftContract).totalSupply(TOKEN_ID);
    }

    /**
     * @inheritdoc IDreamsterBondingCurve
     */
    function getInitialPrice() external view override returns (uint256) {
        return initialPrice;
    }

    /**
     * @inheritdoc IDreamsterBondingCurve
     */
    function getLaunchDate() external view override returns (uint256) {
        return launchDate;
    }

    /**
     * @notice Calculates the buy price for a given amount of NFTs using square root formula
     * @param amount Amount of NFTs to buy
     * @return Total price to buy the NFTs
     */
    function _calculateBuyPrice(uint256 amount) internal view returns (uint256) {
        uint256 supply = IDreamsterNFT(nftContract).totalSupply(TOKEN_ID);
        uint256 price = 0;
        
        // Calculate area under curve from supply to supply + amount
        for (uint256 i = 0; i < amount; i++) {
            uint256 currentSupply = supply + i;
            // p = initial_price + (k * sqrt(supply))
            price += initialPrice + ((K * _sqrt(currentSupply)) / PRECISION);
        }
        
        return price;
    }

    /**
     * @notice Calculates the sell price for a given amount of NFTs
     * @param amount Amount of NFTs to sell
     * @return Actual sell price (40% of theoretical value)
     */
    function _calculateSellPrice(uint256 amount) internal view returns (uint256) {
        uint256 supply = IDreamsterNFT(nftContract).totalSupply(TOKEN_ID);
        if (supply < amount) return 0;
        
        uint256 price = 0;
        
        // Calculate area under curve from (supply - amount) to supply
        for (uint256 i = 0; i < amount; i++) {
            uint256 currentSupply = supply - i;
            // p = initial_price + (k * sqrt(supply - 1))
            price += initialPrice + ((K * _sqrt(currentSupply - 1)) / PRECISION);
        }
        
        // Return 40% of theoretical value to match liquidity pool share
        return (price * LIQUIDITY_SHARE) / 100;
    }

    /**
     * @notice Calculates the square root of a number
     * @param x The number to calculate the square root of
     * @return y The square root of x
     */
    function _sqrt(uint256 x) internal pure returns (uint256 y) {
        if (x == 0) return 0;
        
        // Use the Babylonian method
        uint256 z = (x + 1) / 2;
        y = x;
        
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
    }
}