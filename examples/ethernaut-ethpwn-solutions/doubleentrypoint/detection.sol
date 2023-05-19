// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;


import "exploit_templates/Destructible.sol";
import "exploit_templates/Targeted.sol";

import "doubleentrypoint/exploit.sol";

contract DetectionBot is IDetectionBot {
    DoubleEntryPoint dep_token;
    Forta forta;
    LegacyToken legacy_token;
    CryptoVault crypto_vault;
    constructor (address dep_token_addr) {
        dep_token = DoubleEntryPoint(dep_token_addr);
        forta = dep_token.forta();
        legacy_token = LegacyToken(dep_token.delegatedFrom());
        crypto_vault = CryptoVault(dep_token.cryptoVault());
    }
    function handleTransaction(address user, bytes calldata msgData) external override {
        bytes4 selector = bytes4(msgData[0:4]);

        if (selector != bytes4(keccak256("delegateTransfer(address,uint256,address)"))) {
            return;
        }
        // abi decode the arguments
        (address to, uint256 value, address origSender) = abi.decode(msgData[4:], (address, uint256, address));
        if (origSender != address(crypto_vault)) {
            return;
        }
        if (to != address(crypto_vault.sweptTokensRecipient())) {
            return;
        }
        if (value != dep_token.balanceOf(address(crypto_vault))) {
            return;
        }
        forta.raiseAlert(user);
    }
}


// We can't use a contract to deploy the bot, because it stores it using `msg.sender`, so the transaction has to be sent
// from our wallet address.

// contract DeployDetection is Destructible, Targeted {
//     DetectionBot public detection_bot;
//     DoubleEntryPoint dep_token;
//     Forta forta;
//     LegacyToken legacy_token;
//     CryptoVault crypto_vault;
//     constructor(address target_addr) payable Targeted(target_addr) {
//         dep_token = DoubleEntryPoint(target_addr);
//         forta = dep_token.forta();
//         legacy_token = LegacyToken(dep_token.delegatedFrom());
//         crypto_vault = CryptoVault(dep_token.cryptoVault());

//         detection_bot = new DetectionBot(target_addr);
//     }
//     function deploy() public payable {
//         forta.setDetectionBot(address(detection_bot));
//     }
// }