import os
import time
import json
import functools
from dotenv import load_dotenv
from binance.client import Client


def print_timestamped_message(message):
    timeFormat = "%a, %d %b %Y %H:%M:%S"
    timestamp = time.strftime(timeFormat, time.gmtime())
    print(timestamp + '    ' + message)


def print_and_sleep(seconds):
    print('SLEEP FOR {} SECONDS'.format(seconds))
    time.sleep(seconds)


def handle_api_errors(message):
    def method_wrapper(method):
        @functools.wraps(method)
        def _handle_api_errors(self, *args, **kwargs):
            try:
                result = method(self, *args, **kwargs)
            except Exception as e:
                print(
                    f"""
                    ERROR: {message}.\n 
                    REASON: {e}
                    """
                )
            else:
                return result
        return _handle_api_errors
    return method_wrapper


class BinanceClient:
    @handle_api_errors(message='UNABLE TO INIT CLIENT')
    def __init__(self, publicKey, privateKey):
        self.client = Client(publicKey, privateKey)

    @handle_api_errors(message='UNABLE TO GET PAIR INFO')
    def _get_pair_info(self, symbol):
        return self.client.get_symbol_info(symbol=symbol)

    def _get_pair_format(self, symbol):
        for filter_ in self._get_pair_info(symbol)['filters']:
            if filter_['filterType'] == 'LOT_SIZE':
                step_size = float(filter_['stepSize'])
                if step_size >= 1.0:
                    step_size_format = '{:.0f}'
                elif step_size == 0.1:
                    step_size_format = '{:.1f}'
                elif step_size == 0.01:
                    step_size_format = '{:.2f}'
                elif step_size == 0.001:
                    step_size_format = '{:.3f}'
                elif step_size == 0.0001:
                    step_size_format = '{:.4f}'
                elif step_size == 0.00001:
                    step_size_format = '{:.5f}'
                elif step_size == 0.000001:
                    step_size_format = '{:.6f}'
                elif step_size == 0.0000001:
                    step_size_format = '{:.7f}'
                elif step_size == 0.00000001:
                    step_size_format = '{:.8f}'
            if filter_['filterType'] == 'PRICE_FILTER':
                tick_size = float(filter_['tickSize'])
                if tick_size >= 1.0:
                    tick_size_format = '{:.0f}'
                elif tick_size == 0.1:
                    tick_size_format = '{:.1f}'
                elif tick_size == 0.01:
                    tick_size_format = '{:.2f}'
                elif tick_size == 0.001:
                    tick_size_format = '{:.3f}'
                elif tick_size == 0.0001:
                    tick_size_format = '{:.4f}'
                elif tick_size == 0.00001:
                    tick_size_format = '{:.5f}'
                elif tick_size == 0.000001:
                    tick_size_format = '{:.6f}'
                elif tick_size == 0.0000001:
                    tick_size_format = '{:.7f}'
                elif tick_size == 0.00000001:
                    tick_size_format = '{:.8f}'
        return {
            'stepSizeFormat': step_size_format,
            'tickSizeFormat': tick_size_format,
            'stepSize': step_size,
            'tickSize': tick_size,
        }

    def get_pair_formats(self, symbols):
        return {
            symbol: self._get_pair_format(symbol)
            for symbol in symbols
        }

    @handle_api_errors(message='UNABLE TO GET TICKER')
    def _get_ticker(self, symbol):
        price = self.client.get_ticker(symbol=symbol)
        return {
            'bidPrice': float(price['bidPrice']),
            'askPrice': float(price['askPrice']),
        }

    def get_all_prices(self, symbols):
        return {
            symbol: self._get_ticker(symbol)
            for symbol in symbols
        }

    @handle_api_errors(message='UNABLE TO GET OPEN ORDERS')
    def _get_open_orders(self, symbol):
        return self.client.get_open_orders(symbol=symbol)

    @handle_api_errors(message='UNABLE TO CANCEL ORDER')
    def _cancel_order(self, symbol, order_id):
        self.client.cancel_order(
            symbol=symbol, 
            orderId=order_id,
        )

    def cancel_all_open_orders(self, symbols):
        for symbol in symbols:
            for open_order in self._get_open_orders(symbol=symbol):
                self._cancel_order(
                    symbol=symbol, 
                    order_id=open_order['orderId'],
                )

    @handle_api_errors(message='UNABLE TO GET TRADES')
    def _get_trades(self, symbol, trade_id):
        return self.client.get_my_trades(
            symbol=symbol,
            fromId=trade_id + 1,
            limit=1000,
        )

    def _get_new_trades(self, symbol, last_id):
        trades = sorted(
            self._get_trades(
                symbol=symbol,
                trade_id=last_id,
            ),
            key=lambda x: x['id'],
        )
        return [
            {
                'id': trade['id'],
                'orderId': trade['orderId'],
                'symbol': trade['symbol'],
                'price': float(trade['price']),
                'baseAssetQty': float(trade['qty']),
                'quoteAssetQty': float(trade['quoteQty']),
                'time': trade['time'],
                'isBuyer': trade['isBuyer'],
            } 
            for trade in trades
        ]

    def get_all_new_trades(self, last_trades):
        return {
            symbol: self._get_new_trades(symbol, trade['id'])
            for symbol, trade in last_trades.items()
        }

    @handle_api_errors(message='UNABLE TO SEND BUY ORDER')
    def send_buy_order(self, order):
        self.client.order_limit_buy(
            symbol=order['symbol'], 
            quantity=order['qty'],
            price=order['price'],
            newClientOrderId=order['newClientOrderId']
        )

    @handle_api_errors(message='UNABLE TO SEND SELL ORDER')
    def send_sell_order(self, order):
        self.client.order_limit_sell(
            symbol=order['symbol'],
            quantity=order['qty'],
            price=order['price'],
            newClientOrderId=order['newClientOrderId']
        )

    def send_all_orders(self, all_orders):
        for orders in all_orders.values():
            self.send_buy_order(orders['buy_order'])
            self.send_sell_order(orders['sell_order'])


class Model():
    def __init__(self, filenames):
        self.data = {}
        self.filenames = filenames
        self.read_config()
    
    def read_config(self):
        with \
            open(self.filenames['config']) as fh1, \
            open(self.filenames['pairs']) as fh2, \
            open(self.filenames['trades']) as fh3:
            self.data['config'] = json.load(fh1)
            self.data['pairs'] = json.load(fh2)
            self.data['trades'] = json.load(fh3)
    
    def write_config(self):
        with \
            open(self.filenames['config'], 'w') as fh1, \
            open(self.filenames['pairs'], 'w') as fh2, \
            open(self.filenames['trades'], 'w') as fh3:
            json.dump(self.data['config'], fh1)
            json.dump(self.data['pairs'], fh2)
            json.dump(self.data['trades'], fh3)


class View:
    def __init__(self):
        pass

    def print_new_trades(self, all_trades):
        for symbol, trades in all_trades.items():
            print(f'NEW EXECUTED TRADES FOR THE PAIR {symbol}:')
            for trade in trades:
                print(
                    f'''
                    *************************************
                    Timestamp: {trade['time']}
                    Operation Type: {'BUY' if trade['isBuyer'] else 'SELL'}
                    Price: {trade['price']}
                    Quantity: {trade['baseAssetQty']}
                    *************************************
                    '''
                )
    
    def print_new_orders(self, all_orders):
        for symbol, orders in all_orders.items():
            print(f'SENDING NEW ORDERS FOR THE PAIR {symbol}:')
            print(f'BUY ORDERS:')
            print(
                f'''
                *************************************
                Type: Buy Order
                Price: {orders['buy_order']['price']}
                Quantity: {orders['buy_order']['qty']}
                *************************************
                '''
            )
            print(f'SELL ORDERS:')
            print(
                f'''
                *************************************
                Type: Sell Order
                Price: {orders['sell_order']['price']}
                Quantity: {orders['sell_order']['qty']}
                *************************************
                '''
            )


class Analyzer:
    def __init__(self, special_orders):
        self.initial_time = 1579349682.0
        self.special_orders = special_orders

    @property
    def _order_timestamp(self):
        return str(int(time.time() - self.initial_time))
    
    def _calc_percentages(self, buy_percentage, sell_percentage, away_from_mid_price):
        if self.special_orders:
            if away_from_mid_price >= 0.05:
                bid_percentage = min(0.95, buy_percentage)
                ask_percentage = max(1.05, 1.0 + away_from_mid_price)
            elif away_from_mid_price <= -0.05:
                bid_percentage = min(0.95, 1.0 + away_from_mid_price)
                ask_percentage = max(1.05, sell_percentage)
            else:
                bid_percentage = min(0.95, buy_percentage)
                ask_percentage = max(1.05, sell_percentage)
        else:
            bid_percentage = min(0.95, buy_percentage)
            ask_percentage = max(1.05, sell_percentage)
        return {
            'bidPercentage': bid_percentage,
            'askPercentage': ask_percentage,
        }

    def _calc_new_prices(self, percentages, fair_price, tick_size, bid_price, ask_price):
        my_bid_price = min(percentages['bidPercentage'] * fair_price, bid_price + tick_size)
        my_ask_price = max(percentages['askPercentage'] * fair_price, ask_price - tick_size)
        return {
            'bidPrice': my_bid_price,
            'askPrice': my_ask_price,
        }

    def _calc_new_quantities(self, total_coin, total_cash, new_prices):
        my_bid_quantity = 0.5*(total_cash - total_coin*new_prices['bidPrice']) / new_prices['bidPrice']
        my_ask_quantity = 0.5*(total_coin*new_prices['askPrice'] - total_cash) / new_prices['askPrice']
        return {
            'bidQty': my_bid_quantity,
            'askQty': my_ask_quantity,
        }

    def _calc_orders(self, symbol, pair, price):
        fair_price = pair['quoteAssetQty'] / pair['baseAssetQty']
        mid_price = 0.5*(price['bidPrice'] + price['askPrice'])
        away_from_mid_price = (mid_price - fair_price) / fair_price
        percentages = self._calc_percentages(
            buy_percentage=pair['buyPercentage'], 
            sell_percentage=pair['sellPercentage'], 
            away_from_mid_price=away_from_mid_price, 
        )
        new_prices = self._calc_new_prices(
            percentages=percentages, 
            fair_price=fair_price, 
            tick_size=pair['tickSize'], 
            bid_price=price['bidPrice'], 
            ask_price=price['askPrice'],
        )
        new_quantities = self._calc_new_quantities(
            total_coin=pair['baseAssetQty'], 
            total_cash=pair['quoteAssetQty'], 
            new_prices=new_prices,
        )
        tick_size_format = pair['tickSizeFormat']
        step_size_format = pair['stepSizeFormat']
        buy_order = {
            'symbol': symbol,
            'qty': step_size_format.format(new_quantities['bidQty']),
            'price': tick_size_format.format(new_prices['bidPrice']),
            'newClientOrderId': f'SHN-B-{symbol}-{self._order_timestamp}',
        }
        sell_order = {
            'symbol': symbol,
            'qty': step_size_format.format(new_quantities['askQty']),
            'price': tick_size_format.format(new_prices['askPrice']),
            'newClientOrderId': f'SHN-S-{symbol}-{self._order_timestamp}',
        }
        return {
            'buy_order': buy_order,
            'sell_order': sell_order,
        }

    def calc_all_orders(self, pairs, prices):
        return {
            symbol: self._calc_orders(symbol, pair, price)
            for symbol, pair, price in zip(
                pairs.keys(), 
                pairs.values(), 
                prices.values()
            )
        }


class ShannonsDemon:
    def __init__(self, publicKey, privateKey, filenames):
        self.lastRebalanceTime = time.time()
        self.apiClient = BinanceClient(publicKey, privateKey)
        self.view = View()
        self.analyzer = Analyzer(special_orders=False)
        self.model = Model(filenames)

    @property
    def bot_status(self):
        return self.model.data['config']['state']

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
        rebalanceIntervalSeconds = float(self.model.data['config']['delay_after_rebalance'])        
        if time.time() > self.lastRebalanceTime + rebalanceIntervalSeconds:
            self.lastRebalanceTime = time.time()
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
        #formats = self.apiClient.get_pair_formats(self.symbols)

        print_timestamped_message('CANCELLING ALL ORDERS')
        if self.bot_status == 'TRADE':
            self.apiClient.cancel_all_open_orders(self.symbols)
        
        while True:
            self.check_special_order_status()
            new_trades = self.apiClient.get_all_new_trades(self.trades)
            if self.are_there_new_trades(new_trades):
                self.view.print_new_trades(new_trades)
                #self.update_asset_quantities(new_trades)

            new_prices = self.apiClient.get_all_prices(self.symbols)

            new_orders = self.analyzer.calc_all_orders(
                self.pairs, 
                new_prices
            )
            
            self.view.print_new_orders(new_orders)
            
            print_timestamped_message('SENDING BUY AND SELL ORDERS')
            if self.bot_status == 'TRADE':
                self.apiClient.send_all_orders(new_orders)

            self.analyzer.special_orders = False
            
            #self.model.write_config()
            
            print_and_sleep(float(self.model.data['config']['delay_after_send']))        
            print_timestamped_message('CANCELLING ALL ORDERS')
            if self.bot_status == 'TRADE':
                self.apiClient.cancel_all_open_orders(self.symbols)
            print_and_sleep(float(self.model.data['config']['delay_after_cancel']))


if __name__ == '__main__':
    load_dotenv()
    bot = ShannonsDemon(
        publicKey=os.environ['BIN_PUB_KEY'],
        privateKey = os.environ['BIN_PRIV_KEY'],
        filenames={
            'config': 'config.json', 
            'pairs': 'pairs.json', 
            'trades': 'trades.json',
        }
    )
    bot.run()