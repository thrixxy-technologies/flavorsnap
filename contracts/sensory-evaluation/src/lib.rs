#![no_std]
use soroban_sdk::{contract, contractimpl, Address, Env, String, Vec};

mod types;
mod admin;
mod token;
mod staking;
mod test;

pub use types::*;
pub use admin::*;
pub use token::*;
pub use staking::*;

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
}