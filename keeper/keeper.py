import argparse
import logging
import logging.config
import time
import toml
import json
import requests
import threading

from web3 import Web3, HTTPProvider, middleware
import eth_utils
from eth_utils import encode_hex
from eth_account import Account
from web3.middleware import construct_sign_and_send_raw_middleware, geth_poa_middleware
from web3.gas_strategies.time_based import medium_gas_price_strategy


from lib.address import Address
from lib.wad import Wad
from mcdex import Mcdex
from watcher import Watcher
from contract.perpetual import Perpetual, PositionSide, Status
from contract.token import ERC20Token

class Keeper:
    logger = logging.getLogger()

    def __init__(self, args: list, **kwargs):
        parser = argparse.ArgumentParser(prog='mai-keeper')
        parser.add_argument("--config", help="keeper config path", default="./config.toml", type=str)
        self.arguments = parser.parse_args(args)

        self.config = toml.load(self.arguments.config)
        logging.config.dictConfig(self.config['logging'])
        self.keeper_accounts = []
        self.keeper_account_keys = []
        self.web3 = kwargs['web3'] if 'web3' in kwargs else Web3(HTTPProvider(endpoint_uri=self.config['rpc']['url'],
                                                                              request_kwargs={"timeout": self.config['rpc']['timeout']}))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.gas_price = self.web3.toWei(10, "gwei")
        self.gas_level = 'fast'
        self.eth_gas_url = 'https://ethgasstation.info/json/ethgasAPI.json'
        self.get_gas_info()


        # gas price strategy 
        # self._set_gas_price_strategy()

        # contract 
        self.perp = Perpetual(web3=self.web3, address=Address(self.config['contracts']['perpetual']))
        self.token = ERC20Token(web3=self.web3, address=Address(self.config['contracts']['collateral_token']))

        # mcdex
        self.mcdex = None
        self.position_limit = 0
        self.inverse = True
        if self.config['mcdex'] is not None:
            self.mcdex = Mcdex(self.config['mcdex']['url'], self.config['mcdex']['market_id'])
            self.position_limit = self.config['mcdex']['position_limit']
            self.inverse = self.config['mcdex']['inverse']
            self.leverage = self.config['mcdex']['leverage']


        # watcher
        self.watcher = Watcher(self.web3)

    def get_gas_info(self):
        if self.web3 is None or self.config.get('gas', None) is None:
            return
        try:
            self.gas_level = self.config['gas'].get('gas_level')
            self.eth_gas_url = self.config['gas'].get('eth_gas_url')
        except Exception as e:
            self.logger.fatal(f"parse gas config error {e}")

    def get_gas_price(self):
        try:
            resp = requests.get(self.eth_gas_url, timeout=5)
            if resp.status_code / 100 == 2:
                rsp = json.loads(resp.content)
                self.gas_price = self.web3.toWei(rsp.get(self.gas_level) / 10, "gwei")
                self.logger.info(f"new gas price: {self.gas_price}")
        except Exception as e:
            self.logger.fatal(f"get gas price error {e}")


    def _check_accounts_balance(self):
        self.get_gas_price()
        for address in self.keeper_accounts:
            if self.token.address != Address('0x0000000000000000000000000000000000000000'):
                allowance = self.token.allowance(address, self.perp.address)
                self.logger.info(f"address:{address} allowance:{allowance}")

                if allowance.value == 0:
                    self.token.approve(self.perp.address, address)
                margin_account = self.perp.getMarginAccount(address)
                self.logger.info(f"address:{address} cash_balance:{margin_account.cash_balance}")
                if margin_account.cash_balance.value == 0:
                    self.logger.error(f"your cash balance is {margin_account.cash_balance}, please deposit enough balance in perpetual contract {self.perp.address}")
                    return False
            else:
                eth_balance = self.web3.eth.getBalance(address.address)
                self.logger.info(f"address:{address} eth_balance:{eth_balance}")
                margin_account = self.perp.getMarginAccount(address)
                self.logger.info(f"address:{address} cash_balance:{margin_account.cash_balance}")
                if margin_account.cash_balance.value == 0:
                    #self.perp.depositEther(100, address, self.gas_price)
                    self.logger.error(f"your cash balance is {margin_account.cash_balance}, please deposit enough balance in perpetual contract {self.perp.address}")
                    return False

        return True


    def _set_gas_price_strategy(self):
        # medium_gas_price_strategy: Transaction mined within 5 minutes
        if self.web3 is None or self.config.get('gas', None) is None:
            return
        if self.config['gas'].get('time_based', False):
            self.web3.eth.setGasPriceStrategy(medium_gas_price_strategy)
            self.web3.middleware_onion.add(middleware.time_based_cache_middleware)
            self.web3.middleware_onion.add(middleware.latest_block_based_cache_middleware)
            self.web3.middleware_onion.add(middleware.simple_cache_middleware)

    def _check_account_from_key(self, private_key):
        try:
            account = Account()
            acct = account.from_key(private_key)
            self.web3.middleware_onion.add(construct_sign_and_send_raw_middleware(acct))
        except:
            return False
        return True

    def _check_keeper_accounts(self):
        if len(self.config.get("accounts", [])) == 0 :
            self.logger.fatal(f"set account for keeper transact")
            return False
        for user_account in self.config["accounts"]:
            private_key = user_account.get("private_key", "")
            if private_key == "":
                return False

            # check account with key
            if self._check_account_from_key(private_key) is False:
                self.logger.exception(f"Account {user_account['address']} register key error")
                return False
            else:
                self.keeper_accounts.append(Address(user_account["address"]))
                self.keeper_account_keys.append(private_key)
            
        return True

    def _check_accounts_position(self):
        for i in range(len(self.keeper_accounts)):
            self.mcdex.set_wallet(self.keeper_account_keys[i], self.keeper_accounts[i].address)
            margin_account = self.perp.getMarginAccount(self.keeper_accounts[i])
            size = int(margin_account.size)
            if size < self.position_limit:
                continue

            # skip if active orders exist
            try:
                active_orders = self.mcdex.get_active_orders()
                if len(active_orders) > 0:
                    self.logger.info(f"active orders exist. address:{self.keeper_accounts[i].address}")
                    continue
            except Exception as e:
                self.logger.fatal(f"close position in mcdex failed. address:{self.keeper_accounts[i].address} error:{e}")
                continue
            
            side = "buy" if margin_account.side == PositionSide.SHORT else "sell"
            if self.inverse:
                side = "sell" if margin_account.side == PositionSide.SHORT else "buy"

            try:
                self.mcdex.place_order(str(size), "market", "0", side, 300, str(self.leverage))
            except Exception as e:
                self.logger.fatal(f"close position in mcdex failed. address:{self.keeper_accounts[i].address} error:{e}")
                continue

    def _check_all_accounts(self):
        def thread_fun(start, end, keeper_account_idx):
            self.logger.info(f"start thread! start:{start} end:{end} account:{self.keeper_accounts[keeper_account_idx]}")
            for index in range(start, end):
                self._check_account(index, keeper_account_idx)
 
        # check keeper accounts position
        self._check_accounts_position()

        # check perpetual contract status
        perp_status = self.perp.status()
        if perp_status != Status.NORMAL:
            self.logger.info(f"perpetual contract status is {perp_status}. keeper will stop!")
            self.watcher.set_terminated()
            return
        
        total = self.perp.total_accounts()
        account_num = len(self.keeper_accounts)
        num = int(total / account_num)
        thread_list = []
        self.get_gas_price()
        for i in range(len(self.keeper_accounts)):
            start_idx = i*num
            end_idx = total if i == account_num-1 else (i+1) * num
            thread = threading.Thread(target=thread_fun, args=(start_idx, end_idx, i))
            thread_list.append(thread)

        for i in range(len(thread_list)):
            thread_list[i].start()

        for i in range(len(thread_list)):
            thread_list[i].join()

        self.logger.info(f"check all accounts end! total:{total}")


    def _check_account(self, index, keeper_account_idx):
        keeper_account = self.keeper_accounts[keeper_account_idx]
        address = self.perp.accounts(index)
        margin_account = self.perp.getMarginAccount(address)
        self.logger.info(f"check_account: keeper_account:{keeper_account} address:{address} side:{margin_account.side} size:{margin_account.size}")
        if not self.perp.is_safe(address):
            try:
                liquidate_data = self.perp.liquidate(address, margin_account.size, keeper_account, self.gas_price)
                self.logger.info(f"liquidate success. address:{address} price:{liquidate_data.price} amount:{liquidate_data.amount}")
            except Exception as e:
                self.logger.fatal(f"liquidate failed. address:{address} error:{e}")
                return

    def main(self):
        if self._check_keeper_accounts() and self._check_accounts_balance():
            self.watcher.add_block_syncer(self._check_all_accounts)
            self.watcher.run()
