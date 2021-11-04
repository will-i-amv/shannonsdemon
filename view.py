import time


class View:
    def __init__(self):
        pass

    def input_bot_parameters(self):
        pairs = {}
        print(f"Enter the Base Asset parameters:\n")
        while True: 
            base_asset = input(f"Base Asset: ")
            base_asset_qty = input(f"Base Asset Quantity: ")
            quote_asset_qty = input(f"Quote Asset Quantity: ")
            buy_percentage = input(f"Buy percentage: ")
            sell_percentage = input(f"Sell percentage: ")
            symbol = str(f'{base_asset}USDT')
            pairs[symbol] = { 
                'baseAssetQty': float(base_asset_qty),
                'quoteAssetQty': float(quote_asset_qty),
                'buyPercentage': float(buy_percentage),
                'sellPercentage': float(sell_percentage),
            }
            exit_ = input(f"Exit? (Type 'y' to exit): ")
            if exit_ == 'y':
                break
        while True: 
            print(f"Enter the bot's status (Type 'e' to exit):\n")
            status = input("Status:")
            if status not in ['TEST', 'TRADE']:
                print("Invalid Status")
            else:
                break
        return pairs, status

    def print_timestamped_message(self, message):
        time_format = "%a, %d %b %Y %H:%M:%S"
        timestamp = time.strftime(time_format, time.gmtime())
        print(timestamp + '    ' + message)

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
        print(f'NEW ORDERS:')
        for order in all_orders:
            print(
                f"""
                *************************************
                Symbol: {order['symbol']}
                Type: {'Buy Order' if order['orderId'][:5] == 'SHN-B' else 'Sell Order'}
                Price: {order['price']}
                Quantity: {order['qty']}
                *************************************
                """
            )
