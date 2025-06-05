use crate::types::*;
use soroban_sdk::{Address, Env, Map, Vec};

pub fn stake_tokens(env: Env, staker: Address, amount: u128, duration: u64) {
    staker.require_auth();

    // Check balance
    let mut balances: Map<Address, u128> = env.storage().instance().get(&DataKey::Balances(staker.clone())).unwrap_or_else(|| Map::new(&env));
    let current_balance = balances.get(staker.clone()).unwrap_or(0);
    if current_balance < amount {
        panic!("Insufficient balance to stake");
    }

    // Update balance
    balances.set(staker.clone(), current_balance - amount);
    env.storage().instance().set(&DataKey::Balances(staker.clone()), &balances);

    // Create stake
    let stake_id = env.storage().instance().get(&DataKey::NextStakeId).unwrap_or(1u32);
    let stake = Stake {
        id: stake_id,
        amount,
        start_time: env.ledger().timestamp(),
        duration,
        claimed: false,
    };

    // Store stake
    let mut stakes: Vec<Stake> = env.storage().instance().get(&DataKey::Stakes(staker.clone())).unwrap_or_else(|| Vec::new(&env));
    stakes.push_back(stake);
    env.storage().instance().set(&DataKey::Stakes(staker.clone()), &stakes);

    // Increment stake ID
    env.storage().instance().set(&DataKey::NextStakeId, &(stake_id + 1));
}

pub fn unstake_tokens(env: Env, staker: Address, stake_id: u32) {
    staker.require_auth();

    // Get stakes
    let mut stakes: Vec<Stake> = env.storage().instance().get(&DataKey::Stakes(staker.clone())).unwrap_or_else(|| Vec::new(&env));
    let mut stake = stakes.get(stake_id).unwrap_or_else(|| panic!("Stake not found"));

    // Check if stake is claimable
    let current_time = env.ledger().timestamp();
    if current_time < stake.start_time + stake.duration {
        panic!("Stake is still locked");
    }
    if stake.claimed {
        panic!("Stake already claimed");
    }

    // Mark as claimed
    stake.claimed = true;
    stakes.set(stake_id, stake.clone());
    env.storage().instance().set(&DataKey::Stakes(staker.clone()), &stakes);

    // Return tokens to balance
    let mut balances: Map<Address, u128> = env.storage().instance().get(&DataKey::Balances(staker.clone())).unwrap_or_else(|| Map::new(&env));
    let current_balance = balances.get(staker.clone()).unwrap_or(0);
    balances.set(staker.clone(), current_balance + stake.amount);
    env.storage().instance().set(&DataKey::Balances(staker), &balances);
}

pub fn get_stakes(env: Env, user: Address) -> Vec<Stake> {
    env.storage().instance().get(&DataKey::Stakes(user)).unwrap_or_else(|| Vec::new(&env))
}