import pytest
from lib.wad import Wad

class TestWad:
    def test_from_number(self):
        num_1 = Wad.from_number(1)
        assert 1 * 10**18 == num_1.value
        assert Wad(1 * 10**18) == num_1

        num_2 = Wad.from_number(0.1)

        assert 1 * 10**17 == num_2.value
        assert Wad(1 * 10**17) == num_2

    def test_operate(self):
        num_1 = Wad.from_number(10)
        num_2 = Wad.from_number(5)

        assert num_1 > num_2
        assert num_2 < num_1
        assert Wad.from_number(5) == num_1 - num_2
        assert Wad.from_number(15) == num_1 + num_2
        assert Wad.from_number(50) == num_1 * num_2
        assert Wad.from_number(2) == num_1 / num_2

        assert Wad.from_number(5) == Wad.min(num_1, num_2)
        assert Wad.from_number(10) == Wad.max(num_1, num_2)

        num_3 = Wad.from_number(3)
        assert 3 == int(num_1 / num_3)
        assert 10/3 == float(num_1 / num_3)
        assert abs(Wad.from_number(-10)) == num_1
        assert f"{num_1}"=="10.000000000000000000"
