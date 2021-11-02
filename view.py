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
    
    def print_new_orders(self, all_orders):
        for symbol, orders in all_orders.items():
            print(f'SENDING NEW ORDERS FOR THE PAIR {symbol}:')
            print(f'BUY ORDERS:')
            print(
                f'''
                *************************************
                Type: Buy Order
                Price: {orders['buy_order']['price']}
                Quantity: {orders['buy_order']['qty']}
                *************************************
                '''
            )
            print(f'SELL ORDERS:')
            print(
                f'''
                *************************************
                Type: Sell Order
                Price: {orders['sell_order']['price']}
                Quantity: {orders['sell_order']['qty']}
                *************************************
                '''
            )
