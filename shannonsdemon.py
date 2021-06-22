from binance.client import Client
import time
import json
import os


def print_timestamped_message(message):
    timeFormat = "%a, %d %b %Y %H:%M:%S"
    timestamp = time.strftime(timeFormat, time.gmtime())
    print(timestamp + '    ' + message)


class BinanceClient(Client):
    def __init__(self, publicKey, privateKey):
        self.circuitBreaker = True
        try:
            super(BinanceClient, self).__init__(publicKey, privateKey)
        except:
            print_timestamped_message('Not able to init client, please fix and restart: ' + e)
            self.circuitBreaker = False


    def get_exchange_info(self):
        try:
            self.circuitBreaker = True
            marketPairs = super(BinanceClient, self).get_exchange_info()
        except Exception as e:
            print_timestamped_message('Cannot get market info from exchange: ' + e)
            self.circuitBreaker = False
        return marketPairs['symbols']


    def cancel_all_orders(self, pair):
        try:
            self.circuitBreaker = True
            currentOrders = super(BinanceClient, self).get_open_orders(symbol=pair)
            for order in currentOrders:
                if order['clientOrderId'][0:3] == 'SHN':
                    super(BinanceClient, self).cancel_order(symbol=pair, orderId=order['orderId'])
                time.sleep(1.05)
        except Exception as e:
            print_timestamped_message('Cannot cancel all orders: ' + e)
            self.circuitBreaker = False


    def get_my_trades(self, pair, lastOrderId):
        lastTrades = []
        try:
            self.circuitBreaker = True
            tradesTemp = super(BinanceClient, self).get_my_trades(symbol=pair, limit=1000, fromId=lastOrderId + 1)
            lastTrades = sorted(tradesTemp, key=lambda k: k['id'])
        except Exception as e:
            print_timestamped_message('Not able to get all trades: ' + e)
            self.circuitBreaker = False
        return lastTrades 


    def get_order(self, pair, id):
        try:
            self.circuitBreaker = True
            order = super(BinanceClient, self).get_order(symbol=pair, orderId=id)
        except Exception as e:
            print_timestamped_message('Not able to get order: ' + e)
            self.circuitBreaker = False
        return order


    def get_ticker(self, pair):
        try:
            prices = super(BinanceClient, self).get_ticker(symbol=pair)
            self.circuitBreaker = True
        except Exception as e:
            self.circuitBreaker = False
            print_timestamped_message('Not able to get price ' + e)
        return prices


    def order_limit_buy(self, buyOrderData):

        try:
            super(BinanceClient, self).order_limit_buy(
                symbol=buyOrderData['pair'], 
                quantity=buyOrderData['order_bid_quantity'],
                price=buyOrderData['order_bid_price'],
                newClientOrderId=buyOrderData['myOrderId'])
        
        except Exception as e:
            print_timestamped_message('Not able to send buy order for ' + buyOrderData['pair'] + ' because: ' + e)


    def order_limit_sell(self, sellOrderData):
        try:
            super(BinanceClient, self).order_limit_sell(
                symbol=sellOrderData['pair'],
                quantity=sellOrderData['order_ask_quantity'],
                price=sellOrderData['order_ask_price'],
                newClientOrderId=sellOrderData['myOrderId'])
        
        except Exception as e:
            print_timestamped_message('Not able to send sell order for ' + sellOrderData['pair'] + ' because: ' + e)


class ConfigurationData():
    def __init__(self):
        self.circuitBreaker = True
        self.config = {}


    def read_config(self, filename):
        try:
            self.circuitBreaker = True
            with open(filename) as f:
                self.config = json.load(f)
        except Exception as e:
            print_timestamped_message('Not able to read config file, please fix and restart: ', e)
            self.circuitBreaker = False


    def write_config(self, filename):
        try:
            with open(filename, 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            print_timestamped_message('Cannot write to file: ', e)
            self.circuitBreaker = False


class ShannonsDemon():
    def __init__(self):
        self.initialized = True
        self.firstRun = True
        self.circuitBreaker = True
        self.marketsConfig = {}
        self.tradeData = {}
        self.specialOrders = False
        self.timeConst = 1579349682.0


    def get_market_parameters(self, market, i):
        for marketFilter in market['filters']:
            if marketFilter['filterType'] == 'LOT_SIZE':
                stepSize = float(marketFilter['stepSize'])
                if stepSize >= 1.0:
                    stepSizesFormat = '{:.0f}'
                elif stepSize == 0.1:
                    stepSizesFormat = '{:.1f}'
                elif stepSize == 0.01:
                    stepSizesFormat = '{:.2f}'
                elif stepSize == 0.001:
                    stepSizesFormat = '{:.3f}'
                elif stepSize == 0.0001:
                    stepSizesFormat = '{:.4f}'
                elif stepSize == 0.00001:
                    stepSizesFormat = '{:.5f}'
                elif stepSize == 0.000001:
                    stepSizesFormat = '{:.6f}'
                elif stepSize == 0.0000001:
                    stepSizesFormat = '{:.7f}'
                elif stepSize == 0.00000001:
                    stepSizesFormat = '{:.8f}'
            if marketFilter['filterType'] == 'PRICE_FILTER':
                tickSize = float(marketFilter['tickSize'])
                if tickSize >= 1.0:
                    tickSizesFormat = '{:.0f}'
                elif tickSize == 0.1:
                    tickSizesFormat = '{:.1f}'
                elif tickSize == 0.01:
                    tickSizesFormat = '{:.2f}'
                elif tickSize == 0.001:
                    tickSizesFormat = '{:.3f}'
                elif tickSize == 0.0001:
                    tickSizesFormat = '{:.4f}'
                elif tickSize == 0.00001:
                    tickSizesFormat = '{:.5f}'
                elif tickSize == 0.000001:
                    tickSizesFormat = '{:.6f}'
                elif tickSize == 0.0000001:
                    tickSizesFormat = '{:.7f}'
                elif tickSize == 0.00000001:
                    tickSizesFormat = '{:.8f}'
        self.marketsConfig['pairs'][i]['tick_size_format'] = tickSizesFormat
        self.marketsConfig['pairs'][i]['step_size_format'] = stepSizesFormat
        self.marketsConfig['pairs'][i]['tick_size'] = tickSize
        self.marketsConfig['pairs'][i]['step_size'] = stepSize


    def get_new_trade(self, trade):
        self.tradeData['timestamp'] = str(time.ctime((float(trade['time']) / 1000.0)))
        self.tradeData['operationType'] = 'buy' if trade['isBuyer'] else 'sell'
        self.tradeData['pair'] = trade['symbol']
        self.tradeData['price'] = '{0: <10}'.format(trade['price'])
        self.tradeData['base_asset_qty'] = '{0: <10}'.format(trade['qty'])
        self.tradeData['quote_asset_qty'] = '{0: <10}'.format(trade['quoteQty'])
        self.tradeData['id'] = trade['id']
        

    def get_market_prices(self, prices, i):
        self.marketsConfig['pairs'][i]['bid_price'] = prices['bidPrice']
        self.marketsConfig['pairs'][i]['ask_price'] = prices['askPrice']


    def calculate_new_asset_quantities(self, i):        
        try:
            if self.tradeData['operationType'] == 'buy':
                self.marketsConfig['pairs'][i]['base_asset_qty'] += float(self.tradeData['base_asset_qty'])
                self.marketsConfig['pairs'][i]['quote_asset_qty'] -= float(self.tradeData['quote_asset_qty'])
            else:
                self.marketsConfig['pairs'][i]['base_asset_qty'] -= float(self.tradeData['base_asset_qty'])
                self.marketsConfig['pairs'][i]['quote_asset_qty'] += float(self.tradeData['quote_asset_qty'])       
            self.marketsConfig['pairs'][i]['fromId'] = self.tradeData['id']

        except Exception as e:
            print_timestamped_message('Not able to update config ', e)
            self.circuitBreaker = False


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
            print_timestamped_message('Please inspect quantities config file as bot hits market')
            self.circuitBreaker = False
        
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


    def print_new_trade(self):
        try:
            print_timestamped_message(
                ' NEW EXECUTED TRADE:\n' + \
                ' Timestamp\n: {}'.format(self.tradeData['timestamp']) + \
                ' Operation Type\n: {}'.format(self.tradeData['operationType']) + \
                ' Pair: {}\n'.format(self.tradeData['pair']) + \
                ' Price: {}\n'.format(self.tradeData['price'])  + \
                ' Quantity: {}\n'.format(self.tradeData['quantity']))
    
        except Exception as e:
            print_timestamped_message('Not able to print trade ' + e)
            self.circuitBreaker = False


    def print_buy_order_data(self, pair, i):
        print_timestamped_message(
            'SEND BUY ORDER: {}\n'.format(pair) + \
            'Order bid price: {0: <9}\n'.format(
                self.marketsConfig['pairs'][i]['order_bid_price']) + \
            'Order bid quantity: {0: <8}\n'.format(
                self.marketsConfig['pairs'][i]['order_bid_quantity']) + \
            'Mid Price: {0: <9}\n'.format(
                self.marketsConfig['pairs'][i]['mid_price']) + \
            'Away from buy %: {}\n'.format(
                self.marketsConfig['pairs'][i]['away_from_buy']))


    def print_sell_order_data(self, pair, i):        
        print_timestamped_message(
            'SEND SELL ORDER: {}\n'.format(pair) + \
            'Order ask price: {0: <9}\n'.format(
                self.marketsConfig['pairs'][i]['order_ask_price']) + \
            'Order ask quantity: {0: <8}\n'.format(
                self.marketsConfig['pairs'][i]['order_ask_quantity']) + \
            'Mid Price: {0: <9}\n'.format(
                self.marketsConfig['pairs'][i]['mid_price']) + \
            'Away from sell %: {}\n'.format(
                self.marketsConfig['pairs'][i]['away_from_sell']))


def main():
    
    filename = 'config.json'
    publicKey = os.environ['PUBLIC_KEY']
    privateKey = os.environ['PRIVATE_KEY']
    
    apiClient = BinanceClient(publicKey, privateKey)
    bot = ShannonsDemon()
    configData = ConfigurationData()
    
    # Read config file
    configData.read_config(filename)
    bot.marketsConfig  = configData.config
         
    print_timestamped_message('INITIALIZING')
    binanceMarkets = apiClient.get_exchange_info()
    
    print_timestamped_message('CANCELLING ALL ORDERS')
    for i in range(len(bot.marketsConfig['pairs'])):
        pair = bot.marketsConfig['pairs'][i]['market']
        for j in range(len(binanceMarkets)):            
            if binanceMarkets[j]['symbol'] == pair:
                bot.get_market_parameters(binanceMarkets[j], i)
        time.sleep(5)
        apiClient.cancel_all_orders(pair)        
    
    rebalanceIntervalSeconds = float(bot.marketsConfig['rebalance_interval_sec'])        
    rebalanceUpdate = time.time() # if start with rebalance:   - rebalanceIntervalSeconds -1.0

    while bot.circuitBreaker and bot.initialized:

        # Send orders special or normal
        lastUpdate = time.time()
        if time.time() > rebalanceUpdate + rebalanceIntervalSeconds and rebalanceIntervalSeconds > 0:
            rebalanceUpdate = time.time()
            bot.specialOrders = True

        print_timestamped_message('SENDING BUY AND SELL ORDERS')
        for i in range(len(bot.marketsConfig['pairs'])):
            pair = bot.marketsConfig['pairs'][i]['market']
            lastOrderId = bot.marketsConfig['pairs'][i]['fromId']

            lastTrades = apiClient.get_my_trades(pair, lastOrderId)

            for j in range(len(lastTrades)):
                orderId = lastTrades[j]['orderId']
                order = apiClient.get_order(pair, orderId)
                if order['clientOrderId'][0:3] == 'SHN':
                    bot.get_new_trade(lastTrades[j])
                    bot.print_new_trade()
                    bot.calculate_new_asset_quantities(i)

            lastPrice = apiClient.get_ticker(pair)

            bot.get_market_prices(lastPrice, i)            
            bot.calculate_order_data(i)
            buyData = bot.set_buy_order_data(pair, i)
            sellData = bot.set_sell_order_data(pair, i)
            bot.print_buy_order_data(pair, i)
            bot.print_sell_order_data(pair, i)

            if bot.marketsConfig['state'] == 'TRADE' and bot.circuitBreaker:                
                apiClient.order_limit_buy(buyData)
                apiClient.order_limit_sell(sellData)
            
            bot.firstRun = False
            bot.SpecialOrders = False

        configData.config = bot.marketsConfig
        configData.write_config(filename)

        quoteIntervalSeconds = float(bot.marketsConfig['sleep_seconds_after_send_orders'])
        print_timestamped_message('SLEEP FOR {} SECONDS'.format(quoteIntervalSeconds))
        time.sleep(quoteIntervalSeconds)

        # Cancel orders
        lastUpdate = time.time()

        print_timestamped_message('CANCELLING ALL ORDERS')
        for i in range(len(bot.marketsConfig['pairs'])):
            pair = bot.marketsConfig['pairs'][i]['market']
            apiClient.cancel_all_orders(pair)

        waitIntervalSeconds = float(bot.marketsConfig['sleep_seconds_after_cancel_orders'])
        print_timestamped_message('SLEEP FOR {} SECONDS'.format(waitIntervalSeconds))
        time.sleep(waitIntervalSeconds)


if __name__ == '__main__':
    main()
