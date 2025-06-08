#![no_std]
use soroban_sdk::{contract, contractimpl, Address, Env, String};

mod governance;
mod storage;
mod test;
mod types;

pub use governance::*;
pub use storage::*;
pub use types::*;

#[contract]
pub struct ModelUpdateGovernance;

#[contractimpl]
impl ModelUpdateGovernance {
    /// Initializes the contract with admin, quorum, voting period, and min stake
    pub fn initialize(env: Env, admin: Address, quorum: u32, voting_period: u64, min_stake: u32) {
        governance::initialize(env, admin, quorum, voting_period, min_stake)
    }

    /// Submits a new proposal for an AI model update or dataset expansion
    pub fn submit_proposal(env: Env, proposer: Address, metadata: String, stake: u32) -> u32 {
        governance::submit_proposal(env, proposer, metadata, stake)
    }

    /// Allows token holders to vote on a proposal
    pub fn vote(env: Env, voter: Address, proposal_id: u32, in_favor: bool) {
        governance::vote(env, voter, proposal_id, in_favor)
    }

    /// Evaluates a proposal and executes or rejects it
    pub fn evaluate_proposal(env: Env, proposal_id: u32) {
        governance::evaluate_proposal(env, proposal_id)
    }

    /// Cancels an active proposal
    pub fn cancel_proposal(env: Env, caller: Address, proposal_id: u32) {
        governance::cancel_proposal(env, caller, proposal_id)
    }

    /// Amends the metadata of an active proposal
    pub fn amend_proposal(env: Env, proposer: Address, proposal_id: u32, new_metadata: String) {
        governance::amend_proposal(env, proposer, proposal_id, new_metadata)
    }

    /// Retrieves details of a proposal
    pub fn get_proposal_info(env: Env, proposal_id: u32) -> Proposal {
        governance::get_proposal_info(env, proposal_id)
    }

    /// Sets a token balance (admin only)
    pub fn set_token_balance(env: Env, admin: Address, address: Address, balance: u32) {
        governance::set_token_balance(env, admin, address, balance)
    }
}
