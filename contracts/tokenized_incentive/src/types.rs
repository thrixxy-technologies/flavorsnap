use soroban_sdk::{contracttype, Address};

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
}

/// Represents a vesting schedule for token distribution over time.
#[contracttype]
#[derive(Clone)]
pub struct VestingSchedule {
    pub id: u32,             // Unique identifier for the vesting schedule
    pub recipient: Address,  // Address receiving the vested tokens
    pub total_amount: u64,   // Total token amount to vest
    pub released_amount: u64,// Amount already released to the recipient
    pub start_time: u64,     // Timestamp when vesting begins
    pub duration: u64,       // Total duration of vesting in seconds
    pub cliff: u64,          // Cliff period in seconds before vesting starts
}

/// Represents an admin action requiring multi-signature approval.
#[contracttype]
#[derive(Clone)]
pub enum AdminAction {
    Mint(Address, u64),    // Action to mint tokens to an address
    Burn(Address, u64),    // Action to burn tokens from an address
}

/// Tracks approvals for an admin action in multi-signature operations.
#[contracttype]
#[derive(Clone)]
pub struct Approval {
    pub action: AdminAction, // The admin action being approved
    pub approvals: u32,      // Number of admin approvals received
}