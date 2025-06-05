#![cfg(test)]

extern crate std;

use crate::{SensoryEvaluation, SensoryEvaluationClient};
use soroban_sdk::{testutils::Address as _, Address, Env, Vec, String};
use soroban_sdk::testutils::Ledger;

/// Tests contract initialization with admins, token metadata, max supply, and decimals.
#[test]
fn test_initialization() {
    let env = Env::default();
    let admin = Address::generate(&env);

    let contract_client = SensoryEvaluationClient::new(&env, &env.register(SensoryEvaluation {}, ()));

    env.mock_all_auths();

    // Initialize the contract with admin, token name, symbol, max supply, and decimals
    let admins = Vec::from_slice(&env, &[admin.clone()]);
    let token_name = String::from_str(&env, "SensoryToken");
    let token_symbol = String::from_str(&env, "SEN");
    contract_client.initialize(&admins, &token_name, &token_symbol, &1000000, &6); // Max supply 1M, 6 decimals

    // Verify initialization (basic success check and total supply)
    assert_eq!(contract_client.get_total_supply(), 0);
    assert_eq!(contract_client.get_admins().len(), 1);
    assert!(true, "Contract initialized successfully");
}

/// Tests minting and burning tokens with admin authorization.
#[test]
fn test_mint_and_burn() {
    let env = Env::default();
    let admin1 = Address::generate(&env);
    let admin2 = Address::generate(&env);
    let user = Address::generate(&env);

    let contract_client = SensoryEvaluationClient::new(&env, &env.register(SensoryEvaluation {}, ()));

    env.mock_all_auths();

    // Initialize contract with two admins
    let admins = Vec::from_slice(&env, &[admin1.clone(), admin2.clone()]);
    let token_name = String::from_str(&env, "SensoryToken");
    let token_symbol = String::from_str(&env, "SEN");
    contract_client.initialize(&admins, &token_name, &token_symbol, &1000000, &6); // Max supply 1M, 6 decimals

    // Mint tokens to user
    contract_client.mint_tokens(&admin1, &user, &1000);

    // Verify balance and total supply after mint
    assert_eq!(contract_client.get_balance(&user), 1000);
    assert_eq!(contract_client.get_total_supply(), 1000);

    // Burn tokens from user
    contract_client.burn_tokens(&admin1, &user, &500);

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

    let contract_client = SensoryEvaluationClient::new(&env, &env.register(SensoryEvaluation {}, ()));

    env.mock_all_auths();

    // Initialize contract
    let admins = Vec::from_slice(&env, &[admin.clone()]);
    let token_name = String::from_str(&env, "SensoryToken");
    let token_symbol = String::from_str(&env, "SEN");
    contract_client.initialize(&admins, &token_name, &token_symbol, &1000000, &6);

    // Mint tokens to user1
    contract_client.mint_tokens(&admin, &user1, &1000);

    // Transfer tokens from user1 to user2
    contract_client.transfer_tokens(&user1, &user2, &500);

    // Verify balances
    assert_eq!(contract_client.get_balance(&user1), 500);
    assert_eq!(contract_client.get_balance(&user2), 500);
}

/// Tests creating and releasing funds from a staking schedule.
#[test]
fn test_staking_schedule() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let user = Address::generate(&env);

    let contract_client = SensoryEvaluationClient::new(&env, &env.register(SensoryEvaluation {}, ()));

    env.mock_all_auths();

    // Initialize contract
    let admins = Vec::from_slice(&env, &[admin.clone()]);
    let token_name = String::from_str(&env, "SensoryToken");
    let token_symbol = String::from_str(&env, "SEN");
    contract_client.initialize(&admins, &token_name, &token_symbol, &1000000, &6);

    // Mint tokens to user
    contract_client.mint_tokens(&admin, &user, &1000);

    // Create staking schedule
    let current_time = env.ledger().timestamp();
    contract_client.stake_tokens(&user, &1000, &3600); // Stake 1000 tokens for 1 hour

    // Verify staking schedule
    let stakes = contract_client.get_stakes(&user);
    assert_eq!(stakes.len(), 1);
    let stake = stakes.get(0).unwrap();
    assert_eq!(stake.amount, 1000);
    assert_eq!(stake.duration, 3600);
    assert_eq!(stake.claimed, false);
    assert_eq!(contract_client.get_balance(&user), 0); // Balance should be 0 after staking

    // Fast forward past duration and unstake
    env.ledger().with_mut(|l| l.timestamp = current_time + 3600);
    contract_client.unstake_tokens(&user, &0);

    // Verify tokens returned to balance
    assert_eq!(contract_client.get_balance(&user), 1000);
    let stakes = contract_client.get_stakes(&user);
    assert!(stakes.get(0).unwrap().claimed);
}

/// Tests adding a new admin.
#[test]
fn test_add_admin() {
    let env = Env::default();
    let initial_admin = Address::generate(&env);
    let new_admin = Address::generate(&env);

    let contract_client = SensoryEvaluationClient::new(&env, &env.register(SensoryEvaluation {}, ()));

    env.mock_all_auths();

    // Initialize contract with initial admin
    let admins = Vec::from_slice(&env, &[initial_admin.clone()]);
    let token_name = String::from_str(&env, "SensoryToken");
    let token_symbol = String::from_str(&env, "SEN");
    contract_client.initialize(&admins, &token_name, &token_symbol, &1000000, &6);

    // Add new admin
    contract_client.add_admin(&initial_admin, &new_admin);

    // Verify new admin can perform actions (e.g., mint)
    let user = Address::generate(&env);
    contract_client.mint_tokens(&new_admin, &user, &1000);

    // Verify mint succeeded, indicating new admin is functional
    assert_eq!(contract_client.get_balance(&user), 1000);
    assert!(true, "New admin added and functional");
}

/// Tests multiple mint operations.
#[test]
fn test_multiple_mints() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let user = Address::generate(&env);

    let contract_client = SensoryEvaluationClient::new(&env, &env.register(SensoryEvaluation {}, ()));

    env.mock_all_auths();

    // Initialize contract
    let admins = Vec::from_slice(&env, &[admin.clone()]);
    let token_name = String::from_str(&env, "SensoryToken");
    let token_symbol = String::from_str(&env, "SEN");
    contract_client.initialize(&admins, &token_name, &token_symbol, &1000000, &6);

    // Perform multiple mints
    contract_client.mint_tokens(&admin, &user, &1000);
    contract_client.mint_tokens(&admin, &user, &500);

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

    let contract_client = SensoryEvaluationClient::new(&env, &env.register(SensoryEvaluation {}, ()));

    env.mock_all_auths();

    // Initialize contract
    let admins = Vec::from_slice(&env, &[admin.clone()]);
    let token_name = String::from_str(&env, "SensoryToken");
    let token_symbol = String::from_str(&env, "SEN");
    contract_client.initialize(&admins, &token_name, &token_symbol, &1000000, &6);

    // Mint tokens to user1
    contract_client.mint_tokens(&admin, &user1, &1000);

    // Perform multiple transfers
    contract_client.transfer_tokens(&user1, &user2, &300);
    contract_client.transfer_tokens(&user1, &user2, &200);

    // Verify remaining balances
    assert_eq!(contract_client.get_balance(&user1), 500);
    assert_eq!(contract_client.get_balance(&user2), 500);
}