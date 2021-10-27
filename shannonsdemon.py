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

    @handle_api_errors(message='UNABLE TO GET ORDER')
    def get_order(self, symbol, order_id):
        return self.client.get_order(
            symbol=symbol,
            orderId=order_id,
        )

    @handle_api_errors(message='UNABLE TO GET OPEN ORDERS')
    def get_open_orders(self, pair):
        return self.client.get_open_orders(symbol=pair)

    @handle_api_errors(message='UNABLE TO CANCEL ORDER')
    def cancel_order(self, pair, order_id):
        self.client.cancel_order(
            symbol=pair, 
            orderId=order_id,
        )

    def cancel_open_orders(self, pair):
        for order in self.get_open_orders(pair=pair):
            if order['clientOrderId'][0:3] == 'SHN':
                self.cancel_order(
                    pair=pair, 
                    order_id=order['orderId'],
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
                'time': trade['time'],
                'id': trade['id'],
                'orderId': trade['orderId'],
                'price': float(trade['price']),
                'baseAssetQty': float(trade['qty']),
                'quoteAssetQty': float(trade['quoteQty']),
                'isBuyer': trade['isBuyer'],
            } 
            for trade in trades
        ]

    def get_all_new_trades(self, last_ids):
        return {
            symbol: self._get_new_trades(symbol, last_id)
            for symbol, last_id in last_ids.items()
        }

    @handle_api_errors(message='UNABLE TO SEND BUY ORDER')
    def send_buy_order(self, buyOrderData):
        self.client.order_limit_buy(
            symbol=buyOrderData['pair'], 
            quantity=buyOrderData['order_bid_quantity'],
            price=buyOrderData['order_bid_price'],
            newClientOrderId=buyOrderData['myOrderId']
        )

    @handle_api_errors(message='UNABLE TO SEND SELL ORDER')
    def send_sell_order(self, sellOrderData):
        self.client.order_limit_sell(
            symbol=sellOrderData['pair'],
            quantity=sellOrderData['order_ask_quantity'],
            price=sellOrderData['order_ask_price'],
            newClientOrderId=sellOrderData['myOrderId']
        )


class ConfigurationData():
    def __init__(self):
        self.config = {}

    def read_config(self, filename):
        try:
            with open(filename) as f:
                self.config = json.load(f)
        except Exception as e:
            print_timestamped_message('ERROR: UNABLE TO READ FROM CONFIG FILE, BECAUSE: {}'.format(e))

    def write_config(self, filename):
        try:
            with open(filename, 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            print_timestamped_message('ERROR: UNABLE TO WRITE TO CONFIG FILE, BECAUSE: {}'.format(e))


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
    def __init__(self, publicKey, privateKey):
        self.marketsConfig = {}
        self.lastRebalanceTime = time.time()
        self.apiClient = BinanceClient(publicKey, privateKey)
        self.view = View()
        self.analyzer = Analyzer(special_orders=False)
        self.configData = ConfigurationData()

    def check_special_order_status(self):
        rebalanceIntervalSeconds = float(self.marketsConfig['rebalance_interval_sec'])        
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

    def run(self, filename):
        symbols = ['BNBUSDT', 'ETHUSDT']
        last_ids = {'BNBUSDT': 418495317, 'ETHUSDT': 634206855}

        self.configData.read_config(filename) # Read initial config
        self.marketsConfig  = self.configData.config

        print_timestamped_message('INITIALIZING')
        formats = self.apiClient.get_pair_formats(symbols)

        print_timestamped_message('CANCELLING ALL ORDERS')
        for symbol in self.marketsConfig['pairs'].keys():
            self.apiClient.cancel_open_orders(symbol)
        
        while True:
            self.check_special_order_status()
            new_trades = self.apiClient.get_all_new_trades(last_ids)
            if self.are_there_new_trades(new_trades):
                self.view.print_new_trades(new_trades)
                #self.update_asset_quantities(new_trades)

            new_prices = self.apiClient.get_all_prices(symbols)

            new_orders = self.analyzer.calc_all_orders(
                self.marketsConfig['pairs'], 
                new_prices
            )
            
            self.view.print_new_orders(new_orders)
            
            print_timestamped_message('SENDING BUY AND SELL ORDERS')
            '''
            for i, bot_pair in enumerate(self.marketsConfig['pairs']):
                if self.marketsConfig['state'] == 'TRADE':
                    self.apiClient.send_buy_order(buy_order)
                    self.apiClient.send_sell_order(sell_order)
            '''
            self.analyzer.special_orders = False
            
            #self.configData.config = self.marketsConfig # Write updated config            
            #self.configData.write_config(filename)
            
            print_and_sleep(float(self.marketsConfig['sleep_seconds_after_send_orders']))        
            print_timestamped_message('CANCELLING ALL ORDERS')
            for bot_pairs in self.marketsConfig['pairs']:
                self.apiClient.cancel_open_orders(bot_pairs['market'])
            print_and_sleep(float(self.marketsConfig['sleep_seconds_after_cancel_orders']))


if __name__ == '__main__':
    load_dotenv()
    bot = ShannonsDemon(
        publicKey=os.environ['BIN_PUB_KEY'],
        privateKey = os.environ['BIN_PRIV_KEY'],
    )
    bot.run(filename='config.json')