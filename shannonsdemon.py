import os
import time
from dotenv import load_dotenv
from client import BinanceClient
from model import Model
from view import View
from analyzer import Analyzer


def print_timestamped_message(message):
    time_format = "%a, %d %b %Y %H:%M:%S"
    timestamp = time.strftime(time_format, time.gmtime())
    print(timestamp + '    ' + message)


def print_and_sleep(seconds):
    print('SLEEP FOR {} SECONDS'.format(seconds))
    time.sleep(seconds)


class ShannonsDemon:
    def __init__(self, public_key, private_key, filenames):
        self.rebalance_time = time.time()
        self.client = BinanceClient(public_key, private_key)
        self.view = View()
        self.analyzer = Analyzer(special_orders=False)
        self.model = Model(filenames)

    @property
    def bot_status(self):
        return self.model.data['config']['state']

    @property
    def delay_after_send_orders(self):
        return self.model.data['config']['delay_after_send']

    @property
    def delay_after_cancel_orders(self):
        return self.model.data['config']['delay_after_cancel']

    @property
    def delay_after_rebalance(self):
        return self.model.data['config']['delay_after_rebalance']

    @property
    def pairs(self):
        return self.model.data['pairs']
    
    @property
    def trades(self):
        return self.model.data['trades']

    @property
    def symbols(self):
        return [
            symbol
            for symbol in self.pairs.keys()
        ]

    @property
    def last_trades(self):
        return {
            symbol: sorted(
                last_trades, 
                key=lambda x: x['id'],
                reverse=True
            )[0]
            for symbol, last_trades in self.trades.items()
        }

    def check_special_order_status(self):
        if time.time() > self.rebalance_time + self.delay_after_rebalance:
            self.rebalance_time = time.time()
            self.analyzer.special_orders = True

    def are_there_new_trades(self, all_trades):
        return any([
                len(trades) 
                for trades in all_trades.values()
            ]
        )

    def check_if_initialized(self):
        if self.model.data:
            return
        else:
            self._initialize()
            self.model.write_config()

    def _initialize(self):
        pairs, status = self.view.input_bot_parameters()
        self.model.data['config'] = {
            "state": f"{status}",
            "delay_after_send": 300,
            "delay_after_cancel": 60,
            "delay_after_rebalance": 1080
        }
        formats = self.client.get_pair_formats(pairs)
        self.model.data['pairs'] = {
            symbol: {**pair, **format_}
            for symbol, pair, format_ in zip(
                pairs.keys(), 
                pairs.values(),
                formats.values(),
            )
        }
        last_trades = {
            symbol: {"id": 0}
            for symbol in self.symbols
        }
        self.model.data['trades'] = self.client.get_all_new_trades(last_trades)

    def update_asset_quantities(self, new_trades):
        for symbol, new_trades_by_symbol in new_trades.items():            
            for new_trade in new_trades_by_symbol:
                if new_trade['isBuyer']:
                    self.pairs[symbol]['baseAssetQty'] += new_trade['baseAssetQty']
                    self.pairs[symbol]['quoteAssetQty'] -= new_trade['quoteAssetQty']
                else:
                    self.pairs[symbol]['baseAssetQty'] -= new_trade['baseAssetQty']
                    self.pairs[symbol]['quoteAssetQty'] += new_trade['quoteAssetQty']
            self.trades[symbol] = new_trades_by_symbol

    def run(self):
        print_timestamped_message('INITIALIZING')
        self.check_if_initialized()

        print_timestamped_message('CANCELLING ALL ORDERS')
        if self.bot_status == 'TRADE':
            self.client.cancel_all_open_orders(self.symbols)
        
        while True:
            self.check_special_order_status()
            
            new_trades = self.client.get_all_new_trades(self.last_trades)
            if self.are_there_new_trades(new_trades):
                self.view.print_new_trades(new_trades)
                self.update_asset_quantities(new_trades)
                self.model.write_config()

            new_prices = self.client.get_all_prices(self.symbols)

            new_orders = self.analyzer.calc_all_orders(
                self.pairs, 
                new_prices
            )
            
            self.view.print_new_orders(new_orders)
            
            print_timestamped_message('SENDING BUY AND SELL ORDERS')
            if self.bot_status == 'TRADE':
                self.client.send_all_orders(new_orders)

            self.analyzer.special_orders = False
                        
            print_and_sleep(self.delay_after_send_orders)        
            print_timestamped_message('CANCELLING ALL ORDERS')
            if self.bot_status == 'TRADE':
                self.client.cancel_all_open_orders(self.symbols)
            print_and_sleep(self.delay_after_cancel_orders)


if __name__ == '__main__':
    load_dotenv()
    bot = ShannonsDemon(
        public_key=os.environ['BIN_PUB_KEY'],
        private_key = os.environ['BIN_PRIV_KEY'],
        filenames={
            'config': 'config.json', 
            'pairs': 'pairs.json', 
            'trades': 'trades.json',
        }
    )
    bot.run()