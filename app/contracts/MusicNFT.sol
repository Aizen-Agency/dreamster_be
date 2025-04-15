// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

contract MusicNFT is ERC721URIStorage, Ownable {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenIds;
    
    // Mapping from token ID to royalty percentage (in basis points, e.g., 250 = 2.5%)
    mapping(uint256 => uint256) private _royaltyBps;
    
    // Mapping from token ID to artist address
    mapping(uint256 => address) private _artistAddresses;
    
    // Events
    event RoyaltySet(uint256 indexed tokenId, uint256 royaltyBps);
    
    constructor() ERC721("Music NFT", "MNFT") {}
    
    function mintNFT(address recipient, string memory tokenURI) 
        public 
        onlyOwner
        returns (uint256) 
    {
        _tokenIds.increment();
        uint256 newItemId = _tokenIds.current();
        
        _mint(recipient, newItemId);
        _setTokenURI(newItemId, tokenURI);
        
        return newItemId;
    }
    
    function mintNFTWithRoyalty(
        address recipient, 
        string memory tokenURI, 
        address artistAddress,
        uint256 royaltyBps
    ) 
        public 
        onlyOwner
        returns (uint256) 
    {
        require(royaltyBps <= 10000, "Royalty too high"); // Max 100%
        
        uint256 tokenId = mintNFT(recipient, tokenURI);
        
        _royaltyBps[tokenId] = royaltyBps;
        _artistAddresses[tokenId] = artistAddress;
        
        emit RoyaltySet(tokenId, royaltyBps);
        
        return tokenId;
    }
    
    // EIP-2981 royalty standard
    function royaltyInfo(uint256 tokenId, uint256 salePrice) 
        external 
        view 
        returns (address receiver, uint256 royaltyAmount) 
    {
        receiver = _artistAddresses[tokenId];
        royaltyAmount = (salePrice * _royaltyBps[tokenId]) / 10000;
    }
    
    // Get royalty percentage for a token
    function getRoyaltyBps(uint256 tokenId) external view returns (uint256) {
        return _royaltyBps[tokenId];
    }
    
    // Get artist address for a token
    function getArtistAddress(uint256 tokenId) external view returns (address) {
        return _artistAddresses[tokenId];
    }
} 