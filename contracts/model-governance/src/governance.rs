use crate::storage::*;
use crate::types::*;
use soroban_sdk::Vec;
use soroban_sdk::{Address, Env, String};

/// Initializes the contract with admin, quorum, voting period, and minimum stake
pub fn initialize(env: Env, admin: Address, quorum: u32, voting_period: u64, min_stake: u32) {
    admin.require_auth();
    env.storage().instance().set(&DataKey::Admin, &admin);
    env.storage().instance().set(&DataKey::Quorum, &quorum); // e.g., 5000 = 50.00%
    env.storage()
        .instance()
        .set(&DataKey::VotingPeriod, &voting_period);
    env.storage().instance().set(&DataKey::MinStake, &min_stake);
    env.storage()
        .instance()
        .set(&DataKey::NextProposalId, &1u32);
}

/// Submits a new proposal with metadata and a stake
pub fn submit_proposal(env: Env, proposer: Address, metadata: String, stake: u32) -> u32 {
    proposer.require_auth();

    let min_stake = get_min_stake(&env);
    let balance = get_token_balance(&env, &proposer);
    if balance < stake || stake < min_stake {
        panic!("Insufficient stake for proposal submission");
    }

    let proposal_id = next_proposal_id(&env);
    let proposal = Proposal {
        id: proposal_id,
        proposer: proposer.clone(),
        metadata,
        stake,
        status: ProposalStatus::Active,
        yes_votes: 0,
        no_votes: 0,
        timestamp: env.ledger().timestamp(),
        executed: false,
    };
    store_proposal(&env, &proposal);

    // Deduct stake from proposer's balance
    update_token_balance(&env, &proposer, balance - stake);
    proposal_id
}

/// Allows token holders to vote on a proposal
pub fn vote(env: Env, voter: Address, proposal_id: u32, in_favor: bool) {
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

    let weight = get_token_balance(&env, &voter);
    if weight == 0 {
        panic!("No tokens to vote with");
    }

    // Record the vote
    let vote = Vote {
        voter: voter.clone(),
        in_favor,
        weight,
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
    store_proposal(&env, &proposal);
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
    // Sum balances of all token holders
    let token_holders: Vec<Address> = env
        .storage()
        .instance()
        .get(&DataKey::TokenHolders)
        .unwrap_or_else(|| Vec::new(&env));
    let total_supply: u32 = token_holders
        .iter()
        .fold(0u32, |sum, holder| sum + get_token_balance(&env, &holder));

    // Check quorum (e.g., 5000 = 50.00%, so total_votes * 10000 / total_supply >= quorum)
    if total_votes == 0 || total_votes * 10000 / total_supply < quorum {
        proposal.status = ProposalStatus::Rejected;
        store_proposal(&env, &proposal);
        // Return stake on rejection
        let balance = get_token_balance(&env, &proposal.proposer);
        update_token_balance(&env, &proposal.proposer, balance + proposal.stake);
        panic!("Quorum not met, proposal rejected");
    }

    // Determine outcome (approve if yes votes exceed no votes, reject on tie or less)
    if proposal.yes_votes > proposal.no_votes {
        proposal.status = ProposalStatus::Approved;
        proposal.executed = true;
    } else {
        proposal.status = ProposalStatus::Rejected;
        // Return stake on rejection or tie
        let balance = get_token_balance(&env, &proposal.proposer);
        update_token_balance(&env, &proposal.proposer, balance + proposal.stake);
    }
    store_proposal(&env, &proposal);
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

/// Retrieves details of a proposal
pub fn get_proposal_info(env: Env, proposal_id: u32) -> Proposal {
    get_proposal(&env, proposal_id)
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
