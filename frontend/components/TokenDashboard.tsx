import React from 'react';

export const TokenDashboard: React.FC = () => {
    return (
        <div className="token-dashboard p-6 bg-white rounded-lg shadow-md">
            <h2 className="text-2xl font-bold mb-4">Token Economy Dashboard</h2>
            
            <div className="distribution mb-4">
                <h3 className="text-xl font-semibold">Distribution & Inflation</h3>
                <p>Circulating Supply: 500,000 FLV</p>
                <p>Inflation Control: Active (2% Annual)</p>
            </div>

            <div className="staking mb-4">
                <h3 className="text-xl font-semibold">Staking & Rewards</h3>
                <p>Current APY: 12%</p>
                <button className="mt-2 px-4 py-2 bg-purple-600 text-white rounded">
                    Stake Tokens
                </button>
            </div>

            <div className="market-integration">
                <h3 className="text-xl font-semibold">Market Integration & Utility</h3>
                <p>Governance Voting Rights: Enabled based on staked balance.</p>
            </div>
        </div>
    );
};