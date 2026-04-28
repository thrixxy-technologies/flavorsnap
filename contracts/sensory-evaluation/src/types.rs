use soroban_sdk::{contracttype, Address, Vec, String};

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
    Evaluations(u32),  // Evaluation ID -> evaluation data
    NextEvaluationId,  // Counter for evaluation IDs
    UserReputation(Address), // User address -> reputation score
    EvaluationHistory(Address), // User address -> evaluation history
    ExpertPanel,       // List of expert evaluator addresses
    EvaluationCriteria, // Evaluation criteria configuration
    DisputeResolutions(u32), // Dispute ID -> resolution data
    NextDisputeId,     // Counter for dispute IDs
    ReputationHistory(Address), // User address -> reputation changes
    ContractVersion,   // Contract version for upgrades
    Paused,            // Contract pause state
}

/// Sensory evaluation with detailed scoring
#[contracttype]
#[derive(Clone)]
pub struct Evaluation {
    pub id: u32,
    pub evaluator: Address,
    pub food_item_id: String,
    pub scores: Vec<EvaluationScore>,
    pub comments: String,
    pub timestamp: u64,
    pub verified: bool,
    pub verification_count: u32,
    pub reward_earned: u128,
    pub confidence_score: u32, // Evaluator's confidence (0-100)
}

/// Individual evaluation score for a criterion
#[contracttype]
#[derive(Clone)]
pub struct EvaluationScore {
    pub criterion: String,
    pub score: u32,        // 0-100
    pub weight: u32,       // Weight of this criterion in overall score
    pub justification: String,
}

/// User reputation system
#[contracttype]
#[derive(Clone)]
pub struct Reputation {
    pub address: Address,
    pub score: i32,        // Can be negative for bad behavior
    pub tier: ReputationTier,
    pub total_evaluations: u32,
    pub accuracy_score: u32, // Historical accuracy percentage
    pub consistency_score: u32, // Consistency with other evaluators
    pub expertise_areas: Vec<String>, // Areas of expertise
    pub last_updated: u64,
}

/// Reputation tiers with different benefits
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum ReputationTier {
    Novice,     // 0-100 points
    Apprentice, // 101-300 points
    Expert,     // 301-600 points
    Master,     // 601-1000 points
    Grandmaster, // 1000+ points
}

/// Dispute resolution for contested evaluations
#[contracttype]
#[derive(Clone)]
pub struct DisputeResolution {
    pub id: u32,
    pub evaluation_id: u32,
    pub challenger: Address,
    pub reason: String,
    pub status: DisputeStatus,
    pub admin_review: Vec<Address>,
    pub resolution: String,
    pub timestamp: u64,
}

/// Dispute status tracking
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum DisputeStatus {
    Open,
    UnderReview,
    Resolved,
    Dismissed,
}

/// Evaluation criteria configuration
#[contracttype]
#[derive(Clone)]
pub struct EvaluationCriteria {
    pub criteria: Vec<CriterionConfig>,
    pub version: u32,
    pub last_updated: u64,
}

/// Individual criterion configuration
#[contracttype]
#[derive(Clone)]
pub struct CriterionConfig {
    pub name: String,
    pub description: String,
    pub weight: u32,
    pub min_score: u32,
    pub max_score: u32,
    pub required_expertise: Option<String>,
}

/// Reputation change history
#[contracttype]
#[derive(Clone)]
pub struct ReputationChange {
    pub evaluation_id: u32,
    pub old_score: i32,
    pub new_score: i32,
    pub reason: String,
    pub timestamp: u64,
}

/// Enhanced stake with reputation requirements
#[contracttype]
#[derive(Clone)]
pub struct Stake {
    pub id: u32,
    pub amount: u128,
    pub start_time: u64,
    pub duration: u64, // Duration in seconds
    pub claimed: bool,
    pub reputation_requirement: i32, // Minimum reputation required
    pub multiplier: u32, // Reward multiplier based on reputation
}

/// Expert panel member information
#[contracttype]
#[derive(Clone)]
pub struct ExpertMember {
    pub address: Address,
    pub expertise_areas: Vec<String>,
    pub joined_date: u64,
    pub contributions: u32,
    pub verification_power: u32, // Weight in verification process
}