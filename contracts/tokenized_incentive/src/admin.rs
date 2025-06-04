use crate::types::*;
use soroban_sdk::{Address, Env, Vec};

/// Initializes the contract with admin addresses, max supply, and token decimals.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `admins` - Vector of admin addresses.
/// * `max_supply` - Maximum token supply limit.
/// * `decimals` - Number of decimal places for token precision.
pub fn initialize(env: Env, admins: Vec<Address>, max_supply: u64, decimals: u32) {
    if admins.is_empty() {
        panic!("At least one admin required");
    }
    for admin in admins.iter() {
        admin.require_auth();
    }

    // Initialize storage
    env.storage().instance().set(&DataKey::Admins, &admins);
    env.storage().instance().set(&DataKey::MaxSupply, &max_supply);
    env.storage().instance().set(&DataKey::Decimals, &decimals);
    env.storage().instance().set(&DataKey::TotalSupply, &0u64);
    env.storage().instance().set(&DataKey::NextScheduleId, &0u32);
}

/// Adds a new admin to the contract.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `caller` - The address of the caller (must be an existing admin).
/// * `new_admin` - The address of the new admin to add.
pub fn add_admin(env: Env, caller: Address, new_admin: Address) {
    caller.require_auth();
    check_admin(&env, &caller);

    let mut admins: Vec<Address> = env.storage().instance().get(&DataKey::Admins).unwrap();
    if admins.contains(&new_admin) {
        panic!("Admin already exists");
    }
    admins.push_back(new_admin);
    env.storage().instance().set(&DataKey::Admins, &admins);
}

/// Checks if the caller is an authorized admin.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `caller` - The address to check.
///
/// # Returns
/// True if the caller is an admin, false otherwise.
pub fn check_admin(env: &Env, caller: &Address) -> bool {
    let admins: Vec<Address> = env.storage().instance().get(&DataKey::Admins).unwrap();
    admins.contains(caller)
}

/// Compares two AdminAction instances for equality.
///
/// # Arguments
/// * `a` - First admin action to compare.
/// * `b` - Second admin action to compare.
///
/// # Returns
/// True if the actions are equivalent, false otherwise.
fn compare_actions(a: &AdminAction, b: &AdminAction) -> bool {
    match (a, b) {
        (AdminAction::Mint(addr1, amt1), AdminAction::Mint(addr2, amt2)) => {
            addr1 == addr2 && amt1 == amt2
        }
        (AdminAction::Burn(addr1, amt1), AdminAction::Burn(addr2, amt2)) => {
            addr1 == addr2 && amt1 == amt2
        }
        _ => false,
    }
}

/// Checks if an admin action has received enough approvals for multi-signature.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `action` - The admin action to check.
///
/// # Returns
/// True if the action has majority approval, false otherwise.
pub fn require_multi_sig(env: &Env, action: &AdminAction) -> bool {
    let admins: Vec<Address> = env.storage().instance().get(&DataKey::Admins).unwrap();
    let required_approvals = admins.len() / 2 + 1; // Majority required

    let approvals: Vec<Approval> = env
        .storage()
        .instance()
        .get(&DataKey::AdminApprovals)
        .unwrap_or_else(|| Vec::new(env));
    
    for i in 0..approvals.len() {
        let approval = approvals.get(i).unwrap();
        if compare_actions(&approval.action, action) {
            return approval.approvals >= required_approvals as u32;
        }
    }
    false
}

/// Approves an admin action as part of multi-signature process.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `caller` - The address of the admin approving the action.
/// * `action` - The admin action to approve.
pub fn approve_action(env: Env, caller: Address, action: AdminAction) {
    caller.require_auth();
    check_admin(&env, &caller);

    let mut approvals: Vec<Approval> = env
        .storage()
        .instance()
        .get(&DataKey::AdminApprovals)
        .unwrap_or_else(|| Vec::new(&env));

    let mut found = false;
    for i in 0..approvals.len() {
        let mut approval = approvals.get(i).unwrap();
        if compare_actions(&approval.action, &action) {
            approval.approvals += 1;
            approvals.set(i, approval);
            found = true;
            break;
        }
    }
    if !found {
        approvals.push_back(Approval {
            action,
            approvals: 1,
        });
    }
    env.storage().instance().set(&DataKey::AdminApprovals, &approvals);
}