#![no_std]
use soroban_sdk::{contract, contractimpl, Address, Env, String, Vec};

mod types;
mod admin;
mod token;
mod staking;
mod evaluation;
mod storage;
mod test;

pub use types::*;
pub use admin::*;
pub use token::*;
pub use staking::*;
pub use evaluation::*;
pub use storage::*;

#[contract]
pub struct SensoryEvaluation;

#[contractimpl]
impl SensoryEvaluation {
    // Initialize the contract
    pub fn initialize(env: Env, admins: Vec<Address>, token_name: String, token_symbol: String, max_supply: u128, decimals: u32) {
        admin::initialize(env, admins, token_name, token_symbol, max_supply, decimals)
    }

    // Admin functions
    pub fn add_admin(env: Env, caller: Address, new_admin: Address) {
        admin::add_admin(env, caller, new_admin)
    }

    pub fn remove_admin(env: Env, caller: Address, admin: Address) {
        admin::remove_admin(env, caller, admin)
    }

    // Token functions
    pub fn mint_tokens(env: Env, caller: Address, to: Address, amount: u128) {
        token::mint_tokens(env, caller, to, amount)
    }

    pub fn burn_tokens(env: Env, caller: Address, from: Address, amount: u128) {
        token::burn_tokens(env, caller, from, amount)
    }

    pub fn transfer_tokens(env: Env, from: Address, to: Address, amount: u128) {
        token::transfer_tokens(env, from, to, amount)
    }

    // Staking functions
    pub fn stake_tokens(env: Env, staker: Address, amount: u128, duration: u64) {
        staking::stake_tokens(env, staker, amount, duration)
    }

    pub fn unstake_tokens(env: Env, staker: Address, stake_id: u32) {
        staking::unstake_tokens(env, staker, stake_id)
    }

    // Evaluation functions
    pub fn submit_evaluation(
        env: Env,
        evaluator: Address,
        food_item_id: String,
        scores: Vec<EvaluationScore>,
        comments: String,
        confidence_score: u32,
    ) -> u32 {
        evaluation::submit_evaluation(env, evaluator, food_item_id, scores, comments, confidence_score)
    }

    pub fn verify_evaluation(env: Env, verifier: Address, evaluation_id: u32, approve: bool) {
        evaluation::verify_evaluation(env, verifier, evaluation_id, approve)
    }

    pub fn create_dispute(
        env: Env,
        challenger: Address,
        evaluation_id: u32,
        reason: String,
    ) -> u32 {
        evaluation::create_dispute(env, challenger, evaluation_id, reason)
    }

    pub fn resolve_dispute(
        env: Env,
        admin: Address,
        dispute_id: u32,
        resolution: String,
        approve_dispute: bool,
    ) {
        evaluation::resolve_dispute(env, admin, dispute_id, resolution, approve_dispute)
    }

    // Query functions
    pub fn get_balance(env: Env, user: Address) -> u128 {
        token::get_balance(env, user)
    }

    pub fn get_total_supply(env: Env) -> u128 {
        token::get_total_supply(env)
    }

    pub fn get_stakes(env: Env, user: Address) -> Vec<Stake> {
        staking::get_stakes(env, user)
    }

    pub fn get_admins(env: Env) -> Vec<Address> {
        admin::get_admins(env)
    }

    pub fn get_evaluation_info(env: Env, evaluation_id: u32) -> Evaluation {
        evaluation::get_evaluation_info(env, evaluation_id)
    }

    pub fn get_user_evaluation_history(env: Env, user: Address) -> Vec<u32> {
        evaluation::get_user_evaluation_history(env, user)
    }

    pub fn get_user_reputation_info(env: Env, user: Address) -> Reputation {
        evaluation::get_user_reputation_info(env, user)
    }

    pub fn get_all_disputes(env: Env) -> Vec<DisputeResolution> {
        evaluation::get_all_disputes(env)
    }

    pub fn get_expert_panel_members(env: Env) -> Vec<ExpertMember> {
        evaluation::get_expert_panel_members(env)
    }

    // Admin-only functions for configuration
    pub fn set_evaluation_criteria(env: Env, admin: Address, criteria: EvaluationCriteria) {
        admin::set_evaluation_criteria(env, admin, criteria)
    }

    pub fn add_expert_panel_member(env: Env, admin: Address, member: ExpertMember) {
        admin::add_expert_panel_member(env, admin, member)
    }

    pub fn remove_expert_panel_member(env: Env, admin: Address, member_address: Address) {
        admin::remove_expert_panel_member(env, admin, member_address)
    }

    pub fn pause_contract(env: Env, admin: Address) {
        admin::pause_contract(env, admin)
    }

    pub fn unpause_contract(env: Env, admin: Address) {
        admin::unpause_contract(env, admin)
    }
}