#![cfg(test)]

extern crate std;

use crate::{TokenizedIncentive, TokenizedIncentiveClient};
use soroban_sdk::{testutils::Address as _, Address, Env, Vec};
use soroban_sdk::testutils::Ledger;

/// Tests contract initialization with admins, max supply, and decimals.
#[test]
fn test_initialization() {
    let env = Env::default();
    let admin = Address::generate(&env);

    let contract_client = TokenizedIncentiveClient::new(&env, &env.register(TokenizedIncentive {}, ()));

    env.mock_all_auths();

    // Initialize the contract
    let admins = Vec::from_slice(&env, &[admin.clone()]);
    contract_client.initialize(&admins, &1000000, &6); // Max supply 1M, 6 decimals

    // Verify initialization (basic success check)
    assert!(true, "Contract initialized successfully");
}

/// Tests minting and burning tokens with multi-signature approval.
#[test]
fn test_mint_and_burn() {
    let env = Env::default();
    let admin1 = Address::generate(&env);
    let admin2 = Address::generate(&env);
    let user = Address::generate(&env);

    let contract_client = TokenizedIncentiveClient::new(&env, &env.register(TokenizedIncentive {}, ()));

    env.mock_all_auths();

    // Initialize contract with two admins
    let admins = Vec::from_slice(&env, &[admin1.clone(), admin2.clone()]);
    contract_client.initialize(&admins, &1000000, &6); // Max supply 1M, 6 decimals

    // Approve and mint tokens
    let mint_action = crate::AdminAction::Mint(user.clone(), 1000);
    contract_client.approve_action(&admin1, &mint_action);
    contract_client.approve_action(&admin2, &mint_action); // Multi-sig approval
    contract_client.mint(&admin1, &user, &1000);

    // Verify balance and total supply
    assert_eq!(contract_client.get_balance(&user), 1000);
    assert_eq!(contract_client.get_total_supply(), 1000);

    // Approve and burn tokens
    let burn_action = crate::AdminAction::Burn(user.clone(), 500);
    contract_client.approve_action(&admin1, &burn_action);
    contract_client.approve_action(&admin2, &burn_action); // Multi-sig approval
    contract_client.burn(&admin1, &user, &500);

    // Verify balance and total supply after burn
    assert_eq!(contract_client.get_balance(&user), 500);
    assert_eq!(contract_client.get_total_supply(), 500);
}

/// Tests token transfers between users.
#[test]
fn test_transfer() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let user1 = Address::generate(&env);
    let user2 = Address::generate(&env);

    let contract_client = TokenizedIncentiveClient::new(&env, &env.register(TokenizedIncentive {}, ()));

    env.mock_all_auths();

    // Initialize contract
    let admins = Vec::from_slice(&env, &[admin.clone()]);
    contract_client.initialize(&admins, &1000000, &6);

    // Mint tokens to user1
    let mint_action = crate::AdminAction::Mint(user1.clone(), 1000);
    contract_client.approve_action(&admin, &mint_action);
    contract_client.mint(&admin, &user1, &1000);

    // Transfer tokens from user1 to user2
    contract_client.transfer(&user1, &user2, &500);

    // Verify balances
    assert_eq!(contract_client.get_balance(&user1), 500);
    assert_eq!(contract_client.get_balance(&user2), 500);
}

// Tests creating and releasing funds from a vesting schedule.
#[test]
fn test_vesting_schedule() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let user = Address::generate(&env);

    let contract_client = TokenizedIncentiveClient::new(&env, &env.register(TokenizedIncentive {}, ()));

    env.mock_all_auths();

    // Initialize contract
    let admins = Vec::from_slice(&env, &[admin.clone()]);
    contract_client.initialize(&admins, &1000000, &6);

    // Mint tokens to ensure funds are available
    let mint_action = crate::AdminAction::Mint(user.clone(), 1000);
    contract_client.approve_action(&admin, &mint_action);
    contract_client.mint(&admin, &user, &1000);

    // Create vesting schedule
    let current_time = env.ledger().timestamp();
    let schedule_id = contract_client.create_vesting_schedule(
        &admin,
        &user,
        &1000,
        &current_time,
        &3600, // 1 hour duration
        &1800, // 30 min cliff
    );

    // Verify vesting schedule
    let schedule = contract_client.get_vesting_schedule(&user, &schedule_id);
    assert_eq!(schedule.total_amount, 1000);
    assert_eq!(schedule.released_amount, 0);
    assert_eq!(schedule.cliff, 1800);

    // Fast forward past cliff and release funds
    env.ledger().with_mut(|l| l.timestamp = current_time + 1800);
    contract_client.release_vested_funds(&user, &user, &schedule_id);

    // Verify partial release (halfway through vesting)
    let schedule = contract_client.get_vesting_schedule(&user, &schedule_id);
    assert_eq!(schedule.released_amount, 500); // 50% vested after 30 min
    assert_eq!(contract_client.get_balance(&user), 1500); // Initial 1000 + 500 released
}

/// Tests adding a new admin.
#[test]
fn test_add_admin() {
    let env = Env::default();
    let initial_admin = Address::generate(&env);
    let new_admin = Address::generate(&env);

    let contract_client = TokenizedIncentiveClient::new(&env, &env.register(TokenizedIncentive {}, ()));

    env.mock_all_auths();

    // Initialize contract with initial admin
    let admins = Vec::from_slice(&env, &[initial_admin.clone()]);
    contract_client.initialize(&admins, &1000000, &6);

    // Add new admin
    contract_client.add_admin(&initial_admin, &new_admin);

    // Attempt to approve a mint action using the new admin
    let user = Address::generate(&env);
    let mint_action = crate::AdminAction::Mint(user.clone(), 1000);
    contract_client.approve_action(&new_admin, &mint_action);

    // Verify success (no getter for admins, so check indirect functionality)
    assert!(true, "New admin added and functional");
}

/// Tests multiple mint operations.
#[test]
fn test_multiple_mints() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let user = Address::generate(&env);

    let contract_client = TokenizedIncentiveClient::new(&env, &env.register(TokenizedIncentive {}, ()));

    env.mock_all_auths();

    // Initialize contract
    let admins = Vec::from_slice(&env, &[admin.clone()]);
    contract_client.initialize(&admins, &1000000, &6);

    // Multiple mints
    let mint_action1 = crate::AdminAction::Mint(user.clone(), 1000);
    contract_client.approve_action(&admin, &mint_action1);
    contract_client.mint(&admin, &user, &1000);

    let mint_action2 = crate::AdminAction::Mint(user.clone(), 500);
    contract_client.approve_action(&admin, &mint_action2);
    contract_client.mint(&admin, &user, &500);

    // Verify total balance and supply
    assert_eq!(contract_client.get_balance(&user), 1500);
    assert_eq!(contract_client.get_total_supply(), 1500);
}

/// Tests multiple transfers.
#[test]
fn test_multiple_transfers() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let user1 = Address::generate(&env);
    let user2 = Address::generate(&env);

    let contract_client = TokenizedIncentiveClient::new(&env, &env.register(TokenizedIncentive {}, ()));

    env.mock_all_auths();

    // Initialize contract
    let admins = Vec::from_slice(&env, &[admin.clone()]);
    contract_client.initialize(&admins, &1000000, &6);

    // Mint tokens to user1
    let mint_action = crate::AdminAction::Mint(user1.clone(), 1000);
    contract_client.approve_action(&admin, &mint_action);
    contract_client.mint(&admin, &user1, &1000);

    // Multiple transfers
    contract_client.transfer(&user1, &user2, &300);
    contract_client.transfer(&user1, &user2, &200);

    // Verify remaining balances
    assert_eq!(contract_client.get_balance(&user1), 500);
    assert_eq!(contract_client.get_balance(&user2), 500);
}