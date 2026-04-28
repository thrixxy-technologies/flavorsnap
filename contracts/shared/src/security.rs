use soroban_sdk::{contracttype, Address, Env, Vec, String};

/// Security audit storage keys
#[contracttype]
pub enum SecurityKey {
    AuditLog,              // Security audit log
    SecurityLevel,         // Current security level
    AccessControl,         // Access control settings
    SecurityEvents,        // Security events log
    VulnerabilityReports,  // Vulnerability reports
    SecurityAdmin,         // Security admin address
    EmergencyPause,        // Emergency pause state
    RateLimits,           // Rate limiting configuration
    Whitelist,            // Whitelisted addresses
    Blacklist,             // Blacklisted addresses
    SecurityPolicies,      // Security policies configuration
}

/// Security audit log entry
#[contracttype]
#[derive(Clone)]
pub struct AuditLogEntry {
    pub timestamp: u64,
    pub event_type: SecurityEventType,
    pub actor: Address,
    pub action: String,
    pub result: SecurityResult,
    pub details: String,
    pub severity: SecuritySeverity,
}

/// Security event types
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum SecurityEventType {
    AccessControl,
    Authentication,
    Authorization,
    DataModification,
    ConfigurationChange,
    Upgrade,
    EmergencyAction,
    VulnerabilityDiscovery,
    RateLimitExceeded,
    SuspiciousActivity,
}

/// Security operation results
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum SecurityResult {
    Success,
    Failure,
    Blocked,
    Warning,
    Error,
}

/// Security severity levels
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum SecuritySeverity {
    Low,
    Medium,
    High,
    Critical,
}

/// Access control configuration
#[contracttype]
#[derive(Clone)]
pub struct AccessControlConfig {
    pub require_multisig: bool,
    pub required_signatures: u32,
    pub time_lock_period: u64,
    pub allowed_actions: Vec<String>,
    pub restricted_actions: Vec<String>,
}

/// Security event
#[contracttype]
#[derive(Clone)]
pub struct SecurityEvent {
    pub id: u32,
    pub timestamp: u64,
    pub event_type: SecurityEventType,
    pub severity: SecuritySeverity,
    pub description: String,
    pub affected_addresses: Vec<Address>,
    pub resolved: bool,
    pub resolution: String,
}

/// Vulnerability report
#[contracttype]
#[derive(Clone)]
pub struct VulnerabilityReport {
    pub id: u32,
    pub reporter: Address,
    pub severity: SecuritySeverity,
    pub category: String,
    pub description: String,
    pub affected_components: Vec<String>,
    pub recommended_fix: String,
    pub status: VulnerabilityStatus,
    pub reported_at: u64,
    pub resolved_at: Option<u64>,
}

/// Vulnerability status
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum VulnerabilityStatus {
    Open,
    Investigating,
    Confirmed,
    InProgress,
    Resolved,
    FalsePositive,
}

/// Rate limiting configuration
#[contracttype]
#[derive(Clone)]
pub struct RateLimitConfig {
    pub window_size: u64,      // Time window in seconds
    pub max_requests: u32,     // Max requests per window
    pub penalty_period: u64,   // Penalty period for violations
    pub penalty_multiplier: u32, // Penalty multiplier
}

/// Security policy
#[contracttype]
#[derive(Clone)]
pub struct SecurityPolicy {
    pub name: String,
    pub version: u32,
    pub enabled: bool,
    pub rules: Vec<SecurityRule>,
    pub last_updated: u64,
}

/// Security rule
#[contracttype]
#[derive(Clone)]
pub struct SecurityRule {
    pub name: String,
    pub condition: String,
    pub action: SecurityAction,
    pub severity: SecuritySeverity,
    pub enabled: bool,
}

/// Security actions
#[contracttype]
#[derive(Clone, PartialEq, Debug)]
pub enum SecurityAction {
    Allow,
    Block,
    Log,
    Alert,
    Pause,
    EmergencyStop,
}

/// Main security audit implementation
pub struct SecurityAudit;

impl SecurityAudit {
    /// Initialize security audit system
    pub fn initialize(env: &Env, security_admin: Address) {
        if env.storage().instance().has(&SecurityKey::SecurityAdmin) {
            panic!("Security audit already initialized");
        }
        
        env.storage().instance().set(&SecurityKey::SecurityAdmin, &security_admin);
        env.storage().instance().set(&SecurityKey::SecurityLevel, &SecuritySeverity::Medium);
        env.storage().instance().set(&SecurityKey::EmergencyPause, &false);
        
        // Initialize access control with secure defaults
        let default_access_control = AccessControlConfig {
            require_multisig: true,
            required_signatures: 2,
            time_lock_period: 86400, // 24 hours
            allowed_actions: Vec::new(&env),
            restricted_actions: Vec::new(&env),
        };
        env.storage().instance().set(&SecurityKey::AccessControl, &default_access_control);
        
        // Initialize rate limiting
        let default_rate_limit = RateLimitConfig {
            window_size: 60, // 1 minute
            max_requests: 100,
            penalty_period: 300, // 5 minutes
            penalty_multiplier: 2,
        };
        env.storage().instance().set(&SecurityKey::RateLimits, &default_rate_limit);
        
        // Log initialization
        Self::log_security_event(
            env,
            SecurityEventType::ConfigurationChange,
            security_admin,
            "Security audit system initialized",
            SecurityResult::Success,
            SecuritySeverity::Low,
            "Security audit system initialized with default configuration"
        );
    }
    
    /// Log security event
    pub fn log_security_event(
        env: &Env,
        event_type: SecurityEventType,
        actor: Address,
        action: &str,
        result: SecurityResult,
        severity: SecuritySeverity,
        details: &str,
    ) {
        let log_entry = AuditLogEntry {
            timestamp: env.ledger().timestamp(),
            event_type,
            actor,
            action: String::from_str(env, action),
            result,
            severity,
            details: String::from_str(env, details),
        };
        
        let mut audit_log: Vec<AuditLogEntry> = env.storage().instance()
            .get(&SecurityKey::AuditLog)
            .unwrap_or_else(|| Vec::new(env));
        
        audit_log.push_back(log_entry);
        
        // Keep only last 1000 entries to save storage
        if audit_log.len() > 1000 {
            audit_log.remove(0);
        }
        
        env.storage().instance().set(&SecurityKey::AuditLog, &audit_log);
        
        // Emit security event
        env.events().publish(
            ("security_event",),
            (event_type, actor, severity, String::from_str(env, action))
        );
    }
    
    /// Check access control
    pub fn check_access_control(
        env: &Env,
        caller: Address,
        action: &str,
        require_multisig: bool,
    ) -> bool {
        let access_config: AccessControlConfig = env.storage().instance()
            .get(&SecurityKey::AccessControl)
            .unwrap_or_else(|| panic!("Access control not configured"));
        
        // Check if action is restricted
        if access_config.restricted_actions.contains(&String::from_str(env, action)) {
            Self::log_security_event(
                env,
                SecurityEventType::AccessControl,
                caller,
                action,
                SecurityResult::Blocked,
                SecuritySeverity::High,
                "Attempted restricted action"
            );
            return false;
        }
        
        // Check multisig requirement
        if access_config.require_multisig && !require_multisig {
            Self::log_security_event(
                env,
                SecurityEventType::AccessControl,
                caller,
                action,
                SecurityResult::Failure,
                SecuritySeverity::Medium,
                "Multisig required but not provided"
            );
            return false;
        }
        
        // Check time lock
        if access_config.time_lock_period > 0 {
            let current_time = env.ledger().timestamp();
            // In a real implementation, check against last action timestamp
            // For now, allow all actions
        }
        
        Self::log_security_event(
            env,
            SecurityEventType::AccessControl,
            caller,
            action,
            SecurityResult::Success,
            SecuritySeverity::Low,
            "Access control check passed"
        );
        
        true
    }
    
    /// Check rate limiting
    pub fn check_rate_limit(env: &Env, caller: Address, action: &str) -> bool {
        let rate_config: RateLimitConfig = env.storage().instance()
            .get(&SecurityKey::RateLimits)
            .unwrap_or_else(|| panic!("Rate limiting not configured"));
        
        let current_time = env.ledger().timestamp();
        let window_start = current_time - rate_config.window_size;
        
        // Count requests in current window
        let rate_limit_key = format!("rate_limit_{}_{}", caller, action);
        let request_count = Self::get_request_count(env, &rate_limit_key, window_start);
        
        if request_count > rate_config.max_requests {
            Self::log_security_event(
                env,
                SecurityEventType::RateLimitExceeded,
                caller,
                action,
                SecurityResult::Blocked,
                SecuritySeverity::Medium,
                &format!("Rate limit exceeded: {} requests", request_count)
            );
            return false;
        }
        
        // Record this request
        Self::record_request(env, &rate_limit_key, current_time);
        
        true
    }
    
    /// Get request count for rate limiting
    fn get_request_count(env: &Env, key: &str, window_start: u64) -> u32 {
        // In a real implementation, this would query stored request timestamps
        // For now, return 0 as placeholder
        0
    }
    
    /// Record request for rate limiting
    fn record_request(env: &Env, key: &str, timestamp: u64) {
        // In a real implementation, this would store the request timestamp
        // For now, do nothing
    }
    
    /// Check if address is whitelisted
    pub fn is_whitelisted(env: &Env, address: &Address) -> bool {
        let whitelist: Vec<Address> = env.storage().instance()
            .get(&SecurityKey::Whitelist)
            .unwrap_or_else(|| Vec::new(env));
        
        whitelist.contains(address)
    }
    
    /// Check if address is blacklisted
    pub fn is_blacklisted(env: &Env, address: &Address) -> bool {
        let blacklist: Vec<Address> = env.storage().instance()
            .get(&SecurityKey::Blacklist)
            .unwrap_or_else(|| Vec::new(env));
        
        blacklist.contains(address)
    }
    
    /// Add address to whitelist (security admin only)
    pub fn add_to_whitelist(env: &Env, admin: Address, address: Address) {
        if !Self::is_security_admin(env, &admin) {
            panic!("Only security admin can modify whitelist");
        }
        
        let mut whitelist: Vec<Address> = env.storage().instance()
            .get(&SecurityKey::Whitelist)
            .unwrap_or_else(|| Vec::new(env));
        
        if !whitelist.contains(&address) {
            whitelist.push_back(address);
            env.storage().instance().set(&SecurityKey::Whitelist, &whitelist);
            
            Self::log_security_event(
                env,
                SecurityEventType::ConfigurationChange,
                admin,
                "add_to_whitelist",
                SecurityResult::Success,
                SecuritySeverity::Low,
                &format!("Address added to whitelist: {}", address)
            );
        }
    }
    
    /// Add address to blacklist (security admin only)
    pub fn add_to_blacklist(env: &Env, admin: Address, address: Address) {
        if !Self::is_security_admin(env, &admin) {
            panic!("Only security admin can modify blacklist");
        }
        
        let mut blacklist: Vec<Address> = env.storage().instance()
            .get(&SecurityKey::Blacklist)
            .unwrap_or_else(|| Vec::new(env));
        
        if !blacklist.contains(&address) {
            blacklist.push_back(address);
            env.storage().instance().set(&SecurityKey::Blacklist, &blacklist);
            
            Self::log_security_event(
                env,
                SecurityEventType::ConfigurationChange,
                admin,
                "add_to_blacklist",
                SecurityResult::Success,
                SecuritySeverity::Medium,
                &format!("Address added to blacklist: {}", address)
            );
        }
    }
    
    /// Report vulnerability
    pub fn report_vulnerability(
        env: &Env,
        reporter: Address,
        severity: SecuritySeverity,
        category: String,
        description: String,
        affected_components: Vec<String>,
        recommended_fix: String,
    ) -> u32 {
        let vulnerability_id = Self::next_vulnerability_id(env);
        
        let report = VulnerabilityReport {
            id: vulnerability_id,
            reporter,
            severity,
            category,
            description,
            affected_components,
            recommended_fix,
            status: VulnerabilityStatus::Open,
            reported_at: env.ledger().timestamp(),
            resolved_at: None,
        };
        
        let mut reports: Vec<VulnerabilityReport> = env.storage().instance()
            .get(&SecurityKey::VulnerabilityReports)
            .unwrap_or_else(|| Vec::new(env));
        
        reports.push_back(report);
        env.storage().instance().set(&SecurityKey::VulnerabilityReports, &reports);
        
        Self::log_security_event(
            env,
            SecurityEventType::VulnerabilityDiscovery,
            reporter,
            "vulnerability_reported",
            SecurityResult::Success,
            severity,
            &format!("Vulnerability reported: {}", vulnerability_id)
        );
        
        vulnerability_id
    }
    
    /// Resolve vulnerability (security admin only)
    pub fn resolve_vulnerability(env: &Env, admin: Address, vulnerability_id: u32, resolution: String) {
        if !Self::is_security_admin(env, &admin) {
            panic!("Only security admin can resolve vulnerabilities");
        }
        
        let mut reports: Vec<VulnerabilityReport> = env.storage().instance()
            .get(&SecurityKey::VulnerabilityReports)
            .unwrap_or_else(|| Vec::new(env));
        
        for report in reports.iter_mut() {
            if report.id == vulnerability_id {
                report.status = VulnerabilityStatus::Resolved;
                report.resolved_at = Some(env.ledger().timestamp());
                
                env.storage().instance().set(&SecurityKey::VulnerabilityReports, &reports);
                
                Self::log_security_event(
                    env,
                    SecurityEventType::VulnerabilityDiscovery,
                    admin,
                    "vulnerability_resolved",
                    SecurityResult::Success,
                    SecuritySeverity::Low,
                    &format!("Vulnerability resolved: {}", vulnerability_id)
                );
                
                return;
            }
        }
        
        panic!("Vulnerability not found");
    }
    
    /// Emergency pause (security admin only)
    pub fn emergency_pause(env: &Env, admin: Address, reason: String) {
        if !Self::is_security_admin(env, &admin) {
            panic!("Only security admin can emergency pause");
        }
        
        env.storage().instance().set(&SecurityKey::EmergencyPause, &true);
        
        Self::log_security_event(
            env,
            SecurityEventType::EmergencyAction,
            admin,
            "emergency_pause",
            SecurityResult::Success,
            SecuritySeverity::Critical,
            &format!("Emergency pause activated: {}", reason)
        );
        
        // Emit emergency event
        env.events().publish(("emergency_pause",), (admin, reason));
    }
    
    /// Lift emergency pause (security admin only)
    pub fn lift_emergency_pause(env: &Env, admin: Address) {
        if !Self::is_security_admin(env, &admin) {
            panic!("Only security admin can lift emergency pause");
        }
        
        env.storage().instance().set(&SecurityKey::EmergencyPause, &false);
        
        Self::log_security_event(
            env,
            SecurityEventType::EmergencyAction,
            admin,
            "lift_emergency_pause",
            SecurityResult::Success,
            SecuritySeverity::High,
            "Emergency pause lifted"
        );
        
        // Emit resume event
        env.events().publish(("emergency_resume",), admin);
    }
    
    /// Check if emergency pause is active
    pub fn is_emergency_paused(env: &Env) -> bool {
        env.storage().instance().get(&SecurityKey::EmergencyPause).unwrap_or(false)
    }
    
    /// Get security audit log
    pub fn get_audit_log(env: &Env) -> Vec<AuditLogEntry> {
        env.storage().instance()
            .get(&SecurityKey::AuditLog)
            .unwrap_or_else(|| Vec::new(env))
    }
    
    /// Get vulnerability reports
    pub fn get_vulnerability_reports(env: &Env) -> Vec<VulnerabilityReport> {
        env.storage().instance()
            .get(&SecurityKey::VulnerabilityReports)
            .unwrap_or_else(|| Vec::new(env))
    }
    
    /// Get security level
    pub fn get_security_level(env: &Env) -> SecuritySeverity {
        env.storage().instance()
            .get(&SecurityKey::SecurityLevel)
            .unwrap_or(SecuritySeverity::Medium)
    }
    
    /// Set security level (security admin only)
    pub fn set_security_level(env: &Env, admin: Address, level: SecuritySeverity) {
        if !Self::is_security_admin(env, &admin) {
            panic!("Only security admin can set security level");
        }
        
        env.storage().instance().set(&SecurityKey::SecurityLevel, &level);
        
        Self::log_security_event(
            env,
            SecurityEventType::ConfigurationChange,
            admin,
            "set_security_level",
            SecurityResult::Success,
            SecuritySeverity::Medium,
            &format!("Security level set to: {:?}", level)
        );
    }
    
    /// Check if caller is security admin
    fn is_security_admin(env: &Env, caller: &Address) -> bool {
        let security_admin: Address = env.storage().instance()
            .get(&SecurityKey::SecurityAdmin)
            .unwrap_or_else(|| panic!("Security admin not set"));
        
        *caller == security_admin
    }
    
    /// Get next vulnerability ID
    fn next_vulnerability_id(env: &Env) -> u32 {
        let reports: Vec<VulnerabilityReport> = env.storage().instance()
            .get(&SecurityKey::VulnerabilityReports)
            .unwrap_or_else(|| Vec::new(env));
        
        let max_id = reports.iter().map(|r| r.id).max().unwrap_or(0);
        max_id + 1
    }
    
    /// Comprehensive security check before any operation
    pub fn pre_operation_security_check(
        env: &Env,
        caller: Address,
        action: &str,
        require_multisig: bool,
    ) -> Result<(), String> {
        // Check emergency pause
        if Self::is_emergency_paused(env) {
            return Err("Contract is under emergency pause".to_string());
        }
        
        // Check blacklist
        if Self::is_blacklisted(env, &caller) {
            Self::log_security_event(
                env,
                SecurityEventType::AccessControl,
                caller,
                action,
                SecurityResult::Blocked,
                SecuritySeverity::High,
                "Blacklisted address attempted operation"
            );
            return Err("Address is blacklisted".to_string());
        }
        
        // Check rate limiting
        if !Self::check_rate_limit(env, caller.clone(), action) {
            return Err("Rate limit exceeded".to_string());
        }
        
        // Check access control
        if !Self::check_access_control(env, caller.clone(), action, require_multisig) {
            return Err("Access control check failed".to_string());
        }
        
        // Check whitelist if configured
        if !Self::is_whitelisted(env, &caller) {
            // In strict mode, require whitelist
            let security_level = Self::get_security_level(env);
            if security_level == SecuritySeverity::Critical {
                Self::log_security_event(
                    env,
                    SecurityEventType::AccessControl,
                    caller,
                    action,
                    SecurityResult::Blocked,
                    SecuritySeverity::High,
                    "Address not whitelisted in critical security mode"
                );
                return Err("Address not whitelisted".to_string());
            }
        }
        
        Ok(())
    }
}
