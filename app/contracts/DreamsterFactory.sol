// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "../interfaces/IDreamsterFactory.sol";
import "../libraries/DreamsterFactoryLib.sol";
import "./DreamsterNFT.sol";
import "./DreamsterBondingCurve.sol";
import "./DreamsterYield.sol";

/**
 * @title DreamsterFactory
 * @notice Main factory contract for creating and managing Dreamster NFT collections
 * @dev Implements NFT creation, bonding curve deployment, and yield contract management
 */
contract DreamsterFactory is IDreamsterFactory, Ownable, Pausable, ReentrancyGuard {
    using DreamsterFactoryLib for *;

    // Custom errors
    error EmptyName();
    error EmptySymbol();
    error EmptyArweaveUri();
    error InvalidMaxSupply();
    error InvalidLaunchDate();
    error NotFactoryCollection();

    // Mapping from NFT address to its associated contracts
    mapping(address => address) private _bondingCurves;
    mapping(address => address) private _yieldContracts;
    
    // Mapping from creator to their NFT collections
    mapping(address => address[]) private _creatorCollections;
    
    // Set of valid NFT collections created by this factory
    mapping(address => bool) private _isFactoryCollection;

    /**
     * @dev Constructor sets the contract owner
     */
    constructor() {
        _transferOwnership(msg.sender);
    }

    /**
     * @inheritdoc IDreamsterFactory
     */
    function createNFTCollection(NFTCollectionConfig calldata config)
        external
        whenNotPaused
        nonReentrant
        returns (
            address nftAddress,
            address bondingCurveAddress,
            address yieldAddress
        )
    {
        if (bytes(config.name).length == 0) revert EmptyName();
        if (bytes(config.symbol).length == 0) revert EmptySymbol();
        if (bytes(config.arweaveUri).length == 0) revert EmptyArweaveUri();
        if (config.maxSupply == 0) revert InvalidMaxSupply();
        if (config.launchDate != 0 && config.launchDate < block.timestamp)
            revert InvalidLaunchDate();

        // Deploy NFT contract
        nftAddress = DreamsterFactoryLib.deployNFTContract(config, msg.sender);

        // Deploy Bonding Curve contract
        bondingCurveAddress = DreamsterFactoryLib.deployBondingCurveContract(
            nftAddress,
            config.maxSupply,
            config.launchDate,
            msg.sender
        );

        // Deploy Yield Distribution contract
        yieldAddress = DreamsterFactoryLib.deployYieldContract(nftAddress, payable(bondingCurveAddress));

        // Store contract associations
        _bondingCurves[nftAddress] = bondingCurveAddress;
        _yieldContracts[nftAddress] = yieldAddress;
        _isFactoryCollection[nftAddress] = true;
        _creatorCollections[msg.sender].push(nftAddress);

        emit NFTCollectionCreated(
            msg.sender,
            nftAddress,
            bondingCurveAddress,
            yieldAddress
        );

        return (nftAddress, bondingCurveAddress, yieldAddress);
    }

    /**
     * @inheritdoc IDreamsterFactory
     */
    function getCreatorCollections(address creator)
        external
        view
        returns (address[] memory)
    {
        return _creatorCollections[creator];
    }

    /**
     * @inheritdoc IDreamsterFactory
     */
    function getCollectionContracts(address nftAddress)
        external
        view
        returns (address bondingCurve, address yieldContract)
    {
        if (!_isFactoryCollection[nftAddress]) revert NotFactoryCollection();
        return (_bondingCurves[nftAddress], _yieldContracts[nftAddress]);
    }

    /**
     * @inheritdoc IDreamsterFactory
     */
    function isFactoryCollection(address nftAddress) external view returns (bool) {
        return _isFactoryCollection[nftAddress];
    }

    /**
     * @notice Pauses the factory
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpauses the factory
     */
    function unpause() external onlyOwner {
        _unpause();
    }
}