

# ？FAQ #


#### Are transactions sent to the real network?
When debugging a transaction with `ethdbg` everything is emulated locally and nothing is sent on the actual blockchain. 
The connection to the chain RPC node is only needed to pull different information related to the transaction under debugging. 

On the other side, when using `ethpwn`, the library connects to the target blockchain and it is able to perform operations on it. While you can use Sepolia ETH to perform your tests, be always careful NOT to use important accounts with actual valuable funds when using `ethtools`.


#### Are you gonna support other EVM-based chain?
While `ethtools` can support other EVM-based chain, currently we do not have the manpower to maintain other chains. We will rely on the community to further expand `ethtools` compatibility.

#### Are you gonna support non-EVM-based chain?
`ethtools` uses as its backend `py-evm`, hence, any non-EVM-based blockchain is currently out-of-scope.

#### How can I contribute?
See our TODO, we are happy to accept pull request for those features! If you have anything else in mind just reach out on our Github page, or on twitter [@degrigis](https://twitter.com/degrigis), [@honululu](https://twitter.com/dreselli).

