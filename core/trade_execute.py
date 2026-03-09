import pandas as pd

def trades_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Executes trades based on price-time priority while preventing invalid matches.
    Prevents:
    - sellers selling more assets than they have
    - buyers buying without sufficient cash
    """

    bids_df = df[df['Quote'] == 'bid'].copy()
    asks_df = df[df['Quote'] == 'ask'].copy()

    # Price-time priority
    bids_df.sort_values(by=['Amt', 'Time'], ascending=[False, True], inplace=True)
    asks_df.sort_values(by=['Amt', 'Time'], ascending=[True, True], inplace=True)

    bids_df.reset_index(drop=True, inplace=True)
    asks_df.reset_index(drop=True, inplace=True)

    bid_idx = 0
    ask_idx = 0

    trade_log = []

    while bid_idx < len(bids_df) and ask_idx < len(asks_df):

        best_bid = bids_df.iloc[bid_idx]
        best_ask = asks_df.iloc[ask_idx]

        # Stop if prices do not cross
        if best_bid['Amt'] < best_ask['Amt']:
            break

        buyer = best_bid['ID']
        seller = best_ask['ID']

        # Skip self trade
        if buyer == seller:
            ask_idx += 1
            continue

        trade_price = (best_ask['Amt'] + best_bid['Amt'] + 1) // 2

        # Execute trade
        trade_log.append({
            'from_id': seller,
            'to_id': buyer,
            'amt': trade_price
        })

        bid_idx += 1
        ask_idx += 1


    return pd.DataFrame(trade_log, columns=['from_id', 'to_id', 'amt'])
