use soroban_sdk::{contracttype, Address, Vec, String};

/// Enum representing storage keys for the contract.
#[contracttype]
pub enum DataKey {
    TotalSupply,           // Tracks the total token supply
    Balances(Address),     // Maps user address to their token balance
    Admins,                // Stores list of admin addresses
    AdminApprovals,        // Tracks approvals for multi-signature actions
    VestingSchedules(Address, u32), // Maps (user, schedule ID) to vesting schedule
    NextScheduleId,        // Counter for the next vesting schedule ID
    MaxSupply,             // Maximum allowable token supply
    Decimals,              // Number of decimal places for token precision
    Stakes(Address),       // User staking positions
    NextStakeId,           // Counter for stake IDs
    RewardPools,           // Reward pool configurations
    GlobalRewards,         // Global reward tracking
    UserRewards(Address),  // User reward tracking
    StakingStats,          // Global staking statistics
    ContractVersion,       // Contract version for upgrades
    Paused,                // Contract pause state
}

/// Represents a staking position with rewards
#[contracttype]
#[derive(Clone)]
pub struct Stake {
    pub id: u32,             // Unique identifier for the stake
    pub staker: Address,     // Address of the staker
    pub amount: u64,         // Amount staked
    pub start_time: u64,     // When staking began
    pub duration: u64,       // Staking duration in seconds
    pub reward_rate: u32,    // Reward rate in basis points
    pub lock_period: u64,    // Lock period before unstaking
    pub auto_compound: bool, // Whether rewards are auto-compounded
    pub last_claim_time: u64, // Last time rewards were claimed
    pub total_rewards: u64,  // Total rewards earned
}

/// Represents a reward pool configuration
#[contracttype]
#[derive(Clone)]
pub struct RewardPool {
    pub id: u32,             // Pool identifier
    pub name: String,        // Pool name
    pub total_rewards: u64,  // Total rewards allocated to pool
    pub distributed: u64,    // Rewards already distributed
    pub reward_rate: u32,    // Current reward rate
    pub min_stake: u64,      // Minimum stake amount
    pub max_stake: u64,      // Maximum stake amount
    pub duration: u64,       // Pool duration
    pub start_time: u64,     // Pool start time
    pub active: bool,        // Whether pool is active
}

/// Represents user reward tracking
#[contracttype]
#[derive(Clone)]
pub struct UserReward {
    pub stake_id: u32,       // Associated stake ID
    pub pool_id: u32,         // Associated pool ID
    pub pending_rewards: u64, // Pending rewards to claim
    pub claimed_rewards: u64, // Total claimed rewards
    pub last_update: u64,    // Last reward calculation time
}

/// Represents a vesting schedule for token distribution over time.
#[contracttype]
#[derive(Clone)]
pub struct VestingSchedule {
    pub id: u32,             // Unique identifier for the vesting schedule
    pub recipient: Address,  // Address receiving the vested tokens
    pub total_amount: u64,   // Total token amount to vest
    pub released_amount: u64, // Amount already released to the recipient
    pub start_time: u64,     // Timestamp when vesting begins
    pub duration: u64,       // Total duration of vesting in seconds
    pub cliff: u64,          // Cliff period in seconds before vesting starts
    pub linear_vesting: bool, // Whether vesting is linear or milestone-based
}

/// Represents an admin action requiring multi-signature approval.
#[contracttype]
#[derive(Clone)]
pub enum AdminAction {
    Mint(Address, u64),    // Action to mint tokens to an address
    Burn(Address, u64),    // Action to burn tokens from an address
    CreatePool(RewardPool), // Create a new reward pool
    UpdatePool(u32, RewardPool), // Update existing pool
    PauseContract,         // Pause contract operations
    UnpauseContract,       // Unpause contract operations
}

/// Tracks approvals for an admin action in multi-signature operations.
#[contracttype]
#[derive(Clone)]
pub struct Approval {
    pub action: AdminAction, // The admin action being approved
    pub approvals: Vec<Address>, // List of approving admins
    pub required_approvals: u32, // Required number of approvals
    pub timestamp: u64,      // When the approval was created
}

/// Staking statistics
#[contracttype]
#[derive(Clone)]
pub struct StakingStats {
    pub total_staked: u64,    // Total tokens staked
    pub total_stakers: u32,   // Number of active stakers
    pub average_stake_duration: u64, // Average staking duration
    pub total_rewards_distributed: u64, // Total rewards distributed
    pub last_stats_update: u64, // Last stats update time
}

/// Staking tier levels
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum StakingTier {
    Bronze,                 // Basic tier
    Silver,                 // Mid tier
    Gold,                   // High tier
    Platinum,               // Premium tier
}

/// Reward multiplier configuration
#[contracttype]
#[derive(Clone)]
pub struct RewardMultiplier {
    pub tier: StakingTier,   // Staking tier
    pub multiplier: u32,    // Reward multiplier (basis points)
    pub min_stake: u64,      // Minimum stake for this tier
    pub duration_bonus: u32, // Duration bonus (basis points)
}