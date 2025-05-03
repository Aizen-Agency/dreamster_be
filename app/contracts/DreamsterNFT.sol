// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Supply.sol";
import "../interfaces/IDreamsterNFT.sol";

/**
 * @title DreamsterNFT
 * @notice Implementation of Dreamster's NFT contract
 */
contract DreamsterNFT is IDreamsterNFT, ERC1155, ERC1155Supply, Ownable, Pausable {
    // Events
    event TokenURIUpdated(uint256 indexed tokenId, string newUri);

    // State variables
    address public override bondingCurve;
    address public override yieldContract;
    string public name;
    string public symbol;
    address public override creator;
    uint256 public override maxSupply;
    bool private _initialized;
    uint256 private constant FIRST_TOKEN_ID = 1;
    bool private _contractsSet;

    // Track token holders
    mapping(uint256 => mapping(address => bool)) private _isHolder;
    mapping(uint256 => address[]) private _holdersList;

    // Modifiers
    modifier onlyBondingCurve() {
        require(msg.sender == bondingCurve, "Only bonding curve");
        _;
    }

    modifier whenInitialized() {
        require(_initialized, "Contract not initialized");
        _;
    }

    constructor() ERC1155("") {
        _transferOwnership(msg.sender);
    }

    /**
     * @inheritdoc IDreamsterNFT
     */
    function initialize(
        string memory _name,
        string memory _symbol,
        string memory uri,
        uint256 _maxSupply,
        uint256 initialSupply,
        address _creator
    ) external override {
        require(!_initialized, "Already initialized");
        require(bytes(_name).length > 0, "Name cannot be empty");
        require(bytes(_symbol).length > 0, "Symbol cannot be empty");
        require(bytes(uri).length > 0, "URI cannot be empty");
        require(_maxSupply > 0, "Max supply must be greater than 0");
        require(initialSupply <= _maxSupply, "Initial supply exceeds max supply");
        require(_creator != address(0), "Creator cannot be zero address");

        name = _name;
        symbol = _symbol;
        maxSupply = _maxSupply;
        creator = _creator;
        _setURI(uri);
        _initialized = true;
    }

    /**
     * @notice Sets the bonding curve contract address. Can only be called once by the owner.
     * @param _bondingCurve Address of the bonding curve contract
     */
    function setBondingCurve(address _bondingCurve) external onlyOwner whenInitialized {
        require(bondingCurve == address(0), "Bonding curve already set");
        require(_bondingCurve != address(0), "Invalid bonding curve");
        bondingCurve = _bondingCurve;
        _checkAndTransferOwnership();
    }

    /**
     * @notice Sets the yield contract address. Can only be called once by the owner.
     * @param _yieldContract Address of the yield contract
     */
    function setYieldContract(address _yieldContract) external onlyOwner whenInitialized {
        require(yieldContract == address(0), "Yield contract already set");
        require(_yieldContract != address(0), "Invalid yield contract");
        yieldContract = _yieldContract;
        _checkAndTransferOwnership();
    }

    /**
     * @notice Internal function to check if both contracts are set and transfer ownership
     */
    function _checkAndTransferOwnership() private {
        if (!_contractsSet && bondingCurve != address(0) && yieldContract != address(0)) {
            _contractsSet = true;
            _transferOwnership(creator);
        }
    }

    /**
     * @inheritdoc IDreamsterNFT
     */
    function mint(address to, uint256 amount) external override onlyBondingCurve whenNotPaused returns (uint256) {
        require(to != address(0), "Cannot mint to zero address");
        require(amount > 0, "Amount must be greater than 0");

        uint256 supply = totalSupply(FIRST_TOKEN_ID);
        require(supply + amount <= maxSupply, "Exceeds max supply");

        _mint(to, FIRST_TOKEN_ID, amount, "");

        if (!_isHolder[FIRST_TOKEN_ID][to]) {
            _isHolder[FIRST_TOKEN_ID][to] = true;
            _holdersList[FIRST_TOKEN_ID].push(to);
        }

        return FIRST_TOKEN_ID;
    }

    /**
     * @inheritdoc IDreamsterNFT
     */
    function burn(address from, uint256 amount, uint256 tokenId) external override onlyBondingCurve whenNotPaused {
        require(from != address(0), "Cannot burn from zero address");
        require(amount > 0, "Amount must be greater than 0");
        require(balanceOf(from, tokenId) >= amount, "Insufficient balance");

        _burn(from, tokenId, amount);

        if (balanceOf(from, tokenId) == 0) {
            _isHolder[tokenId][from] = false;
            // Remove from holders list
            for (uint256 i = 0; i < _holdersList[tokenId].length; i++) {
                if (_holdersList[tokenId][i] == from) {
                    _holdersList[tokenId][i] = _holdersList[tokenId][_holdersList[tokenId].length - 1];
                    _holdersList[tokenId].pop();
                    break;
                }
            }
        }
    }

    /**
     * @inheritdoc IDreamsterNFT
     */
    function updateTokenURI(uint256 tokenId, string memory newUri) external override onlyOwner {
        require(exists(tokenId), "Token does not exist");
        _setURI(newUri);
        emit TokenURIUpdated(tokenId, newUri);
    }

    /**
     * @notice Returns all holders of a specific token ID
     * @param tokenId The token ID to get holders for
     * @return An array of addresses that hold the token
     */
    function getHolders(uint256 tokenId) external view returns (address[] memory) {
        return _holdersList[tokenId];
    }

    /**
     * @notice Checks if an address is a holder of a specific token ID
     * @param tokenId The token ID to check
     * @param account The address to check
     * @return True if the address holds the token
     */
    function isHolder(uint256 tokenId, address account) external view returns (bool) {
        return _isHolder[tokenId][account];
    }

    /**
     * @notice Pauses all token transfers
     * @dev Can only be called by the contract owner
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpauses all token transfers
     * @dev Can only be called by the contract owner
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @dev See {ERC1155-_beforeTokenTransfer}.
     */
    function _beforeTokenTransfer(
        address operator,
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory amounts,
        bytes memory data
    ) internal override(ERC1155, ERC1155Supply) whenNotPaused {
        super._beforeTokenTransfer(operator, from, to, ids, amounts, data);
    }

    /**
     * @dev Override totalSupply from ERC1155Supply to match interface
     */
    function totalSupply(uint256 tokenId) public view override(ERC1155Supply, IDreamsterNFT) returns (uint256) {
        return super.totalSupply(tokenId);
    }
}