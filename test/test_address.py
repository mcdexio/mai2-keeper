import pytest
from lib.address import Address


def test_equal():
    address_1 = Address('0x6766F3CFD606E1E428747D3364baE65B6f914D56')
    assert Address('0x6766F3CFD606E1E428747D3364baE65B6f914D56') == address_1
    assert Address('0x6766F3CFD606E1E428747D3364baE65B6f914D51') != address_1
    assert Address(address_1).as_bytes() == address_1.as_bytes()
    assert repr(address_1) == f"Address('{address_1}')"
    assert Address('0x6766f3cfd606e1e428747d3364bae65b6f914d51') > address_1

def test_format():
    address_1 = Address('0x6766f3cfd606e1e428747d3364bae65b6f914d56')
    assert "{}".format(address_1) == '0x6766F3CFD606E1E428747D3364baE65B6f914D56'