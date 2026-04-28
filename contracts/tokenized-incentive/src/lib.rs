#![no_std]
use soroban_sdk::{contract, contractimpl, Address, Env, Vec};

mod types;
mod admin;
mod token;
mod vesting;
mod staking;
mod storage;
mod test;

/// Exports for the contract's types and modules.
pub use types::*;
pub use admin::*;
pub use token::*;
pub use vesting::*;
pub use staking::*;
pub use storage::*;

/// The main contract struct for tokenized incentives.
#[contract]
pub struct TokenizedIncentive;

#[contractimpl]
impl TokenizedIncentive {
    /// Initializes the contract with admin addresses, max supply, and token decimals.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `admins` - Vector of admin addresses.
    /// * `max_supply` - Maximum token supply limit.
    /// * `decimals` - Number of decimal places for token precision.
    pub fn initialize(env: Env, admins: Vec<Address>, max_supply: u64, decimals: u32) {
        admin::initialize(env, admins, max_supply, decimals)
    }

    /// Adds a new admin to the contract.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `caller` - The address of the admin initiating the action.
    /// * `new_admin` - The address of the new admin to add.
    pub fn add_admin(env: Env, caller: Address, new_admin: Address) {
        admin::add_admin(env, caller, new_admin)
    }

    /// Approves an admin action for multi-signature operations.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `caller` - The address of the admin approving the action.
    /// * `action` - The admin action to approve.
    pub fn approve_action(env: Env, caller: Address, action: AdminAction) {
        admin::approve_action(env, caller, action)
    }

    /// Mints new tokens to a recipient.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `caller` - The address of the admin initiating the mint.
    /// * `to` - The address to receive the tokens.
    /// * `amount` - The amount of tokens to mint.
    pub fn mint(env: Env, caller: Address, to: Address, amount: u64) {
        token::mint(env, caller, to, amount)
    }

    /// Burns tokens from an address.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `caller` - The address of the admin initiating the burn.
    /// * `from` - The address from which to burn tokens.
    /// * `amount` - The amount of tokens to burn.
    pub fn burn(env: Env, caller: Address, from: Address, amount: u64) {
        token::burn(env, caller, from, amount)
    }

    /// Transfers tokens from one address to another.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `from` - The address sending the tokens.
    /// * `to` - The address receiving the tokens.
    /// * `amount` - The amount of tokens to transfer.
    pub fn transfer(env: Env, from: Address, to: Address, amount: u64) {
        token::transfer(env, from, to, amount)
    }

    /// Creates a vesting schedule for token distribution.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `caller` - The address of the admin creating the schedule.
    /// * `recipient` - The address to receive vested tokens.
    /// * `total_amount` - Total token amount to vest.
    /// * `start_time` - Timestamp when vesting begins.
    /// * `duration` - Total duration of vesting in seconds.
    /// * `cliff` - Cliff period in seconds before vesting starts.
    ///
    /// # Returns
    /// The ID of the created vesting schedule.
    pub fn create_vesting_schedule(
        env: Env,
        caller: Address,
        recipient: Address,
        total_amount: u64,
        start_time: u64,
        duration: u64,
        cliff: u64,
    ) -> u32 {
        vesting::create_vesting_schedule(env, caller, recipient, total_amount, start_time, duration, cliff)
    }

    /// Releases vested funds to the recipient.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `caller` - The address requesting the release (must be the recipient).
    /// * `recipient` - The address associated with the vesting schedule.
    /// * `schedule_id` - The ID of the vesting schedule.
    pub fn release_vested_funds(env: Env, caller: Address, recipient: Address, schedule_id: u32) {
        vesting::release_vested_funds(env, caller, recipient, schedule_id)
    }

    /// Creates a new staking position.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `staker` - The address creating the stake.
    /// * `amount` - Amount to stake.
    /// * `duration` - Staking duration in seconds.
    /// * `pool_id` - Reward pool ID.
    /// * `auto_compound` - Whether to auto-compound rewards.
    ///
    /// # Returns
    /// The ID of the created stake.
    pub fn create_stake(
        env: Env,
        staker: Address,
        amount: u64,
        duration: u64,
        pool_id: u32,
        auto_compound: bool,
    ) -> u32 {
        staking::create_stake(env, staker, amount, duration, pool_id, auto_compound)
    }

    /// Claims rewards from a staking position.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `staker` - The address claiming rewards.
    /// * `stake_id` - The ID of the stake.
    ///
    /// # Returns
    /// The amount of rewards claimed.
    pub fn claim_rewards(env: Env, staker: Address, stake_id: u32) -> u64 {
        staking::claim_rewards(env, staker, stake_id)
    }

    /// Unstakes tokens from a staking position.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `staker` - The address unstaking.
    /// * `stake_id` - The ID of the stake.
    ///
    /// # Returns
    /// The total amount returned (principal + rewards).
    pub fn unstake(env: Env, staker: Address, stake_id: u32) -> u64 {
        staking::unstake(env, staker, stake_id)
    }

    /// Compounds rewards for a staking position.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `staker` - The address compounding rewards.
    /// * `stake_id` - The ID of the stake.
    pub fn compound_rewards(env: Env, staker: Address, stake_id: u32) {
        staking::compound_rewards(env, staker, stake_id)
    }

    /// Queries the balance of a given account.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `account` - The address to query.
    ///
    /// # Returns
    /// The token balance of the account.
    pub fn get_balance(env: Env, account: Address) -> u64 {
        token::get_balance(env, account)
    }

    /// Queries the total token supply.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    ///
    /// # Returns
    /// The total token supply.
    pub fn get_total_supply(env: Env) -> u64 {
        token::get_total_supply(env)
    }

    /// Queries a vesting schedule for a recipient and schedule ID.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `recipient` - The address associated with the vesting schedule.
    /// * `schedule_id` - The ID of the vesting schedule.
    ///
    /// # Returns
    /// The vesting schedule details.
    pub fn get_vesting_schedule(env: Env, recipient: Address, schedule_id: u32) -> VestingSchedule {
        vesting::get_vesting_schedule(env, recipient, schedule_id)
    }

    /// Gets stake information.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `staker` - The address of the staker.
    /// * `stake_id` - The ID of the stake.
    ///
    /// # Returns
    /// The stake details.
    pub fn get_stake_info(env: Env, staker: Address, stake_id: u32) -> Stake {
        staking::get_stake_info(env, staker, stake_id)
    }

    /// Gets all stakes for a user.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `staker` - The address of the staker.
    ///
    /// # Returns
    /// Vector of all stakes for the user.
    pub fn get_user_all_stakes(env: Env, staker: Address) -> Vec<Stake> {
        staking::get_user_all_stakes(env, staker)
    }

    /// Gets pending rewards for a stake.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `staker` - The address of the staker.
    /// * `stake_id` - The ID of the stake.
    ///
    /// # Returns
    /// The amount of pending rewards.
    pub fn get_pending_rewards(env: Env, staker: Address, stake_id: u32) -> u64 {
        staking::get_pending_rewards(env, staker, stake_id)
    }

    /// Creates a reward pool (admin only).
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `caller` - The address of the admin.
    /// * `pool` - The reward pool configuration.
    pub fn create_reward_pool(env: Env, caller: Address, pool: RewardPool) {
        admin::create_reward_pool(env, caller, pool)
    }

    /// Updates a reward pool (admin only).
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    /// * `caller` - The address of the admin.
    /// * `pool_id` - The ID of the pool to update.
    /// * `pool` - The updated pool configuration.
    pub fn update_reward_pool(env: Env, caller: Address, pool_id: u32, pool: RewardPool) {
        admin::update_reward_pool(env, caller, pool_id, pool)
    }

    /// Gets staking statistics.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    ///
    /// # Returns
    /// Global staking statistics.
    pub fn get_staking_stats(env: Env) -> StakingStats {
        storage::get_staking_stats(&env)
    }

    /// Gets all reward pools.
    ///
    /// # Arguments
    /// * `env` - The Soroban environment.
    ///
    /// # Returns
    /// Vector of all reward pools.
    pub fn get_reward_pools(env: Env) -> Vec<RewardPool> {
        storage::get_reward_pools(&env)
    }
}