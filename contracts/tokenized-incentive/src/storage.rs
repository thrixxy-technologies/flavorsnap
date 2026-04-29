use crate::types::*;
use soroban_sdk::{Address, Env, Vec};

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

/// Gets the next stake ID
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

/// Gets the next vesting schedule ID
pub fn next_schedule_id(env: &Env) -> u32 {
    let id: u32 = env
        .storage()
        .instance()
        .get(&DataKey::NextScheduleId)
        .unwrap_or(1u32);
    env.storage()
        .instance()
        .set(&DataKey::NextScheduleId, &(id + 1));
    id
}

/// Gets token balance for an address
pub fn get_balance(env: &Env, address: &Address) -> u64 {
    env.storage()
        .instance()
        .get(&DataKey::Balances(address.clone()))
        .unwrap_or(0)
}

/// Sets token balance for an address
pub fn set_balance(env: &Env, address: &Address, balance: u64) {
    env.storage()
        .instance()
        .set(&DataKey::Balances(address.clone()), &balance);
}

/// Gets total token supply
pub fn get_total_supply(env: &Env) -> u64 {
    env.storage()
        .instance()
        .get(&DataKey::TotalSupply)
        .unwrap_or(0)
}

/// Sets total token supply
pub fn set_total_supply(env: &Env, supply: u64) {
    env.storage().instance().set(&DataKey::TotalSupply, &supply);
}

/// Gets maximum token supply
pub fn get_max_supply(env: &Env) -> u64 {
    env.storage()
        .instance()
        .get(&DataKey::MaxSupply)
        .unwrap_or(0)
}

/// Sets maximum token supply
pub fn set_max_supply(env: &Env, max_supply: u64) {
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

/// Gets reward pools
pub fn get_reward_pools(env: &Env) -> Vec<RewardPool> {
    env.storage()
        .instance()
        .get(&DataKey::RewardPools)
        .unwrap_or_else(|| Vec::new(env))
}

/// Sets reward pools
pub fn set_reward_pools(env: &Env, pools: &Vec<RewardPool>) {
    env.storage().instance().set(&DataKey::RewardPools, pools);
}

/// Gets user rewards
pub fn get_user_rewards(env: &Env, user: &Address) -> Vec<UserReward> {
    env.storage()
        .instance()
        .get(&DataKey::UserRewards(user.clone()))
        .unwrap_or_else(|| Vec::new(env))
}

/// Sets user rewards
pub fn set_user_rewards(env: &Env, user: &Address, rewards: &Vec<UserReward>) {
    env.storage()
        .instance()
        .set(&DataKey::UserRewards(user.clone()), rewards);
}

/// Gets staking statistics
pub fn get_staking_stats(env: &Env) -> StakingStats {
    env.storage()
        .instance()
        .get(&DataKey::StakingStats)
        .unwrap_or_else(|| StakingStats {
            total_staked: 0,
            total_stakers: 0,
            average_stake_duration: 0,
            total_rewards_distributed: 0,
            last_stats_update: 0,
        })
}

/// Sets staking statistics
pub fn set_staking_stats(env: &Env, stats: &StakingStats) {
    env.storage().instance().set(&DataKey::StakingStats, stats);
}

/// Gets vesting schedule
pub fn get_vesting_schedule(env: &Env, recipient: &Address, schedule_id: u32) -> Option<VestingSchedule> {
    env.storage()
        .instance()
        .get(&DataKey::VestingSchedules(recipient.clone(), schedule_id))
}

/// Sets vesting schedule
pub fn set_vesting_schedule(env: &Env, recipient: &Address, schedule_id: u32, schedule: &VestingSchedule) {
    env.storage()
        .instance()
        .set(&DataKey::VestingSchedules(recipient.clone(), schedule_id), schedule);
}

/// Gets admin approval
pub fn get_admin_approval(env: &Env, action: &AdminAction) -> Option<Approval> {
    env.storage()
        .instance()
        .get(&DataKey::AdminApprovals)
        .and_then(|approvals: Vec<Approval>| {
            approvals.iter().find(|a| a.action == *action.clone()).cloned()
        })
}

/// Sets admin approval
pub fn set_admin_approval(env: &Env, approval: &Approval) {
    let mut approvals: Vec<Approval> = env
        .storage()
        .instance()
        .get(&DataKey::AdminApprovals)
        .unwrap_or_else(|| Vec::new(env));
    
    // Remove existing approval for the same action if it exists
    approvals = approvals
        .iter()
        .filter(|a| a.action != approval.action)
        .cloned()
        .collect();
    
    approvals.push_back(approval.clone());
    env.storage().instance().set(&DataKey::AdminApprovals, &approvals);
}

/// Gets contract version
pub fn get_contract_version(env: &Env) -> u32 {
    env.storage().instance().get(&DataKey::ContractVersion).unwrap_or(1)
}

/// Sets contract version
pub fn set_contract_version(env: &Env, version: u32) {
    env.storage().instance().set(&DataKey::ContractVersion, &version);
}

/// Calculates staking tier based on amount and duration
pub fn calculate_staking_tier(amount: u64, duration: u64) -> StakingTier {
    let stake_amount_score = amount / 1_000_000; // 1M tokens = 1 point
    let duration_score = duration / (86400 * 30); // 30 days = 1 point
    let total_score = stake_amount_score + duration_score;
    
    match total_score {
        0..=9 => StakingTier::Bronze,
        10..=24 => StakingTier::Silver,
        25..=49 => StakingTier::Gold,
        _ => StakingTier::Platinum,
    }
}

/// Gets reward multiplier for tier and duration
pub fn get_reward_multiplier(tier: StakingTier, duration: u64) -> u32 {
    let base_multiplier = match tier {
        StakingTier::Bronze => 100,    // 1.0x
        StakingTier::Silver => 125,    // 1.25x
        StakingTier::Gold => 150,      // 1.5x
        StakingTier::Platinum => 200,  // 2.0x
    };
    
    // Duration bonus: +10% for 6+ months, +20% for 12+ months
    let duration_bonus = if duration >= 86400 * 365 {
        20  // +20%
    } else if duration >= 86400 * 180 {
        10  // +10%
    } else {
        0
    };
    
    base_multiplier + duration_bonus
}

/// Updates global staking statistics
pub fn update_staking_stats(env: &Env) {
    let mut stats = get_staking_stats(env);
    let current_time = env.ledger().timestamp();
    
    // Recalculate total staked and stakers
    let mut total_staked = 0u64;
    let mut total_stakers = 0u32;
    let mut total_duration = 0u64;
    
    // This would typically iterate through all users, but for efficiency
    // we'll update incrementally when stakes are created/removed
    
    stats.last_stats_update = current_time;
    set_staking_stats(env, &stats);
}

/// Calculates pending rewards for a stake
pub fn calculate_pending_rewards(env: &Env, stake: &Stake, pool: &RewardPool) -> u64 {
    let current_time = env.ledger().timestamp();
    let time_elapsed = current_time - stake.last_claim_time;
    
    if time_elapsed == 0 {
        return 0;
    }
    
    // Base reward calculation
    let base_rewards = (stake.amount * pool.reward_rate as u64 * time_elapsed) / (10000 * 86400);
    
    // Apply staking tier multiplier
    let tier = calculate_staking_tier(stake.amount, stake.duration);
    let multiplier = get_reward_multiplier(tier, stake.duration);
    
    (base_rewards * multiplier as u64) / 100
}
