from binance.client import Client
import time
import json
import os


class ShannonsDemon():
    def __init__(self):
        self.initialized = True
        self.firstRun = True
        self.circuitBreaker = True
        self.specialOrders = True
        self.timeFormat = "%a, %d %b %Y %H:%M:%S"
        self.timeConst = 1579349682.0
        self.timestamp = time.strftime(self.timeFormat, time.gmtime())
        self.lastTradesCounter = -1
        self.lastTrades = [None] * 3


    def get_markets_info(self, config, client):
        try:
            info = client.get_exchange_info()
        except Exception as e:
            print(self.timestamp,
                '    circuitBreaker set to false, ' +
                'cant get market info from exchange: ', e)
            self.circuitBreaker = False

        formats = {}
        for i in range(len(config['pairs'])):
            key = config['pairs'][i]['market']
            format = {}

            for market in info['symbols']:
                if market['symbol'] == key:

                    for filter in market['filters']:
                        if filter['filterType'] == 'LOT_SIZE':
                            stepSize = float(filter['stepSize'])
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
                        if filter['filterType'] == 'PRICE_FILTER':
                            tickSize = float(filter['tickSize'])
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

            format['tickSizeFormat'] = tickSizesFormat
            format['stepSizeFormat'] = stepSizesFormat
            format['tickSize'] = tickSize
            format['stepSize'] = stepSize

            formats[key] = format

        return formats


    def write_config(self, config, filename):
        try:
            with open(filename, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(self.timestamp,
                '    circuitBreaker set to false, ' +
                'cant write to file: ', e)
            self.circuitBreaker = False


    def cancel_all_orders(self, config, client):
        self.circuitBreaker = True
        try:
            for i in range(len(config['pairs'])):
                key = config['pairs'][i]['market']
                currentOrders = client.get_open_orders(symbol=key)
                if len(currentOrders) > 0:
                    for j, val in enumerate(currentOrders):
                        if currentOrders[j]['clientOrderId'][0:3] == 'SHN':
                            client.cancel_order(symbol=key,
                                                orderId=currentOrders[j]['orderId'])
                        time.sleep(1.05)

        except Exception as e:
            print(self.timestamp,
                '   circuitBreaker set to false, ' +
                'cannot cancel all orders: ', e)
            self.circuitBreaker = False
            time.sleep(5.0)


    def process_all_trades(self, config, client, filename):
        
        self.circuitBreaker = True

        try:
            for i in range(len(config['pairs'])):

                pair = config['pairs'][i]['market']
                lastId = config['pairs'][i]['fromId']
                tradesTemp = client.get_my_trades(symbol=pair,
                                                limit=1000,
                                                fromId=lastId + 1)
                trades = []
                trades = sorted(tradesTemp, key=lambda k: k['id'])

                # process trades
                for j in range(len(trades)):

                    try:

                        order = client.get_order(symbol=pair,
                                                orderId=trades[j]['orderId'])

                        if order['clientOrderId'][0:3] == 'SHN':

                            if trades[j]['isBuyer']:
                                operationType = 'buy'
                                config['pairs'][i]['base_asset_qty'] += float(trades[j]['qty'])
                                config['pairs'][i]['quote_asset_qty'] -= float(trades[j]['quoteQty'])
                            else:
                                operationType = 'sell'
                                config['pairs'][i]['base_asset_qty'] -= float(trades[j]['qty'])
                                config['pairs'][i]['quote_asset_qty'] += float(trades[j]['quoteQty'])

                            print(self.timestamp,
                                '   new trade ({}):'.format(operationType), pair,
                                ' qty: ', trades[j]['qty'],
                                ' price: ', trades[j]['price'])
                            timestamp2 = str(time.ctime((float(trades[j]['time']) / 1000.0)))
                            operation = ' {}:'.format(operationType) + '{0: <10}'.format(pair)
                            quantity = ' qty: ' + '{0: <10}'.format(trades[j]['qty'])
                            price = ' price: ' + '{0: <10}'.format(trades[j]['price'])
                            self.lastTrades[self.lastTradesCounter] = ' ' + timestamp2 + operation + quantity + price

                            config['pairs'][i]['fromId'] = trades[j]['id']
                            self.write_config(config, filename)
                            self.lastTradesCounter += 1
                            if self.lastTradesCounter >= 3:
                                self.lastTradesCounter = 0

                    except Exception as e:
                        print(e)

                time.sleep(1.1)

        except Exception as e:
            print(self.timestamp,
                '   self.circuitBreaker set to false, ' +
                'not able to process all trades ', e)
            self.circuitBreaker = False


    def send_orders(self, config, client, infos):
        try:
            for i in range(len(config['pairs'])):

                self.circuitBreaker = True
                pair = config['pairs'][i]['market']
                coin = float(config['pairs'][i]['base_asset_qty'])
                tickSize = infos[pair]['tickSize']
                tickSizeFormat = infos[pair]['tickSizeFormat']
                stepSizeFormat = infos[pair]['stepSizeFormat']

                try:
                    prices = client.get_ticker(symbol=pair)
                    self.circuitBreaker = True
                except Exception as e:
                    self.circuitBreaker = False
                    print(self.timestamp,
                        '   not able to get price ', e)

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
                    print(self.timestamp,
                        '   please inspect quantities config file ' +
                        'as bot hits market')
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
                    print(self.timestamp,
                        '   send buy  order: ',
                        '{0: <9}'.format(pair),
                        ' p: ', '{0: <9}'.format(str(orderBidPrice)),
                        ' q: ', '{0: <8}'.format(str(myBidQuantity)),
                        ' l: ', '{0: <9}'.format(str(midPrice)),
                        ' b: ', awayFromBuy)

                    myOrderId = 'SHN-B-' + pair + '-' + str(int(time.time() - self.timeConst))
                    try:
                        client.order_limit_buy(symbol=pair,
                                            quantity=orderBidQuantity,
                                            price=orderBidPrice,
                                            newClientOrderId=myOrderId)
                    except Exception as e:
                        print(self.timestamp,
                            '   not able to send buy order for: ', pair,
                            ' because: ', e)
                else:
                    print(self.timestamp,
                        '   send DUMMY  buy order: ', '{0: <9}'.format(pair),
                        ' p: ', '{0: <9}'.format(str(orderBidPrice)),
                        ' q: ', '{0: <8}'.format(str(myBidQuantity)),
                        ' l: ', '{0: <9}'.format(str(midPrice)),
                        ' b: ', awayFromBuy)

                # start sell order
                orderAskPrice = tickSizeFormat.format(
                    max(myaskPrice, askPrice - tickSize))
                orderAskQuantity = myAskQuantity
                if config['state'] == 'TRADE' and self.circuitBreaker:
                    print(self.timestamp,
                        '   send sell order: ', '{0: <9}'.format(pair),
                        ' p: ', '{0: <9}'.format(str(orderAskPrice)),
                        ' q: ', '{0: <8}'.format(str(myAskQuantity)),
                        ' l: ', '{0: <9}'.format(str(midPrice)),
                        ' s: ', awayFromSell)

                    myOrderId = 'SHN-S-' + pair + '-' + str(int(time.time() - self.timeConst))
                    try:
                        client.order_limit_sell(symbol=pair,
                                                quantity=orderAskQuantity,
                                                price=orderAskPrice,
                                                newClientOrderId=myOrderId)
                    except Exception as e:
                        print(self.timestamp,
                            '   not able to send sell order for: ', pair,
                            ' because: ', e)
                else:
                    print(self.timestamp,
                        '   send DUMMY sell order: ', '{0: <9}'.format(pair),
                        ' p: ', '{0: <9}'.format(str(orderAskPrice)),
                        ' q: ', '{0: <8}'.format(str(myAskQuantity)),
                        ' l: ', '{0: <9}'.format(str(midPrice)),
                        ' s: ', awayFromSell)

        except Exception as e:
            print(self.timestamp, '    not able to send orders ', e)

        self.firstRun = False


def main():
    
    bot = ShannonsDemon()
    
    # Read config file
    filename = 'config.json'
    try:
        with open(filename) as json_data_file:
            config = json.load(json_data_file)
    except Exception as e:
        print(bot.timestamp,
            '   not able to read config file, please fix and restart: ', e)
        bot.initialized = False

    # Init binance client
    try:
        publicKey = os.environ['PUBLIC_KEY']
        privateKey = os.environ['PRIVATE_KEY']
        client = Client(publicKey, privateKey)
    except Exception as e:
        print(bot.timestamp,
            '   not able to init client, please fix and restart: ', e)
        bot.initialized = False

    infos = {}
    wait_interval_sec = float(config['sleep_seconds_after_cancel_orders'])
    quote_interval_sec = float(config['sleep_seconds_after_send_orders'])
    rebalance_interval_sec = float(config['rebalance_interval_sec'])
    lastUpdate = time.time()

    if bot.initialized:
        print(bot.timestamp, '   start initializing')
        infos = bot.get_markets_info(config, client)
        time.sleep(5)
        print(bot.timestamp, '   end initializing')

        print(bot.timestamp, '   start cancel all orders')
        bot.cancel_all_orders(config, client)
        print(bot.timestamp, '   end cancel all orders')
        
        rebalanceUpdate = time.time() # if start with rebalance:   - rebalance_interval_sec -1.0

    while True and bot.initialized:

        if not bot.circuitBreaker:
            print(bot.timestamp, '   circuitBreaker false, do not send orders')
        else:

            print(bot.timestamp, '   start processing trades')
            bot.process_all_trades(config, client, filename)
            print(bot.timestamp, '   end processing trades')

            # Send orders special or normal
            lastUpdate = time.time()
            if time.time() > rebalanceUpdate + rebalance_interval_sec and rebalance_interval_sec > 0:
                rebalanceUpdate = time.time()
                print(bot.timestamp, '   start sending special orders')
                bot.specialOrders = True
                bot.send_orders(config, client, infos)
                bot.specialOrders = False
                print(bot.timestamp, '   end sending special orders')
            else:
                print(bot.timestamp, '   start sending orders')
                bot.send_orders(config, client, infos)
                print(bot.timestamp, '   end sending orders')

            for i in range(len(bot.lastTrades)):
                if bot.lastTrades[i] is not None:
                    print(bot.timestamp, '   last 3 trades: ', bot.lastTrades[i])

        print(bot.timestamp, '   sleep for: ', quote_interval_sec, ' seconds')
        time.sleep(quote_interval_sec)

        # Cancel orders
        lastUpdate = time.time()
        print(bot.timestamp, '   start cancel all orders')
        bot.cancel_all_orders(config, client)
        print(bot.timestamp, '   end cancel all orders')

        print(bot.timestamp, '   sleep for: ', wait_interval_sec, ' seconds')
        time.sleep(wait_interval_sec)


if __name__ == '__main__':
    main()