use crate::types::*;
use soroban_sdk::{Address, Env, Vec};

/// Checks if the caller is the admin
pub fn is_admin(env: &Env, address: &Address) -> bool {
    let stored_admin: Address = env.storage().instance().get(&DataKey::Admin).unwrap();
    stored_admin == *address
}

/// Checks if the contract is paused
pub fn is_paused(env: &Env) -> bool {
    env.storage().instance().get(&DataKey::Paused).unwrap_or(false)
}

/// Gets the timelock delay
pub fn get_timelock_delay(env: &Env) -> u64 {
    env.storage().instance().get(&DataKey::TimelockDelay).unwrap_or(86400) // Default 24 hours
}

/// Retrieves and increments the next proposal ID
pub fn next_proposal_id(env: &Env) -> u32 {
    let id: u32 = env
        .storage()
        .instance()
        .get(&DataKey::NextProposalId)
        .unwrap_or(1u32);
    env.storage()
        .instance()
        .set(&DataKey::NextProposalId, &(id + 1));
    id
}

/// Fetches a proposal by its ID
pub fn get_proposal(env: &Env, proposal_id: u32) -> Proposal {
    env.storage()
        .instance()
        .get(&DataKey::Proposals(proposal_id))
        .unwrap_or_else(|| panic!("Proposal not found"))
}

/// Stores a proposal in storage
pub fn store_proposal(env: &Env, proposal: &Proposal) {
    env.storage()
        .instance()
        .set(&DataKey::Proposals(proposal.id), proposal);
}

/// Retrieves a vote for a proposal by a voter
pub fn get_vote(env: &Env, proposal_id: u32, voter: &Address) -> Option<Vote> {
    env.storage()
        .instance()
        .get(&DataKey::Votes(proposal_id, voter.clone()))
}

/// Stores a vote for a proposal
pub fn store_vote(env: &Env, proposal_id: u32, vote: &Vote) {
    env.storage()
        .instance()
        .set(&DataKey::Votes(proposal_id, vote.voter.clone()), vote);
}

/// Retrieves the list of voters for a proposal
pub fn get_voters(env: &Env, proposal_id: u32) -> Vec<Address> {
    env.storage()
        .instance()
        .get(&DataKey::Voters(proposal_id))
        .unwrap_or_else(|| Vec::new(env))
}

/// Stores the list of voters for a proposal
pub fn store_voters(env: &Env, proposal_id: u32, voters: &Vec<Address>) {
    env.storage()
        .instance()
        .set(&DataKey::Voters(proposal_id), voters);
}

/// Retrieves the token balance of an address
pub fn get_token_balance(env: &Env, address: &Address) -> u32 {
    env.storage()
        .instance()
        .get(&DataKey::TokenBalance(address.clone()))
        .unwrap_or(0)
}

/// Updates the token balance of an address
pub fn update_token_balance(env: &Env, address: &Address, balance: u32) {
    env.storage()
        .instance()
        .set(&DataKey::TokenBalance(address.clone()), &balance);
}

/// Retrieves the quorum percentage
pub fn get_quorum(env: &Env) -> u32 {
    env.storage().instance().get(&DataKey::Quorum).unwrap()
}

/// Retrieves the voting period in seconds
pub fn get_voting_period(env: &Env) -> u64 {
    env.storage()
        .instance()
        .get(&DataKey::VotingPeriod)
        .unwrap()
}

/// Retrieves the minimum stake required for proposal submission
pub fn get_min_stake(env: &Env) -> u32 {
    env.storage().instance().get(&DataKey::MinStake).unwrap()
}

/// Gets delegation info for an address
pub fn get_delegation(env: &Env, delegator: &Address) -> Option<Delegation> {
    env.storage()
        .instance()
        .get(&DataKey::Delegations(delegator.clone()))
}

/// Sets delegation info
pub fn set_delegation(env: &Env, delegation: &Delegation) {
    env.storage()
        .instance()
        .set(&DataKey::Delegations(delegation.delegator.clone()), delegation);
}

/// Removes delegation
pub fn remove_delegation(env: &Env, delegator: &Address) {
    env.storage()
        .instance()
        .remove(&DataKey::Delegations(delegator.clone()));
}

/// Gets voting power snapshots for a proposal
pub fn get_voting_power_snapshots(env: &Env, proposal_id: u32) -> Vec<VotingPowerSnapshot> {
    env.storage()
        .instance()
        .get(&DataKey::VotingPowerSnapshot(proposal_id))
        .unwrap_or_else(|| Vec::new(env))
}

/// Sets voting power snapshots for a proposal
pub fn set_voting_power_snapshots(env: &Env, proposal_id: u32, snapshots: &Vec<VotingPowerSnapshot>) {
    env.storage()
        .instance()
        .set(&DataKey::VotingPowerSnapshot(proposal_id), snapshots);
}

/// Calculates effective voting power including delegations
pub fn calculate_effective_voting_power(env: &Env, voter: &Address) -> u32 {
    let base_power = get_token_balance(env, voter);
    
    // Add delegated power
    let mut delegated_power = 0u32;
    let token_holders: Vec<Address> = env
        .storage()
        .instance()
        .get(&DataKey::TokenHolders)
        .unwrap_or_else(|| Vec::new(env));
    
    for holder in token_holders.iter() {
        if let Some(delegation) = get_delegation(env, holder) {
            if delegation.delegate == *voter {
                delegated_power += delegation.weight;
            }
        }
    }
    
    base_power + delegated_power
}

/// Gets contract version
pub fn get_contract_version(env: &Env) -> u32 {
    env.storage().instance().get(&DataKey::ContractVersion).unwrap_or(1)
}

/// Sets contract version
pub fn set_contract_version(env: &Env, version: u32) {
    env.storage().instance().set(&DataKey::ContractVersion, &version);
}
