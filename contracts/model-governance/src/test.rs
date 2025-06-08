#![cfg(test)]

extern crate std;

use crate::types::ProposalStatus;
use crate::{ModelUpdateGovernance, ModelUpdateGovernanceClient};
use soroban_sdk::{
    testutils::{Address as _, Ledger},
    Address, Env, String,
};

/// Tests contract initialization
#[test]
fn test_initialize_contract() {
    let env = Env::default();
    let admin = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &5000, &86400, &100); // 50% quorum, 1 day, 100 min stake
    assert!(true, "Initialize function completed without errors");
}

/// Tests successful proposal submission
#[test]
fn test_submit_proposal() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let proposer = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &5000, &86400, &100);
    client.set_token_balance(&admin, &proposer, &200);

    let proposal_id = client.submit_proposal(
        &proposer,
        &String::from_str(&env, "Update AI model v2"),
        &150,
    );
    let proposal = client.get_proposal_info(&proposal_id);
    assert_eq!(proposal.stake, 150);
    assert_eq!(proposal.status, ProposalStatus::Active);
    assert_eq!(
        proposal.metadata,
        String::from_str(&env, "Update AI model v2")
    );
}

/// Tests proposal submission with insufficient stake
#[test]
#[should_panic(expected = "Insufficient stake for proposal submission")]
fn test_submit_proposal_insufficient_stake() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let proposer = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &5000, &86400, &100);
    client.set_token_balance(&admin, &proposer, &50);
    client.submit_proposal(
        &proposer,
        &String::from_str(&env, "Update AI model v2"),
        &100,
    );
}

/// Tests voting on a proposal
#[test]
fn test_vote() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let proposer = Address::generate(&env);
    let voter = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &5000, &86400, &100);
    client.set_token_balance(&admin, &proposer, &200);
    client.set_token_balance(&admin, &voter, &300);

    let proposal_id = client.submit_proposal(
        &proposer,
        &String::from_str(&env, "Update AI model v2"),
        &150,
    );
    client.vote(&voter, &proposal_id, &true);

    let proposal = client.get_proposal_info(&proposal_id);
    assert_eq!(proposal.yes_votes, 300);
    assert_eq!(proposal.no_votes, 0);
}

/// Tests prevention of double voting
#[test]
#[should_panic(expected = "Double voting is not allowed")]
fn test_double_voting() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let proposer = Address::generate(&env);
    let voter = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &5000, &86400, &100);
    client.set_token_balance(&admin, &proposer, &200);
    client.set_token_balance(&admin, &voter, &300);

    let proposal_id = client.submit_proposal(
        &proposer,
        &String::from_str(&env, "Update AI model v2"),
        &150,
    );
    client.vote(&voter, &proposal_id, &true);
    client.vote(&voter, &proposal_id, &false);
}

/// Tests proposal evaluation with approval
#[test]
fn test_evaluate_proposal_approved() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let proposer = Address::generate(&env);
    let voter = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &5000, &86400, &100);
    client.set_token_balance(&admin, &proposer, &200);
    client.set_token_balance(&admin, &voter, &300);

    let proposal_id = client.submit_proposal(
        &proposer,
        &String::from_str(&env, "Update AI model v2"),
        &150,
    );
    client.vote(&voter, &proposal_id, &true);

    // Fast forward time to end voting period
    env.ledger().with_mut(|l| l.timestamp += 86401);
    client.evaluate_proposal(&proposal_id);

    let proposal = client.get_proposal_info(&proposal_id);
    assert_eq!(proposal.status, ProposalStatus::Approved);
    assert!(proposal.executed);
}

/// Tests proposal evaluation with quorum failure
#[test]
#[should_panic(expected = "Quorum not met, proposal rejected")]
fn test_evaluate_proposal_quorum_failure() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let proposer = Address::generate(&env);
    let voter = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &9000, &86400, &100); // 90% quorum
    client.set_token_balance(&admin, &proposer, &200);
    client.set_token_balance(&admin, &voter, &300);
    client.set_token_balance(&admin, &Address::generate(&env), &700); // More tokens for quorum calc

    let proposal_id = client.submit_proposal(
        &proposer,
        &String::from_str(&env, "Update AI model v2"),
        &150,
    );
    client.vote(&voter, &proposal_id, &true);

    env.ledger().with_mut(|l| l.timestamp += 86401);
    client.evaluate_proposal(&proposal_id);
}
/// Tests proposal evaluation with tie vote
#[test]
fn test_evaluate_proposal_tie() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let proposer = Address::generate(&env);
    let voter1 = Address::generate(&env);
    let voter2 = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &5000, &86400, &100);
    client.set_token_balance(&admin, &proposer, &200);
    client.set_token_balance(&admin, &voter1, &300);
    client.set_token_balance(&admin, &voter2, &300);

    let proposal_id = client.submit_proposal(
        &proposer,
        &String::from_str(&env, "Update AI model v2"),
        &150,
    );
    client.vote(&voter1, &proposal_id, &true);
    client.vote(&voter2, &proposal_id, &false);

    env.ledger().with_mut(|l| l.timestamp += 86401);
    client.evaluate_proposal(&proposal_id);

    let proposal = client.get_proposal_info(&proposal_id);
    assert_eq!(proposal.status, ProposalStatus::Rejected);
    assert_eq!(proposal.yes_votes, 300);
    assert_eq!(proposal.no_votes, 300);
}

/// Tests proposal cancellation by proposer
#[test]
fn test_cancel_proposal() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let proposer = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &5000, &86400, &100);
    client.set_token_balance(&admin, &proposer, &200);

    let proposal_id = client.submit_proposal(
        &proposer,
        &String::from_str(&env, "Update AI model v2"),
        &150,
    );
    client.cancel_proposal(&proposer, &proposal_id);

    let proposal = client.get_proposal_info(&proposal_id);
    assert_eq!(proposal.status, ProposalStatus::Cancelled);
}

/// Tests unauthorized proposal cancellation
#[test]
#[should_panic(expected = "Unauthorized cancellation")]
fn test_unauthorized_cancellation() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let proposer = Address::generate(&env);
    let unauthorized = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &5000, &86400, &100);
    client.set_token_balance(&admin, &proposer, &200);

    let proposal_id = client.submit_proposal(
        &proposer,
        &String::from_str(&env, "Update AI model v2"),
        &150,
    );
    client.cancel_proposal(&unauthorized, &proposal_id);
}

/// Tests proposal amendment
#[test]
fn test_amend_proposal() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let proposer = Address::generate(&env);
    env.mock_all_auths();

    let contract_address = env.register(ModelUpdateGovernance {}, ());
    let client = ModelUpdateGovernanceClient::new(&env, &contract_address);

    client.initialize(&admin, &5000, &86400, &100);
    client.set_token_balance(&admin, &proposer, &200);

    let proposal_id = client.submit_proposal(
        &proposer,
        &String::from_str(&env, "Update AI model v2"),
        &150,
    );
    client.amend_proposal(
        &proposer,
        &proposal_id,
        &String::from_str(&env, "Revised AI model update v3"),
    );

    let proposal = client.get_proposal_info(&proposal_id);
    assert_eq!(
        proposal.metadata,
        String::from_str(&env, "Revised AI model update v3")
    );
}
