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
    
    # Separate book sides
    bids_df = df[df['Quote'] == 'bid'].copy()
    asks_df = df[df['Quote'] == 'ask'].copy()

    # Sort by price-time priority
    # bids_df: Highest price first, then earliest time
    bids_df.sort_values(
        by=['Amt', 'Time'],
        ascending=[False, True],
        inplace=True
    )

    # asks_df_df: Lowest price first, then earliest time
    asks_df.sort_values(
        by=['Amt', 'Time'],
        ascending=[True, True],
        inplace=True
    )

    # Reset index for safe positional indexing
    bids_df.reset_index(drop=True, inplace=True)
    asks_df.reset_index(drop=True, inplace=True)

    bid_idx = 0
    ask_idx = 0

    trade_log = []

    while bid_idx < len(bids_df) and ask_idx < len(asks_df):

        best_bid = bids_df.iloc[bid_idx]
        best_ask = asks_df.iloc[ask_idx]

        # Stop if no price cross
        if best_bid['Amt'] < best_ask['Amt']:
            break

        # Skip self-trading
        if best_bid['ID'] == best_ask['ID']:
            ask_idx += 1
            continue

        # Execute trade
        trade_log.append({
            'from_id': best_ask['ID'],                              # Seller
            'to_id': best_bid['ID'],                                # Buyer
            'amt': (best_ask['Amt'] + best_bid['Amt'] + 1)//2       # Trade price
        })

        # Move to next best order
        bid_idx += 1
        ask_idx += 1

    return pd.DataFrame(trade_log, columns=['from_id', 'to_id', 'amt'])

