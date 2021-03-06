import unittest
import os
import logging
from hermes.stable_api import StableHermes as Hermes

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

email = os.getenv("email")
password = os.getenv("password")


class TestBinaryOption(unittest.TestCase):
    def test_binary_option(self):
        i_want_money = Hermes(email, password)
        i_want_money.connect()

        i_want_money.change_balance("PRACTICE")
        i_want_money.reset_practice_balance()

        self.assertEqual(i_want_money.check_connect(), True)

        all_asset = i_want_money.get_all_open_actives()

        if all_asset["turbo"]["EURUSD"]["open"]:
            active = "EURUSD"
        else:
            active = "EURUSD-OTC"

        check_call, id_call = i_want_money.buy({
            "price_amount": 1,
            "active": active,
            "action": "call",
            "expiration": 1
        })

        self.assertTrue(check_call)
        self.assertTrue(type(id_call) is int)

        i_want_money.sell_option(id_call)

        check_put, id_put = i_want_money.buy({
            "price_amount": 1,
            "active": active,
            "action": "put",
            "expiration": 1
        })

        self.assertTrue(check_put)
        self.assertTrue(type(id_put) is int)

        i_want_money.sell_option(id_put)
        i_want_money.check_win_v2(id_put)

        i_want_money.get_binary_option_detail()

        i_want_money.get_all_profit()

        is_successful = i_want_money.get_bet_info(id_put)

        self.assertTrue(is_successful)

        i_want_money.get_option_info(10)
