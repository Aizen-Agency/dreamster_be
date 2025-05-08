// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IDreamsterYield
 * @notice Interface for Dreamster's yield distribution contract
 * @dev Handles the distribution and claiming of yield from NFT sales
 */
interface IDreamsterYield {
    /**
     * @notice Event emitted when yield is distributed to the contract
     * @param amount Amount of ETH distributed
     * @param totalSupply Total NFT supply at distribution time
     */
    event YieldReceived(uint256 amount, uint256 totalSupply);

    /**
     * @notice Event emitted when a user claims their yield
     * @param user Address of the user claiming
     * @param amount Amount of ETH claimed
     */
    event YieldClaimed(address indexed user, uint256 amount);

    /**
     * @notice Event emitted when a new yield epoch starts
     * @param epochId ID of the new epoch
     * @param amount Amount of ETH for distribution
     * @param totalSupply Total NFT supply for this epoch
     */
    event NewYieldEpoch(uint256 indexed epochId, uint256 amount, uint256 totalSupply);

    /**
     * @notice Struct containing yield information for an epoch
     * @param amount Total ETH amount for distribution
     * @param totalSupply Total NFT supply at distribution time
     * @param perTokenAmount Amount of ETH per token
     * @param timestamp When the epoch was created
     */
    struct YieldEpoch {
        uint256 amount;
        uint256 totalSupply;
        uint256 perTokenAmount;
        uint256 timestamp;
    }

    /**
     * @notice Initializes the yield distribution contract
     * @param nftContract Address of the NFT contract
     * @param bondingCurve Address of the bonding curve contract
     */
    function initialize(address nftContract, address bondingCurve) external;

    /**
     * @notice Distributes yield to the contract
     * @dev Only callable by the bonding curve contract
     */
    function distributeYield() external payable;

    /**
     * @notice Claims accumulated yield for a user
     * @param user Address of the user to claim for
     * @return amount Amount of ETH claimed
     */
    function claimYield(address user) external returns (uint256 amount);

    /**
     * @notice Gets the claimable yield for a user
     * @param user Address of the user to check
     * @return amount Amount of ETH available to claim
     */
    function getClaimableYield(address user) external view returns (uint256 amount);

    /**
     * @notice Gets information about a specific yield epoch
     * @param epochId ID of the epoch to query
     * @return YieldEpoch Epoch information
     */
    function getEpochInfo(uint256 epochId) external view returns (YieldEpoch memory);

    /**
     * @notice Gets the current epoch ID
     * @return uint256 Current epoch ID
     */
    function getCurrentEpoch() external view returns (uint256);

    /**
     * @notice Gets the total yield distributed so far
     * @return uint256 Total yield distributed
     */
    function getTotalDistributed() external view returns (uint256);

    /**
     * @notice Gets the total yield claimed by a user
     * @param user Address of the user
     * @return uint256 Total yield claimed
     */
    function getTotalClaimed(address user) external view returns (uint256);

    /**
     * @notice Gets the last epoch ID that a user has claimed
     * @param user Address of the user
     * @return uint256 Last claimed epoch ID
     */
    function getLastClaimedEpoch(address user) external view returns (uint256);
}