# Shannon;s Demon

## Overview 

A trading bot that grows the value of a crypto portfolio by repeatedly rebalancing it. For more information about the bot's trading strategy, see [here](https://thepfengineer.com/2016/04/25/rebalancing-with-shannons-demon/). For now only Binance is supported.

## How it works

Let's start with a portfolio worth 1000 USD and trade BNB/USDT (market). Since we have to start with a perfectly balanced portfolio, we buy 500 USD worth of USDT (quote_asset_qty) and 500 USD worth of BNB (base_asset_qty). At a current price of of 20 BNBUSDT that is 25 BNB. This is also called the equilibrium price.

T0: 500.0 USDT + 25.00 BNB x 20.0 BNB/USDT = 1000.0 USDT.

At T1 the price decreases to 15.0 BNB/USDT and to be perfectly balanced again the bot buys 4.17 BNB in exchange for 62.5 USDT.

T1: 500.0 USDT + 25.00 BNB x 15.0 BNB/USDT = 875.0 USDT.
T1: Rebalance: buy 4.17 BNB.
T1: 437.5 USDT + 29.17 BNB x 15.0 BNB/USDT = 875.0 USDT.

At T2 the price increases to 20.0 BNB/USDT and to be perfectly balanced again the bot sells 3.65 BNB in exchange for 72.92 USDT.

T2: 437.50 USDT + 29.17 BNB x 20.0 BNB/USDT = 1020.8 USDT.
T2: Rebalance: sell 3.65 BNB.
T2: 510.42 USDT + 25.52 BNB x 20.0 BNB/USDT = 1020.8 USDT.

As you can see in the above example we have generated a small retrun of approximately 2%. Over time the bot generates many small returns which are immediately reinvested. This is also known as volatility harvesting, and if there is plenty of something in the crypto space, it is volatility.

The given example is a simplified explanation of how the bot works. Actually it starts with sending orders at the equilibrium price multiplied by buy_percentage and sell_percentage. With these parameters equal to 0.9 and 1.1 that would be orders with price of 18 and 22 BNB/USDT at time T0. After waiting sleep_seconds_after_send_orders seconds, the bot cancels all open orders, processes all new (trade id > fromId) trades that were send with this bot and finally waits another sleep_seconds_after_cencel_orders seconds. Every rebalance_interval_sec seconds instead of sending orders at fixed percentages, the bot sends special orders. These special orders rebalance at the current price given that it's more than 5% away from equilibrium.

## Installing

Before installing, open a new account on Binance. Create api keys and make sure to have trading option enabled and withdrawal option disabled. Fund your account, make sure you have the right quantities for every market you want to trade and set all parameters in the config.json file.

Then clone the github repository and run the python script.

## Testing

It's recommendable to always start the bot with state equal to TEST to check if the orders that are about to be sent make sense.

Specifically, always start your bot following the steps below until you know what you're doing:

1. Set state equal to TEST in config file. Start your bot by running the python script. Wait until you see [end processing trades] in the ui and stop the bot. If you received any error messages you need to solve the errors first and restart the bot until it runs error free. Now all new trades are processed and fromId is updated if necessary.

2. Now you can increase or decrease the base_asset_qty and quote_asset_qty but make sure that all markets are close to equilibrium. Re-start the bot with state still equal to TEST and check if DUMMY order prices for all markets make sense. The [b:] and [s:] percentage are 0% if in equilibrium. If too far from equilibrium an error is thrown that an order would hit the market and most of the time you have made a mistake in quantities. After checking all markets you can stop the bot.

3. Change the state to TRADE and start again the bot.

## Debugging

But most error messages are related to time sync. This means that the time of your computer is not in sync with the time of Binance’s servers. Sync your system’s clock in order to solve it. Your router's time may needed to be synced also. For all other error messages see the python-binance's api documentation [here](https://python-binance.readthedocs.io/en/latest). 


## Disclaimer

This software is for educational purposes only. Do not risk money which you are not ready to lose. Use the software at your own risk.

