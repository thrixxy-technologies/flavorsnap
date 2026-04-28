#![cfg(test)]

use super::*;
use soroban_sdk::{testutils::{Address as _, Ledger}, Address, Env};


// -----------------------------
// 🧪 Setup Helper
// -----------------------------
fn setup_env() -> (Env, Address) {
    let env = Env::default();
    let admin = Address::generate(&env);

    (env, admin)
}


// -----------------------------
// ✅ Functional Test
// -----------------------------
#[test]
fn test_set_and_get_value() {
    let (env, admin) = setup_env();

    let contract_id = env.register_contract(None, ExampleContract);
    let client = ExampleContractClient::new(&env, &contract_id);

    client.initialize(&admin);
    client.set_value(&admin, &10);

    let result = client.get_value();

    assert_eq!(result, 10);
}


// -----------------------------
// ⚠️ Edge Case: Zero Value
// -----------------------------
#[test]
fn test_set_zero_value() {
    let (env, admin) = setup_env();

    let contract_id = env.register_contract(None, ExampleContract);
    let client = ExampleContractClient::new(&env, &contract_id);

    client.initialize(&admin);
    client.set_value(&admin, &0);

    let result = client.get_value();

    assert_eq!(result, 0);
}


// -----------------------------
// ⚠️ Edge Case: Large Value
// -----------------------------
#[test]
fn test_set_large_value() {
    let (env, admin) = setup_env();

    let contract_id = env.register_contract(None, ExampleContract);
    let client = ExampleContractClient::new(&env, &contract_id);

    let large_value = i128::MAX;

    client.initialize(&admin);
    client.set_value(&admin, &large_value);

    let result = client.get_value();

    assert_eq!(result, large_value);
}


// -----------------------------
// 🔐 Security: Unauthorized Access
// -----------------------------
#[test]
#[should_panic]
fn test_unauthorized_set_value() {
    let (env, admin) = setup_env();
    let attacker = Address::generate(&env);

    let contract_id = env.register_contract(None, ExampleContract);
    let client = ExampleContractClient::new(&env, &contract_id);

    client.initialize(&admin);

    // attacker tries to set value
    client.set_value(&attacker, &100);
}


// -----------------------------
// 🔐 Security: Not Initialized
// -----------------------------
#[test]
#[should_panic]
fn test_use_before_initialize() {
    let (env, admin) = setup_env();

    let contract_id = env.register_contract(None, ExampleContract);
    let client = ExampleContractClient::new(&env, &contract_id);

    // should fail because not initialized
    client.set_value(&admin, &10);
}


// -----------------------------
// 🔁 State Integrity Test
// -----------------------------
#[test]
fn test_state_persistence() {
    let (env, admin) = setup_env();

    let contract_id = env.register_contract(None, ExampleContract);
    let client = ExampleContractClient::new(&env, &contract_id);

    client.initialize(&admin);

    client.set_value(&admin, &42);
    assert_eq!(client.get_value(), 42);

    client.set_value(&admin, &100);
    assert_eq!(client.get_value(), 100);
}