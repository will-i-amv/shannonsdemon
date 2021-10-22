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

    @handle_api_errors(message='UNABLE TO GET SYMBOLS')
    def get_symbols(self):
        return self.client.get_exchange_info()['symbols']

    @handle_api_errors(message='UNABLE TO GET TICKER')
    def get_ticker(self, pair):
        return self.client.get_ticker(symbol=pair)

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

    def is_shannon_order(self, trade):
        order = self.get_order(
                symbol=trade['symbol'],
                order_id=trade['orderId']
            )
        return order['clientOrderId'][0:3] == 'SHN'

    @handle_api_errors(message='UNABLE TO GET TRADES')
    def get_trades(self, pair, order_id, **kwargs):
        executed_trades = self.client.get_my_trades(
            symbol=pair,
            fromId=order_id + 1,
            **kwargs
        )
        return sorted(
            executed_trades,
            key=lambda x: x['id'],
        )

    def get_new_trades(self, pair, lastOrderId):
        trades = self.get_trades(
            pair=pair,
            order_id=lastOrderId,
            limit=1000,
        )
        return [
            trade
            for trade in trades
            if self.is_shannon_order(trade)
        ]

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

    def print_new_trade(self, trade):
        print_timestamped_message(
            ' NEW EXECUTED TRADE:\n' + \
            ' Timestamp: {} '.format(trade['timestamp']) + \
            ' Operation Type: {} '.format(trade['operationType']) + \
            ' Pair: {} '.format(trade['pair']) + \
            ' Price: {} '.format(trade['price'])  + \
            ' Quantity: {} '.format(trade['quantity']))
    
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

    def get_market_parameters(self, market):
        for filter_ in market['filters']:
            if filter_['filterType'] == 'LOT_SIZE':
                stepSize = float(filter_['stepSize'])
                if stepSize >= 1.0:
                    stepSizeFormat = '{:.0f}'
                elif stepSize == 0.1:
                    stepSizeFormat = '{:.1f}'
                elif stepSize == 0.01:
                    stepSizeFormat = '{:.2f}'
                elif stepSize == 0.001:
                    stepSizeFormat = '{:.3f}'
                elif stepSize == 0.0001:
                    stepSizeFormat = '{:.4f}'
                elif stepSize == 0.00001:
                    stepSizeFormat = '{:.5f}'
                elif stepSize == 0.000001:
                    stepSizeFormat = '{:.6f}'
                elif stepSize == 0.0000001:
                    stepSizeFormat = '{:.7f}'
                elif stepSize == 0.00000001:
                    stepSizeFormat = '{:.8f}'
            if filter_['filterType'] == 'PRICE_FILTER':
                tickSize = float(filter_['tickSize'])
                if tickSize >= 1.0:
                    tickSizeFormat = '{:.0f}'
                elif tickSize == 0.1:
                    tickSizeFormat = '{:.1f}'
                elif tickSize == 0.01:
                    tickSizeFormat = '{:.2f}'
                elif tickSize == 0.001:
                    tickSizeFormat = '{:.3f}'
                elif tickSize == 0.0001:
                    tickSizeFormat = '{:.4f}'
                elif tickSize == 0.00001:
                    tickSizeFormat = '{:.5f}'
                elif tickSize == 0.000001:
                    tickSizeFormat = '{:.6f}'
                elif tickSize == 0.0000001:
                    tickSizeFormat = '{:.7f}'
                elif tickSize == 0.00000001:
                    tickSizeFormat = '{:.8f}'
        return {
            'step_size_format': stepSizeFormat,
            'tick_size_format': tickSizeFormat,
            'step_size': stepSize,
            'tick_size': tickSize,
        }

    def run(self, filename):

        self.configData.read_config(filename) # Read initial config
        self.marketsConfig  = self.configData.config

        print_timestamped_message('INITIALIZING')
        binance_pairs = self.apiClient.get_symbols()
        print_timestamped_message('CANCELLING ALL ORDERS')
        for idx, bot_pair in enumerate(self.marketsConfig['pairs']):
            for binance_pair in binance_pairs:
                if binance_pair['symbol'] == bot_pair['market']:
                    formats = self.get_market_parameters(binance_pair)
                    self.marketsConfig['pairs'][idx]['tick_size_format'] = formats['tick_size_format']
                    self.marketsConfig['pairs'][idx]['step_size_format'] = formats['step_size_format']
                    self.marketsConfig['pairs'][idx]['tick_size'] = formats['tick_size']
                    self.marketsConfig['pairs'][idx]['step_size'] = formats['tick_size']
            self.apiClient.cancel_open_orders(bot_pair['market'])
        
        while True:
            self.check_special_order_status()
            print_timestamped_message('SENDING BUY AND SELL ORDERS')
            
            for i, bot_pair in enumerate(self.marketsConfig['pairs']):
                symbol = bot_pair['market']
                lastOrderId = bot_pair['fromId']
                newTrades = self.apiClient.get_new_trades(symbol, lastOrderId) 
                
                for newTrade in newTrades: # For each pair, update its info if there are new executed trades
                    if newTrade['symbol'] == symbol:
                        self.view.print_new_trade(newTrade)
                        new_quantities = self.analyzer.calculate_new_asset_quantities(newTrade)            
                        self.marketsConfig['pairs'][i]['base_asset_qty'] = new_quantities['base_asset_qty']
                        self.marketsConfig['pairs'][i]['quote_asset_qty'] = new_quantities['quote_asset_qty']
                        self.marketsConfig['pairs'][i]['fromId'] = new_quantities['fromId']

                price = self.apiClient.get_ticker(symbol) # For each pair, generate and send new buy and sell orders
                order = self.analyzer.calculate_order_data(bot_pair, price, self.specialOrders)
                buy_order = self.analyzer.set_buy_order_data(bot_pair, order)
                sell_order = self.analyzer.set_sell_order_data(bot_pair, order)
                
                self.view.print_buy_order_data(buy_order)
                self.view.print_sell_order_data(sell_order)
                if self.marketsConfig['state'] == 'TRADE':
                    self.apiClient.send_buy_order(buy_order)
                    self.apiClient.send_sell_order(sell_order)

            self.specialOrders = False
            
            self.configData.config = self.marketsConfig # Write updated config            
            self.configData.write_config(filename)
            
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