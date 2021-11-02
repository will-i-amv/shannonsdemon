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

    def update_asset_quantities(self, all_trades):
        for symbol, trades in all_trades.items():
            for trade in trades:
                if trade['isBuyer']:
                    self.pairs[symbol]['baseAssetQty'] += trade['baseAssetQty']
                    self.pairs[symbol]['quoteAssetQty'] -= trade['quoteAssetQty']
                else:
                    self.pairs[symbol]['baseAssetQty'] -= trade['baseAssetQty']
                    self.pairs[symbol]['quoteAssetQty'] += trade['quoteAssetQty']

    def run(self):
        print_timestamped_message('INITIALIZING')
        #formats = self.client.get_pair_formats(self.symbols)

        print_timestamped_message('CANCELLING ALL ORDERS')
        if self.bot_status == 'TRADE':
            self.client.cancel_all_open_orders(self.symbols)
        
        while True:
            self.check_special_order_status()
            new_trades = self.client.get_all_new_trades(self.trades)
            if self.are_there_new_trades(new_trades):
                self.view.print_new_trades(new_trades)
                #self.update_asset_quantities(new_trades)

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
            
            #self.model.write_config()
            
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