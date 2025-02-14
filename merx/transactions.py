import time

import httpx

import base64
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from merx.wallet import *

from merx.text import colors, timestamp

# Public mint address values
sol_mint = "So11111111111111111111111111111111111111112"
usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Position and trades in market
position = False
trades = 0

# Returns the route to be manipulated in createTransaction()
async def create_exchange(input_amount, input_token_mint):

    output_token_mint = None
    token_decimals = None

    # Determines what mint address should be used in the api link
    if (input_token_mint == sol_mint):
        output_token_mint = usdc_mint
        token_decimals = 10**9
    else:
        output_token_mint = sol_mint
        token_decimals = 10**6
    
    # Finds the response and converts it into a readable array
    api_link = f"https://quote-api.jup.ag/v1/quote?inputMint={input_token_mint}&outputMint={output_token_mint}&amount={input_amount * token_decimals}&slippageBps=50&feeBps=50"
    async with httpx.AsyncClient() as client:
        response = await client.get(api_link)
        return(response.json())

# Returns the swap_transaction to be manipulated in sendTransaction()
async def create_transaction(route):

    # Parameters used for the Jupiter POST request
    parameters = {
        "route": route,
        "userPublicKey": str(public_address),
        "wrapUnwrapSOL": True,
        "feeAccount": "6XeQkUDZdsGsKBrhGWRuweHu4nbcv23t8r8vPt5xEsMv"
    }

    # Returns the JSON parsed response of Jupiter
    async with httpx.AsyncClient() as client:
        response = await client.post("https://quote-api.jup.ag/v1/swap", json=parameters)
        return(response.json())

# Deserializes and sends the transaction from the swap information given
def send_transaction(swap_transaction, opts):

    # Deserializes the transaction for the client to use
    transaction = Transaction.deserialize(base64.b64decode(swap_transaction))

    # Sends and returns the transaction status
    result = client.send_transaction(transaction, keypair, opts=opts)
    txid = result.value
    print(colors.HEADER + timestamp.find_time() + f": Merx TxID: {txid}" + colors.ENDC)
    return(txid)

# Uses the previous functions and parameters to exchange Solana token currencies
async def perform_swap(sent_amount, sent_token_mint):

    global position
        
    # Retries three times in case an exception is thrown
    tries = 3
    for i in range(tries):
        try:
            # Creates token exchange and quote
            transaction_route = await create_exchange(sent_amount, sent_token_mint)
            quote = transaction_route["data"][0]
            trans = await create_transaction(quote)

            # Variables storing necessary transaction values
            setup_transaction = trans["setupTransaction"] if "setupTransaction" in trans else None
            swap_transaction = trans["swapTransaction"] if "swapTransaction" in trans else None
            cleanup_transaction = trans["cleanupTransaction"] if "cleanupTransaction" in trans else None
            opts = TxOpts(skip_preflight=True)
            
            # Sends setup transaction
            if setup_transaction:
                send_transaction(setup_transaction, opts)

            # Sends swap transaction
            if swap_transaction:
                send_transaction(swap_transaction, opts)

            # Sends cleanup transaction
            if cleanup_transaction:
                send_transaction(cleanup_transaction, opts)
            
            if sent_token_mint == usdc_mint:
                print(colors.OKGREEN + timestamp.find_time() + ": Merx has successfully opened a market position." + colors.ENDC)
                position = True
                trades = trades + 1
            else:
                print(colors.OKGREEN + timestamp.find_time() + ": Merx has successfully closed a market position." + colors.ENDC)
                position = False
                trades = trades + 1
        except:
            if i < tries - 1:
                time.sleep(60)
                continue
            else:
                print(colors.FAIL + timestamp.find_time() + ": Merx was unable to take a market position." + colors.ENDC)
        break