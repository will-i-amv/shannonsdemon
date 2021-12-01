import time
from itertools import chain


class Analyzer:
    def __init__(self, special_orders):
        self.initial_time = 1579349682.0
        self.special_orders = special_orders

    @property
    def _order_timestamp(self):
        return str(int(time.time() - self.initial_time))
    
    def _calc_percentages(self, buy_percentage, sell_percentage, away_from_midprice):
        if self.special_orders and away_from_midprice >= 0.05:
            bid_percentage = min(0.95, buy_percentage)
            ask_percentage = max(1.05, 1.0 + away_from_midprice)
        elif self.special_orders and away_from_midprice <= -0.05:
            bid_percentage = min(0.95, 1.0 + away_from_midprice)
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
        percentages = self._calc_percentages(
            buy_percentage=pair['buyPercentage'], 
            sell_percentage=pair['sellPercentage'], 
            away_from_midprice=(mid_price-fair_price)/fair_price, 
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
            'orderId': f'SHN-B-{symbol}-{self._order_timestamp}',
        }
        sell_order = {
            'symbol': symbol,
            'qty': step_size_format.format(new_quantities['askQty']),
            'price': tick_size_format.format(new_prices['askPrice']),
            'orderId': f'SHN-S-{symbol}-{self._order_timestamp}',
        }
        return [buy_order, sell_order]

    def calc_all_orders(self, pairs, prices):
        orders = [
            self._calc_orders(symbol, pair, price)
            for symbol, pair, price in zip(
                pairs.keys(), 
                pairs.values(), 
                prices.values()
            )
        ]
        return list(chain.from_iterable(orders))
