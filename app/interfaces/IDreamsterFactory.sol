// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IDreamsterFactory
 * @notice Interface for the Dreamster Factory contract that manages the creation and deployment
 * of NFTs, bonding curves, and yield distribution contracts
 */
interface IDreamsterFactory {
    /**
     * @notice Event emitted when a new NFT collection is created
     * @param creator Address of the creator
     * @param nftContract Address of the deployed NFT contract
     * @param bondingCurveContract Address of the deployed bonding curve contract
     * @param yieldContract Address of the deployed yield distribution contract
     */
    event NFTCollectionCreated(
        address indexed creator,
        address indexed nftContract,
        address indexed bondingCurveContract,
        address yieldContract
    );

    /**
     * @notice Struct containing the configuration for a new NFT collection
     * @param name Name of the NFT collection
     * @param symbol Symbol of the NFT collection
     * @param arweaveUri URI pointing to the NFT metadata on Arweave
     * @param maxSupply Maximum number of NFTs that can be minted
     * @param launchDate Timestamp when the NFT will be available for purchase (0 for immediate)
     */
    struct NFTCollectionConfig {
        string name;
        string symbol;
        string arweaveUri;
        uint256 maxSupply;
        uint256 launchDate;
    }

    /**
     * @notice Creates a new NFT collection with associated bonding curve and yield contracts
     * @param config Configuration for the new NFT collection
     * @return nftContract Address of the deployed NFT contract
     * @return bondingCurveAddress Address of the deployed bonding curve contract
     * @return yieldContractAddress Address of the deployed yield distribution contract
     */
    function createNFTCollection(NFTCollectionConfig calldata config)
        external
        returns (
            address nftContract,
            address bondingCurveAddress,
            address yieldContractAddress
        );

    /**
     * @notice Returns all NFT collections created by a specific creator
     * @param creator Address of the creator
     * @return collections Array of NFT collection addresses
     */
    function getCreatorCollections(address creator)
        external
        view
        returns (address[] memory collections);

    /**
     * @notice Returns the bonding curve and yield contracts associated with an NFT
     * @param nftContract Address of the NFT contract
     * @return bondingCurve Address of the bonding curve contract
     * @return yieldContract Address of the yield distribution contract
     */
    function getCollectionContracts(address nftContract)
        external
        view
        returns (address bondingCurve, address yieldContract);

    /**
     * @notice Checks if an NFT collection was created by this factory
     * @param nftContract Address of the NFT contract to check
     * @return bool True if the collection was created by this factory
     */
    function isFactoryCollection(address nftContract) external view returns (bool);
}