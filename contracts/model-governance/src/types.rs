use soroban_sdk::{contracttype, Address, String};

/// Storage keys for persistent data
#[contracttype]
pub enum DataKey {
    Proposals(u32),        // Proposal ID -> Proposal data
    NextProposalId,        // Counter for proposal IDs
    Votes(u32, Address),   // (Proposal ID, Voter Address) -> Vote data
    Voters(u32),           // Proposal ID -> List of voter addresses
    TokenBalance(Address), // Address -> Token balance
    Admin,                 // Admin address
    Quorum,                // Quorum percentage (e.g., 5000 = 50.00%)
    VotingPeriod,          // Voting period in seconds
    MinStake,              // Minimum stake for proposal submission
    TokenHolders,          // List of all addresses with non-zero token balances
    Delegations(Address),  // Address -> Delegation info
    VotingPowerSnapshot(u32), // Proposal ID -> Voting power snapshots
    TimelockDelay,         // Delay before execution
    EmergencyProposals,    // Emergency proposal tracking
    ProposalHistory,       // Historical proposal data
    ContractVersion,       // Contract version for upgrades
    Paused,                // Contract pause state
}
/// Represents a proposal for AI model updates or dataset expansions
#[contracttype]
#[derive(Clone)]
pub struct Proposal {
    pub id: u32,
    pub proposer: Address,
    pub metadata: String, // Description of the update or expansion
    pub stake: u32,       // Tokens staked by proposer
    pub status: ProposalStatus,
    pub yes_votes: u32, // Total yes vote weight
    pub no_votes: u32,  // Total no vote weight
    pub timestamp: u64, // Submission timestamp
    pub executed: bool, // Whether the proposal has been executed
    pub execution_time: u64, // Time when proposal can be executed (for timelock)
    pub proposal_type: ProposalType, // Type of proposal
    pub voting_power_used: u32, // Total voting power used
}

/// Represents a vote cast by a token holder
#[contracttype]
#[derive(Clone)]
pub struct Vote {
    pub voter: Address,
    pub in_favor: bool,
    pub weight: u32, // Vote weight based on token balance
    pub timestamp: u64, // When the vote was cast
    pub delegated_to: Option<Address>, // If vote was delegated
}

/// Vote delegation structure
#[contracttype]
#[derive(Clone)]
pub struct Delegation {
    pub delegator: Address,
    pub delegate: Address,
    pub timestamp: u64,
    pub weight: u32,
}

/// Status of a proposal
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum ProposalStatus {
    Active,
    Approved,
    Rejected,
    Cancelled,
    Executed,
    Expired,
}

/// Types of proposals
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum ProposalType {
    ModelUpdate,
    DatasetExpansion,
    ParameterChange,
    Emergency,
    Upgrade,
}

/// Voting power snapshot
#[contracttype]
#[derive(Clone)]
pub struct VotingPowerSnapshot {
    pub address: Address,
    pub power: u32,
    pub timestamp: u64,
    pub delegated: bool,
}
