#![no_std]
use soroban_sdk::{contract, contractimpl, Address, Env, String};
use shared::upgradeability::{UpgradeableContract, UpgradeKey};

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
    /// Initializes the contract with admin, quorum, voting period, min stake, and timelock delay
    pub fn initialize(env: Env, admin: Address, quorum: u32, voting_period: u64, min_stake: u32, timelock_delay: u64) {
        // Initialize upgradeability first
        UpgradeableContract::initialize_upgradeability(&env, admin.clone(), env.current_contract_address(), 1);
        
        // Then initialize contract-specific logic
        governance::initialize(env, admin, quorum, voting_period, min_stake, timelock_delay)
    }

    /// Submits a new proposal for an AI model update or dataset expansion
    pub fn submit_proposal(env: Env, proposer: Address, metadata: String, stake: u32, proposal_type: ProposalType) -> u32 {
        if UpgradeableContract::is_paused_for_upgrade(&env) {
            panic!("Contract is paused for upgrade");
        }
        governance::submit_proposal(env, proposer, metadata, stake, proposal_type)
    }

    /// Allows token holders to vote on a proposal
    pub fn vote(env: Env, voter: Address, proposal_id: u32, in_favor: bool) {
        if UpgradeableContract::is_paused_for_upgrade(&env) {
            panic!("Contract is paused for upgrade");
        }
        governance::vote(env, voter, proposal_id, in_favor)
    }

    /// Evaluates a proposal and executes or rejects it
    pub fn evaluate_proposal(env: Env, proposal_id: u32) {
        if UpgradeableContract::is_paused_for_upgrade(&env) {
            panic!("Contract is paused for upgrade");
        }
        governance::evaluate_proposal(env, proposal_id)
    }

    /// Executes a proposal after timelock period
    pub fn execute_proposal(env: Env, proposal_id: u32) {
        if UpgradeableContract::is_paused_for_upgrade(&env) {
            panic!("Contract is paused for upgrade");
        }
        governance::execute_proposal(env, proposal_id)
    }

    /// Cancels an active proposal
    pub fn cancel_proposal(env: Env, caller: Address, proposal_id: u32) {
        if UpgradeableContract::is_paused_for_upgrade(&env) {
            panic!("Contract is paused for upgrade");
        }
        governance::cancel_proposal(env, caller, proposal_id)
    }

    /// Amends the metadata of an active proposal
    pub fn amend_proposal(env: Env, proposer: Address, proposal_id: u32, new_metadata: String) {
        if UpgradeableContract::is_paused_for_upgrade(&env) {
            panic!("Contract is paused for upgrade");
        }
        governance::amend_proposal(env, proposer, proposal_id, new_metadata)
    }

    /// Delegates voting power to another address
    pub fn delegate_vote(env: Env, delegator: Address, delegate: Address) {
        if UpgradeableContract::is_paused_for_upgrade(&env) {
            panic!("Contract is paused for upgrade");
        }
        governance::delegate_vote(env, delegator, delegate)
    }

    /// Removes vote delegation
    pub fn undelegate_vote(env: Env, delegator: Address) {
        if UpgradeableContract::is_paused_for_upgrade(&env) {
            panic!("Contract is paused for upgrade");
        }
        governance::undelegate_vote(env, delegator)
    }

    /// Pauses the contract (admin only)
    pub fn pause_contract(env: Env, admin: Address) {
        governance::pause_contract(env, admin)
    }

    /// Unpauses the contract (admin only)
    pub fn unpause_contract(env: Env, admin: Address) {
        governance::unpause_contract(env, admin)
    }

    /// Updates contract parameters (admin only)
    pub fn update_parameters(env: Env, admin: Address, quorum: Option<u32>, voting_period: Option<u64>, min_stake: Option<u32>, timelock_delay: Option<u64>) {
        if UpgradeableContract::is_paused_for_upgrade(&env) {
            panic!("Contract is paused for upgrade");
        }
        governance::update_parameters(env, admin, quorum, voting_period, min_stake, timelock_delay)
    }

    /// Retrieves details of a proposal
    pub fn get_proposal_info(env: Env, proposal_id: u32) -> Proposal {
        governance::get_proposal_info(env, proposal_id)
    }

    /// Gets delegation info for an address
    pub fn get_delegation_info(env: Env, address: Address) -> Option<Delegation> {
        governance::get_delegation_info(env, address)
    }

    /// Gets effective voting power for an address
    pub fn get_voting_power(env: Env, address: Address) -> u32 {
        governance::get_voting_power(env, address)
    }

    /// Sets a token balance (admin only)
    pub fn set_token_balance(env: Env, admin: Address, address: Address, balance: u32) {
        if UpgradeableContract::is_paused_for_upgrade(&env) {
            panic!("Contract is paused for upgrade");
        }
        governance::set_token_balance(env, admin, address, balance)
    }

    // ===== UPGRADEABILITY FUNCTIONS =====

    /// Propose an upgrade (upgrade admin only)
    pub fn propose_upgrade(env: Env, caller: Address, new_implementation: Address, version: u32, reason: String) {
        UpgradeableContract::propose_upgrade(&env, caller, new_implementation, version, reason)
    }

    /// Execute a pending upgrade (upgrade admin only)
    pub fn execute_upgrade(env: Env, caller: Address) {
        UpgradeableContract::execute_upgrade(&env, caller)
    }

    /// Cancel a pending upgrade (upgrade admin only)
    pub fn cancel_upgrade(env: Env, caller: Address) {
        UpgradeableContract::cancel_upgrade(&env, caller)
    }

    /// Get current implementation address
    pub fn get_implementation(env: Env) -> Address {
        UpgradeableContract::get_implementation(&env)
    }

    /// Get upgrade admin address
    pub fn get_upgrade_admin(env: Env) -> Address {
        UpgradeableContract::get_upgrade_admin(&env)
    }

    /// Get pending upgrade info
    pub fn get_pending_upgrade(env: Env) -> Option<shared::upgradeability::UpgradeInfo> {
        UpgradeableContract::get_pending_upgrade(&env)
    }

    /// Get upgrade history
    pub fn get_upgrade_history(env: Env) -> Vec<shared::upgradeability::UpgradeHistoryEntry> {
        UpgradeableContract::get_upgrade_history(&env)
    }

    /// Check if upgrade is pending
    pub fn is_upgrade_pending(env: Env) -> bool {
        UpgradeableContract::is_upgrade_pending(&env)
    }

    /// Set upgrade delay (upgrade admin only)
    pub fn set_upgrade_delay(env: Env, admin: Address, delay: u64) {
        UpgradeableContract::set_upgrade_delay(&env, admin, delay)
    }

    /// Get upgrade delay
    pub fn get_upgrade_delay(env: Env) -> u64 {
        UpgradeableContract::get_upgrade_delay(&env)
    }

    /// Pause contract for upgrade (upgrade admin only)
    pub fn pause_for_upgrade(env: Env, admin: Address) {
        UpgradeableContract::pause_for_upgrade(&env, admin)
    }

    /// Unpause contract after upgrade (upgrade admin only)
    pub fn unpause_after_upgrade(env: Env, admin: Address) {
        UpgradeableContract::unpause_after_upgrade(&env, admin)
    }

    /// Transfer upgrade admin (current admin only)
    pub fn transfer_upgrade_admin(env: Env, current_admin: Address, new_admin: Address) {
        UpgradeableContract::transfer_upgrade_admin(&env, current_admin, new_admin)
    }

    /// Get contract version
    pub fn get_contract_version(env: Env) -> u32 {
        UpgradeableContract::get_contract_version(&env)
    }
}
