

from .global_context import context
from .token_price_oracle.price_token import price_token_dollars

def get_val_in_usd(token_address, token_decimals, token_balance, block_number):
    """
    Returns the value of the token at 'token_address" in USD at block number.
    """
    net_token_value = token_balance / pow(10, token_decimals)
    
    # Rounded off to 3 decimal places for simpler interpretation
    net_token_value = round(net_token_value, 3)
    

    price = price_token_dollars(
        context.w3,
        str(token_address),
        block_number
    )
    price_in_usd = price / 10 ** (18 -  token_decimals)
    price_in_usd = float(price_in_usd) * net_token_value

    
    return price_in_usd