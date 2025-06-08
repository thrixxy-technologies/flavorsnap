use crate::admin::*;
use crate::types::*;
use soroban_sdk::{Address, Env};

/// Mints new tokens to a recipient after multi-signature approval.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `caller` - The address of the admin initiating the mint.
/// * `to` - The address to receive the minted tokens.
/// * `amount` - The amount of tokens to mint.
pub fn mint(env: Env, caller: Address, to: Address, amount: u64) {
    caller.require_auth();
    check_admin(&env, &caller);

    let action = AdminAction::Mint(to.clone(), amount);
    if !require_multi_sig(&env, &action) {
        panic!("Multi-signature approval required for minting");
    }

    let max_supply: u64 = env.storage().instance().get(&DataKey::MaxSupply).unwrap();
    let total_supply: u64 = env.storage().instance().get(&DataKey::TotalSupply).unwrap();
    if total_supply + amount > max_supply {
        panic!("Minting would exceed max supply");
    }

    let mut balance: u64 = env
        .storage()
        .instance()
        .get(&DataKey::Balances(to.clone()))
        .unwrap_or(0);
    balance += amount;
    env.storage().instance().set(&DataKey::Balances(to), &balance);

    let new_supply = total_supply + amount;
    env.storage().instance().set(&DataKey::TotalSupply, &new_supply);
}

/// Burns tokens from an address after multi-signature approval.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `caller` - The address of the admin initiating the burn.
/// * `from` - The address from which to burn tokens.
/// * `amount` - The amount of tokens to burn.
pub fn burn(env: Env, caller: Address, from: Address, amount: u64) {
    caller.require_auth();
    check_admin(&env, &caller);

    let action = AdminAction::Burn(from.clone(), amount);
    if !require_multi_sig(&env, &action) {
        panic!("Multi-signature approval required for burning");
    }

    let mut balance: u64 = env
        .storage()
        .instance()
        .get(&DataKey::Balances(from.clone()))
        .unwrap_or(0);
    if balance < amount {
        panic!("Insufficient balance to burn");
    }

    balance -= amount;
    env.storage().instance().set(&DataKey::Balances(from), &balance);

    let total_supply: u64 = env.storage().instance().get(&DataKey::TotalSupply).unwrap();
    let new_supply = total_supply - amount;
    env.storage().instance().set(&DataKey::TotalSupply, &new_supply);
}

/// Transfers tokens from one address to another.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `from` - The address sending the tokens.
/// * `to` - The address receiving the tokens.
/// * `amount` - The amount of tokens to transfer.
pub fn transfer(env: Env, from: Address, to: Address, amount: u64) {
    from.require_auth();

    let mut from_balance: u64 = env
        .storage()
        .instance()
        .get(&DataKey::Balances(from.clone()))
        .unwrap_or(0);
    if from_balance < amount {
        panic!("Insufficient balance for transfer");
    }

    from_balance -= amount;
    let mut to_balance: u64 = env
        .storage()
        .instance()
        .get(&DataKey::Balances(to.clone()))
        .unwrap_or(0);
    to_balance += amount;

    env.storage().instance().set(&DataKey::Balances(from), &from_balance);
    env.storage().instance().set(&DataKey::Balances(to), &to_balance);
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
    env.storage()
        .instance()
        .get(&DataKey::Balances(account))
        .unwrap_or(0)
}

/// Queries the total token supply.
///
/// # Arguments
/// * `env` - The Soroban environment.
///
/// # Returns
/// The total token supply.
pub fn get_total_supply(env: Env) -> u64 {
    env.storage().instance().get(&DataKey::TotalSupply).unwrap_or(0)
}