import pandas as pd

def trades_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Executes trades based on the given DataFrame 
    Returns a new DataFrame with 'from_id', 'to_id', and 'amt' columns.

    Assumptions:
    - 'ID' is the player
    - 'Quote' is the qute(bid/ask) of the trade
    - 'Amt' is the amt at which player wants to trade
    - 'Time' is the time at which player quotes the trade
    """
    
    bids_df = df[df['Quote'] == 'bid']
    asks_df = df[df['Quote'] == 'ask']

    bids_df = bids_df.sort_values(
        by=["Amt", "Time"],
        ascending=[False, True]
    )

    asks_df = asks_df.sort_values(
        by=["Amt", "Time"],
        ascending=[True, True]
    )

    max_bid = bids_df['Amt'].max()
    min_ask = asks_df['Amt'].min()

    num_bids = num_asks = 0

    for _, bid in bids_df.iterrows():
        if bid['Amt'] >= min_ask:
            num_bids += 1
    
    for _, ask in asks_df.iterrows():
        if ask['Amt'] <= max_bid:
            num_asks += 1
    
    num_trades = min(num_bids, num_asks)

    bids_df = bids_df.head(num_trades)
    asks_df = asks_df.head(num_trades)

    bids_df = bids_df.sort_values(
        by=["Amt", "Time"],
        ascending=[False, False]
    )

    asks_df = asks_df.sort_values(
        by=["Amt", "Time"],
        ascending=[False, True]
    )

    trade_log = []

    bid_idx = 0
    ask_idx = 0

    while bid_idx < len(bids_df) and ask_idx < len(asks_df):
        bid = bids_df.iloc[bid_idx]
        ask = asks_df.iloc[ask_idx]
        
        # Skip self trades
        if bid['ID'] == ask['ID']:
            ask_idx += 1
            continue
        
        if bid['Amt'] >= ask['Amt']:
            trade_log.append({
                'from_id': ask['ID'],  # seller
                'to_id': bid['ID'],    # buyer
                'amt': ask['Amt']      # trade price (usually ask price in most engines)
            })
            
            bid_idx += 1
            ask_idx += 1
        else:
            break
    
    return pd.DataFrame(trade_log, columns=['from_id', 'to_id', 'amt'])
