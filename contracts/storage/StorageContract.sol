// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title StorageContract
 * @dev Decentralized storage contract for IPFS file verification and management
 * @author FlavorSnap Team
 */
contract StorageContract is Ownable, ReentrancyGuard, Pausable {
    using Counters for Counters.Counter;
    
    // Events
    event FileRegistered(
        bytes32 indexed fileHash,
        string indexed cid,
        address indexed owner,
        uint256 timestamp,
        uint256 size
    );
    
    event FileVerified(
        bytes32 indexed fileHash,
        string indexed cid,
        bool verified,
        uint256 timestamp
    );
    
    event AccessGranted(
        bytes32 indexed fileHash,
        address indexed user,
        string permission,
        uint256 timestamp
    );
    
    event StorageOptimized(
        bytes32 indexed fileHash,
        uint256 spaceSaved,
        uint256 timestamp
    );
    
    // Structs
    struct FileInfo {
        string cid;
        bytes32 contentHash;
        address owner;
        uint256 timestamp;
        uint256 size;
        bool verified;
        mapping(address => string) permissions;
        uint256 accessCount;
        uint256 lastAccessed;
        uint256 costEstimate;
        bool isActive;
    }
    
    struct StorageMetrics {
        uint256 totalFiles;
        uint256 totalSize;
        uint256 verifiedFiles;
        uint256 activeFiles;
        uint256 totalCost;
        uint256 averageFileSize;
    }
    
    // State variables
    Counters.Counter private _fileIds;
    mapping(bytes32 => FileInfo) private _files;
    mapping(address => bytes32[]) private _userFiles;
    mapping(string => bytes32) private _cidToHash;
    
    StorageMetrics public metrics;
    
    // Constants
    uint256 public constant MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024; // 1GB
    uint256 public constant MIN_REPLICATION = 3;
    uint256 public constant COST_PER_MB = 0.01 ether; // $0.01 per MB in wei
    
    // Modifiers
    modifier onlyFileOwner(bytes32 fileHash) {
        require(_files[fileHash].owner == msg.sender, "StorageContract: Not file owner");
        _;
    }
    
    modifier hasAccess(bytes32 fileHash) {
        require(
            _files[fileHash].owner == msg.sender ||
            keccak256(abi.encodePacked(_files[fileHash].permissions[msg.sender])) != keccak256(abi.encodePacked("")),
            "StorageContract: No access"
        );
        _;
    }
    
    modifier validFile(bytes32 fileHash) {
        require(_files[fileHash].isActive, "StorageContract: File not active");
        _;
    }
    
    /**
     * @dev Register a new file on the blockchain
     * @param cid IPFS content identifier
     * @param contentHash SHA-256 hash of file content
     * @param size File size in bytes
     */
    function registerFile(
        string memory cid,
        bytes32 contentHash,
        uint256 size
    ) external whenNotPaused nonReentrant returns (bytes32) {
        require(size <= MAX_FILE_SIZE, "StorageContract: File too large");
        require(bytes(cid).length > 0, "StorageContract: Invalid CID");
        require(contentHash != bytes32(0), "StorageContract: Invalid hash");
        
        // Generate file hash
        bytes32 fileHash = keccak256(abi.encodePacked(cid, contentHash, msg.sender));
        
        // Check if file already exists
        require(!_files[fileHash].isActive, "StorageContract: File already registered");
        
        // Calculate cost estimate
        uint256 costEstimate = (size / (1024 * 1024)) * COST_PER_MB;
        
        // Create file info
        FileInfo storage fileInfo = _files[fileHash];
        fileInfo.cid = cid;
        fileInfo.contentHash = contentHash;
        fileInfo.owner = msg.sender;
        fileInfo.timestamp = block.timestamp;
        fileInfo.size = size;
        fileInfo.verified = false;
        fileInfo.accessCount = 0;
        fileInfo.lastAccessed = block.timestamp;
        fileInfo.costEstimate = costEstimate;
        fileInfo.isActive = true;
        
        // Set owner permissions
        fileInfo.permissions[msg.sender] = "owner";
        
        // Update mappings
        _cidToHash[cid] = fileHash;
        _userFiles[msg.sender].push(fileHash);
        
        // Update metrics
        _updateMetrics(size, true);
        
        emit FileRegistered(fileHash, cid, msg.sender, block.timestamp, size);
        
        return fileHash;
    }
    
    /**
     * @dev Verify file integrity
     * @param fileHash Hash of the file to verify
     */
    function verifyFile(bytes32 fileHash) 
        external 
        whenNotPaused 
        validFile(fileHash) 
        returns (bool) 
    {
        // In a real implementation, this would interact with IPFS
        // For now, we'll simulate verification
        bool verified = _simulateVerification(fileHash);
        
        _files[fileHash].verified = verified;
        
        if (verified) {
            metrics.verifiedFiles++;
        }
        
        emit FileVerified(fileHash, _files[fileHash].cid, verified, block.timestamp);
        
        return verified;
    }
    
    /**
     * @dev Grant access to a file
     * @param fileHash Hash of the file
     * @param user Address to grant access to
     * @param permission Type of permission ("read", "write", "admin")
     */
    function grantAccess(
        bytes32 fileHash,
        address user,
        string memory permission
    ) external onlyFileOwner(fileHash) whenNotPaused {
        require(user != address(0), "StorageContract: Invalid user address");
        require(
            keccak256(bytes(permission)) == keccak256(bytes("read")) ||
            keccak256(bytes(permission)) == keccak256(bytes("write")) ||
            keccak256(bytes(permission)) == keccak256(bytes("admin")),
            "StorageContract: Invalid permission"
        );
        
        _files[fileHash].permissions[user] = permission;
        
        emit AccessGranted(fileHash, user, permission, block.timestamp);
    }
    
    /**
     * @dev Revoke access to a file
     * @param fileHash Hash of the file
     * @param user Address to revoke access from
     */
    function revokeAccess(bytes32 fileHash, address user) 
        external 
        onlyFileOwner(fileHash) 
        whenNotPaused 
    {
        require(user != msg.sender, "StorageContract: Cannot revoke own access");
        require(user != _files[fileHash].owner, "StorageContract: Cannot revoke owner access");
        
        delete _files[fileHash].permissions[user];
    }
    
    /**
     * @dev Access file (increment access count)
     * @param fileHash Hash of the file to access
     */
    function accessFile(bytes32 fileHash) 
        external 
        hasAccess(fileHash) 
        validFile(fileHash) 
    {
        _files[fileHash].accessCount++;
        _files[fileHash].lastAccessed = block.timestamp;
    }
    
    /**
     * @dev Deactivate a file (mark as inactive)
     * @param fileHash Hash of the file to deactivate
     */
    function deactivateFile(bytes32 fileHash) 
        external 
        onlyFileOwner(fileHash) 
        whenNotPaused 
    {
        require(_files[fileHash].isActive, "StorageContract: File already inactive");
        
        _files[fileHash].isActive = false;
        
        // Update metrics
        _updateMetrics(_files[fileHash].size, false);
        
        // Remove from user files list
        _removeFromUserFiles(msg.sender, fileHash);
    }
    
    /**
     * @dev Get file information
     * @param fileHash Hash of the file
     */
    function getFileInfo(bytes32 fileHash) 
        external 
        view 
        hasAccess(fileHash) 
        returns (
            string memory cid,
            bytes32 contentHash,
            address owner,
            uint256 timestamp,
            uint256 size,
            bool verified,
            uint256 accessCount,
            uint256 lastAccessed,
            uint256 costEstimate,
            bool isActive
        ) 
    {
        FileInfo storage fileInfo = _files[fileHash];
        return (
            fileInfo.cid,
            fileInfo.contentHash,
            fileInfo.owner,
            fileInfo.timestamp,
            fileInfo.size,
            fileInfo.verified,
            fileInfo.accessCount,
            fileInfo.lastAccessed,
            fileInfo.costEstimate,
            fileInfo.isActive
        );
    }
    
    /**
     * @dev Get user's permission for a file
     * @param fileHash Hash of the file
     * @param user User address
     */
    function getUserPermission(bytes32 fileHash, address user) 
        external 
        view 
        returns (string memory) 
    {
        return _files[fileHash].permissions[user];
    }
    
    /**
     * @dev Get all files for a user
     * @param user User address
     */
    function getUserFiles(address user) 
        external 
        view 
        returns (bytes32[] memory) 
    {
        return _userFiles[user];
    }
    
    /**
     * @dev Get file hash by CID
     * @param cid IPFS content identifier
     */
    function getFileHashByCID(string memory cid) 
        external 
        view 
        returns (bytes32) 
    {
        return _cidToHash[cid];
    }
    
    /**
     * @dev Optimize storage (cleanup old files)
     * @param fileHashes Array of file hashes to optimize
     */
    function optimizeStorage(bytes32[] memory fileHashes) 
        external 
        onlyOwner 
        whenNotPaused 
    {
        uint256 totalSpaceSaved = 0;
        
        for (uint256 i = 0; i < fileHashes.length; i++) {
            bytes32 fileHash = fileHashes[i];
            
            if (_files[fileHash].isActive) {
                uint256 fileSize = _files[fileHash].size;
                
                // Check if file should be optimized (old, rarely accessed)
                if (block.timestamp - _files[fileHash].lastAccessed > 30 days &&
                    _files[fileHash].accessCount < 5) {
                    
                    _files[fileHash].isActive = false;
                    totalSpaceSaved += fileSize;
                    
                    // Update metrics
                    _updateMetrics(fileSize, false);
                    
                    // Remove from user files
                    _removeFromUserFiles(_files[fileHash].owner, fileHash);
                }
            }
        }
        
        if (totalSpaceSaved > 0) {
            emit StorageOptimized(bytes32(0), totalSpaceSaved, block.timestamp);
        }
    }
    
    /**
     * @dev Update storage metrics
     * @param size File size
     * @param add Whether to add or subtract from metrics
     */
    function _updateMetrics(uint256 size, bool add) internal {
        if (add) {
            metrics.totalFiles++;
            metrics.totalSize += size;
            metrics.activeFiles++;
        } else {
            metrics.totalFiles--;
            metrics.totalSize -= size;
            metrics.activeFiles--;
        }
        
        if (metrics.totalFiles > 0) {
            metrics.averageFileSize = metrics.totalSize / metrics.totalFiles;
        }
    }
    
    /**
     * @dev Remove file from user's file list
     * @param user User address
     * @param fileHash File hash to remove
     */
    function _removeFromUserFiles(address user, bytes32 fileHash) internal {
        bytes32[] storage userFiles = _userFiles[user];
        
        for (uint256 i = 0; i < userFiles.length; i++) {
            if (userFiles[i] == fileHash) {
                userFiles[i] = userFiles[userFiles.length - 1];
                userFiles.pop();
                break;
            }
        }
    }
    
    /**
     * @dev Simulate file verification (placeholder for IPFS integration)
     * @param fileHash File hash to verify
     */
    function _simulateVerification(bytes32 fileHash) internal view returns (bool) {
        // In a real implementation, this would:
        // 1. Fetch file from IPFS using CID
        // 2. Calculate SHA-256 hash of content
        // 3. Compare with stored contentHash
        // 4. Return verification result
        
        // For simulation, we'll use a simple heuristic
        FileInfo storage fileInfo = _files[fileHash];
        return (block.timestamp - fileInfo.timestamp) < 365 days; // "Valid" if less than a year old
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
