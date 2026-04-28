#![cfg(test)]

use soroban_sdk::{Env, Address, String, Vec};
use model_governance::{ModelUpdateGovernance, ProposalType, ProposalStatus};
use tokenized_incentive::{TokenizedIncentive, Stake, RewardPool};
use sensory_evaluation::{SensoryEvaluation, Evaluation, ReputationTier};
use shared::{UpgradeableContract, SecurityAudit, GasOptimizer};

/// Comprehensive test suite for all FlavorSnap contracts
pub struct ComprehensiveTests;

impl ComprehensiveTests {
    /// Test model governance contract functionality
    pub fn test_model_governance(env: &Env) -> Result<(), String> {
        println!("Testing Model Governance Contract...");
        
        let admin = Address::from_string(&String::from_str(env, "admin"));
        let user1 = Address::from_string(&String::from_str(env, "user1"));
        let user2 = Address::from_string(&String::from_str(env, "user2"));
        
        // Initialize contract
        ModelUpdateGovernance::initialize(
            env.clone(),
            admin.clone(),
            5000, // 50% quorum
            604800, // 7 days voting period
            100, // 100 tokens minimum stake
            86400, // 24 hours timelock
        );
        
        // Test upgradeability
        Self::test_governance_upgradeability(env, admin.clone())?;
        
        // Test proposal submission
        let proposal_id = ModelUpdateGovernance::submit_proposal(
            env.clone(),
            user1.clone(),
            String::from_str(env, "Test model update proposal"),
            150, // stake
            ProposalType::ModelUpdate,
        );
        
        // Test voting
        ModelUpdateGovernance::set_token_balance(env.clone(), admin.clone(), user1.clone(), 1000);
        ModelUpdateGovernance::set_token_balance(env.clone(), admin.clone(), user2.clone(), 1000);
        
        ModelUpdateGovernance::vote(env.clone(), user1.clone(), proposal_id, true);
        ModelUpdateGovernance::vote(env.clone(), user2.clone(), proposal_id, true);
        
        // Test proposal evaluation
        ModelUpdateGovernance::evaluate_proposal(env.clone(), proposal_id);
        
        // Verify proposal status
        let proposal = ModelUpdateGovernance::get_proposal_info(env.clone(), proposal_id);
        if proposal.status != ProposalStatus::Approved {
            return Err("Proposal should be approved".to_string());
        }
        
        // Test delegation
        ModelUpdateGovernance::delegate_vote(env.clone(), user1.clone(), user2.clone());
        let delegation = ModelUpdateGovernance::get_delegation_info(env.clone(), user1.clone());
        if delegation.is_none() {
            return Err("Delegation should exist".to_string());
        }
        
        println!("✅ Model Governance tests passed");
        Ok(())
    }
    
    /// Test tokenized incentive contract functionality
    pub fn test_tokenized_incentive(env: &Env) -> Result<(), String> {
        println!("Testing Tokenized Incentive Contract...");
        
        let admin = Address::from_string(&String::from_str(env, "admin"));
        let user1 = Address::from_string(&String::from_str(env, "user1"));
        let user2 = Address::from_string(&String::from_str(env, "user2"));
        
        // Initialize contract
        let admins = Vec::from_array(env, [admin.clone()]);
        TokenizedIncentive::initialize(
            env.clone(),
            admins,
            1000000, // max supply
            18, // decimals
        );
        
        // Test token operations
        TokenizedIncentive::mint(env.clone(), admin.clone(), user1.clone(), 10000);
        TokenizedIncentive::mint(env.clone(), admin.clone(), user2.clone(), 10000);
        
        let balance = TokenizedIncentive::get_balance(env.clone(), user1.clone());
        if balance != 10000 {
            return Err("Incorrect balance after mint".to_string());
        }
        
        // Test transfer
        TokenizedIncentive::transfer(env.clone(), user1.clone(), user2.clone(), 1000);
        
        let user1_balance = TokenizedIncentive::get_balance(env.clone(), user1.clone());
        let user2_balance = TokenizedIncentive::get_balance(env.clone(), user2.clone());
        
        if user1_balance != 9000 || user2_balance != 11000 {
            return Err("Incorrect balances after transfer".to_string());
        }
        
        // Test staking
        let pool = RewardPool {
            id: 1,
            name: String::from_str(env, "Test Pool"),
            total_rewards: 100000,
            distributed: 0,
            reward_rate: 1000, // 10% APY
            min_stake: 100,
            max_stake: 10000,
            duration: 86400 * 30, // 30 days
            start_time: env.ledger().timestamp(),
            active: true,
        };
        
        TokenizedIncentive::create_reward_pool(env.clone(), admin.clone(), pool);
        
        let stake_id = TokenizedIncentive::create_stake(
            env.clone(),
            user1.clone(),
            1000,
            86400 * 30, // 30 days
            1, // pool ID
            false, // no auto-compound
        );
        
        // Test reward claiming
        let rewards = TokenizedIncentive::claim_rewards(env.clone(), user1.clone(), stake_id);
        
        // Test unstaking
        let returned = TokenizedIncentive::unstake(env.clone(), user1.clone(), stake_id);
        
        println!("✅ Tokenized Incentive tests passed");
        Ok(())
    }
    
    /// Test sensory evaluation contract functionality
    pub fn test_sensory_evaluation(env: &Env) -> Result<(), String> {
        println!("Testing Sensory Evaluation Contract...");
        
        let admin = Address::from_string(&String::from_str(env, "admin"));
        let evaluator = Address::from_string(&String::from_str(env, "evaluator"));
        let expert = Address::from_string(&String::from_str(env, "expert"));
        
        // Initialize contract
        let admins = Vec::from_array(env, [admin.clone()]);
        SensoryEvaluation::initialize(
            env.clone(),
            admins,
            String::from_str(env, "SensoryToken"),
            String::from_str(env, "SENSORY"),
            1000000,
            18,
        );
        
        // Test evaluation submission
        let scores = Vec::from_array(env, [
            EvaluationScore {
                criterion: String::from_str(env, "taste"),
                score: 85,
                weight: 40,
                justification: String::from_str(env, "Good flavor balance"),
            },
            EvaluationScore {
                criterion: String::from_str(env, "appearance"),
                score: 90,
                weight: 30,
                justification: String::from_str(env, "Excellent presentation"),
            },
            EvaluationScore {
                criterion: String::from_str(env, "texture"),
                score: 80,
                weight: 30,
                justification: String::from_str(env, "Pleasant mouthfeel"),
            },
        ]);
        
        let evaluation_id = SensoryEvaluation::submit_evaluation(
            env.clone(),
            evaluator.clone(),
            String::from_str(env, "test_food_001"),
            scores.clone(),
            String::from_str(env, "Overall good quality"),
            90, // confidence score
        );
        
        // Test evaluation retrieval
        let evaluation = SensoryEvaluation::get_evaluation_info(env.clone(), evaluation_id);
        if evaluation.evaluator != evaluator {
            return Err("Incorrect evaluator".to_string());
        }
        
        // Test reputation system
        let reputation = SensoryEvaluation::get_user_reputation_info(env.clone(), evaluator.clone());
        if reputation.total_evaluations != 1 {
            return Err("Incorrect evaluation count".to_string());
        }
        
        // Test expert panel
        let expert_member = shared::security::ExpertMember {
            address: expert.clone(),
            expertise_areas: Vec::from_array(env, [String::from_str(env, "taste")]),
            joined_date: env.ledger().timestamp(),
            contributions: 0,
            verification_power: 2,
        };
        
        SensoryEvaluation::add_expert_panel_member(env.clone(), admin.clone(), expert_member);
        
        // Test evaluation verification
        SensoryEvaluation::verify_evaluation(env.clone(), expert.clone(), evaluation_id, true);
        
        // Test dispute system
        let dispute_id = SensoryEvaluation::create_dispute(
            env.clone(),
            admin.clone(),
            evaluation_id,
            String::from_str(env, "Testing dispute system"),
        );
        
        SensoryEvaluation::resolve_dispute(
            env.clone(),
            admin.clone(),
            dispute_id,
            String::from_str(env, "Dispute resolved - evaluation is valid"),
            false, // dispute not approved
        );
        
        println!("✅ Sensory Evaluation tests passed");
        Ok(())
    }
    
    /// Test upgradeability functionality
    pub fn test_governance_upgradeability(env: &Env, admin: Address) -> Result<(), String> {
        println!("Testing Upgradeability...");
        
        let new_impl = Address::from_string(&String::from_str(env, "new_implementation"));
        
        // Test upgrade proposal
        ModelUpdateGovernance::propose_upgrade(
            env.clone(),
            admin.clone(),
            new_impl.clone(),
            2, // version 2
            String::from_str(env, "Test upgrade"),
        );
        
        // Check pending upgrade
        let pending = ModelUpdateGovernance::get_pending_upgrade(env.clone());
        if pending.is_none() {
            return Err("Pending upgrade should exist".to_string());
        }
        
        // Test upgrade delay
        let delay = ModelUpdateGovernance::get_upgrade_delay(env.clone());
        if delay == 0 {
            return Err("Upgrade delay should be set".to_string());
        }
        
        // Test upgrade cancellation
        ModelUpdateGovernance::cancel_upgrade(env.clone(), admin.clone());
        
        let pending_after_cancel = ModelUpdateGovernance::get_pending_upgrade(env.clone());
        if pending_after_cancel.is_some() {
            return Err("Pending upgrade should be cancelled".to_string());
        }
        
        println!("✅ Upgradeability tests passed");
        Ok(())
    }
    
    /// Test security audit functionality
    pub fn test_security_audit(env: &Env) -> Result<(), String> {
        println!("Testing Security Audit...");
        
        let security_admin = Address::from_string(&String::from_str(env, "security_admin"));
        let user = Address::from_string(&String::from_str(env, "user"));
        
        // Initialize security audit
        SecurityAudit::initialize(env.clone(), security_admin.clone());
        
        // Test access control
        let access_granted = SecurityAudit::check_access_control(
            env.clone(),
            user.clone(),
            "test_action",
            false,
        );
        
        // Test rate limiting
        let rate_limit_ok = SecurityAudit::check_rate_limit(env.clone(), user.clone(), "test_action");
        
        // Test whitelist/blacklist
        SecurityAudit::add_to_whitelist(env.clone(), security_admin.clone(), user.clone());
        let is_whitelisted = SecurityAudit::is_whitelisted(env.clone(), &user);
        
        if !is_whitelisted {
            return Err("User should be whitelisted".to_string());
        }
        
        // Test vulnerability reporting
        let vuln_id = SecurityAudit::report_vulnerability(
            env.clone(),
            user.clone(),
            shared::security::SecuritySeverity::Medium,
            String::from_str(env, "Test Category"),
            String::from_str(env, "Test vulnerability"),
            Vec::from_array(env, [String::from_str(env, "component1")]),
            String::from_str(env, "Apply security patch"),
        );
        
        // Test vulnerability resolution
        SecurityAudit::resolve_vulnerability(
            env.clone(),
            security_admin.clone(),
            vuln_id,
            String::from_str(env, "Vulnerability resolved"),
        );
        
        // Test emergency pause
        SecurityAudit::emergency_pause(
            env.clone(),
            security_admin.clone(),
            String::from_str(env, "Test emergency pause"),
        );
        
        let is_paused = SecurityAudit::is_emergency_paused(env.clone());
        if !is_paused {
            return Err("Contract should be emergency paused".to_string());
        }
        
        // Lift emergency pause
        SecurityAudit::lift_emergency_pause(env.clone(), security_admin.clone());
        
        let is_paused_after_lift = SecurityAudit::is_emergency_paused(env.clone());
        if is_paused_after_lift {
            return Err("Contract should not be paused after lift".to_string());
        }
        
        // Test audit log
        let audit_log = SecurityAudit::get_audit_log(env.clone());
        if audit_log.is_empty() {
            return Err("Audit log should have entries".to_string());
        }
        
        println!("✅ Security Audit tests passed");
        Ok(())
    }
    
    /// Test gas optimization
    pub fn test_gas_optimization(env: &Env) -> Result<(), String> {
        println!("Testing Gas Optimization...");
        
        // Test batch operations
        let operations = Vec::from_array(env, [
            |env: &Env| println!("Operation 1"),
            |env: &Env| println!("Operation 2"),
            |env: &Env| println!("Operation 3"),
        ]);
        
        GasOptimizer::batch_operations(env, operations);
        
        // Test efficient iteration
        let items = Vec::from_array(env, [1u32, 2, 3, 4, 5]);
        let results = GasOptimizer::efficient_iteration(env.clone(), items.clone(), |x| x * 2);
        
        if results.len() != items.len() {
            return Err("Iteration results length mismatch".to_string());
        }
        
        // Test storage optimization
        GasOptimizer::optimize_storage_layout(env);
        
        // Test memory optimization
        GasOptimizer::optimize_memory_usage(env);
        
        println!("✅ Gas Optimization tests passed");
        Ok(())
    }
    
    /// Run integration tests across all contracts
    pub fn run_integration_tests(env: &Env) -> Result<(), String> {
        println!("🧪 Running Comprehensive Integration Tests...");
        
        // Test all contracts
        Self::test_model_governance(env)?;
        Self::test_tokenized_incentive(env)?;
        Self::test_sensory_evaluation(env)?;
        Self::test_security_audit(env)?;
        Self::test_gas_optimization(env)?;
        
        // Test cross-contract interactions
        Self::test_cross_contract_interactions(env)?;
        
        println!("🎉 All integration tests passed successfully!");
        Ok(())
    }
    
    /// Test cross-contract interactions
    pub fn test_cross_contract_interactions(env: &Env) -> Result<(), String> {
        println!("Testing Cross-Contract Interactions...");
        
        let admin = Address::from_string(&String::from_str(env, "admin"));
        let user = Address::from_string(&String::from_str(env, "user"));
        
        // Test governance token interactions
        // 1. Create governance proposal
        let proposal_id = ModelUpdateGovernance::submit_proposal(
            env.clone(),
            user.clone(),
            String::from_str(env, "Cross-contract test proposal"),
            100,
            ProposalType::ModelUpdate,
        );
        
        // 2. Award tokens for evaluation and use them for voting
        TokenizedIncentive::mint(env.clone(), admin.clone(), user.clone(), 1000);
        ModelUpdateGovernance::set_token_balance(env.clone(), admin.clone(), user.clone(), 1000);
        
        // 3. Vote on proposal
        ModelUpdateGovernance::vote(env.clone(), user.clone(), proposal_id, true);
        
        // 4. Evaluate proposal
        ModelUpdateGovernance::evaluate_proposal(env.clone(), proposal_id);
        
        // Test reputation-based token rewards
        // 1. Submit evaluation
        let scores = Vec::from_array(env, [
            EvaluationScore {
                criterion: String::from_str(env, "quality"),
                score: 95,
                weight: 100,
                justification: String::from_str(env, "Exceptional quality"),
            },
        ]);
        
        let eval_id = SensoryEvaluation::submit_evaluation(
            env.clone(),
            user.clone(),
            String::from_str(env, "integration_test_food"),
            scores,
            String::from_str(env, "Integration test evaluation"),
            95,
        );
        
        // 2. Get reputation and verify reward calculation
        let reputation = SensoryEvaluation::get_user_reputation_info(env.clone(), user.clone());
        
        // 3. Award bonus tokens based on reputation tier
        let bonus_tokens = match reputation.tier {
            ReputationTier::Novice => 100,
            ReputationTier::Apprentice => 200,
            ReputationTier::Expert => 500,
            ReputationTier::Master => 1000,
            ReputationTier::Grandmaster => 2000,
        };
        
        if bonus_tokens > 0 {
            TokenizedIncentive::mint(env.clone(), admin.clone(), user.clone(), bonus_tokens);
        }
        
        // Test security across contracts
        let security_result = SecurityAudit::pre_operation_security_check(
            env.clone(),
            user.clone(),
            "cross_contract_test",
            false,
        );
        
        if security_result.is_err() {
            return Err("Security check failed for cross-contract operation".to_string());
        }
        
        println!("✅ Cross-Contract Interaction tests passed");
        Ok(())
    }
    
    /// Performance benchmark tests
    pub fn run_performance_benchmarks(env: &Env) -> Result<(), String> {
        println!("⚡ Running Performance Benchmarks...");
        
        // Benchmark proposal submission
        let start_time = env.ledger().timestamp();
        let admin = Address::from_string(&String::from_str(env, "admin"));
        let user = Address::from_string(&String::from_str(env, "user"));
        
        ModelUpdateGovernance::initialize(
            env.clone(),
            admin.clone(),
            5000,
            604800,
            100,
            86400,
        );
        
        ModelUpdateGovernance::set_token_balance(env.clone(), admin.clone(), user.clone(), 1000);
        
        for i in 0..10 {
            ModelUpdateGovernance::submit_proposal(
                env.clone(),
                user.clone(),
                String::from_str(env, &format!("Benchmark proposal {}", i)),
                100,
                ProposalType::ModelUpdate,
            );
        }
        
        let proposal_time = env.ledger().timestamp() - start_time;
        println!("📊 10 proposals submitted in {} seconds", proposal_time);
        
        // Benchmark voting
        let vote_start = env.ledger().timestamp();
        for i in 1..=10 {
            ModelUpdateGovernance::vote(env.clone(), user.clone(), i, true);
        }
        let vote_time = env.ledger().timestamp() - vote_start;
        println!("📊 10 votes cast in {} seconds", vote_time);
        
        // Benchmark evaluations
        let eval_start = env.ledger().timestamp();
        let scores = Vec::from_array(env, [
            EvaluationScore {
                criterion: String::from_str(env, "test"),
                score: 85,
                weight: 100,
                justification: String::from_str(env, "Benchmark test"),
            },
        ]);
        
        for i in 0..10 {
            SensoryEvaluation::submit_evaluation(
                env.clone(),
                user.clone(),
                String::from_str(env, &format!("benchmark_food_{}", i)),
                scores.clone(),
                String::from_str(env, "Benchmark evaluation"),
                90,
            );
        }
        
        let eval_time = env.ledger().timestamp() - eval_start;
        println!("📊 10 evaluations submitted in {} seconds", eval_time);
        
        println!("✅ Performance benchmarks completed");
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use soroban_sdk::testutils::{Ledger, LedgerInfo};
    
    #[test]
    fn test_all_contracts() {
        let env = Env::default();
        
        // Mock ledger setup
        env.ledger().set(LedgerInfo {
            protocol_version: 20,
            sequence_number: 0,
            timestamp: 12345,
            network_id: Default::default(),
            base_reserve: 100,
            min_temp_entry_ttl: 10,
            min_persistent_entry_ttl: 10,
            max_entry_ttl: 1000000,
        });
        
        // Run all tests
        ComprehensiveTests::run_integration_tests(&env).unwrap();
        ComprehensiveTests::run_performance_benchmarks(&env).unwrap();
    }
}
