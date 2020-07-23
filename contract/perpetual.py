from web3 import Web3

from lib.address import Address
from lib.contract import Contract
from lib.wad import Wad
from enum import Enum

class PositionSide(Enum):
     FLAT = 0
     SHORT = 1
     LONG = 2

class Status(Enum):
     NORMAL = 0
     SETTLING = 1
     SETTLED = 2

class MarginAccount():
    def __init__(self, side: int, size: int, entry_value: int, entry_social_loss: int, entry_funding_loss: int, cash_balance: int):
        assert(isinstance(side, int))
        assert(isinstance(size, int))
        assert(isinstance(entry_value, int))
        assert(isinstance(entry_social_loss, int))
        assert(isinstance(entry_funding_loss, int))

        self.side = PositionSide(side)
        self.size = Wad(size)
        self.entry_value = Wad(entry_value)
        self.entry_social_loss = Wad(entry_social_loss)
        self.entry_funding_loss = Wad(entry_funding_loss)
        self.cash_balance = Wad(cash_balance)

class Liquidate:
    def __init__(self, price: int, amount: int):
        assert(isinstance(price, int))
        assert(isinstance(amount, int))

        self.price = Wad(price)
        self.amount = Wad(amount)

class Perpetual(Contract):
    abi = Contract._load_abi(__name__, '../abi/Perpetual.abi')

    def __init__(self, web3: Web3, address: Address):
        assert(isinstance(web3, Web3))
        assert(isinstance(address, Address))

        self.web3 = web3
        self.address = address
        self.contract = self._get_contract(web3, self.abi, address)

    def total_accounts(self) -> int:
        return self.contract.functions.totalAccounts().call()

    def status(self) -> Status:
        return Status(self.contract.functions.status().call())

    def accounts(self, account_id: int) -> Address:
        return Address(self.contract.functions.accountList(account_id).call())

    def markPrice(self) -> Wad:
        return Wad(self.contract.functions.markPrice().call())

    def getAvailableMargin(self, address: Address) -> Wad:
        availableMargin = self.contract.functions.availableMargin(address.address).call()
        return Wad(availableMargin)

    def getMarginAccount(self, address: Address) -> MarginAccount:
        margin_account = self.contract.functions.getMarginAccount(address.address).call()
        return MarginAccount(margin_account[0], margin_account[1], margin_account[2], margin_account[3], margin_account[4], margin_account[5])

    def is_safe(self, address: Address) -> bool:
        assert isinstance(address, Address)
        return self.contract.functions.isSafe(address.address).call()

    def depositEther(self, amount: int, user: Address, gasPrice: int):
        self.logger.info(self.web3.toWei(amount, 'ether'))
        self.logger.info(self.web3.toHex(self.web3.toWei(amount, 'ether')))
        amount_towei = self.web3.toWei(amount, 'ether')
        tx_hash = self.contract.functions.deposit(amount_towei).transact({'from': user.address,
                'value': self.web3.toHex(amount_towei),
                'gasPrice': gasPrice
        })
        tx_receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)
        #self.logger.info(tx_receipt)
        return tx_receipt

    def deposit(self, amount: Wad, user: Address, gasPrice: int):
        assert isinstance(amount, Wad)
        tx_hash = self.contract.functions.deposit(amount.value).transact({'from': user.address,
                    'gasPrice': gasPrice
                })
        tx_receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)
        #self.logger.info(tx_receipt)
        return tx_receipt

    def liquidate(self, guy: Address, amount: Wad, user: Address, gasPrice: int) -> Liquidate:
        assert isinstance(amount, Wad)
        tx_hash = self.contract.functions.liquidate(guy.address, amount.value).transact({
                    'from': user.address,
                    'gasPrice': gasPrice
                })
        tx_receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)
        self.logger.info(tx_receipt)
        logs_len = len(tx_receipt['logs'])
        log_to_process = tx_receipt['logs'][logs_len-1]
        event_data = self.contract.events.Liquidate().processLog(log_to_process)
        assert event_data['event'] == 'Liquidate'
        return Liquidate(price=event_data['args']['price'], amount=event_data['args']['amount'])

