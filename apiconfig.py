#!/usr/bin/env python3

# recur Config


#####################################
# CBPro API Setup
# Public / Auth Client
public_client = cbpro.PublicClient()

cbpro_api = {
    "key" : ""
    "b64secret" : ""
    "passphrase" : ""
}

# Sandbox
cbpro_api_url = "https://api-public.sandbox.pro.coinbase.com"
# Prod
#cbpro_api_url = "https://api.pro.coinbase.com"
auth_client = cbpro.AuthenticatedClient(key, b64secret, passphrase, api_url=cbpro_api_url)

# Change fiat pairs here

if "sandbox" in cbpro_api_url:
    cb_coins = [
    "BTC-USD"
    ]
else:
    cb_coins = [
    "ETH-USD",
    "BTC-USD",
    "UNI-USD",
    "LTC-USD",
    "XLM-USD",
    "COMP-USD",
    "GRT-USD",
    "SNX-USD"
    ]
#####################################

# Timings
intervals = {}
intervals['Daily'] = 86400
intervals['Weekly'] = 604800
intervals['Monthly'] = 2592000 # 30 days
