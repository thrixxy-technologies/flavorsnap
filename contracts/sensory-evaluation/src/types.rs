use soroban_sdk::{contracttype, Address};

#[contracttype]
pub enum DataKey {
    Admins,            // List of admin addresses
    Balances(Address), // User address -> balance
    TotalSupply,       // Total token supply
    TokenName,         // Token name
    TokenSymbol,       // Token symbol
    MaxSupply,         // Maximum token supply
    Decimals,          // Token decimal places
    Stakes(Address),   // User address -> list of stakes
    NextStakeId,       // Counter for stake IDs
}

#[contracttype]
#[derive(Clone)]
pub struct Stake {
    pub id: u32,
    pub amount: u128,
    pub start_time: u64,
    pub duration: u64, // Duration in seconds
    pub claimed: bool,
}