use crate::storage::*;
use crate::types::*;
use soroban_sdk::{Address, Env, Vec};

/// Submits a new sensory evaluation
pub fn submit_evaluation(
    env: Env,
    evaluator: Address,
    food_item_id: String,
    scores: Vec<EvaluationScore>,
    comments: String,
    confidence_score: u32,
) -> u32 {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    evaluator.require_auth();
    
    if confidence_score > 100 {
        panic!("Confidence score must be 0-100");
    }
    
    // Check evaluator reputation
    let reputation = get_user_reputation(&env, &evaluator);
    if reputation.score < 0 {
        panic!("Evaluator has negative reputation");
    }
    
    // Validate scores against criteria
    let criteria = get_evaluation_criteria(&env);
    validate_scores(&scores, &criteria, &reputation)?;
    
    // Create evaluation
    let evaluation_id = next_evaluation_id(&env);
    let current_time = env.ledger().timestamp();
    
    let evaluation = Evaluation {
        id: evaluation_id,
        evaluator: evaluator.clone(),
        food_item_id: food_item_id.clone(),
        scores: scores.clone(),
        comments,
        timestamp: current_time,
        verified: false,
        verification_count: 0,
        reward_earned: 0,
        confidence_score,
    };
    
    // Store evaluation
    store_evaluation(&env, &evaluation);
    
    // Update evaluator history
    let mut history = get_evaluation_history(&env, &evaluator);
    history.push_back(evaluation_id);
    store_evaluation_history(&env, &evaluator, &history);
    
    // Update reputation
    update_reputation_for_evaluation(&env, &evaluator, evaluation_id);
    
    // Calculate and award rewards
    let reward = calculate_evaluation_reward(&env, &evaluation, &reputation);
    award_evaluation_reward(&env, &evaluator, reward);
    
    evaluation_id
}

/// Verifies an evaluation (expert panel members only)
pub fn verify_evaluation(env: Env, verifier: Address, evaluation_id: u32, approve: bool) {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    verifier.require_auth();
    
    // Check if verifier is in expert panel
    if !is_expert_panel_member(&env, &verifier) {
        panic!("Only expert panel members can verify evaluations");
    }
    
    // Get evaluation
    let mut evaluation = get_evaluation(&env, evaluation_id);
    if evaluation.verified {
        panic!("Evaluation already verified");
    }
    
    // Update verification count
    evaluation.verification_count += 1;
    
    // Check if verification threshold is met
    let expert_panel = get_expert_panel(&env);
    let required_verifications = (expert_panel.len() as u32 + 1) / 2; // Majority
    
    if evaluation.verification_count >= required_verifications {
        evaluation.verified = true;
        
        // Update evaluator reputation bonus for verification
        let reputation_bonus = if approve { 10 } else { -5 };
        update_reputation_score(&env, &evaluation.evaluator, reputation_bonus, "Evaluation verified");
    }
    
    store_evaluation(&env, &evaluation);
}

/// Creates a dispute for an evaluation
pub fn create_dispute(
    env: Env,
    challenger: Address,
    evaluation_id: u32,
    reason: String,
) -> u32 {
    if is_paused(&env) {
        panic!("Contract is paused");
    }
    
    challenger.require_auth();
    
    // Check if evaluation exists
    let evaluation = get_evaluation(&env, evaluation_id);
    
    // Check if dispute already exists
    if dispute_exists(&env, evaluation_id) {
        panic!("Dispute already exists for this evaluation");
    }
    
    // Create dispute
    let dispute_id = next_dispute_id(&env);
    let dispute = DisputeResolution {
        id: dispute_id,
        evaluation_id,
        challenger: challenger.clone(),
        reason,
        status: DisputeStatus::Open,
        admin_review: Vec::new(&env),
        resolution: String::from_str(&env, "Pending review"),
        timestamp: env.ledger().timestamp(),
    };
    
    store_dispute(&env, &dispute);
    
    dispute_id
}

/// Resolves a dispute (admin only)
pub fn resolve_dispute(
    env: Env,
    admin: Address,
    dispute_id: u32,
    resolution: String,
    approve_dispute: bool,
) {
    admin.require_auth();
    if !is_admin(&env, &admin) {
        panic!("Only admins can resolve disputes");
    }
    
    let mut dispute = get_dispute(&env, dispute_id);
    if dispute.status != DisputeStatus::Open && dispute.status != DisputeStatus::UnderReview {
        panic!("Dispute is not open for resolution");
    }
    
    dispute.status = DisputeStatus::Resolved;
    dispute.resolution = resolution;
    
    // Apply resolution effects
    if approve_dispute {
        // Dispute approved - penalize evaluator
        let evaluation = get_evaluation(&env, dispute.evaluation_id);
        update_reputation_score(&env, &evaluation.evaluator, -20, "Dispute upheld");
        
        // Remove reward
        clawback_evaluation_reward(&env, &evaluation.evaluator, evaluation.reward_earned);
    } else {
        // Dispute dismissed - reward challenger for valid dispute
        update_reputation_score(&env, &dispute.challenger, 5, "Valid dispute challenge");
    }
    
    store_dispute(&env, &dispute);
}

/// Gets evaluation information
pub fn get_evaluation_info(env: Env, evaluation_id: u32) -> Evaluation {
    get_evaluation(&env, evaluation_id)
}

/// Gets user's evaluation history
pub fn get_user_evaluation_history(env: Env, user: Address) -> Vec<u32> {
    get_evaluation_history(&env, &user)
}

/// Gets user reputation
pub fn get_user_reputation_info(env: Env, user: Address) -> Reputation {
    get_user_reputation(&env, &user)
}

/// Gets all disputes
pub fn get_all_disputes(env: Env) -> Vec<DisputeResolution> {
    get_all_disputes_storage(&env)
}

/// Gets expert panel members
pub fn get_expert_panel_members(env: Env) -> Vec<ExpertMember> {
    get_expert_panel(&env)
}

/// Validates evaluation scores against criteria
fn validate_scores(
    scores: &Vec<EvaluationScore>,
    criteria: &EvaluationCriteria,
    reputation: &Reputation,
) -> Result<(), String> {
    if scores.is_empty() {
        return Err("No scores provided".to_string());
    }
    
    // Check each score
    for score in scores.iter() {
        let criterion = criteria.criteria.iter()
            .find(|c| c.name == score.criterion)
            .ok_or_else(|| format!("Invalid criterion: {}", score.criterion))?;
        
        if score.score < criterion.min_score || score.score > criterion.max_score {
            return Err(format!("Score out of range for criterion: {}", score.criterion));
        }
        
        // Check expertise requirement
        if let Some(required_expertise) = &criterion.required_expertise {
            if !reputation.expertise_areas.contains(required_expertise) {
                return Err(format!("Insufficient expertise for criterion: {}", score.criterion));
            }
        }
    }
    
    Ok(())
}

/// Calculates evaluation reward based on quality and reputation
fn calculate_evaluation_reward(env: &Env, evaluation: &Evaluation, reputation: &Reputation) -> u128 {
    let base_reward = 1000u128; // Base reward in tokens
    
    // Reputation multiplier
    let reputation_multiplier = match reputation.tier {
        ReputationTier::Novice => 100,
        ReputationTier::Apprentice => 125,
        ReputationTier::Expert => 150,
        ReputationTier::Master => 200,
        ReputationTier::Grandmaster => 300,
    };
    
    // Quality bonus based on confidence and thoroughness
    let quality_bonus = (evaluation.confidence_score as u128 * evaluation.scores.len() as u128) / 100;
    
    // Accuracy bonus (if available)
    let accuracy_bonus = (reputation.accuracy_score as u128 * base_reward) / 10000;
    
    let total_reward = (base_reward * reputation_multiplier as u128) / 100 + quality_bonus + accuracy_bonus;
    
    // Cap maximum reward
    total_reward.min(10000u128)
}

/// Awards evaluation reward to evaluator
fn award_evaluation_reward(env: &Env, evaluator: &Address, reward: u128) {
    let current_balance = get_balance(env, evaluator);
    set_balance(env, evaluator, current_balance + reward);
    
    // Update total supply
    let current_supply = get_total_supply(env);
    set_total_supply(env, current_supply + reward);
}

/// Claws back evaluation reward (for disputes)
fn clawback_evaluation_reward(env: &Env, evaluator: &Address, amount: u128) {
    let current_balance = get_balance(env, evaluator);
    if current_balance >= amount {
        set_balance(env, evaluator, current_balance - amount);
        
        // Update total supply
        let current_supply = get_total_supply(env);
        set_total_supply(env, current_supply - amount);
    }
}

/// Updates reputation for new evaluation
fn update_reputation_for_evaluation(env: &Env, evaluator: &Address, evaluation_id: u32) {
    let mut reputation = get_user_reputation(env, evaluator);
    
    reputation.total_evaluations += 1;
    reputation.last_updated = env.ledger().timestamp();
    
    // Update tier based on score
    reputation.tier = calculate_reputation_tier(reputation.score);
    
    store_user_reputation(env, evaluator, &reputation);
    
    // Record reputation change
    record_reputation_change(env, evaluator, evaluation_id, 0, reputation.score, "New evaluation");
}

/// Updates reputation score
fn update_reputation_score(env: &Env, user: &Address, change: i32, reason: &str) {
    let mut reputation = get_user_reputation(env, user);
    let old_score = reputation.score;
    
    reputation.score += change;
    reputation.last_updated = env.ledger().timestamp();
    reputation.tier = calculate_reputation_tier(reputation.score);
    
    store_user_reputation(env, user, &reputation);
    
    // Record reputation change
    record_reputation_change(env, user, 0, old_score, reason);
}

/// Calculates reputation tier based on score
fn calculate_reputation_tier(score: i32) -> ReputationTier {
    match score {
        s if s < 0 => ReputationTier::Novice,
        s if s <= 100 => ReputationTier::Novice,
        s if s <= 300 => ReputationTier::Apprentice,
        s if s <= 600 => ReputationTier::Expert,
        s if s <= 1000 => ReputationTier::Master,
        _ => ReputationTier::Grandmaster,
    }
}

/// Records reputation change in history
fn record_reputation_change(env: &Env, user: &Address, evaluation_id: u32, old_score: i32, reason: &str) {
    let reputation = get_user_reputation(env, user);
    let change = ReputationChange {
        evaluation_id,
        old_score,
        new_score: reputation.score,
        reason: String::from_str(env, reason),
        timestamp: env.ledger().timestamp(),
    };
    
    let mut history = get_reputation_history(env, user);
    history.push_back(change);
    store_reputation_history(env, user, &history);
}
