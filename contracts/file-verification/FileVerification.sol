// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title FileVerification
 * @dev Decentralized file verification system with cryptographic proofs
 * @author FlavorSnap Team
 */
contract FileVerification is Ownable, ReentrancyGuard, Pausable {
    using Counters for Counters.Counter;
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;
    
    // Events
    event VerificationRequested(
        bytes32 indexed fileHash,
        string indexed cid,
        address indexed requester,
        uint256 timestamp
    );
    
    event VerificationCompleted(
        bytes32 indexed fileHash,
        bool verified,
        address indexed verifier,
        uint256 timestamp,
        bytes32 proofHash
    );
    
    event ProofSubmitted(
        bytes32 indexed fileHash,
        bytes32 indexed proofHash,
        address indexed submitter,
        uint256 timestamp
    );
    
    event ChallengeCreated(
        bytes32 indexed fileHash,
        bytes32 indexed challengeHash,
        uint256 reward,
        uint256 deadline
    );
    
    event ChallengeCompleted(
        bytes32 indexed fileHash,
        bytes32 indexed challengeHash,
        bool success,
        address indexed solver,
        uint256 timestamp
    );
    
    // Structs
    struct FileProof {
        bytes32 contentHash;
        bytes32 merkleRoot;
        uint256 fileSize;
        uint256 timestamp;
        address verifier;
        bool verified;
        bytes signature;
        mapping(bytes32 => bool) chunkProofs;
    }
    
    struct VerificationChallenge {
        bytes32 challengeHash;
        bytes32 fileHash;
        address challenger;
        uint256 reward;
        uint256 deadline;
        bool completed;
        bool success;
        address solver;
    }
    
    struct VerificationMetrics {
        uint256 totalFiles;
        uint256 verifiedFiles;
        uint256 pendingVerifications;
        uint256 successfulChallenges;
        uint256 totalRewardsPaid;
        uint256 averageVerificationTime;
    }
    
    // State variables
    Counters.Counter private _verificationIds;
    Counters.Counter private _challengeIds;
    
    mapping(bytes32 => FileProof) private _fileProofs;
    mapping(bytes32 => VerificationChallenge) private _challenges;
    mapping(address => bytes32[]) private _verifierFiles;
    mapping(address => bytes32[]) private _challengerChallenges;
    
    VerificationMetrics public metrics;
    
    // Constants
    uint256 public constant CHUNK_SIZE = 1024 * 1024; // 1MB chunks
    uint256 public constant MIN_VERIFICATION_STAKE = 0.1 ether;
    uint256 public constant CHALLENGE_DURATION = 24 hours;
    uint256 public constant VERIFICATION_REWARD = 0.05 ether;
    
    // Modifiers
    modifier onlyVerifier(bytes32 fileHash) {
        require(
            _fileProofs[fileHash].verifier == msg.sender || 
            _fileProofs[fileHash].verifier == address(0),
            "FileVerification: Not authorized verifier"
        );
        _;
    }
    
    modifier validChallenge(bytes32 challengeHash) {
        require(
            _challenges[challengeHash].deadline > block.timestamp,
            "FileVerification: Challenge expired"
        );
        require(
            !_challenges[challengeHash].completed,
            "FileVerification: Challenge already completed"
        );
        _;
    }
    
    /**
     * @dev Submit file for verification
     * @param cid IPFS content identifier
     * @param contentHash SHA-256 hash of file content
     * @param merkleRoot Merkle root of file chunks
     * @param fileSize Total file size in bytes
     * @param signature Cryptographic signature of the file data
     */
    function submitForVerification(
        string memory cid,
        bytes32 contentHash,
        bytes32 merkleRoot,
        uint256 fileSize,
        bytes memory signature
    ) external whenNotPaused nonReentrant returns (bytes32) {
        require(bytes(cid).length > 0, "FileVerification: Invalid CID");
        require(contentHash != bytes32(0), "FileVerification: Invalid content hash");
        require(merkleRoot != bytes32(0), "FileVerification: Invalid merkle root");
        require(fileSize > 0, "FileVerification: Invalid file size");
        
        // Generate file hash
        bytes32 fileHash = keccak256(abi.encodePacked(cid, contentHash, merkleRoot));
        
        // Check if file already exists
        require(_fileProofs[fileHash].verifier == address(0), "FileVerification: File already submitted");
        
        // Create file proof
        FileProof storage proof = _fileProofs[fileHash];
        proof.contentHash = contentHash;
        proof.merkleRoot = merkleRoot;
        proof.fileSize = fileSize;
        proof.timestamp = block.timestamp;
        proof.verifier = msg.sender;
        proof.verified = false;
        proof.signature = signature;
        
        // Add to verifier's files
        _verifierFiles[msg.sender].push(fileHash);
        
        // Update metrics
        metrics.totalFiles++;
        metrics.pendingVerifications++;
        
        emit VerificationRequested(fileHash, cid, msg.sender, block.timestamp);
        
        return fileHash;
    }
    
    /**
     * @dev Verify file with cryptographic proof
     * @param fileHash Hash of the file to verify
     * @param proofHash Hash of the verification proof
     * @param chunkProofs Array of chunk proofs
     * @param verificationResult Result of the verification
     */
    function verifyFile(
        bytes32 fileHash,
        bytes32 proofHash,
        bytes32[] memory chunkProofs,
        bool verificationResult
    ) external whenNotPaused nonReentrant onlyVerifier(fileHash) returns (bool) {
        require(_fileProofs[fileHash].verifier != address(0), "FileVerification: File not found");
        require(!_fileProofs[fileHash].verified, "FileVerification: File already verified");
        
        // Verify chunk proofs
        bool proofsValid = _verifyChunkProofs(fileHash, chunkProofs);
        
        if (proofsValid && verificationResult) {
            _fileProofs[fileHash].verified = true;
            metrics.verifiedFiles++;
            
            // Send reward to verifier
            if (address(this).balance >= VERIFICATION_REWARD) {
                payable(_fileProofs[fileHash].verifier).transfer(VERIFICATION_REWARD);
                metrics.totalRewardsPaid += VERIFICATION_REWARD;
            }
        }
        
        // Update metrics
        if (metrics.pendingVerifications > 0) {
            metrics.pendingVerifications--;
        }
        
        // Calculate average verification time
        uint256 verificationTime = block.timestamp - _fileProofs[fileHash].timestamp;
        metrics.averageVerificationTime = (
            (metrics.averageVerificationTime * (metrics.totalFiles - 1) + verificationTime) /
            metrics.totalFiles
        );
        
        emit VerificationCompleted(
            fileHash,
            _fileProofs[fileHash].verified,
            msg.sender,
            block.timestamp,
            proofHash
        );
        
        return _fileProofs[fileHash].verified;
    }
    
    /**
     * @dev Create verification challenge
     * @param fileHash Hash of the file to challenge
     * @param reward Reward amount for solving the challenge
     */
    function createChallenge(bytes32 fileHash, uint256 reward) 
        external 
        whenNotPaused 
        nonReentrant 
        returns (bytes32) 
    {
        require(_fileProofs[fileHash].verifier != address(0), "FileVerification: File not found");
        require(reward >= MIN_VERIFICATION_STAKE, "FileVerification: Insufficient reward");
        
        // Transfer reward to contract
        require(msg.value >= reward, "FileVerification: Insufficient payment");
        
        // Generate challenge hash
        bytes32 challengeHash = keccak256(abi.encodePacked(
            fileHash,
            msg.sender,
            block.timestamp,
            reward
        ));
        
        // Create challenge
        VerificationChallenge storage challenge = _challenges[challengeHash];
        challenge.challengeHash = challengeHash;
        challenge.fileHash = fileHash;
        challenge.challenger = msg.sender;
        challenge.reward = reward;
        challenge.deadline = block.timestamp + CHALLENGE_DURATION;
        challenge.completed = false;
        challenge.success = false;
        
        // Add to challenger's challenges
        _challengerChallenges[msg.sender].push(challengeHash);
        
        emit ChallengeCreated(
            fileHash,
            challengeHash,
            reward,
            challenge.deadline
        );
        
        return challengeHash;
    }
    
    /**
     * @dev Solve verification challenge
     * @param challengeHash Hash of the challenge
     * @param solution Solution data for the challenge
     * @param proof Cryptographic proof of solution
     */
    function solveChallenge(
        bytes32 challengeHash,
        bytes memory solution,
        bytes memory proof
    ) external whenNotPaused nonReentrant validChallenge(challengeHash) returns (bool) {
        VerificationChallenge storage challenge = _challenges[challengeHash];
        
        // Verify solution (simplified verification logic)
        bool solutionValid = _verifyChallengeSolution(
            challenge.fileHash,
            solution,
            proof
        );
        
        if (solutionValid) {
            // Mark challenge as successful
            challenge.completed = true;
            challenge.success = true;
            challenge.solver = msg.sender;
            
            // Transfer reward to solver
            payable(msg.sender).transfer(challenge.reward);
            
            metrics.successfulChallenges++;
        } else {
            // Mark challenge as failed
            challenge.completed = true;
            challenge.success = false;
            
            // Return reward to challenger
            payable(challenge.challenger).transfer(challenge.reward);
        }
        
        emit ChallengeCompleted(
            challenge.fileHash,
            challengeHash,
            challenge.success,
            msg.sender,
            block.timestamp
        );
        
        return solutionValid;
    }
    
    /**
     * @dev Get file proof information
     * @param fileHash Hash of the file
     */
    function getFileProof(bytes32 fileHash) 
        external 
        view 
        returns (
            bytes32 contentHash,
            bytes32 merkleRoot,
            uint256 fileSize,
            uint256 timestamp,
            address verifier,
            bool verified
        ) 
    {
        FileProof storage proof = _fileProofs[fileHash];
        return (
            proof.contentHash,
            proof.merkleRoot,
            proof.fileSize,
            proof.timestamp,
            proof.verifier,
            proof.verified
        );
    }
    
    /**
     * @dev Get challenge information
     * @param challengeHash Hash of the challenge
     */
    function getChallenge(bytes32 challengeHash) 
        external 
        view 
        returns (
            bytes32 fileHash,
            address challenger,
            uint256 reward,
            uint256 deadline,
            bool completed,
            bool success,
            address solver
        ) 
    {
        VerificationChallenge storage challenge = _challenges[challengeHash];
        return (
            challenge.fileHash,
            challenge.challenger,
            challenge.reward,
            challenge.deadline,
            challenge.completed,
            challenge.success,
            challenge.solver
        );
    }
    
    /**
     * @dev Get all files verified by a verifier
     * @param verifier Address of the verifier
     */
    function getVerifierFiles(address verifier) 
        external 
        view 
        returns (bytes32[] memory) 
    {
        return _verifierFiles[verifier];
    }
    
    /**
     * @dev Get all challenges created by a challenger
     * @param challenger Address of the challenger
     */
    function getChallengerChallenges(address challenger) 
        external 
        view 
        returns (bytes32[] memory) 
    {
        return _challengerChallenges[challenger];
    }
    
    /**
     * @dev Verify chunk proofs
     * @param fileHash Hash of the file
     * @param chunkProofs Array of chunk proofs to verify
     */
    function _verifyChunkProofs(bytes32 fileHash, bytes32[] memory chunkProofs) 
        internal 
        view 
        returns (bool) 
    {
        FileProof storage proof = _fileProofs[fileHash];
        
        // Verify each chunk proof against the merkle root
        for (uint256 i = 0; i < chunkProofs.length; i++) {
            bytes32 chunkHash = keccak256(abi.encodePacked(chunkProofs[i]));
            
            // Simple merkle proof verification (simplified)
            // In a real implementation, this would use proper merkle proof verification
            if (chunkHash == bytes32(0)) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * @dev Verify challenge solution
     * @param fileHash Hash of the file
     * @param solution Solution data
     * @param proof Cryptographic proof
     */
    function _verifyChallengeSolution(
        bytes32 fileHash,
        bytes memory solution,
        bytes memory proof
    ) internal view returns (bool) {
        // In a real implementation, this would:
        // 1. Verify the cryptographic proof
        // 2. Check that the solution correctly addresses the challenge
        // 3. Ensure the solution is unique and not previously submitted
        
        // For simulation, we'll use a simple hash check
        bytes32 solutionHash = keccak256(abi.encodePacked(solution, proof));
        bytes32 expectedHash = keccak256(abi.encodePacked(fileHash, block.timestamp));
        
        return solutionHash == expectedHash;
    }
    
    /**
     * @dev Batch verify multiple files
     * @param fileHashes Array of file hashes to verify
     * @param proofHashes Array of proof hashes
     * @param chunkProofsArray Array of chunk proofs for each file
     * @param verificationResults Array of verification results
     */
    function batchVerifyFiles(
        bytes32[] memory fileHashes,
        bytes32[] memory proofHashes,
        bytes32[][] memory chunkProofsArray,
        bool[] memory verificationResults
    ) external whenNotPaused nonReentrant returns (bool[] memory) {
        require(
            fileHashes.length == proofHashes.length &&
            fileHashes.length == chunkProofsArray.length &&
            fileHashes.length == verificationResults.length,
            "FileVerification: Array length mismatch"
        );
        
        bool[] memory results = new bool[](fileHashes.length);
        
        for (uint256 i = 0; i < fileHashes.length; i++) {
            results[i] = this.verifyFile(
                fileHashes[i],
                proofHashes[i],
                chunkProofsArray[i],
                verificationResults[i]
            );
        }
        
        return results;
    }
    
    /**
     * @dev Get verification statistics
     */
    function getVerificationStats() 
        external 
        view 
        returns (
            uint256 totalFiles,
            uint256 verifiedFiles,
            uint256 pendingVerifications,
            uint256 successRate,
            uint256 averageTime
        ) 
    {
        uint256 successRate = 0;
        if (metrics.totalFiles > 0) {
            successRate = (metrics.verifiedFiles * 100) / metrics.totalFiles;
        }
        
        return (
            metrics.totalFiles,
            metrics.verifiedFiles,
            metrics.pendingVerifications,
            successRate,
            metrics.averageVerificationTime
        );
    }
    
    /**
     * @dev Pause contract operations
     */
    function pause() external onlyOwner {
        _pause();
    }
    
    /**
     * @dev Unpause contract operations
     */
    function unpause() external onlyOwner {
        _unpause();
    }
    
    /**
     * @dev Update verification reward
     * @param newReward New reward amount
     */
    function updateVerificationReward(uint256 newReward) external onlyOwner {
        VERIFICATION_REWARD = newReward;
    }
    
    /**
     * @dev Update challenge duration
     * @param newDuration New challenge duration in seconds
     */
    function updateChallengeDuration(uint256 newDuration) external onlyOwner {
        CHALLENGE_DURATION = newDuration;
    }
    
    /**
     * @dev Emergency function to recover stuck funds
     */
    function emergencyWithdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }
    
    /**
     * @dev Get contract version
     */
    function getVersion() external pure returns (string memory) {
        return "1.0.0";
    }
}
