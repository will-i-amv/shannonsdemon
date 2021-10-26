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
    
    def print_buy_order_data(self, order):
        print_timestamped_message(
            'SEND BUY ORDER: {}\n'.format(order['newClientOrderId']) + \
            'Order bid price: {0: <9} '.format(order['price']) + \
            'Order bid quantity: {0: <8} '.format(order['quantity'])
        )

    def print_sell_order_data(self, order):
        print_timestamped_message(
            'SEND SELL ORDER: {}\n'.format(order['newClientOrderId']) + \
            'Order ask price: {0: <9} '.format(order['price']) + \
            'Order ask quantity: {0: <8} '.format(order['quantity'])
        )


class Analyzer:
    def __init__(self):
        self.timeConst = 1579349682.0

    def calculate_new_asset_quantities(self, pair, trade):
        new_quantity = {}
        if trade['operationType'] == 'buy':
            new_quantity['base_asset_qty'] = pair['base_asset_qty'] + float(trade['base_asset_qty'])
            new_quantity['quote_asset_qty']  = pair['base_asset_qty'] - float(trade['quote_asset_qty'])
        else:
            new_quantity['base_asset_qty'] = pair['base_asset_qty'] - float(trade['base_asset_qty'])
            new_quantity['quote_asset_qty'] = pair['base_asset_qty'] + float(trade['quote_asset_qty'])       
        new_quantity['fromId'] = trade['id']
        return new_quantity

    def calculate_order_data(self, pair, price, specialOrders):
        tickSize = pair['tick_size']
        tickSizeFormat = pair['tick_size_format']
        stepSizeFormat = pair['step_size_format']
        totalCoin = float(pair['base_asset_qty'])
        totalCash = float(pair['quote_asset_qty'])                        
        buyPercentage = float(pair['buy_percentage'])
        sellPercentage = float(pair['sell_percentage'])
        bidPrice = float(price['bidPrice'])
        askPrice = float(price['askPrice'])
        fairPrice = totalCash / totalCoin
        midPrice = tickSizeFormat.format(0.5 * (bidPrice + askPrice))
        awayFromBuy = '{:.1f}'.format(100.0 * (float(midPrice) - fairPrice) / fairPrice) + '%'
        awayFromSell = '{:.1f}'.format(100.0 * (float(midPrice) - fairPrice) / fairPrice) + '%'
        awayFromMidPrice = (float(midPrice) - fairPrice) / fairPrice        
        
        if specialOrders:
            if float(awayFromMidPrice) >= 0.05:
                bidPercentage = min(0.95, buyPercentage)
                askPercentage = max(1.05, 1.0 + float(awayFromMidPrice))
            elif float(awayFromMidPrice) <= -0.05:
                bidPercentage = min(0.95, 1.0 + float(awayFromMidPrice))
                askPercentage = max(1.05, sellPercentage)
            else:
                bidPercentage = min(0.95, buyPercentage)
                askPercentage = max(1.05, sellPercentage)
        else:
            bidPercentage = min(0.95, buyPercentage)
            askPercentage = max(1.05, sellPercentage)
        mybidPrice = bidPercentage * fairPrice
        myaskPrice = askPercentage * fairPrice
        myBidQuantity = stepSizeFormat.format((0.5 * (totalCoin * mybidPrice + totalCash) - totalCoin * mybidPrice)* 1.0 / mybidPrice)
        myAskQuantity = stepSizeFormat.format((-0.5 * (totalCoin * myaskPrice + totalCash) + totalCoin * myaskPrice)* 1.0 / myaskPrice)
        if float(midPrice) < 0.99 * mybidPrice or float(midPrice) > 1.01 * myaskPrice:
            print_timestamped_message('ERROR: THE BOT HITS MARKET, INSPECT QUANTITIES CONFIG FILE')        
        return {
            'mid_price': midPrice,
            'away_from_buy': awayFromBuy,
            'away_from_sell': awayFromSell,
            'order_bid_price': tickSizeFormat.format(min(mybidPrice, bidPrice + tickSize)),
            'order_bid_quantity': myBidQuantity,
            'order_ask_price': tickSizeFormat.format(max(myaskPrice, askPrice - tickSize)),
            'order_ask_quantity': myAskQuantity,
        }

    def set_buy_order_data(self, pair, order):
        buyOrderData = {}
        myOrderId = 'SHN-B-' + pair['market'] + '-' + str(int(time.time() - self.timeConst))                
        buyOrderData['symbol'] = pair['market']
        buyOrderData['quantity'] = order['order_bid_price']
        buyOrderData['price'] = order['order_bid_quantity']
        buyOrderData['newClientOrderId'] = myOrderId
        return buyOrderData

    def set_sell_order_data(self, pair, order):
        sellOrderData = {}        
        myOrderId = 'SHN-S-' + pair['market'] + '-' + str(int(time.time() - self.timeConst))        
        sellOrderData['symbol'] = pair['market']
        sellOrderData['quantity'] = order['order_ask_quantity']
        sellOrderData['price'] = order['order_ask_price']
        sellOrderData['newClientOrderId'] = myOrderId
        return sellOrderData


class ShannonsDemon:
    def __init__(self, publicKey, privateKey):
        self.marketsConfig = {}
        self.specialOrders = False
        self.lastRebalanceTime = time.time()

        self.apiClient = BinanceClient(publicKey, privateKey)
        self.view = View()
        self.analyzer = Analyzer()
        self.configData = ConfigurationData()

    def check_special_order_status(self):
        rebalanceIntervalSeconds = float(self.marketsConfig['rebalance_interval_sec'])        
        if time.time() > self.lastRebalanceTime + rebalanceIntervalSeconds:
            self.lastRebalanceTime = time.time()
            self.specialOrders = True

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
        for bot_pair in self.marketsConfig['pairs']:
            self.apiClient.cancel_open_orders(bot_pair['market'])
        
        while True:
            self.check_special_order_status()
            new_trades = self.apiClient.get_all_new_trades(last_ids)
            if self.are_there_new_trades(new_trades):
                self.view.print_new_trades(new_trades)
                #self.update_asset_quantities(new_trades)

            new_prices = self.apiClient.get_all_prices(symbols)

            print_timestamped_message('SENDING BUY AND SELL ORDERS')
            for i, bot_pair in enumerate(self.marketsConfig['pairs']):
                symbol = bot_pair['market']
                order = self.analyzer.calculate_order_data(bot_pair, price, self.specialOrders)
                buy_order = self.analyzer.set_buy_order_data(bot_pair, order)
                sell_order = self.analyzer.set_sell_order_data(bot_pair, order)
                
                self.view.print_buy_order_data(buy_order)
                self.view.print_sell_order_data(sell_order)
                if self.marketsConfig['state'] == 'TRADE':
                    self.apiClient.send_buy_order(buy_order)
                    self.apiClient.send_sell_order(sell_order)

            self.specialOrders = False
            
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