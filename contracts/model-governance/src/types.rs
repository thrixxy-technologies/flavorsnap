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
}

/// Represents a vote cast by a token holder
#[contracttype]
#[derive(Clone)]
pub struct Vote {
    pub voter: Address,
    pub in_favor: bool,
    pub weight: u32, // Vote weight based on token balance
}

/// Status of a proposal
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum ProposalStatus {
    Active,
    Approved,
    Rejected,
    Cancelled,
}
