use crate::types::*;
use soroban_sdk::{Address, Env};

/// Creates a vesting schedule for token distribution.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `caller` - The address of the admin creating the schedule.
/// * `recipient` - The address to receive vested tokens.
/// * `total_amount` - Total token amount to vest.
/// * `start_time` - Timestamp when vesting begins.
/// * `duration` - Total duration of vesting in seconds.
/// * `cliff` - Cliff period in seconds before vesting starts.
///
/// # Returns
/// The ID of the created vesting schedule.
pub fn create_vesting_schedule(
    env: Env,
    caller: Address,
    recipient: Address,
    total_amount: u64,
    start_time: u64,
    duration: u64,
    cliff: u64,
) -> u32 {
    caller.require_auth();
    crate::admin::check_admin(&env, &caller);

    if duration == 0 {
        panic!("Vesting duration must be greater than 0");
    }
    if cliff > duration {
        panic!("Cliff cannot exceed duration");
    }

    let schedule_id = env
        .storage()
        .instance()
        .get(&DataKey::NextScheduleId)
        .unwrap_or(0u32);

    let schedule = VestingSchedule {
        id: schedule_id,
        recipient: recipient.clone(),
        total_amount,
        released_amount: 0,
        start_time,
        duration,
        cliff,
    };

    env.storage()
        .instance()
        .set(&DataKey::VestingSchedules(recipient, schedule_id), &schedule);

    env.storage()
        .instance()
        .set(&DataKey::NextScheduleId, &(schedule_id + 1));

    schedule_id
}

/// Releases vested funds to the recipient based on the schedule.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `caller` - The address requesting the release (must be the recipient).
/// * `recipient` - The address associated with the vesting schedule.
/// * `schedule_id` - The ID of the vesting schedule.
pub fn release_vested_funds(env: Env, caller: Address, recipient: Address, schedule_id: u32) {
    caller.require_auth();

    let mut schedule: VestingSchedule = env
        .storage()
        .instance()
        .get(&DataKey::VestingSchedules(recipient.clone(), schedule_id))
        .unwrap_or_else(|| panic!("Vesting schedule not found"));

    if caller != schedule.recipient {
        panic!("Only recipient can release vested funds");
    }

    let current_time = env.ledger().timestamp();
    if current_time < schedule.start_time + schedule.cliff {
        panic!("Cliff period not yet reached");
    }

    let elapsed = current_time - schedule.start_time;
    let vested_amount = if elapsed >= schedule.duration {
        schedule.total_amount
    } else {
        (schedule.total_amount * elapsed) / schedule.duration
    };

    let releasable = vested_amount - schedule.released_amount;
    if releasable == 0 {
        panic!("No funds available to release");
    }

    schedule.released_amount += releasable;
    env.storage()
        .instance()
        .set(&DataKey::VestingSchedules(recipient.clone(), schedule_id), &schedule);

    let mut balance: u64 = env
        .storage()
        .instance()
        .get(&DataKey::Balances(recipient.clone()))
        .unwrap_or(0);
    balance += releasable;
    env.storage().instance().set(&DataKey::Balances(recipient), &balance);
}

/// Queries a vesting schedule for a recipient and schedule ID.
///
/// # Arguments
/// * `env` - The Soroban environment.
/// * `recipient` - The address associated with the vesting schedule.
/// * `schedule_id` - The ID of the vesting schedule.
///
/// # Returns
/// The vesting schedule details.
pub fn get_vesting_schedule(env: Env, recipient: Address, schedule_id: u32) -> VestingSchedule {
    env.storage()
        .instance()
        .get(&DataKey::VestingSchedules(recipient, schedule_id))
        .unwrap_or_else(|| panic!("Vesting schedule not found"))
}