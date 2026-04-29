use soroban_sdk::{contracttype, Address, Env, Vec, String};

/// Upgradeability storage keys
#[contracttype]
pub enum UpgradeKey {
    Implementation,      // Current implementation contract address
    Admin,              // Upgrade admin address
    PendingImplementation, // Pending implementation for upgrade
    UpgradeDelay,       // Delay before upgrade can be executed
    PendingUpgradeTime, // Timestamp when pending upgrade can be executed
    UpgradeHistory,     // History of all upgrades
    ContractVersion,    // Current contract version
    Paused,            // Contract pause state for upgrades
}

/// Upgrade information
#[contracttype]
#[derive(Clone)]
pub struct UpgradeInfo {
    pub old_implementation: Address,
    pub new_implementation: Address,
    pub proposed_by: Address,
    pub timestamp: u64,
    pub reason: String,
    pub version: u32,
}

/// Upgrade history entry
#[contracttype]
#[derive(Clone)]
pub struct UpgradeHistoryEntry {
    pub implementation: Address,
    pub version: u32,
    pub timestamp: u64,
    pub upgraded_by: Address,
    pub reason: String,
}

/// Upgradeability trait for contracts
pub trait Upgradeable {
    /// Initialize upgradeability
    fn initialize_upgradeability(env: &Env, admin: Address, implementation: Address, version: u32);
    
    /// Propose an upgrade
    fn propose_upgrade(env: &Env, caller: Address, new_implementation: Address, version: u32, reason: String);
    
    /// Execute a pending upgrade
    fn execute_upgrade(env: &Env, caller: Address);
    
    /// Cancel a pending upgrade
    fn cancel_upgrade(env: &Env, caller: Address);
    
    /// Get current implementation
    fn get_implementation(env: &Env) -> Address;
    
    /// Get upgrade admin
    fn get_upgrade_admin(env: &Env) -> Address;
    
    /// Get pending upgrade
    fn get_pending_upgrade(env: &Env) -> Option<UpgradeInfo>;
    
    /// Get upgrade history
    fn get_upgrade_history(env: &Env) -> Vec<UpgradeHistoryEntry>;
    
    /// Check if upgrade is pending
    fn is_upgrade_pending(env: &Env) -> bool;
    
    /// Set upgrade delay (admin only)
    fn set_upgrade_delay(env: &Env, admin: Address, delay: u64);
    
    /// Get upgrade delay
    fn get_upgrade_delay(env: &Env) -> u64;
}

/// Default implementation of upgradeability
pub struct UpgradeableContract;

impl UpgradeableContract {
    /// Initialize upgradeability
    pub fn initialize_upgradeability(env: &Env, admin: Address, implementation: Address, version: u32) {
        if env.storage().instance().has(&UpgradeKey::Admin) {
            panic!("Upgradeability already initialized");
        }
        
        env.storage().instance().set(&UpgradeKey::Admin, &admin);
        env.storage().instance().set(&UpgradeKey::Implementation, &implementation);
        env.storage().instance().set(&UpgradeKey::ContractVersion, &version);
        env.storage().instance().set(&UpgradeKey::UpgradeDelay, &86400u64); // 24 hours default
        env.storage().instance().set(&UpgradeKey::Paused, &false);
        
        // Initialize upgrade history
        let history = Vec::new(env);
        env.storage().instance().set(&UpgradeKey::UpgradeHistory, &history);
    }
    
    /// Propose an upgrade
    pub fn propose_upgrade(env: &Env, caller: Address, new_implementation: Address, version: u32, reason: String) {
        caller.require_auth();
        
        // Check if caller is admin
        let admin: Address = env.storage().instance().get(&UpgradeKey::Admin).unwrap();
        if caller != admin {
            panic!("Only upgrade admin can propose upgrades");
        }
        
        // Check if upgrade is already pending
        if env.storage().instance().has(&UpgradeKey::PendingImplementation) {
            panic!("Upgrade already pending");
        }
        
        let current_implementation: Address = env.storage().instance().get(&UpgradeKey::Implementation).unwrap();
        let current_version: u32 = env.storage().instance().get(&UpgradeKey::ContractVersion).unwrap();
        
        if version <= current_version {
            panic!("New version must be greater than current version");
        }
        
        // Store pending upgrade
        env.storage().instance().set(&UpgradeKey::PendingImplementation, &new_implementation);
        env.storage().instance().set(&UpgradeKey::PendingUpgradeTime, &(env.ledger().timestamp()));
        
        let upgrade_info = UpgradeInfo {
            old_implementation: current_implementation,
            new_implementation,
            proposed_by: caller,
            timestamp: env.ledger().timestamp(),
            reason,
            version,
        };
        
        env.storage().instance().set(&UpgradeKey::PendingImplementation, &upgrade_info);
    }
    
    /// Execute a pending upgrade
    pub fn execute_upgrade(env: &Env, caller: Address) {
        caller.require_auth();
        
        // Check if caller is admin
        let admin: Address = env.storage().instance().get(&UpgradeKey::Admin).unwrap();
        if caller != admin {
            panic!("Only upgrade admin can execute upgrades");
        }
        
        // Check if upgrade is pending
        let pending_info: UpgradeInfo = env.storage().instance()
            .get(&UpgradeKey::PendingImplementation)
            .unwrap_or_else(|| panic!("No pending upgrade"));
        
        // Check if delay has passed
        let delay: u64 = env.storage().instance().get(&UpgradeKey::UpgradeDelay).unwrap();
        let pending_time: u64 = env.storage().instance().get(&UpgradeKey::PendingUpgradeTime).unwrap();
        
        if env.ledger().timestamp() < pending_time + delay {
            panic!("Upgrade delay not yet passed");
        }
        
        // Record upgrade in history
        let mut history: Vec<UpgradeHistoryEntry> = env.storage().instance()
            .get(&UpgradeKey::UpgradeHistory)
            .unwrap_or_else(|| Vec::new(env));
        
        let history_entry = UpgradeHistoryEntry {
            implementation: pending_info.new_implementation.clone(),
            version: pending_info.version,
            timestamp: env.ledger().timestamp(),
            upgraded_by: caller,
            reason: pending_info.reason.clone(),
        };
        
        history.push_back(history_entry);
        env.storage().instance().set(&UpgradeKey::UpgradeHistory, &history);
        
        // Execute upgrade
        env.storage().instance().set(&UpgradeKey::Implementation, &pending_info.new_implementation);
        env.storage().instance().set(&UpgradeKey::ContractVersion, &pending_info.version);
        
        // Clear pending upgrade
        env.storage().instance().remove(&UpgradeKey::PendingImplementation);
        env.storage().instance().remove(&UpgradeKey::PendingUpgradeTime);
    }
    
    /// Cancel a pending upgrade
    pub fn cancel_upgrade(env: &Env, caller: Address) {
        caller.require_auth();
        
        // Check if caller is admin
        let admin: Address = env.storage().instance().get(&UpgradeKey::Admin).unwrap();
        if caller != admin {
            panic!("Only upgrade admin can cancel upgrades");
        }
        
        // Clear pending upgrade
        if env.storage().instance().has(&UpgradeKey::PendingImplementation) {
            env.storage().instance().remove(&UpgradeKey::PendingImplementation);
            env.storage().instance().remove(&UpgradeKey::PendingUpgradeTime);
        }
    }
    
    /// Get current implementation
    pub fn get_implementation(env: &Env) -> Address {
        env.storage().instance()
            .get(&UpgradeKey::Implementation)
            .unwrap_or_else(|| panic!("No implementation set"))
    }
    
    /// Get upgrade admin
    pub fn get_upgrade_admin(env: &Env) -> Address {
        env.storage().instance()
            .get(&UpgradeKey::Admin)
            .unwrap_or_else(|| panic!("No upgrade admin set"))
    }
    
    /// Get pending upgrade
    pub fn get_pending_upgrade(env: &Env) -> Option<UpgradeInfo> {
        env.storage().instance().get(&UpgradeKey::PendingImplementation)
    }
    
    /// Get upgrade history
    pub fn get_upgrade_history(env: &Env) -> Vec<UpgradeHistoryEntry> {
        env.storage().instance()
            .get(&UpgradeKey::UpgradeHistory)
            .unwrap_or_else(|| Vec::new(env))
    }
    
    /// Check if upgrade is pending
    pub fn is_upgrade_pending(env: &Env) -> bool {
        env.storage().instance().has(&UpgradeKey::PendingImplementation)
    }
    
    /// Set upgrade delay (admin only)
    pub fn set_upgrade_delay(env: &Env, admin: Address, delay: u64) {
        admin.require_auth();
        
        let current_admin: Address = env.storage().instance().get(&UpgradeKey::Admin).unwrap();
        if admin != current_admin {
            panic!("Only upgrade admin can set upgrade delay");
        }
        
        env.storage().instance().set(&UpgradeKey::UpgradeDelay, &delay);
    }
    
    /// Get upgrade delay
    pub fn get_upgrade_delay(env: &Env) -> u64 {
        env.storage().instance()
            .get(&UpgradeKey::UpgradeDelay)
            .unwrap_or(86400u64)
    }
    
    /// Pause contract for upgrade (admin only)
    pub fn pause_for_upgrade(env: &Env, admin: Address) {
        admin.require_auth();
        
        let current_admin: Address = env.storage().instance().get(&UpgradeKey::Admin).unwrap();
        if admin != current_admin {
            panic!("Only upgrade admin can pause for upgrade");
        }
        
        env.storage().instance().set(&UpgradeKey::Paused, &true);
    }
    
    /// Unpause contract after upgrade (admin only)
    pub fn unpause_after_upgrade(env: &Env, admin: Address) {
        admin.require_auth();
        
        let current_admin: Address = env.storage().instance().get(&UpgradeKey::Admin).unwrap();
        if admin != current_admin {
            panic!("Only upgrade admin can unpause after upgrade");
        }
        
        env.storage().instance().set(&UpgradeKey::Paused, &false);
    }
    
    /// Check if contract is paused for upgrade
    pub fn is_paused_for_upgrade(env: &Env) -> bool {
        env.storage().instance().get(&UpgradeKey::Paused).unwrap_or(false)
    }
    
    /// Transfer upgrade admin (current admin only)
    pub fn transfer_upgrade_admin(env: &Env, current_admin: Address, new_admin: Address) {
        current_admin.require_auth();
        
        let admin: Address = env.storage().instance().get(&UpgradeKey::Admin).unwrap();
        if current_admin != admin {
            panic!("Only current upgrade admin can transfer admin rights");
        }
        
        env.storage().instance().set(&UpgradeKey::Admin, &new_admin);
    }
    
    /// Get contract version
    pub fn get_contract_version(env: &Env) -> u32 {
        env.storage().instance()
            .get(&UpgradeKey::ContractVersion)
            .unwrap_or(1)
    }
}

/// Proxy contract for upgradeable contracts
pub struct Proxy;

impl Proxy {
    /// Forward call to implementation
    pub fn forward_call(env: &Env, implementation: Address, data: Vec<u8>) -> Vec<u8> {
        // In a real implementation, this would use cross-contract calls
        // For now, return empty as placeholder
        Vec::new(env)
    }
    
    /// Get implementation address
    pub fn implementation(env: &Env) -> Address {
        UpgradeableContract::get_implementation(env)
    }
    
    /// Check if call should be allowed (not paused)
    pub fn allow_call(env: &Env) -> bool {
        !UpgradeableContract::is_paused_for_upgrade(env)
    }
}
