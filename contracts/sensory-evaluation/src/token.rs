use crate::types::*;
use soroban_sdk::{Address, Env, Map};

pub fn mint_tokens(env: Env, caller: Address, to: Address, amount: u128) {
    caller.require_auth();
    if !crate::admin::is_admin(&env, &caller) {
        panic!("Only admins can mint tokens");
    }

    let max_supply: u128 = env.storage().instance().get(&DataKey::MaxSupply).unwrap();
    let mut total_supply: u128 = env.storage().instance().get(&DataKey::TotalSupply).unwrap_or(0);
    if total_supply + amount > max_supply {
        panic!("Minting would exceed max supply");
    }

    // Update balance
    let mut balances: Map<Address, u128> = env.storage().instance().get(&DataKey::Balances(to.clone())).unwrap_or_else(|| Map::new(&env));
    let current_balance = balances.get(to.clone()).unwrap_or(0);
    balances.set(to.clone(), current_balance + amount);
    env.storage().instance().set(&DataKey::Balances(to), &balances);

    // Update total supply
    total_supply += amount;
    env.storage().instance().set(&DataKey::TotalSupply, &total_supply);
}

pub fn burn_tokens(env: Env, caller: Address, from: Address, amount: u128) {
    caller.require_auth();
    if !crate::admin::is_admin(&env, &caller) {
        panic!("Only admins can burn tokens");
    }

    // Check balance
    let mut balances: Map<Address, u128> = env.storage().instance().get(&DataKey::Balances(from.clone())).unwrap_or_else(|| Map::new(&env));
    let current_balance = balances.get(from.clone()).unwrap_or(0);
    if current_balance < amount {
        panic!("Insufficient balance to burn");
    }

    // Update balance
    balances.set(from.clone(), current_balance - amount);
    env.storage().instance().set(&DataKey::Balances(from), &balances);

    // Update total supply
    let mut total_supply: u128 = env.storage().instance().get(&DataKey::TotalSupply).unwrap();
    total_supply -= amount;
    env.storage().instance().set(&DataKey::TotalSupply, &total_supply);
}

pub fn transfer_tokens(env: Env, from: Address, to: Address, amount: u128) {
    from.require_auth();

    // Check balance
    let mut balances: Map<Address, u128> = env.storage().instance().get(&DataKey::Balances(from.clone())).unwrap_or_else(|| Map::new(&env));
    let current_balance = balances.get(from.clone()).unwrap_or(0);
    if current_balance < amount {
        panic!("Insufficient balance to transfer");
    }

    // Update sender balance
    balances.set(from.clone(), current_balance - amount);
    env.storage().instance().set(&DataKey::Balances(from), &balances);

    // Update receiver balance
    let mut receiver_balances: Map<Address, u128> = env.storage().instance().get(&DataKey::Balances(to.clone())).unwrap_or_else(|| Map::new(&env));
    let receiver_balance = receiver_balances.get(to.clone()).unwrap_or(0);
    receiver_balances.set(to.clone(), receiver_balance + amount);
    env.storage().instance().set(&DataKey::Balances(to), &receiver_balances);
}

pub fn get_balance(env: Env, user: Address) -> u128 {
    let balances: Map<Address, u128> = env.storage().instance().get(&DataKey::Balances(user.clone())).unwrap_or_else(|| Map::new(&env));
    balances.get(user).unwrap_or(0)
}

pub fn get_total_supply(env: Env) -> u128 {
    env.storage().instance().get(&DataKey::TotalSupply).unwrap_or(0)
}