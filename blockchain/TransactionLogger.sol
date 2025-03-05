// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TransactionLogger {
    struct FileTransaction {
        address user;
        string fileHash;
        uint256 timestamp;
    }

    FileTransaction[] public transactions;
    mapping(string => bool) private loggedFiles;

    event FileUploaded(address indexed user, string fileHash, uint256 timestamp);
    event FileRetrieved(address indexed user, string fileHash, uint256 timestamp);

    function uploadFile(string memory _fileHash) public {
        require(!loggedFiles[_fileHash], "File already logged on blockchain.");
        
        transactions.push(FileTransaction(msg.sender, _fileHash, block.timestamp));
        loggedFiles[_fileHash] = true;
        
        emit FileUploaded(msg.sender, _fileHash, block.timestamp);
    }

    function retrieveFile(string memory _fileHash) public {
        emit FileRetrieved(msg.sender, _fileHash, block.timestamp);
    }

    function getTransactionCount() public view returns (uint256) {
        return transactions.length;
    }

    function getTransaction(uint256 index) public view returns (address, string memory, uint256) {
        require(index < transactions.length, "Invalid index.");
        FileTransaction memory txData = transactions[index];
        return (txData.user, txData.fileHash, txData.timestamp);
    }
}
