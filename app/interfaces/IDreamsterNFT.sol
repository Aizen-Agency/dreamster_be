// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC1155/IERC1155.sol";

/**
 * @title IDreamsterNFT
 * @notice Interface for Dreamster's ERC1155 NFT contract
 * @dev Extends ERC1155 with additional functionality for music NFTs
 */
interface IDreamsterNFT is IERC1155 {
    /**
     * @notice Event emitted when NFT metadata is updated
     * @param tokenId The ID of the token
     * @param newUri The new URI for the token's metadata
     */
    event MetadataUpdated(uint256 indexed tokenId, string newUri);

    /**
     * @notice Event emitted when NFTs are burned through a sale
     * @param tokenId The ID of the token burned
     * @param amount The amount of tokens burned
     * @param seller The address of the seller
     */
    event TokensBurned(uint256 indexed tokenId, uint256 amount, address indexed seller);

    /**
     * @notice Initializes the NFT contract
     * @param name Name of the NFT collection
     * @param symbol Symbol of the NFT collection
     * @param uri URI for the NFT metadata
     * @param maxSupply Maximum supply of NFTs
     * @param initialSupply Initial supply of NFTs
     * @param creator Address of the collection creator
     */
    function initialize(
        string memory name,
        string memory symbol,
        string memory uri,
        uint256 maxSupply,
        uint256 initialSupply,
        address creator
    ) external;

    /**
     * @notice Sets the bonding curve contract address
     * @param bondingCurve Address of the bonding curve contract
     */
    function setBondingCurve(address bondingCurve) external;

    /**
     * @notice Sets the yield contract address
     * @param yieldContract Address of the yield contract
     */
    function setYieldContract(address yieldContract) external;

    /**
     * @notice Mints new NFTs
     * @param to Address to mint to
     * @param amount Amount of NFTs to mint
     * @return uint256 Token ID of the minted NFTs
     */
    function mint(address to, uint256 amount) external returns (uint256);

    /**
     * @notice Burns NFTs
     * @param from Address to burn from
     * @param amount Amount of NFTs to burn
     * @param tokenId Token ID to burn
     */
    function burn(address from, uint256 amount, uint256 tokenId) external;

    /**
     * @notice Gets the bonding curve contract address
     * @return address Bonding curve contract address
     */
    function bondingCurve() external view returns (address);

    /**
     * @notice Gets the yield contract address
     * @return address Yield contract address
     */
    function yieldContract() external view returns (address);

    /**
     * @notice Gets the creator address
     * @return address Creator address
     */
    function creator() external view returns (address);

    /**
     * @notice Gets the maximum supply
     * @return uint256 Maximum supply
     */
    function maxSupply() external view returns (uint256);

    /**
     * @notice Gets the current total supply of tokens
     * @param tokenId The ID of the token
     * @return uint256 The current total supply
     */
    function totalSupply(uint256 tokenId) external view returns (uint256);

    /**
     * @notice Updates the metadata URI for a token
     * @dev Only callable by the creator or admin
     * @param tokenId The ID of the token to update
     * @param newUri The new URI for the token's metadata
     */
    function updateTokenURI(uint256 tokenId, string memory newUri) external;
}