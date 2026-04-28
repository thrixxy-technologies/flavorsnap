# FlavorSnap Smart Contracts

Comprehensive smart contract suite for the FlavorSnap decentralized food evaluation and governance platform.

## Overview

This repository contains advanced smart contracts built on Soroban (Stellar) that provide:

- **Model Governance**: Decentralized voting and proposal system for AI model updates
- **Tokenized Incentives**: Staking, rewards, and vesting mechanisms
- **Sensory Evaluation**: Reputation-based food evaluation system
- **Security & Upgradeability**: Comprehensive security audit and upgrade patterns

## Architecture

### Core Contracts

#### 1. Model Governance (`model-governance/`)
Advanced governance system with:
- Weighted voting with delegation
- Timelock execution
- Emergency proposals
- Multi-signature admin controls
- Proposal types (Model Update, Dataset Expansion, Parameter Change, Emergency, Upgrade)

#### 2. Tokenized Incentive (`tokenized-incentive/`)
Comprehensive token system with:
- Multi-tier staking with rewards
- Reward pools and auto-compounding
- Vesting schedules with cliffs
- Multi-signature admin operations
- Gas-optimized operations

#### 3. Sensory Evaluation (`sensory-evaluation/`)
Reputation-based evaluation system with:
- Multi-criteria scoring
- Expert panel verification
- Reputation tiers (Novice → Grandmaster)
- Dispute resolution system
- Quality-based rewards

### Shared Infrastructure

#### Upgradeability (`shared/src/upgradeability.rs`)
- Proxy pattern implementation
- Timelock upgrades
- Upgrade history tracking
- Emergency pause capabilities

#### Security (`shared/src/security.rs`)
- Comprehensive audit logging
- Access control and rate limiting
- Whitelist/blacklist management
- Vulnerability reporting
- Emergency pause/resume

#### Gas Optimization (`shared/src/optimization.rs`)
- Batch operations
- Storage optimization patterns
- Efficient data structures
- Memory usage optimization

## Features

### 🏛️ Governance Features
- **Proposal Types**: Model updates, dataset expansion, parameter changes, emergency actions
- **Voting Mechanisms**: Weighted voting, delegation, voting power snapshots
- **Timelock Execution**: Configurable delays for proposal execution
- **Emergency Proposals**: Fast-track for critical updates
- **Multi-signature**: Enhanced security for admin operations

### 💰 Incentive Features
- **Staking Tiers**: Bronze, Silver, Gold, Platinum with increasing rewards
- **Reward Pools**: Configurable pools with different rates and durations
- **Auto-compounding**: Automatic reward reinvestment
- **Vesting Schedules**: Cliff and linear vesting options
- **Dynamic Rewards**: Based on reputation and contribution

### 👨‍🔬 Evaluation Features
- **Multi-criteria Scoring**: Taste, appearance, texture, aroma, etc.
- **Reputation System**: 5-tier system with increasing benefits
- **Expert Verification**: Peer review by qualified experts
- **Dispute Resolution**: Structured process for contested evaluations
- **Quality Metrics**: Accuracy and consistency tracking

### 🔒 Security Features
- **Access Control**: Role-based permissions with multi-sig
- **Rate Limiting**: Prevent spam and abuse
- **Audit Logging**: Comprehensive security event tracking
- **Emergency Controls**: Pause/resume capabilities
- **Vulnerability Management**: Reporting and resolution tracking

### ⚡ Performance Features
- **Gas Optimization**: Efficient storage and computation patterns
- **Batch Operations**: Reduced transaction costs
- **Caching**: Smart data caching strategies
- **Event Optimization**: Efficient event emissions

## Quick Start

### Prerequisites
- Rust 1.70+
- Soroban CLI
- Node.js (for frontend integration)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/flavorsnap-contracts
cd flavorsnap-contracts

# Install dependencies
cargo build --release --workspace
```

### Deployment

#### Testnet Deployment
```bash
./scripts/deploy_comprehensive.sh testnet
```

#### Mainnet Deployment
```bash
./scripts/deploy_comprehensive.sh mainnet
```

### Configuration

Create environment configuration files:

`config/testnet.env`:
```bash
SOROBAN_SECRET_KEY=your_testnet_secret_key
SOROBAN_NETWORK_PASSPHRASE="Test SDF Network ; September 2015"
SOROBAN_RPC_URL="https://soroban-testnet.stellar.org"
```

`config/mainnet.env`:
```bash
SOROBAN_SECRET_KEY=your_mainnet_secret_key
SOROBAN_NETWORK_PASSPHRASE="Public Global Stellar Network ; September 2015"
SOROBAN_RPC_URL="https://soroban-rpc.stellar.org"
```

## Usage Examples

### Model Governance

```rust
// Submit a proposal
let proposal_id = governance_contract.submit_proposal(
    env,
    proposer,
    "Update model to v2.0 with improved accuracy",
    1000, // stake
    ProposalType::ModelUpdate
);

// Vote on proposal
governance_contract.vote(env, voter, proposal_id, true);

// Execute after timelock
governance_contract.execute_proposal(env, admin, proposal_id);
```

### Tokenized Incentives

```rust
// Create staking position
let stake_id = incentive_contract.create_stake(
    env,
    staker,
    10000, // amount
    86400 * 30, // 30 days
    1, // pool ID
    true // auto-compound
);

// Claim rewards
let rewards = incentive_contract.claim_rewards(env, staker, stake_id);
```

### Sensory Evaluation

```rust
// Submit evaluation
let eval_id = evaluation_contract.submit_evaluation(
    env,
    evaluator,
    "food_item_123",
    scores,
    "Excellent quality and presentation",
    95 // confidence
);

// Verify as expert
evaluation_contract.verify_evaluation(env, expert, eval_id, true);
```

## Testing

### Run All Tests
```bash
cargo test --workspace
```

### Comprehensive Integration Tests
```bash
cargo test comprehensive_tests --release
```

### Performance Benchmarks
```bash
cargo test performance_benchmarks --release
```

## Security Considerations

### Audit Checklist
- [ ] Access control properly configured
- [ ] Rate limits set appropriately
- [ ] Emergency pause tested
- [ ] Upgradeability verified
- [ ] Multi-signature working
- [ ] Audit logging enabled

### Security Best Practices
1. **Multi-signature**: Always use multi-sig for admin operations
2. **Timelocks**: Configure appropriate delays for critical operations
3. **Monitoring**: Set up monitoring for security events
4. **Regular Audits**: Conduct periodic security audits
5. **Emergency Plans**: Have emergency response procedures

## Gas Optimization Tips

### Storage Optimization
- Use packed storage for multiple small values
- Implement efficient caching strategies
- Minimize storage operations in batches

### Computation Optimization
- Use lookup tables for expensive calculations
- Implement efficient sorting algorithms
- Minimize redundant calculations

### Event Optimization
- Batch multiple events when possible
- Use compact binary formats for event data
- Minimize event emissions for non-critical data

## Upgrade Process

### Standard Upgrade
1. Propose upgrade with new implementation address
2. Wait for timelock period (default 24 hours)
3. Execute upgrade
4. Verify new implementation

### Emergency Upgrade
1. Use emergency pause if needed
2. Propose emergency upgrade
3. Execute immediately (no timelock)
4. Resume operations

## Monitoring

### Key Metrics to Monitor
- Proposal success rate
- Voting participation
- Staking ratios
- Evaluation quality scores
- Security event frequency
- Gas usage patterns

### Alert Configuration
Set up alerts for:
- High failure rates
- Unusual voting patterns
- Security events
- Gas consumption spikes
- Emergency pause activations

## Contributing

### Development Setup
```bash
# Install development dependencies
cargo install soroban-cli

# Run tests
cargo test --workspace

# Build for deployment
cargo build --target wasm32-unknown-unknown --release
```

### Code Style
- Follow Rust standard style guidelines
- Use comprehensive documentation
- Include security considerations in comments
- Write tests for all public functions

### Security Review Process
1. Code review by team members
2. Automated security scanning
3. Manual security audit
4. Testnet deployment verification
5. Mainnet deployment approval

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Join our Discord community
- Contact the development team

## Acknowledgments

- Soroban team for the excellent smart contract platform
- Stellar Development Foundation for network infrastructure
- Community contributors and testers
- Security auditors and reviewers

---

**Built with ❤️ for the FlavorSnap community**
