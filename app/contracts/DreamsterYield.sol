// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "../interfaces/IDreamsterYield.sol";
import "../interfaces/IDreamsterNFT.sol";

/**
 * @title DreamsterYield
 * @notice Implementation of Dreamster's yield distribution contract
 */
contract DreamsterYield is IDreamsterYield, Ownable, Pausable, ReentrancyGuard {
    // State variables
    address public nftContract;
    address public bondingCurveContract;
    uint256 public currentEpoch;
    uint256 public epochDuration;
    uint256 public lastDistributionTime;
    bool private _initialized;

    // Epoch data
    mapping(uint256 => YieldEpoch) private epochs;
    mapping(address => uint256) private lastClaimedEpoch;
    mapping(address => uint256) private totalClaimed;

    // Modifiers
    modifier whenInitialized() {
        require(_initialized, "Contract not initialized");
        _;
    }

    constructor() {
        _transferOwnership(msg.sender);
    }

    /**
     * @inheritdoc IDreamsterYield
     */
    function initialize(
        address _nftContract,
        address _bondingCurve
    ) external {
        require(!_initialized, "Already initialized");
        require(_nftContract != address(0), "Invalid NFT contract");
        require(_bondingCurve != address(0), "Invalid bonding curve");

        nftContract = _nftContract;
        bondingCurveContract = _bondingCurve;
        epochDuration = 1 days; // Default epoch duration
        currentEpoch = 0;
        lastDistributionTime = block.timestamp;
        _initialized = true;
    }

    /**
     * @inheritdoc IDreamsterYield
     */
    function distributeYield() external payable whenInitialized whenNotPaused {
        require(msg.value > 0, "No yield to distribute");

        // Create new epoch
        currentEpoch++;
        uint256 totalSupply = IDreamsterNFT(nftContract).totalSupply(1);
        uint256 perTokenAmount = totalSupply > 0 ? msg.value / totalSupply : 0;

        epochs[currentEpoch] = YieldEpoch({
            amount: msg.value,
            totalSupply: totalSupply,
            perTokenAmount: perTokenAmount,
            timestamp: block.timestamp
        });

        lastDistributionTime = block.timestamp;
        emit YieldReceived(msg.value, totalSupply);
        emit NewYieldEpoch(currentEpoch, msg.value, totalSupply);
    }

    /**
     * @inheritdoc IDreamsterYield
     */
    function claimYield(address user) external whenInitialized whenNotPaused nonReentrant returns (uint256 amount) {
        require(user != address(0), "Invalid user address");

        uint256 lastClaimed = lastClaimedEpoch[user];
        require(lastClaimed < currentEpoch, "No yield to claim");

        uint256 totalYield = 0;
        for (uint256 i = lastClaimed + 1; i <= currentEpoch; i++) {
            YieldEpoch storage epoch = epochs[i];
            if (epoch.totalSupply == 0) continue;

            uint256 userShares = IDreamsterNFT(nftContract).balanceOf(user, 1);
            uint256 epochYield = (epoch.amount * userShares) / epoch.totalSupply;
            totalYield += epochYield;
        }

        require(totalYield > 0, "No yield available");

        lastClaimedEpoch[user] = currentEpoch;
        totalClaimed[user] += totalYield;

        (bool success, ) = user.call{value: totalYield}("");
        require(success, "Transfer failed");

        emit YieldClaimed(user, totalYield);
        return totalYield;
    }

    /**
     * @inheritdoc IDreamsterYield
     */
    function getClaimableYield(address user) external view returns (uint256 amount) {
        uint256 lastClaimed = lastClaimedEpoch[user];
        if (lastClaimed >= currentEpoch) return 0;

        uint256 totalYield = 0;
        for (uint256 i = lastClaimed + 1; i <= currentEpoch; i++) {
            YieldEpoch storage epoch = epochs[i];
            if (epoch.totalSupply == 0) continue;

            uint256 userShares = IDreamsterNFT(nftContract).balanceOf(user, 1);
            uint256 epochYield = (epoch.amount * userShares) / epoch.totalSupply;
            totalYield += epochYield;
        }

        return totalYield;
    }

    /**
     * @inheritdoc IDreamsterYield
     */
    function getTotalDistributed() external view returns (uint256) {
        uint256 total = 0;
        for (uint256 i = 1; i <= currentEpoch; i++) {
            total += epochs[i].amount;
        }
        return total;
    }

    /**
     * @inheritdoc IDreamsterYield
     */
    function getCurrentEpoch() external view returns (uint256) {
        return currentEpoch;
    }

    /**
     * @inheritdoc IDreamsterYield
     */
    function getEpochInfo(uint256 epochId) external view returns (YieldEpoch memory) {
        require(epochId > 0 && epochId <= currentEpoch, "Invalid epoch ID");
        return epochs[epochId];
    }

    /**
     * @inheritdoc IDreamsterYield
     */
    function getTotalClaimed(address user) external view returns (uint256) {
        return totalClaimed[user];
    }

    /**
     * @inheritdoc IDreamsterYield
     */
    function getLastClaimedEpoch(address user) external view returns (uint256) {
        return lastClaimedEpoch[user];
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    receive() external payable {
        require(msg.sender == address(nftContract) || msg.sender == bondingCurveContract, "Only NFT or bonding curve");
    }
}