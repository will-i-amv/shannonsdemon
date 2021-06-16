import time
import json
import os
from binance.client import Client


def get_markets_info(configDict, binanceClient, timeFormat, circuitBreaker):
    try:
        info = binanceClient.get_exchange_info()
    except Exception as e:
        print(time.strftime(timeFormat, time.gmtime()),
              '    circuitBreaker set to false, ' +
              'cant get market info from exchange: ', e)
        circuitBreaker = False
    formats = {}
    for i in range(len(configDict['pairs'])):
        key = configDict['pairs'][i]['market']
        format = {}
        for market in info['symbols']:
            if market['symbol'] == key:
                for filter in market['filters']:
                    if filter['filterType'] == 'LOT_SIZE':
                        stepSize = float(filter['stepSize'])
                        t = float(filter['stepSize'])
                        if t >= 1.0:
                            stepSizesFormat = '{:.0f}'
                        elif t == 0.1:
                            stepSizesFormat = '{:.1f}'
                        elif t == 0.01:
                            stepSizesFormat = '{:.2f}'
                        elif t == 0.001:
                            stepSizesFormat = '{:.3f}'
                        elif t == 0.0001:
                            stepSizesFormat = '{:.4f}'
                        elif t == 0.00001:
                            stepSizesFormat = '{:.5f}'
                        elif t == 0.000001:
                            stepSizesFormat = '{:.6f}'
                        elif t == 0.0000001:
                            stepSizesFormat = '{:.7f}'
                        elif t == 0.00000001:
                            stepSizesFormat = '{:.8f}'
                    if filter['filterType'] == 'PRICE_FILTER':
                        tickSize = (float(filter['tickSize']))
                        t = float(filter['tickSize'])
                        if t >= 1.0:
                            tickSizesFormat = '{:.0f}'
                        elif t == 0.1:
                            tickSizesFormat = '{:.1f}'
                        elif t == 0.01:
                            tickSizesFormat = '{:.2f}'
                        elif t == 0.001:
                            tickSizesFormat = '{:.3f}'
                        elif t == 0.0001:
                            tickSizesFormat = '{:.4f}'
                        elif t == 0.00001:
                            tickSizesFormat = '{:.5f}'
                        elif t == 0.000001:
                            tickSizesFormat = '{:.6f}'
                        elif t == 0.0000001:
                            tickSizesFormat = '{:.7f}'
                        elif t == 0.00000001:
                            tickSizesFormat = '{:.8f}'
        format['tickSizeFormat'] = tickSizesFormat
        format['stepSizeFormat'] = stepSizesFormat
        format['tickSize'] = tickSize
        format['stepSize'] = stepSize
        formats[key] = format
    return formats, circuitBreaker


def write_config(configDict, fileName, timeFormat, circuitBreaker):
    try:
        with open(fileName, 'w') as outfile:
            json.dump(configDict, outfile)
    except Exception as e:
        print(time.strftime(timeFormat, time.gmtime()),
              '    circuitBreaker set to false, ' +
              'cant write to file: ', e)
        circuitBreaker = False
    return circuitBreaker


def cancel_all_orders(binanceClient, configDict, timeFormat, circuitBreaker=True):
    try:
        for i in range(len(configDict['pairs'])):
            key = configDict['pairs'][i]['market']
            crtOrders = binanceClient.get_open_orders(symbol=key)
            if len(crtOrders) > 0:
                for j, val in enumerate(crtOrders):
                    if crtOrders[j]['clientOrderId'][0:3] == 'SHN':
                        binanceClient.cancel_order(symbol=key,
                                            orderId=crtOrders[j]['orderId'])
                    time.sleep(1.05)

    except Exception as e:
        print(time.strftime(timeFormat, time.gmtime()),
              '   circuitBreaker set to false, ' +
              'cannot cancel all orders: ', e)
        circuitBreaker = False
        time.sleep(5.0)
    
    return circuitBreaker


def process_all_trades(configDict, binanceClient, lastTrades, lastTradesCounter, timeFormat, circuitBreaker=True):
    #ordersAllowed = False
    try:
        for i in range(len(configDict['pairs'])):

            key = configDict['pairs'][i]['market']
            lastId = configDict['pairs'][i]['fromId']
            tradesTemp = binanceClient.get_my_trades(symbol=key,
                                              limit=1000,
                                              fromId=lastId + 1)
            trades = []
            trades = sorted(tradesTemp, key=lambda k: k['id'])

            # process trades
            for j in range(len(trades)):

                try:

                    order = binanceClient.get_order(symbol=key,
                                             orderId=trades[j]['orderId'])

                    if order['clientOrderId'][0:3] == 'SHN':

                        if trades[j]['isBuyer']:
                            configDict['pairs'][i]['base_asset_qty'] += float(trades[j]['qty'])
                            configDict['pairs'][i]['quote_asset_qty'] -= float(trades[j]['quoteQty'])
                        else:
                            configDict['pairs'][i]['base_asset_qty'] -= float(trades[j]['qty'])
                            configDict['pairs'][i]['quote_asset_qty'] += float(trades[j]['quoteQty'])

                        configDict['pairs'][i]['fromId'] = trades[j]['id']
                        circuitBreaker = write_config(configDict, fileName, timeFormat, circuitBreaker)

                        lastTradesCounter = lastTradesCounter + 1
                        if lastTradesCounter >= 3:
                            lastTradesCounter = 0
                        if trades[j]['isBuyer']:
                            print(time.strftime(timeFormat, time.gmtime()),
                                  '   new trade (buy) :', key,
                                  ' qty: ', trades[j]['qty'],
                                  ' price: ', trades[j]['price'])
                            timeStamp = str(time.ctime((float(trades[j]['time']) / 1000.0)))
                            buy = ' buy:' + '{0: <10}'.format(key)
                            qty = ' qty: ' + '{0: <10}'.format(trades[j]['qty'])
                            price = ' price: ' + '{0: <10}'.format(trades[j]['price'])
                            lastTrades[lastTradesCounter] = ' ' + timeStamp + buy + qty + price
                        else:
                            print(time.strftime(timeFormat, time.gmtime()),
                                  '   new trade (sell):', key,
                                  ' qty: ', trades[j]['qty'],
                                  ' price: ', trades[j]['price'])
                            timeStamp = str(time.ctime((float(trades[j]['time']) / 1000.0)))
                            sell = ' sell:' + '{0: <10}'.format(key)
                            qty = ' qty: ' + '{0: <10}'.format(trades[j]['qty'])
                            price = ' price: ' + '{0: <10}'.format(trades[j]['price'])
                            lastTrades[lastTradesCounter] = ' ' + timeStamp + sell + qty + price

                except Exception as e:
                    print('')

            time.sleep(1.1)
    except Exception as e:
        print(time.strftime(timeFormat, time.gmtime()),
              '   circuitBreaker set to fasle, ' +
              'not able to process all trades ', e)
        circuitBreaker = False
    return circuitBreaker


def send_orders(configDict, binanceClient, initialized, firstRun, infos, specialOrders, timeFormat, timeConstant, circuitBreaker):
    try:
        for i in range(len(configDict['pairs'])):
            circuitBreaker=True
            key = configDict['pairs'][i]['market']
            coin = float(configDict['pairs'][i]['base_asset_qty'])
            ticksize = infos[key]['tickSize']
            ticksizeformat = infos[key]['tickSizeFormat']
            stepsizeformat = infos[key]['stepSizeFormat']

            try:
                prices = binanceClient.get_ticker(symbol=key)
                circuitBreaker = True
            except Exception as e:
                circuitBreaker = False
                print(time.strftime(timeFormat, time.gmtime()),
                      '   not able to get price ', e)

            bidp = float(prices['bidPrice'])
            askp = float(prices['askPrice'])
            mid = ticksizeformat.format(0.5 * (bidp + askp))

            totcoin = float(coin)
            totcash = float(configDict['pairs'][i]['quote_asset_qty'])

            fairp = totcash / totcoin

            awayFromBuy = '{:.1f}'.format(
                100.0 * (float(mid) - fairp) / fairp) + '%'
            awayFromSell = '{:.1f}'.format(
                100.0 * (float(mid) - fairp) / fairp) + '%'
            awayFromMid = (float(mid) - fairp) / fairp

            if specialOrders:
                if float(awayFromMid) >= 0.05:
                    bidpercentage = min(
                        0.95,
                        float(configDict['pairs'][i]['buy_percentage']))
                    askpercentage = max(
                        1.05,
                        1.0 + float(awayFromMid))
                elif float(awayFromMid) <= -0.05:
                    bidpercentage = min(
                        0.95,
                        1.0 + float(awayFromMid))
                    askpercentage = max(
                        1.05,
                        float(configDict['pairs'][i]['sell_percentage']))
                else:
                    bidpercentage = min(
                        0.95,
                        float(configDict['pairs'][i]['buy_percentage']))
                    askpercentage = max(
                        1.05,
                        float(configDict['pairs'][i]['sell_percentage']))
            else:
                bidpercentage = min(
                    0.95,
                    float(configDict['pairs'][i]['buy_percentage']))
                askpercentage = max(
                    1.05,
                    float(configDict['pairs'][i]['sell_percentage']))

            mybidp = bidpercentage * fairp
            myaskp = askpercentage * fairp

            if float(mid) < 0.99 * mybidp or float(mid) > 1.01 * myaskp:
                circuitBreaker = False
                print(time.strftime(timeFormat, time.gmtime()),
                      '   please inspect quantities configDict file ' +
                      'as bot hits market')
                if firstRun:
                    initialized = False
            else:
                circuitBreaker = True

            mybidq = stepsizeformat.format(
                (0.5 * (totcoin * mybidp + totcash) - totcoin * mybidp)
                * 1.0 / mybidp)
            myaskq = stepsizeformat.format(
                (-0.5 * (totcoin * myaskp + totcash) + totcoin * myaskp)
                * 1.0 / myaskp)

            # start buy order
            orderbidp = ticksizeformat.format(
                min(mybidp, bidp + ticksize))
            orderbidq = mybidq
            if configDict['state'] == 'TRADE' and circuitBreaker:
                print(time.strftime(timeFormat, time.gmtime()),
                      '   send buy  order: ',
                      '{0: <9}'.format(key),
                      ' p: ', '{0: <9}'.format(str(orderbidp)),
                      ' q: ', '{0: <8}'.format(str(mybidq)),
                      ' l: ', '{0: <9}'.format(str(mid)),
                      ' b: ', awayFromBuy)

                myId = 'SHN-B-' + key + '-' + str(int(time.time() - timeConstant))
                try:
                    binanceClient.order_limit_buy(symbol=key,
                                           quantity=orderbidq,
                                           price=orderbidp,
                                           newbinanceClientOrderId=myId)
                except Exception as e:
                    print(time.strftime(timeFormat, time.gmtime()),
                          '   not able to send buy order for: ', key,
                          ' because: ', e)
            else:
                print(time.strftime(timeFormat, time.gmtime()),
                      '   send DUMMY  buy order: ', '{0: <9}'.format(key),
                      ' p: ', '{0: <9}'.format(str(orderbidp)),
                      ' q: ', '{0: <8}'.format(str(mybidq)),
                      ' l: ', '{0: <9}'.format(str(mid)),
                      ' b: ', awayFromBuy)

            # start sell order
            orderaskp = ticksizeformat.format(
                max(myaskp, askp - ticksize))
            orderaskq = myaskq
            if configDict['state'] == 'TRADE' and circuitBreaker:
                print(time.strftime(timeFormat, time.gmtime()),
                      '   send sell order: ', '{0: <9}'.format(key),
                      ' p: ', '{0: <9}'.format(str(orderaskp)),
                      ' q: ', '{0: <8}'.format(str(myaskq)),
                      ' l: ', '{0: <9}'.format(str(mid)),
                      ' s: ', awayFromSell)

                myId = 'SHN-S-' + key + '-' + str(int(time.time() - timeConstant))
                try:
                    binanceClient.order_limit_sell(symbol=key,
                                            quantity=orderaskq,
                                            price=orderaskp,
                                            newbinanceClientOrderId=myId)
                except Exception as e:
                    print(time.strftime(timeFormat, time.gmtime()),
                          '   not able to send sell order for: ', key,
                          ' because: ', e)
            else:
                print(time.strftime(timeFormat, time.gmtime()),
                      '   send DUMMY sell order: ', '{0: <9}'.format(key),
                      ' p: ', '{0: <9}'.format(str(orderaskp)),
                      ' q: ', '{0: <8}'.format(str(myaskq)),
                      ' l: ', '{0: <9}'.format(str(mid)),
                      ' s: ', awayFromSell)

    except Exception as e:
        print(time.strftime(timeFormat, time.gmtime()),
              '    not able to send orders ',
              e)

    firstRun = False
    return firstRun, initialized

def main():

    timeConstant = 1579349682.0
    infos = {}
    lastTrades = [None] * 3
    lastTradesCounter = -1
    specialOrders = True
    timeFormat = "%a, %d %b %Y %H:%M:%S"
    fileName = 'config.json'
    circuitBreaker = True
    initialized = True
    firstRun = True
    timeStamp = time.strftime(timeFormat, time.gmtime())

    # read config file
    try:
        with open(fileName) as json_data_file:
            configDict = json.load(json_data_file)
    except Exception as e:
        print(timeStamp,
            '   not able to read config file, ' +
            'please fix and restart: ', e)
        initialized = False

    # init binance binanceClient
    try:
        publicKey = os.environ['PUBLIC_KEY']
        privateKey = os.environ['PRIVATE_KEY']
        binanceClient = Client(publicKey, privateKey)
    except Exception as e:
        print(timeStamp,
              '   not able to init client,' +
              ' please fix and restart: ', e)
        initialized = False

    waitIntervalSeconds = float(configDict['sleep_seconds_after_cancel_orders'])
    quoteIntervalSeconds = float(configDict['sleep_seconds_after_send_orders'])
    rebalanceIntervalSeconds = float(configDict['rebalanceIntervalSeconds'])
    lastUpdate = time.time()

    if initialized:

        print(timeStamp, '   start initializing')
        infos, circuitBreaker = get_markets_info(configDict, binanceClient, timeFormat, circuitBreaker)
        time.sleep(5)
        print(timeStamp, '   end initializing')
        print(timeStamp, '   start cancel all orders')
        circuitBreaker = cancel_all_orders(binanceClient, configDict, timeFormat, circuitBreaker)
        print(timeStamp, '   end cancel all orders')
        rebalanceUpdate = time.time() # if start with rebalance:   - rebalanceIntervalSeconds -1.0

    while True and initialized:

        if not circuitBreaker:
            print(timeStamp, '   circuitBreaker false, do not send orders')
        else:
            print(timeStamp, '   start processing trades')
            circuitBreaker = process_all_trades(configDict, binanceClient, lastTrades, lastTradesCounter, timeFormat, circuitBreaker)
            print(timeStamp, '   end processing trades')

            # send orders special or normal
            lastUpdate = time.time()
            if time.time() > rebalanceUpdate + rebalanceIntervalSeconds and rebalanceIntervalSeconds > 0:
                rebalanceUpdate = time.time()
                print(timeStamp, '   start sending special orders')
                specialOrders = True
                firstRun, initialized = send_orders(configDict, binanceClient, initialized, firstRun, infos, specialOrders, timeFormat, timeConstant, circuitBreaker)
                specialOrders = False
                print(timeStamp, '   end sending special orders')
            else:
                print(timeStamp, '   start sending orders')
                firstRun, initialized = send_orders(configDict, binanceClient, initialized, firstRun, infos, specialOrders, timeFormat, timeConstant, circuitBreaker)
                print(timeStamp, '   end sending orders')

            for i in range(len(lastTrades)):
                if lastTrades[i] is not None:
                    print(timeStamp, '   last 3 trades: ', lastTrades[i])

        print(timeStamp, '   sleep for: ', quoteIntervalSeconds, ' seconds')
        time.sleep(quoteIntervalSeconds)

        lastUpdate = time.time()
        print(timeStamp, '   start cancel all orders')
        circuitBreaker = cancel_all_orders(binanceClient, configDict, timeFormat, circuitBreaker)
        print(timeStamp, '   end cancel all orders')
        print(timeStamp, '   sleep for: ', waitIntervalSeconds, ' seconds')
        time.sleep(waitIntervalSeconds)


if __name__ == "__main__":
    main()