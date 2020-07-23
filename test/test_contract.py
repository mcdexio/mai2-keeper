import pytest
from lib.contract import Contract
from lib.address import Address
from web3 import Web3, HTTPProvider


def test_contract():
    web3 = Web3(HTTPProvider(endpoint_uri=f"http://localhost:8545",request_kwargs={"timeout":10}))
    perp = Contract()
    abi = Contract._load_abi(__name__, '../abi/Perpetual.abi')
    contract = perp._get_contract(web3, abi, Address("0x0D1dB4ef31ebe69c4e91BA703A829Ca0Ae49C534"))
    assert contract.address == "0x0D1dB4ef31ebe69c4e91BA703A829Ca0Ae49C534"