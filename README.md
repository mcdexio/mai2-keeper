# A Liquidate Bot for MCDEX Perpetual

The MCDEX Perpetual contract incentives external agents, called keepers, to monitor and keep margin accounts safe.

This bot keeps track of margin accounts in the MCDEX perpetual contract and finds out accounts that have been unsafe. The bot will initiate a "liquidate" command to the Ethereum network, your current margin account will:
* Earn penalty prize
* Get his/her position

## Getting Started

1. Create an account (ex: in your MetaMask)
2. Goto [mcdex account page](https://mcdex.io/account/wallet). Press "Deposit" button to transfer some margin
3. Checkout the example code
```
# we need python 3.6
git clone https://github.com/mcdexio/mai2-keeper.git
cd mai2-keeper
pip install -r requirements.txt
```
4. Editing `config.toml`:
  * Set rpc.url to an ETH node. We recommend that you start an Ethereum node yourself (ex: geth or parity). You can also register an infura account and paste the node url from infura dashboard.
  * Set accounts.address and accounts.private_key. you may need [export the private key from MetaMask](https://metamask.zendesk.com/hc/en-us/articles/360015289632-How-to-Export-an-Account-Private-Key)
5. Run it `python main.py`

