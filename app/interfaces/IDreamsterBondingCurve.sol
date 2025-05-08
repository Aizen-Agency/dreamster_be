// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IDreamsterBondingCurve
 * @notice Interface for Dreamster's bonding curve contract that manages NFT pricing and trading
 */
interface IDreamsterBondingCurve {
    /**
     * @notice Event emitted when NFTs are purchased
     * @param buyer Address of the buyer
     * @param amount Amount of NFTs purchased
     * @param pricePaid Total price paid
     * @param refund Amount refunded
     */
    event Purchase(address indexed buyer, uint256 amount, uint256 pricePaid, uint256 refund);

    /**
     * @notice Event emitted when NFTs are sold
     * @param seller Address of the seller
     * @param amount Amount of NFTs sold
     * @param ethReceived Amount of ETH received
     */
    event Sale(address indexed seller, uint256 amount, uint256 ethReceived);

    /**
     * @notice Event emitted when yield is distributed
     * @param amount Amount of ETH distributed
     */
    event YieldDistributed(uint256 amount);

    /**
     * @notice Initializes the bonding curve contract
     * @param nftContract Address of the NFT contract
     * @param maxSupply Maximum supply of NFTs
     * @param initialPrice Initial price for NFTs
     * @param launchDate Launch date for the collection
     */
    function initialize(
        address nftContract,
        uint256 maxSupply,
        uint256 initialPrice,
        uint256 launchDate
    ) external;

    /**
     * @notice Sets the yield contract address
     * @param yieldContract Address of the yield contract
     */
    function setYieldContract(address yieldContract) external;

    /**
     * @notice Buys NFTs from the bonding curve
     * @param amount Amount of NFTs to buy
     * @param maxPricePerNFT Maximum price per NFT willing to pay
     * @return nftsReceived Amount of NFTs received
     * @return pricePaid Total price paid
     * @return refund Amount refunded
     */
    function buy(uint256 amount, uint256 maxPricePerNFT) 
        external 
        payable 
        returns (uint256 nftsReceived, uint256 pricePaid, uint256 refund);

    /**
     * @notice Sells NFTs back to the bonding curve
     * @param amount Amount of NFTs to sell
     * @param minEthToReceive Minimum amount of ETH to receive (95% slippage protection)
     * @return ethReceived Amount of ETH received
     */
    function sell(uint256 amount, uint256 minEthToReceive) external returns (uint256 ethReceived);

    /**
     * @notice Gets the price to buy NFTs
     * @param amount Amount of NFTs to buy
     * @return price Total price to buy the NFTs
     */
    function getBuyPrice(uint256 amount) external view returns (uint256 price);

    /**
     * @notice Gets the price to sell NFTs
     * @param amount Amount of NFTs to sell
     * @return price Total price to sell the NFTs
     */
    function getSellPrice(uint256 amount) external view returns (uint256 price);

    /**
     * @notice Gets the current max supply
     * @return maxSupply Maximum supply of NFTs
     */
    function getMaxSupply() external view returns (uint256 maxSupply);

    /**
     * @notice Gets the current supply
     * @return currentSupply Current supply of NFTs
     */
    function getCurrentSupply() external view returns (uint256 currentSupply);

    /**
     * @notice Gets the initial price
     * @return price Initial price of NFTs
     */
    function getInitialPrice() external view returns (uint256 price);

    /**
     * @notice Gets the launch date
     * @return date Launch date of the collection
     */
    function getLaunchDate() external view returns (uint256 date);
}