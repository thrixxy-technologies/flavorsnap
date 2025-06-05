use crate::types::*;
use soroban_sdk::{Address, Env, Vec, String};

pub fn initialize(env: Env, admins: Vec<Address>, token_name: String, token_symbol: String, max_supply: u128, decimals: u32) {
    if admins.is_empty() {
        panic!("At least one admin required");
    }
    for admin in admins.iter() {
        admin.require_auth();
    }

    // Initialize storage
    env.storage().instance().set(&DataKey::Admins, &admins);
    env.storage().instance().set(&DataKey::TokenName, &token_name);
    env.storage().instance().set(&DataKey::TokenSymbol, &token_symbol);
    env.storage().instance().set(&DataKey::MaxSupply, &max_supply);
    env.storage().instance().set(&DataKey::Decimals, &decimals);
    env.storage().instance().set(&DataKey::TotalSupply, &0u128);
    env.storage().instance().set(&DataKey::NextStakeId, &1u32);
}

pub fn is_admin(env: &Env, caller: &Address) -> bool {
    let admins: Vec<Address> = env.storage().instance().get(&DataKey::Admins).unwrap_or_else(|| Vec::new(env));
    admins.contains(caller)
}

pub fn add_admin(env: Env, caller: Address, new_admin: Address) {
    caller.require_auth();
    if !is_admin(&env, &caller) {
        panic!("Only admins can add admins");
    }
    let mut admins: Vec<Address> = env.storage().instance().get(&DataKey::Admins).unwrap();
    if admins.contains(&new_admin) {
        panic!("Admin already exists");
    }
    admins.push_back(new_admin);
    env.storage().instance().set(&DataKey::Admins, &admins);
}

pub fn remove_admin(env: Env, caller: Address, admin: Address) {
    caller.require_auth();
    if !is_admin(&env, &caller) {
        panic!("Only admins can remove admins");
    }
    let admins: Vec<Address> = env.storage().instance().get(&DataKey::Admins).unwrap();
    if admins.len() <= 1 {
        panic!("Cannot remove last admin");
    }
    let mut new_admins: Vec<Address> = Vec::new(&env);
    for a in admins.iter() {
        if a != admin {
            new_admins.push_back(a);
        }
    }
    env.storage().instance().set(&DataKey::Admins, &new_admins);
}

pub fn get_admins(env: Env) -> Vec<Address> {
    env.storage().instance().get(&DataKey::Admins).unwrap_or_else(|| Vec::new(&env))
}