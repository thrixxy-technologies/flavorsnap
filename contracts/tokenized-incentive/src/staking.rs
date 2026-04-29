use crate::storage::*;
use crate::types::*;
use soroban_sdk::{Address, Env, Vec};

/// Creates a new staking position
pub fn create_stake(
    env: Env,
    staker: Address,
    amount: u64,
    duration: u64,
    pool_id: u32,
    auto_compound: bool,
) -> u32 {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    staker.require_auth();
    
    if amount == 0 {
        panic!("Stake amount must be greater than 0");
    }
    
    if duration < 86400 {
        panic!("Stake duration must be at least 1 day");
    }
    
    // Check user balance
    let balance = get_balance(&env, &staker);
    if balance < amount {
        panic!("Insufficient balance for staking");
    }
    
    // Get reward pool
    let pools = get_reward_pools(&env);
    let pool = pools
        .iter()
        .find(|p| p.id == pool_id && p.active)
        .cloned()
        .unwrap_or_else(|| panic!("Invalid or inactive reward pool"));
    
    // Check pool limits
    if amount < pool.min_stake || amount > pool.max_stake {
        panic!("Stake amount outside pool limits");
    }
    
    // Create stake
    let stake_id = next_stake_id(&env);
    let current_time = env.ledger().timestamp();
    let tier = calculate_staking_tier(amount, duration);
    let multiplier = get_reward_multiplier(tier, duration);
    
    let stake = Stake {
        id: stake_id,
        staker: staker.clone(),
        amount,
        start_time: current_time,
        duration,
        reward_rate: pool.reward_rate,
        lock_period: duration, // Full duration as lock period
        auto_compound,
        last_claim_time: current_time,
        total_rewards: 0,
    };
    
    // Update user stakes
    let mut user_stakes = get_user_stakes(&env, &staker);
    user_stakes.push_back(stake.clone());
    set_user_stakes(&env, &staker, &user_stakes);
    
    // Create user reward tracking
    let user_reward = UserReward {
        stake_id,
        pool_id,
        pending_rewards: 0,
        claimed_rewards: 0,
        last_update: current_time,
    };
    
    let mut user_rewards = get_user_rewards(&env, &staker);
    user_rewards.push_back(user_reward);
    set_user_rewards(&env, &staker, &user_rewards);
    
    // Deduct balance
    set_balance(&env, &staker, balance - amount);
    
    // Update staking stats
    update_staking_stats(&env);
    
    stake_id
}

/// Claims rewards from a staking position
pub fn claim_rewards(env: Env, staker: Address, stake_id: u32) -> u64 {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    staker.require_auth();
    
    // Get stake
    let user_stakes = get_user_stakes(&env, &staker);
    let stake = user_stakes
        .iter()
        .find(|s| s.id == stake_id)
        .cloned()
        .unwrap_or_else(|| panic!("Stake not found"));
    
    // Get user reward
    let mut user_rewards = get_user_rewards(&env, &staker);
    let user_reward_index = user_rewards
        .iter()
        .position(|r| r.stake_id == stake_id)
        .unwrap_or_else(|| panic!("Reward tracking not found"));
    
    let mut user_reward = user_rewards.get(user_reward_index).unwrap().clone();
    
    // Get reward pool
    let pools = get_reward_pools(&env);
    let pool = pools
        .iter()
        .find(|p| p.id == user_reward.pool_id)
        .cloned()
        .unwrap_or_else(|| panic!("Reward pool not found"));
    
    // Calculate pending rewards
    let pending_rewards = calculate_pending_rewards(&env, &stake, &pool);
    let total_rewards = user_reward.pending_rewards + pending_rewards;
    
    if total_rewards == 0 {
        return 0;
    }
    
    // Update user reward tracking
    user_reward.pending_rewards = 0;
    user_reward.claimed_rewards += total_rewards;
    user_reward.last_update = env.ledger().timestamp();
    user_rewards.set(user_reward_index, user_reward.clone());
    set_user_rewards(&env, &staker, &user_rewards);
    
    // Update stake
    let mut updated_stakes = user_stakes;
    let stake_index = updated_stakes.iter().position(|s| s.id == stake_id).unwrap();
    let mut updated_stake = updated_stakes.get(stake_index).unwrap().clone();
    updated_stake.last_claim_time = env.ledger().timestamp();
    updated_stake.total_rewards += total_rewards;
    updated_stakes.set(stake_index, updated_stake);
    set_user_stakes(&env, &staker, &updated_stakes);
    
    // Mint rewards to user
    let current_balance = get_balance(&env, &staker);
    set_balance(&env, &staker, current_balance + total_rewards);
    
    // Update total supply
    let current_supply = get_total_supply(&env);
    set_total_supply(&env, current_supply + total_rewards);
    
    // Update pool distributed rewards
    let mut updated_pools = pools;
    let pool_index = updated_pools.iter().position(|p| p.id == user_reward.pool_id).unwrap();
    let mut updated_pool = updated_pools.get(pool_index).unwrap().clone();
    updated_pool.distributed += total_rewards;
    updated_pools.set(pool_index, updated_pool);
    set_reward_pools(&env, &updated_pools);
    
    // Update staking stats
    let mut stats = get_staking_stats(&env);
    stats.total_rewards_distributed += total_rewards;
    set_staking_stats(&env, &stats);
    
    total_rewards
}

/// Unstakes tokens from a staking position
pub fn unstake(env: Env, staker: Address, stake_id: u32) -> u64 {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    staker.require_auth();
    
    // Get stake
    let user_stakes = get_user_stakes(&env, &staker);
    let stake = user_stakes
        .iter()
        .find(|s| s.id == stake_id)
        .cloned()
        .unwrap_or_else(|| panic!("Stake not found"));
    
    let current_time = env.ledger().timestamp();
    
    // Check if lock period has passed
    if current_time < stake.start_time + stake.lock_period {
        panic!("Stake is still locked");
    }
    
    // Claim any pending rewards first
    let rewards_claimed = claim_rewards(env.clone(), staker.clone(), stake_id);
    
    // Remove stake from user stakes
    let mut updated_stakes = user_stakes;
    let stake_index = updated_stakes.iter().position(|s| s.id == stake_id).unwrap();
    updated_stakes.remove(stake_index);
    set_user_stakes(&env, &staker, &updated_stakes);
    
    // Remove reward tracking
    let mut user_rewards = get_user_rewards(&env, &staker);
    let reward_index = user_rewards
        .iter()
        .position(|r| r.stake_id == stake_id);
    if let Some(index) = reward_index {
        user_rewards.remove(index);
        set_user_rewards(&env, &staker, &user_rewards);
    }
    
    // Return staked amount to user
    let current_balance = get_balance(&env, &staker);
    set_balance(&env, &staker, current_balance + stake.amount);
    
    // Update staking stats
    update_staking_stats(&env);
    
    stake.amount + rewards_claimed
}

/// Compounds rewards for a staking position
pub fn compound_rewards(env: Env, staker: Address, stake_id: u32) {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    staker.require_auth();
    
    // Get stake
    let user_stakes = get_user_stakes(&env, &staker);
    let stake = user_stakes
        .iter()
        .find(|s| s.id == stake_id)
        .cloned()
        .unwrap_or_else(|| panic!("Stake not found"));
    
    if !stake.auto_compound {
        panic!("Auto-compound not enabled for this stake");
    }
    
    // Get user reward
    let mut user_rewards = get_user_rewards(&env, &staker);
    let user_reward_index = user_rewards
        .iter()
        .position(|r| r.stake_id == stake_id)
        .unwrap_or_else(|| panic!("Reward tracking not found"));
    
    let mut user_reward = user_rewards.get(user_reward_index).unwrap().clone();
    
    // Get reward pool
    let pools = get_reward_pools(&env);
    let pool = pools
        .iter()
        .find(|p| p.id == user_reward.pool_id)
        .cloned()
        .unwrap_or_else(|| panic!("Reward pool not found"));
    
    // Calculate pending rewards
    let pending_rewards = calculate_pending_rewards(&env, &stake, &pool);
    
    if pending_rewards == 0 {
        return;
    }
    
    // Add rewards to stake amount
    let mut updated_stakes = user_stakes;
    let stake_index = updated_stakes.iter().position(|s| s.id == stake_id).unwrap();
    let mut updated_stake = updated_stakes.get(stake_index).unwrap().clone();
    updated_stake.amount += pending_rewards;
    updated_stake.last_claim_time = env.ledger().timestamp();
    updated_stake.total_rewards += pending_rewards;
    updated_stakes.set(stake_index, updated_stake);
    set_user_stakes(&env, &staker, &updated_stakes);
    
    // Update reward tracking
    user_reward.pending_rewards = 0;
    user_reward.last_update = env.ledger().timestamp();
    user_rewards.set(user_reward_index, user_reward);
    set_user_rewards(&env, &staker, &user_rewards);
    
    // Update pool distributed rewards
    let mut updated_pools = pools;
    let pool_index = updated_pools.iter().position(|p| p.id == user_reward.pool_id).unwrap();
    let mut updated_pool = updated_pools.get(pool_index).unwrap().clone();
    updated_pool.distributed += pending_rewards;
    updated_pools.set(pool_index, updated_pool);
    set_reward_pools(&env, &updated_pools);
    
    // Update staking stats
    let mut stats = get_staking_stats(&env);
    stats.total_rewards_distributed += pending_rewards;
    set_staking_stats(&env, &stats);
}

/// Gets stake information
pub fn get_stake_info(env: Env, staker: Address, stake_id: u32) -> Stake {
    let user_stakes = get_user_stakes(&env, &staker);
    user_stakes
        .iter()
        .find(|s| s.id == stake_id)
        .cloned()
        .unwrap_or_else(|| panic!("Stake not found"))
}

/// Gets all stakes for a user
pub fn get_user_all_stakes(env: Env, staker: Address) -> Vec<Stake> {
    get_user_stakes(&env, &staker)
}

/// Gets pending rewards for a stake
pub fn get_pending_rewards(env: Env, staker: Address, stake_id: u32) -> u64 {
    // Get stake
    let user_stakes = get_user_stakes(&env, &staker);
    let stake = user_stakes
        .iter()
        .find(|s| s.id == stake_id)
        .cloned()
        .unwrap_or_else(|| panic!("Stake not found"));
    
    // Get user reward
    let user_rewards = get_user_rewards(&env, &staker);
    let user_reward = user_rewards
        .iter()
        .find(|r| r.stake_id == stake_id)
        .cloned()
        .unwrap_or_else(|| panic!("Reward tracking not found"));
    
    // Get reward pool
    let pools = get_reward_pools(&env);
    let pool = pools
        .iter()
        .find(|p| p.id == user_reward.pool_id)
        .cloned()
        .unwrap_or_else(|| panic!("Reward pool not found"));
    
    // Calculate pending rewards
    let calculated_rewards = calculate_pending_rewards(&env, &stake, &pool);
    user_reward.pending_rewards + calculated_rewards
}
