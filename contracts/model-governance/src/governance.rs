use crate::storage::*;
use crate::types::*;
use soroban_sdk::Vec;
use soroban_sdk::{Address, Env, String};

/// Initializes the contract with admin, quorum, voting period, minimum stake, and timelock delay
pub fn initialize(env: Env, admin: Address, quorum: u32, voting_period: u64, min_stake: u32, timelock_delay: u64) {
    admin.require_auth();
    if env.storage().instance().has(&DataKey::Admin) {
        panic!("Contract already initialized");
    }
    
    env.storage().instance().set(&DataKey::Admin, &admin);
    env.storage().instance().set(&DataKey::Quorum, &quorum);
    env.storage().instance().set(&DataKey::VotingPeriod, &voting_period);
    env.storage().instance().set(&DataKey::MinStake, &min_stake);
    env.storage().instance().set(&DataKey::TimelockDelay, &timelock_delay);
    env.storage().instance().set(&DataKey::NextProposalId, &1u32);
    env.storage().instance().set(&DataKey::Paused, &false);
    env.storage().instance().set(&DataKey::ContractVersion, &1u32);
}

/// Submits a new proposal with metadata, stake, and type
pub fn submit_proposal(env: Env, proposer: Address, metadata: String, stake: u32, proposal_type: ProposalType) -> u32 {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    proposer.require_auth();

    let min_stake = get_min_stake(&env);
    let balance = get_token_balance(&env, &proposer);
    if balance < stake || stake < min_stake {
        panic!("Insufficient stake for proposal submission");
    }

    let proposal_id = next_proposal_id(&env);
    let current_time = env.ledger().timestamp();
    let timelock_delay = match proposal_type {
        ProposalType::Emergency => 0, // No timelock for emergency proposals
        _ => get_timelock_delay(&env),
    };
    
    let proposal = Proposal {
        id: proposal_id,
        proposer: proposer.clone(),
        metadata,
        stake,
        status: ProposalStatus::Active,
        yes_votes: 0,
        no_votes: 0,
        timestamp: current_time,
        executed: false,
        execution_time: current_time + timelock_delay,
        proposal_type,
        voting_power_used: 0,
    };
    
    store_proposal(&env, &proposal);

    // Create voting power snapshot
    create_voting_power_snapshot(&env, proposal_id);

    // Deduct stake from proposer's balance
    update_token_balance(&env, &proposer, balance - stake);
    proposal_id
}

/// Creates a snapshot of voting power at proposal submission
fn create_voting_power_snapshot(env: &Env, proposal_id: u32) {
    let token_holders: Vec<Address> = env
        .storage()
        .instance()
        .get(&DataKey::TokenHolders)
        .unwrap_or_else(|| Vec::new(env));
    
    let mut snapshots = Vec::new(env);
    let current_time = env.ledger().timestamp();
    
    for holder in token_holders.iter() {
        let power = calculate_effective_voting_power(env, holder);
        if power > 0 {
            let delegation = get_delegation(env, holder);
            snapshots.push_back(VotingPowerSnapshot {
                address: holder.clone(),
                power,
                timestamp: current_time,
                delegated: delegation.is_some(),
            });
        }
    }
    
    set_voting_power_snapshots(env, proposal_id, &snapshots);
}

/// Allows token holders to vote on a proposal
pub fn vote(env: Env, voter: Address, proposal_id: u32, in_favor: bool) {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    voter.require_auth();

    let mut proposal = get_proposal(&env, proposal_id);
    if proposal.status != ProposalStatus::Active {
        panic!("Proposal is not active");
    }

    // Check if voting period has expired
    let voting_period = get_voting_period(&env);
    if env.ledger().timestamp() > proposal.timestamp + voting_period {
        panic!("Voting period has ended");
    }

    // Prevent double voting
    if get_vote(&env, proposal_id, &voter).is_some() {
        panic!("Double voting is not allowed");
    }

    // Get voting power from snapshot
    let snapshots = get_voting_power_snapshots(&env, proposal_id);
    let weight = snapshots
        .iter()
        .find(|snapshot| snapshot.address == voter)
        .map(|snapshot| snapshot.power)
        .unwrap_or(0);
        
    if weight == 0 {
        panic!("No voting power available");
    }

    // Check if voter has delegated their vote
    if let Some(delegation) = get_delegation(&env, &voter) {
        panic!("Cannot vote directly when vote is delegated");
    }

    // Record the vote
    let vote = Vote {
        voter: voter.clone(),
        in_favor,
        weight,
        timestamp: env.ledger().timestamp(),
        delegated_to: None,
    };
    store_vote(&env, proposal_id, &vote);

    // Update voter list
    let mut voters = get_voters(&env, proposal_id);
    voters.push_back(voter.clone());
    store_voters(&env, proposal_id, &voters);

    // Update vote counts
    if in_favor {
        proposal.yes_votes += weight;
    } else {
        proposal.no_votes += weight;
    }
    proposal.voting_power_used += weight;
    store_proposal(&env, &proposal);
}

/// Delegates voting power to another address
pub fn delegate_vote(env: Env, delegator: Address, delegate: Address) {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    delegator.require_auth();
    
    if delegator == delegate {
        panic!("Cannot delegate to yourself");
    }
    
    let current_time = env.ledger().timestamp();
    let weight = get_token_balance(&env, &delegator);
    
    if weight == 0 {
        panic!("No tokens to delegate");
    }
    
    let delegation = Delegation {
        delegator: delegator.clone(),
        delegate: delegate.clone(),
        timestamp: current_time,
        weight,
    };
    
    set_delegation(&env, &delegation);
}

/// Removes vote delegation
pub fn undelegate_vote(env: Env, delegator: Address) {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    delegator.require_auth();
    remove_delegation(&env, &delegator);
}

/// Evaluates a proposal and executes or rejects it based on vote results
pub fn evaluate_proposal(env: Env, proposal_id: u32) {
    let mut proposal = get_proposal(&env, proposal_id);
    if proposal.status != ProposalStatus::Active {
        panic!("Proposal is not active");
    }

    let voting_period = get_voting_period(&env);
    if env.ledger().timestamp() <= proposal.timestamp + voting_period {
        panic!("Voting period not yet ended");
    }

    let total_votes = proposal.yes_votes + proposal.no_votes;
    let quorum = get_quorum(&env);
    
    // Calculate total voting power from snapshots
    let snapshots = get_voting_power_snapshots(&env, proposal_id);
    let total_voting_power: u32 = snapshots.iter().map(|s| s.power).sum();

    // Check quorum
    if total_votes == 0 || total_votes * 10000 / total_voting_power < quorum {
        proposal.status = ProposalStatus::Rejected;
        store_proposal(&env, &proposal);
        // Return stake on rejection
        let balance = get_token_balance(&env, &proposal.proposer);
        update_token_balance(&env, &proposal.proposer, balance + proposal.stake);
        panic!("Quorum not met, proposal rejected");
    }

    // Determine outcome
    if proposal.yes_votes > proposal.no_votes {
        proposal.status = ProposalStatus::Approved;
        // Set execution time for timelock
        if proposal.proposal_type != ProposalType::Emergency {
            proposal.execution_time = env.ledger().timestamp() + get_timelock_delay(&env);
        } else {
            proposal.execution_time = env.ledger().timestamp(); // Immediate for emergency
        }
    } else {
        proposal.status = ProposalStatus::Rejected;
        // Return stake on rejection or tie
        let balance = get_token_balance(&env, &proposal.proposer);
        update_token_balance(&env, &proposal.proposer, balance + proposal.stake);
    }
    store_proposal(&env, &proposal);
}

/// Executes a proposal after timelock period
pub fn execute_proposal(env: Env, proposal_id: u32) {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    let mut proposal = get_proposal(&env, proposal_id);
    
    if proposal.status != ProposalStatus::Approved {
        panic!("Proposal is not approved");
    }
    
    if proposal.executed {
        panic!("Proposal already executed");
    }
    
    let current_time = env.ledger().timestamp();
    if current_time < proposal.execution_time {
        panic!("Timelock period not yet passed");
    }
    
    // Execute the proposal (in a real implementation, this would trigger the actual action)
    proposal.executed = true;
    proposal.status = ProposalStatus::Executed;
    store_proposal(&env, &proposal);
    
    // Return stake to proposer on successful execution
    let balance = get_token_balance(&env, &proposal.proposer);
    update_token_balance(&env, &proposal.proposer, balance + proposal.stake);
}

/// Cancels an active proposal (admin or proposer only)
pub fn cancel_proposal(env: Env, caller: Address, proposal_id: u32) {
    caller.require_auth();

    let mut proposal = get_proposal(&env, proposal_id);
    if proposal.status != ProposalStatus::Active {
        panic!("Proposal is not active");
    }

    if caller != proposal.proposer && !is_admin(&env, &caller) {
        panic!("Unauthorized cancellation");
    }

    proposal.status = ProposalStatus::Cancelled;
    store_proposal(&env, &proposal);

    // Return stake to proposer
    let balance = get_token_balance(&env, &proposal.proposer);
    update_token_balance(&env, &proposal.proposer, balance + proposal.stake);
}

/// Amends the metadata of an active proposal (proposer only)
pub fn amend_proposal(env: Env, proposer: Address, proposal_id: u32, new_metadata: String) {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    proposer.require_auth();

    let mut proposal = get_proposal(&env, proposal_id);
    if proposal.status != ProposalStatus::Active {
        panic!("Proposal is not active");
    }

    if proposal.proposer != proposer {
        panic!("Only proposer can amend the proposal");
    }

    proposal.metadata = new_metadata;
    store_proposal(&env, &proposal);
}

/// Pauses the contract (admin only)
pub fn pause_contract(env: Env, admin: Address) {
    admin.require_auth();
    if !is_admin(&env, &admin) {
        panic!("Only admin can pause the contract");
    }
    env.storage().instance().set(&DataKey::Paused, &true);
}

/// Unpauses the contract (admin only)
pub fn unpause_contract(env: Env, admin: Address) {
    admin.require_auth();
    if !is_admin(&env, &admin) {
        panic!("Only admin can unpause the contract");
    }
    env.storage().instance().set(&DataKey::Paused, &false);
}

/// Updates contract parameters (admin only)
pub fn update_parameters(env: Env, admin: Address, quorum: Option<u32>, voting_period: Option<u64>, min_stake: Option<u32>, timelock_delay: Option<u64>) {
    admin.require_auth();
    if !is_admin(&env, &admin) {
        panic!("Only admin can update parameters");
    }
    
    if let Some(q) = quorum {
        env.storage().instance().set(&DataKey::Quorum, &q);
    }
    if let Some(vp) = voting_period {
        env.storage().instance().set(&DataKey::VotingPeriod, &vp);
    }
    if let Some(ms) = min_stake {
        env.storage().instance().set(&DataKey::MinStake, &ms);
    }
    if let Some(tl) = timelock_delay {
        env.storage().instance().set(&DataKey::TimelockDelay, &tl);
    }
}

/// Retrieves details of a proposal
pub fn get_proposal_info(env: Env, proposal_id: u32) -> Proposal {
    get_proposal(&env, proposal_id)
}

/// Gets delegation info for an address
pub fn get_delegation_info(env: Env, address: Address) -> Option<Delegation> {
    get_delegation(&env, &address)
}

/// Gets effective voting power for an address
pub fn get_voting_power(env: Env, address: Address) -> u32 {
    calculate_effective_voting_power(&env, &address)
}

/// Sets a token balance for testing or admin purposes
pub fn set_token_balance(env: Env, admin: Address, address: Address, balance: u32) {
    admin.require_auth();
    if !is_admin(&env, &admin) {
        panic!("Only admin can set token balances");
    }
    update_token_balance(&env, &address, balance);

    // Update token holders list
    let mut token_holders: Vec<Address> = env
        .storage()
        .instance()
        .get(&DataKey::TokenHolders)
        .unwrap_or_else(|| Vec::new(&env));
    if balance > 0 && !token_holders.contains(&address) {
        token_holders.push_back(address.clone());
    } else if balance == 0 {
        // Remove address if balance is zero
        let index = token_holders.iter().position(|a| a == address);
        if let Some(i) = index {
            token_holders.remove(i as u32);
        }
    }
    env.storage()
        .instance()
        .set(&DataKey::TokenHolders, &token_holders);
}
