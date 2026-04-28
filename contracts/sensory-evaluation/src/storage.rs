use crate::types::*;
use soroban_sdk::{Address, Env, Vec, String};

/// Checks if the caller is an admin
pub fn is_admin(env: &Env, address: &Address) -> bool {
    let admins: Vec<Address> = env
        .storage()
        .instance()
        .get(&DataKey::Admins)
        .unwrap_or_else(|| Vec::new(env));
    admins.contains(address)
}

/// Checks if the contract is paused
pub fn is_paused(env: &Env) -> bool {
    env.storage().instance().get(&DataKey::Paused).unwrap_or(false)
}

/// Gets the next evaluation ID
pub fn next_evaluation_id(env: &Env) -> u32 {
    let id: u32 = env
        .storage()
        .instance()
        .get(&DataKey::NextEvaluationId)
        .unwrap_or(1u32);
    env.storage()
        .instance()
        .set(&DataKey::NextEvaluationId, &(id + 1));
    id
}

/// Gets the next dispute ID
pub fn next_dispute_id(env: &Env) -> u32 {
    let id: u32 = env
        .storage()
        .instance()
        .get(&DataKey::NextDisputeId)
        .unwrap_or(1u32);
    env.storage()
        .instance()
        .set(&DataKey::NextDisputeId, &(id + 1));
    id
}

/// Gets token balance for an address
pub fn get_balance(env: &Env, address: &Address) -> u128 {
    env.storage()
        .instance()
        .get(&DataKey::Balances(address.clone()))
        .unwrap_or(0)
}

/// Sets token balance for an address
pub fn set_balance(env: &Env, address: &Address, balance: u128) {
    env.storage()
        .instance()
        .set(&DataKey::Balances(address.clone()), &balance);
}

/// Gets total token supply
pub fn get_total_supply(env: &Env) -> u128 {
    env.storage()
        .instance()
        .get(&DataKey::TotalSupply)
        .unwrap_or(0)
}

/// Sets total token supply
pub fn set_total_supply(env: &Env, supply: u128) {
    env.storage().instance().set(&DataKey::TotalSupply, &supply);
}

/// Gets maximum token supply
pub fn get_max_supply(env: &Env) -> u128 {
    env.storage()
        .instance()
        .get(&DataKey::MaxSupply)
        .unwrap_or(0)
}

/// Sets maximum token supply
pub fn set_max_supply(env: &Env, max_supply: u128) {
    env.storage().instance().set(&DataKey::MaxSupply, &max_supply);
}

/// Gets token decimals
pub fn get_decimals(env: &Env) -> u32 {
    env.storage()
        .instance()
        .get(&DataKey::Decimals)
        .unwrap_or(18)
}

/// Sets token decimals
pub fn set_decimals(env: &Env, decimals: u32) {
    env.storage().instance().set(&DataKey::Decimals, &decimals);
}

/// Gets admin list
pub fn get_admins(env: &Env) -> Vec<Address> {
    env.storage()
        .instance()
        .get(&DataKey::Admins)
        .unwrap_or_else(|| Vec::new(env))
}

/// Sets admin list
pub fn set_admins(env: &Env, admins: &Vec<Address>) {
    env.storage().instance().set(&DataKey::Admins, admins);
}

/// Gets user stakes
pub fn get_user_stakes(env: &Env, user: &Address) -> Vec<Stake> {
    env.storage()
        .instance()
        .get(&DataKey::Stakes(user.clone()))
        .unwrap_or_else(|| Vec::new(env))
}

/// Sets user stakes
pub fn set_user_stakes(env: &Env, user: &Address, stakes: &Vec<Stake>) {
    env.storage()
        .instance()
        .set(&DataKey::Stakes(user.clone()), stakes);
}

/// Gets evaluation by ID
pub fn get_evaluation(env: &Env, evaluation_id: u32) -> Evaluation {
    env.storage()
        .instance()
        .get(&DataKey::Evaluations(evaluation_id))
        .unwrap_or_else(|| panic!("Evaluation not found"))
}

/// Stores evaluation
pub fn store_evaluation(env: &Env, evaluation: &Evaluation) {
    env.storage()
        .instance()
        .set(&DataKey::Evaluations(evaluation.id), evaluation);
}

/// Gets user evaluation history
pub fn get_evaluation_history(env: &Env, user: &Address) -> Vec<u32> {
    env.storage()
        .instance()
        .get(&DataKey::EvaluationHistory(user.clone()))
        .unwrap_or_else(|| Vec::new(env))
}

/// Sets user evaluation history
pub fn store_evaluation_history(env: &Env, user: &Address, history: &Vec<u32>) {
    env.storage()
        .instance()
        .set(&DataKey::EvaluationHistory(user.clone()), history);
}

/// Gets user reputation
pub fn get_user_reputation(env: &Env, user: &Address) -> Reputation {
    env.storage()
        .instance()
        .get(&DataKey::UserReputation(user.clone()))
        .unwrap_or_else(|| Reputation {
            address: user.clone(),
            score: 0,
            tier: ReputationTier::Novice,
            total_evaluations: 0,
            accuracy_score: 0,
            consistency_score: 0,
            expertise_areas: Vec::new(env),
            last_updated: env.ledger().timestamp(),
        })
}

/// Sets user reputation
pub fn store_user_reputation(env: &Env, user: &Address, reputation: &Reputation) {
    env.storage()
        .instance()
        .set(&DataKey::UserReputation(user.clone()), reputation);
}

/// Gets expert panel
pub fn get_expert_panel(env: &Env) -> Vec<ExpertMember> {
    env.storage()
        .instance()
        .get(&DataKey::ExpertPanel)
        .unwrap_or_else(|| Vec::new(env))
}

/// Sets expert panel
pub fn set_expert_panel(env: &Env, panel: &Vec<ExpertMember>) {
    env.storage().instance().set(&DataKey::ExpertPanel, panel);
}

/// Checks if address is expert panel member
pub fn is_expert_panel_member(env: &Env, address: &Address) -> bool {
    let panel = get_expert_panel(env);
    panel.iter().any(|member| member.address == *address)
}

/// Gets evaluation criteria
pub fn get_evaluation_criteria(env: &Env) -> EvaluationCriteria {
    env.storage()
        .instance()
        .get(&DataKey::EvaluationCriteria)
        .unwrap_or_else(|| EvaluationCriteria {
            criteria: Vec::new(env),
            version: 1,
            last_updated: env.ledger().timestamp(),
        })
}

/// Sets evaluation criteria
pub fn set_evaluation_criteria(env: &Env, criteria: &EvaluationCriteria) {
    env.storage().instance().set(&DataKey::EvaluationCriteria, criteria);
}

/// Gets dispute by ID
pub fn get_dispute(env: &Env, dispute_id: u32) -> DisputeResolution {
    env.storage()
        .instance()
        .get(&DataKey::DisputeResolutions(dispute_id))
        .unwrap_or_else(|| panic!("Dispute not found"))
}

/// Stores dispute
pub fn store_dispute(env: &Env, dispute: &DisputeResolution) {
    env.storage()
        .instance()
        .set(&DataKey::DisputeResolutions(dispute.id), dispute);
}

/// Gets all disputes
pub fn get_all_disputes_storage(env: &Env) -> Vec<DisputeResolution> {
    // This would typically require a more complex storage pattern
    // For now, return empty vector - in production, you'd store a list of dispute IDs
    Vec::new(env)
}

/// Checks if dispute exists for evaluation
pub fn dispute_exists(env: &Env, evaluation_id: u32) -> bool {
    // This would typically check against a mapping of evaluation_id -> dispute_id
    // For now, return false - in production, implement proper tracking
    false
}

/// Gets reputation history for user
pub fn get_reputation_history(env: &Env, user: &Address) -> Vec<ReputationChange> {
    env.storage()
        .instance()
        .get(&DataKey::ReputationHistory(user.clone()))
        .unwrap_or_else(|| Vec::new(env))
}

/// Sets reputation history for user
pub fn store_reputation_history(env: &Env, user: &Address, history: &Vec<ReputationChange>) {
    env.storage()
        .instance()
        .set(&DataKey::ReputationHistory(user.clone()), history);
}

/// Gets contract version
pub fn get_contract_version(env: &Env) -> u32 {
    env.storage().instance().get(&DataKey::ContractVersion).unwrap_or(1)
}

/// Sets contract version
pub fn set_contract_version(env: &Env, version: u32) {
    env.storage().instance().set(&DataKey::ContractVersion, &version);
}

/// Gets next stake ID
pub fn next_stake_id(env: &Env) -> u32 {
    let id: u32 = env
        .storage()
        .instance()
        .get(&DataKey::NextStakeId)
        .unwrap_or(1u32);
    env.storage()
        .instance()
        .set(&DataKey::NextStakeId, &(id + 1));
    id
}

/// Calculates overall evaluation score from individual scores
pub fn calculate_overall_score(scores: &Vec<EvaluationScore>) -> u32 {
    if scores.is_empty() {
        return 0;
    }
    
    let total_weight: u32 = scores.iter().map(|s| s.weight).sum();
    if total_weight == 0 {
        return 0;
    }
    
    let weighted_sum: u32 = scores.iter()
        .map(|s| s.score * s.weight)
        .sum();
    
    weighted_sum / total_weight
}

/// Checks if user meets reputation requirement
pub fn meets_reputation_requirement(env: &Env, user: &Address, requirement: i32) -> bool {
    let reputation = get_user_reputation(env, user);
    reputation.score >= requirement
}

/// Gets reward multiplier based on reputation tier
pub fn get_reward_multiplier(tier: ReputationTier) -> u32 {
    match tier {
        ReputationTier::Novice => 100,
        ReputationTier::Apprentice => 125,
        ReputationTier::Expert => 150,
        ReputationTier::Master => 200,
        ReputationTier::Grandmaster => 300,
    }
}

/// Updates expertise areas for user
pub fn update_expertise_areas(env: &Env, user: &Address, new_areas: &Vec<String>) {
    let mut reputation = get_user_reputation(env, user);
    reputation.expertise_areas = new_areas.clone();
    reputation.last_updated = env.ledger().timestamp();
    store_user_reputation(env, user, &reputation);
}

/// Gets token name
pub fn get_token_name(env: &Env) -> String {
    env.storage()
        .instance()
        .get(&DataKey::TokenName)
        .unwrap_or_else(|| String::from_str(env, "SensoryToken"))
}

/// Sets token name
pub fn set_token_name(env: &Env, name: &String) {
    env.storage().instance().set(&DataKey::TokenName, name);
}

/// Gets token symbol
pub fn get_token_symbol(env: &Env) -> String {
    env.storage()
        .instance()
        .get(&DataKey::TokenSymbol)
        .unwrap_or_else(|| String::from_str(env, "SENSORY"))
}

/// Sets token symbol
pub fn set_token_symbol(env: &Env, symbol: &String) {
    env.storage().instance().set(&DataKey::TokenSymbol, symbol);
}
