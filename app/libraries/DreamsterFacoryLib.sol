// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../DreamsterBondingCurve.sol";
import "../DreamsterYield.sol";
import "../interfaces/IDreamsterFactory.sol";
import "../DreamsterNFT.sol";

library DreamsterFactoryLib {
    function deployNFTContract(IDreamsterFactory.NFTCollectionConfig calldata config, address creator)
        internal
        returns (address nftContract)
    {
        DreamsterNFT nft = new DreamsterNFT();
        nft.initialize(
            config.name,
            config.symbol,
            config.arweaveUri,
            config.maxSupply,
            0, // No initial supply - bonding curve controls minting
            creator
        );
        return address(nft);
    }

    /**
     * @dev Deploys a new bonding curve contract
     * @param nftContract Address of the NFT contract
     * @param maxSupply Maximum supply of NFTs
     * @param launchDate Launch date for the collection
     * @param creator Address of the collection creator
     * @return address Address of the deployed bonding curve contract
     */
    function deployBondingCurveContract(
        address nftContract,
        uint256 maxSupply,
        uint256 launchDate,
        address creator
    ) internal returns (address) {
        // Deploy bonding curve contract
        DreamsterBondingCurve bondingCurve = new DreamsterBondingCurve();
        address bondingCurveAddress = address(bondingCurve);
        
        // Set bonding curve address in NFT contract
        DreamsterNFT(nftContract).setBondingCurve(bondingCurveAddress);

        // Initialize bonding curve
        bondingCurve.initialize(
            nftContract,
            maxSupply,
            1 ether, // initial price
            launchDate
        );

        // Transfer ownership to creator
        bondingCurve.transferOwnership(creator);
        
        return bondingCurveAddress;
    }

    /**
     * @dev Deploys a new yield distribution contract
     * @param nftContract Address of the NFT contract
     * @param bondingCurveAddress Address of the bonding curve contract
     * @return address Address of the deployed yield contract
     */
    function deployYieldContract(address nftContract, address payable bondingCurveAddress)
        internal
        returns (address)
    {
        DreamsterYield yieldContract = new DreamsterYield();
        yieldContract.initialize(nftContract, bondingCurveAddress);
        
        // Set yield contract address in NFT contract
        DreamsterNFT(nftContract).setYieldContract(address(yieldContract));

        return address(yieldContract);
    }
}