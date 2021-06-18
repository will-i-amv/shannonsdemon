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
        return marketPairs


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


    def get_my_trades(self, pair, lastId):
        lastTrades = []
        try:
            self.circuitBreaker = True
            tradesTemp = super(BinanceClient, self).get_my_trades(symbol=pair, limit=1000, fromId=lastId + 1)
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


    def update_config(self, trade, i):
        try:
            if trade['isBuyer']:
                self.config['pairs'][i]['base_asset_qty'] += float(trade['qty'])
                self.config['pairs'][i]['quote_asset_qty'] -= float(trade['quoteQty'])
            else:
                self.config['pairs'][i]['base_asset_qty'] -= float(trade['qty'])
                self.config['pairs'][i]['quote_asset_qty'] += float(trade['quoteQty'])       
            self.config['pairs'][i]['fromId'] = trade['id']

        except Exception as e:
            print_timestamped_message('Not able to updte config ', e)
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
        self.specialOrders = True
        self.timeConst = 1579349682.0
        self.lastTradesCounter = -1
        self.lastTrades = [None] * 3
    

    def get_market_parameters(self, market):
        parameters = {}
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
        parameters['tickSizeFormat'] = tickSizesFormat
        parameters['stepSizeFormat'] = stepSizesFormat
        parameters['tickSize'] = tickSize
        parameters['stepSize'] = stepSize
        return parameters


    def print_new_trade(self, trade, pair):
        try:
            
            operationType = 'buy' if trade['isBuyer'] else 'sell'
            
            print_timestamped_message(
                '   new trade ({}):'.format(operationType), pair,
                ' quantity: ', trade['qty'],
                ' price: ', trade['price'])
            
            timestamp2 = str(time.ctime((float(trade['time']) / 1000.0)))
            operation = ' {}:'.format(operationType) + '{0: <10}'.format(pair)
            quantity = ' qty: ' + '{0: <10}'.format(trade['qty'])
            price = ' price: ' + '{0: <10}'.format(trade['price'])
            
            self.lastTrades[self.lastTradesCounter] = ' ' + timestamp2 + operation + quantity + price
            self.lastTradesCounter += 1
            if self.lastTradesCounter >= 3:
                self.lastTradesCounter = 0
            
            time.sleep(1.1)
            
        except Exception as e:
            print_timestamped_message('Not able to print trade ' + e)
            self.circuitBreaker = False


    def send_orders(self, config, client, marketsInfo):
        try:
            for i in range(len(config['pairs'])):

                self.circuitBreaker = True
                pair = config['pairs'][i]['market']
                coin = float(config['pairs'][i]['base_asset_qty'])
                tickSize = marketsInfo[pair]['tickSize']
                tickSizeFormat = marketsInfo[pair]['tickSizeFormat']
                stepSizeFormat = marketsInfo[pair]['stepSizeFormat']

                try:
                    prices = client.get_ticker(symbol=pair)
                    self.circuitBreaker = True
                except Exception as e:
                    self.circuitBreaker = False
                    print_timestamped_message('Not able to get price ' + e)

                bidPrice = float(prices['bidPrice'])
                askPrice = float(prices['askPrice'])
                midPrice = tickSizeFormat.format(0.5 * (bidPrice + askPrice))

                totalCoin = float(coin)
                totalCash = float(config['pairs'][i]['quote_asset_qty'])

                fairPrice = totalCash / totalCoin

                awayFromBuy = '{:.1f}'.format(
                    100.0 * (float(midPrice) - fairPrice) / fairPrice) + '%'
                awayFromSell = '{:.1f}'.format(
                    100.0 * (float(midPrice) - fairPrice) / fairPrice) + '%'
                awayFrommidPrice = (float(midPrice) - fairPrice) / fairPrice

                if self.specialOrders:
                    if float(awayFrommidPrice) >= 0.05:
                        bidPercentage = min(
                            0.95,
                            float(config['pairs'][i]['buy_percentage']))
                        askPercentage = max(
                            1.05,
                            1.0 + float(awayFrommidPrice))
                    elif float(awayFrommidPrice) <= -0.05:
                        bidPercentage = min(
                            0.95,
                            1.0 + float(awayFrommidPrice))
                        askPercentage = max(
                            1.05,
                            float(config['pairs'][i]['sell_percentage']))
                    else:
                        bidPercentage = min(
                            0.95,
                            float(config['pairs'][i]['buy_percentage']))
                        askPercentage = max(
                            1.05,
                            float(config['pairs'][i]['sell_percentage']))
                else:
                    bidPercentage = min(
                        0.95,
                        float(config['pairs'][i]['buy_percentage']))
                    askPercentage = max(
                        1.05,
                        float(config['pairs'][i]['sell_percentage']))

                mybidPrice = bidPercentage * fairPrice
                myaskPrice = askPercentage * fairPrice

                if float(midPrice) < 0.99 * mybidPrice or float(midPrice) > 1.01 * myaskPrice:
                    self.circuitBreaker = False
                    print_timestamped_message('Please inspect quantities config file as bot hits market')
                    if self.firstRun:
                        self.initialized = False
                else:
                    self.circuitBreaker = True

                myBidQuantity = stepSizeFormat.format(
                    (0.5 * (totalCoin * mybidPrice + totalCash) - totalCoin * mybidPrice)
                    * 1.0 / mybidPrice)
                myAskQuantity = stepSizeFormat.format(
                    (-0.5 * (totalCoin * myaskPrice + totalCash) + totalCoin * myaskPrice)
                    * 1.0 / myaskPrice)

                # start buy order
                orderBidPrice = tickSizeFormat.format(
                    min(mybidPrice, bidPrice + tickSize))
                orderBidQuantity = myBidQuantity
                if config['state'] == 'TRADE' and self.circuitBreaker:
                    print_timestamped_message(
                        'Send buy  order: {0: <9}'.format(pair) + \
                        ' p: {0: <9}'.format(str(orderBidPrice)) + \
                        ' q: {0: <8}'.format(str(myBidQuantity)) + \
                        ' l: {0: <9}'.format(str(midPrice)) + \
                        ' b: {}'.format(awayFromBuy))

                    myOrderId = 'SHN-B-' + pair + '-' + str(int(time.time() - self.timeConst))
                    try:
                        client.order_limit_buy(symbol=pair,
                                            quantity=orderBidQuantity,
                                            price=orderBidPrice,
                                            newClientOrderId=myOrderId)
                    except Exception as e:
                        print_timestamped_message('Not able to send buy order for ' + pair + ' because: ' + e)
                else:
                    print_timestamped_message(
                        'Send DUMMY  buy order: {0: <9}'.format(pair) + \
                        ' p: {0: <9}'.format(str(orderBidPrice)) + \
                        ' q: {0: <8}'.format(str(myBidQuantity)) + \
                        ' l: {0: <9}'.format(str(midPrice)) + \
                        ' b: {}'.format(awayFromBuy))

                # start sell order
                orderAskPrice = tickSizeFormat.format(
                    max(myaskPrice, askPrice - tickSize))
                orderAskQuantity = myAskQuantity
                if config['state'] == 'TRADE' and self.circuitBreaker:
                    print_timestamped_message(
                        'Send sell order: ', '{0: <9}'.format(pair) + \
                        ' p: {0: <9}'.format(str(orderAskPrice)) + \
                        ' q: {0: <8}'.format(str(myAskQuantity)) + \
                        ' l: {0: <9}'.format(str(midPrice)) + \
                        ' s: {}'.format(awayFromSell))

                    myOrderId = 'SHN-S-' + pair + '-' + str(int(time.time() - self.timeConst))
                    try:
                        client.order_limit_sell(symbol=pair,
                                                quantity=orderAskQuantity,
                                                price=orderAskPrice,
                                                newClientOrderId=myOrderId)
                    except Exception as e:
                        print_timestamped_message('Not able to send buy order for ' + pair + ' because: ' + e)

                else:
                    print_timestamped_message(
                        'Send DUMMY sell order: {0: <9}'.format(pair) + \
                        ' p: {0: <9}'.format(str(orderAskPrice)) + \
                        ' q: {0: <8}'.format(str(myAskQuantity)) + \
                        ' l: {0: <9}'.format(str(midPrice)) + \
                        ' s: {}'.format(awayFromSell))

        except Exception as e:
            print_timestamped_message('Not able to send orders ' + e)

        self.firstRun = False


def main():
    
    filename = 'config.json'
    publicKey = os.environ['PUBLIC_KEY']
    privateKey = os.environ['PRIVATE_KEY']
    
    apiClient = BinanceClient(publicKey, privateKey)
    bot = ShannonsDemon()
    configData = ConfigurationData()
    
    # Read config file
    configData.read_config(filename)
    waitIntervalSeconds = float(configData.config['sleep_seconds_after_cancel_orders'])
    quoteIntervalSeconds = float(configData.config['sleep_seconds_after_send_orders'])
    rebalanceIntervalSeconds = float(configData.config['rebalance_interval_sec'])

    markets = configData.config['pairs']
    marketsInfo = {}
    
    if bot.initialized:
        
        print_timestamped_message('Start initializing')
        binanceMarkets = apiClient.get_exchange_info()['symbols']
        print_timestamped_message('End initializing')
        
        print_timestamped_message('Start cancel all orders')
        for market in markets:
            pair = market['market']

            parameters = {}
            for binanceMarket in binanceMarkets:
                if binanceMarket['symbol'] == pair:
                    parameters = bot.get_market_parameters(binanceMarket)
            marketsInfo[pair] = parameters
        
            time.sleep(5)
            apiClient.cancel_all_orders(pair)       
        print_timestamped_message('End cancel all orders')
        
        rebalanceUpdate = time.time() # if start with rebalance:   - rebalanceIntervalSeconds -1.0

    while True and bot.initialized:

        if not bot.circuitBreaker:
            print_timestamped_message('CircuitBreaker false, do not send orders')
        else:
            
            print_timestamped_message('Start processing trades')
            for i, market in enumerate(markets):
                pair = market['market']
                lastId = market['fromId']

                lastTrades = apiClient.get_my_trades(pair, lastId)

                for trade in lastTrades:
                    orderId = trade['orderId']
                    order = apiClient.get_order(pair, orderId)
                    if order['clientOrderId'][0:3] == 'SHN':
                        configData.update_config(trade, i)
                        bot.print_new_trade(trade, pair)
            
            configData.write_config(filename)           
            print_timestamped_message('End processing trades')


            # Send orders special or normal
            lastUpdate = time.time()
            if time.time() > rebalanceUpdate + rebalanceIntervalSeconds and rebalanceIntervalSeconds > 0:
                rebalanceUpdate = time.time()
                print_timestamped_message('Start sending special orders')
                bot.specialOrders = True
                bot.send_orders(configData.config, apiClient, marketsInfo)
                bot.specialOrders = False
                print_timestamped_message('End sending special orders')
            else:
                print_timestamped_message('Start sending orders')
                bot.send_orders(configData.config, apiClient, marketsInfo)
                print_timestamped_message('End sending orders')

            for i in range(len(bot.lastTrades)):
                if bot.lastTrades[i] is not None:
                    print_timestamped_message('Last 3 trades: ' + bot.lastTrades[i])

        print_timestamped_message('Sleep for: ' + str(quoteIntervalSeconds) + ' seconds')
        time.sleep(quoteIntervalSeconds)

        # Cancel orders
        lastUpdate = time.time()
        print_timestamped_message('Start cancel all orders')
        for market in markets:
            apiClient.cancel_all_orders(pair)
        print_timestamped_message('End cancel all orders')

        print_timestamped_message('Sleep for: ' + str(waitIntervalSeconds) + ' seconds')
        time.sleep(waitIntervalSeconds)


if __name__ == '__main__':
    main()
