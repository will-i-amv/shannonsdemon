import functools
from binance.client import Client


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

    @handle_api_errors(message='UNABLE TO GET OPEN ORDERS')
    def _get_open_orders(self, symbol):
        return self.client.get_open_orders(symbol=symbol)

    @handle_api_errors(message='UNABLE TO CANCEL ORDER')
    def _cancel_order(self, symbol, order_id):
        self.client.cancel_order(
            symbol=symbol, 
            orderId=order_id,
        )

    def cancel_all_open_orders(self, symbols):
        for symbol in symbols:
            for open_order in self._get_open_orders(symbol=symbol):
                self._cancel_order(
                    symbol=symbol, 
                    order_id=open_order['orderId'],
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
                'id': trade['id'],
                'orderId': trade['orderId'],
                'price': float(trade['price']),
                'baseAssetQty': float(trade['qty']),
                'quoteAssetQty': float(trade['quoteQty']),
                'time': trade['time'],
                'isBuyer': trade['isBuyer'],
            } 
            for trade in trades
        ]

    def get_all_new_trades(self, last_trades):
        return {
            symbol: self._get_new_trades(symbol, trade['id'])
            for symbol, trade in last_trades.items()
        }

    @handle_api_errors(message='UNABLE TO SEND BUY ORDER')
    def send_buy_order(self, order):
        self.client.order_limit_buy(
            symbol=order['symbol'], 
            quantity=order['qty'],
            price=order['price'],
            newClientOrderId=order['newClientOrderId']
        )

    @handle_api_errors(message='UNABLE TO SEND SELL ORDER')
    def send_sell_order(self, order):
        self.client.order_limit_sell(
            symbol=order['symbol'],
            quantity=order['qty'],
            price=order['price'],
            newClientOrderId=order['newClientOrderId']
        )

    def send_all_orders(self, all_orders):
        for orders in all_orders.values():
            self.send_buy_order(orders['buy_order'])
            self.send_sell_order(orders['sell_order'])
