#!/usr/bin/env bash

set -e  # stop on error

NETWORK=$1

if [ -z "$NETWORK" ]; then
  echo "❌ Please specify network: testnet or mainnet"
  echo "Usage: ./deploy_contracts.sh testnet"
  exit 1
fi

echo "🚀 Deploying contracts to $NETWORK..."

# -----------------------------
# Load environment config
# -----------------------------
if [ "$NETWORK" == "testnet" ]; then
  source ./config/testnet.env
elif [ "$NETWORK" == "mainnet" ]; then
  source ./config/mainnet.env
else
  echo "❌ Invalid network. Use 'testnet' or 'mainnet'"
  exit 1
fi

# -----------------------------
# Build contracts
# -----------------------------
echo "🔨 Building contracts..."
cargo build --target wasm32-unknown-unknown --release

# -----------------------------
# Deploy each contract
# -----------------------------
for contract in contracts/*; do
  if [ -d "$contract" ]; then
    CONTRACT_NAME=$(basename "$contract")

    WASM_PATH="$contract/target/wasm32-unknown-unknown/release/${CONTRACT_NAME}.wasm"

    if [ ! -f "$WASM_PATH" ]; then
      echo "⚠️ Skipping $CONTRACT_NAME (WASM not found)"
      continue
    fi

    echo "📦 Deploying $CONTRACT_NAME..."

    CONTRACT_ID=$(soroban contract deploy \
      --wasm "$WASM_PATH" \
      --source "$SOROBAN_SECRET_KEY" \
      --network "$SOROBAN_NETWORK_PASSPHRASE" \
      --rpc-url "$SOROBAN_RPC_URL")

    echo "✅ $CONTRACT_NAME deployed at: $CONTRACT_ID"

    echo "$CONTRACT_NAME=$CONTRACT_ID" >> deployed_$NETWORK.txt
  fi
done

echo "🎉 Deployment complete!"