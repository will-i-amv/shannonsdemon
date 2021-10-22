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


class ShannonsDemon():
    def __init__(self):
        self.marketsConfig = {}
        self.trades = []
        self.specialOrders = False
        self.timeConst = 1579349682.0
        self.lastRebalanceTime = time.time()

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

    def get_market_prices(self, prices, i):
        self.marketsConfig['pairs'][i]['bid_price'] = prices['bidPrice']
        self.marketsConfig['pairs'][i]['ask_price'] = prices['askPrice']

    def calculate_new_asset_quantities(self, trade, i):        
        try:
            if trade['operationType'] == 'buy':
                self.marketsConfig['pairs'][i]['base_asset_qty'] += float(trade['base_asset_qty'])
                self.marketsConfig['pairs'][i]['quote_asset_qty'] -= float(trade['quote_asset_qty'])
            else:
                self.marketsConfig['pairs'][i]['base_asset_qty'] -= float(trade['base_asset_qty'])
                self.marketsConfig['pairs'][i]['quote_asset_qty'] += float(trade['quote_asset_qty'])       
            self.marketsConfig['pairs'][i]['fromId'] = trade['id']
        except Exception as e:
            print_timestamped_message('ERROR: UNABLE TO CALCULATE NEW QUANTITIES, BECAUSE: {}'.format(e))

    def calculate_order_data(self, i):
        tickSize = self.marketsConfig['pairs'][i]['tick_size']
        tickSizeFormat = self.marketsConfig['pairs'][i]['tick_size_format']
        stepSizeFormat = self.marketsConfig['pairs'][i]['step_size_format']        
        totalCoin = float(self.marketsConfig['pairs'][i]['base_asset_qty'])
        totalCash = float(self.marketsConfig['pairs'][i]['quote_asset_qty'])                        
        bidPrice = float(self.marketsConfig['pairs'][i]['bid_price'])
        askPrice = float(self.marketsConfig['pairs'][i]['ask_price'])
        buyPercentage = float(self.marketsConfig['pairs'][i]['buy_percentage'])
        sellPercentage = float(self.marketsConfig['pairs'][i]['sell_percentage'])
        fairPrice = totalCash / totalCoin
        midPrice = tickSizeFormat.format(0.5 * (bidPrice + askPrice))
        awayFromBuy = '{:.1f}'.format(100.0 * (float(midPrice) - fairPrice) / fairPrice) + '%'
        awayFromSell = '{:.1f}'.format(100.0 * (float(midPrice) - fairPrice) / fairPrice) + '%'
        awayFromMidPrice = (float(midPrice) - fairPrice) / fairPrice        
        if self.specialOrders:
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
        self.marketsConfig['pairs'][i]['mid_price'] = midPrice
        self.marketsConfig['pairs'][i]['away_from_buy'] = awayFromBuy
        self.marketsConfig['pairs'][i]['away_from_sell'] = awayFromSell
        self.marketsConfig['pairs'][i]['order_bid_price'] = tickSizeFormat.format(min(mybidPrice, bidPrice + tickSize))
        self.marketsConfig['pairs'][i]['order_bid_quantity'] = myBidQuantity
        self.marketsConfig['pairs'][i]['order_ask_price'] = tickSizeFormat.format(max(myaskPrice, askPrice - tickSize))
        self.marketsConfig['pairs'][i]['order_ask_quantity'] = myAskQuantity

    def set_buy_order_data(self, pair, i):
        buyOrderData = {}
        myOrderId = 'SHN-B-' + pair + '-' + str(int(time.time() - self.timeConst))                
        buyOrderData['symbol'] = pair
        buyOrderData['quantity'] = self.marketsConfig['pairs'][i]['order_bid_price']
        buyOrderData['price'] = self.marketsConfig['pairs'][i]['order_bid_quantity']
        buyOrderData['newClientOrderId'] = myOrderId
        return buyOrderData

    def set_sell_order_data(self, pair, i):
        sellOrderData = {}        
        myOrderId = 'SHN-S-' + pair + '-' + str(int(time.time() - self.timeConst))        
        sellOrderData['symbol'] = pair
        sellOrderData['quantity'] = self.marketsConfig['pairs'][i]['order_ask_quantity']
        sellOrderData['price'] = self.marketsConfig['pairs'][i]['order_ask_price']
        sellOrderData['newClientOrderId'] = myOrderId
        return sellOrderData

    def print_new_trade(self, trade):
        print_timestamped_message(
            ' NEW EXECUTED TRADE:\n' + \
            ' Timestamp: {} '.format(trade['timestamp']) + \
            ' Operation Type: {} '.format(trade['operationType']) + \
            ' Pair: {} '.format(trade['pair']) + \
            ' Price: {} '.format(trade['price'])  + \
            ' Quantity: {} '.format(trade['quantity']))
    
    def print_buy_order_data(self, pair, i):
        print_timestamped_message(
            'SEND BUY ORDER: {}\n'.format(pair) + \
            'Order bid price: {0: <9} '.format(
                self.marketsConfig['pairs'][i]['order_bid_price']) + \
            'Order bid quantity: {0: <8} '.format(
                self.marketsConfig['pairs'][i]['order_bid_quantity']) + \
            'Mid Price: {0: <9} '.format(
                self.marketsConfig['pairs'][i]['mid_price']) + \
            'Away from buy %: {} '.format(
                self.marketsConfig['pairs'][i]['away_from_buy']))

    def print_sell_order_data(self, pair, i):        
        print_timestamped_message(
            'SEND SELL ORDER: {}\n'.format(pair) + \
            'Order ask price: {0: <9} '.format(
                self.marketsConfig['pairs'][i]['order_ask_price']) + \
            'Order ask quantity: {0: <8} '.format(
                self.marketsConfig['pairs'][i]['order_ask_quantity']) + \
            'Mid Price: {0: <9} '.format(
                self.marketsConfig['pairs'][i]['mid_price']) + \
            'Away from sell %: {} '.format(
                self.marketsConfig['pairs'][i]['away_from_sell']))


def main():    
    filename = 'config.json'
    load_dotenv()
    publicKey = os.environ['BIN_PUB_KEY']
    privateKey = os.environ['BIN_PRIV_KEY']
    apiClient = BinanceClient(publicKey, privateKey)
    bot = ShannonsDemon()
    configData = ConfigurationData()
    configData.read_config(filename) # Read initial config
    bot.marketsConfig  = configData.config
    print_timestamped_message('INITIALIZING')
    binanceMarkets = apiClient.get_symbols()
    print_timestamped_message('CANCELLING ALL ORDERS')
    for idx, crypto_pair in enumerate(bot.marketsConfig['pairs']):
        for bin_market in binanceMarkets:
            if bin_market['symbol'] == crypto_pair['market']:
                formats = bot.get_market_parameters(bin_market)
                bot.marketsConfig['pairs'][idx]['tick_size_format'] = formats['tick_size_format']
                bot.marketsConfig['pairs'][idx]['step_size_format'] = formats['step_size_format']
                bot.marketsConfig['pairs'][idx]['tick_size'] = formats['tick_size']
                bot.marketsConfig['pairs'][idx]['step_size'] = formats['tick_size']
        apiClient.cancel_open_orders(crypto_pair['market'])
    
    while True:
        bot.check_special_order_status()
        print_timestamped_message('SENDING BUY AND SELL ORDERS')
        for i in range(len(bot.marketsConfig['pairs'])):
            pair = bot.marketsConfig['pairs'][i]['market']
            lastOrderId = bot.marketsConfig['pairs'][i]['fromId']
            newTrades = apiClient.get_new_trades(pair, lastOrderId) 
            for j in range(len(newTrades)): # For each pair, update its info if there are new executed trades
                if newTrades[j]['symbol'] == pair:
                    bot.trades.append(newTrades[j])
                    bot.print_new_trade(newTrades[j])
                    bot.calculate_new_asset_quantities(newTrades[j])            
            lastPrice = apiClient.get_ticker(pair) # For each pair, generate and send new buy and sell orders
            bot.get_market_prices(lastPrice, i)            
            bot.calculate_order_data(i)
            buyData = bot.set_buy_order_data(pair, i)
            sellData = bot.set_sell_order_data(pair, i)
            bot.print_buy_order_data(pair, i)
            bot.print_sell_order_data(pair, i)
            if bot.marketsConfig['state'] == 'TRADE':
                apiClient.send_buy_order(buyData)
                apiClient.send_sell_order(sellData)
        bot.specialOrders = False
        configData.config = bot.marketsConfig # Write updated config            
        configData.write_config(filename)
        print_and_sleep(float(bot.marketsConfig['sleep_seconds_after_send_orders']))        
        print_timestamped_message('CANCELLING ALL ORDERS')
        for i in range(len(bot.marketsConfig['pairs'])):
            pair = bot.marketsConfig['pairs'][i]['market']
            apiClient.cancel_open_orders(pair)
        print_and_sleep(float(bot.marketsConfig['sleep_seconds_after_cancel_orders']))


if __name__ == '__main__':
    main()
