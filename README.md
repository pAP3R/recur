![recur Image](https://i.imgur.com/YXTXzWE.mp4)

## Why pay more to lose money, when you can pay less??

recur is a web-based order scheduler created to provide additional functionality, such as recurring orders, to popular cryptocurrency exchange APIs which currently do not support them. Currently only configured to work with Coinbase Pro, the application allows scheduling of various recurring order configurations, allowing users to pay substantially lower fees than those they'd encounter on www.Coinbase.com, by interacting directly with the CB Pro API.

### Why do you care?

Lower fees, mainly. Assuming you have four $25 purchases a month that occur at regular intervals through normal Coinbase.com (a weekly buy schedule). That's $1.99 each purchase, so you're currently paying **$7.96 a month in fees**.

Each of those purchases costs only $0.125 through Coinbase Pro, even at their highest fee tier. **That's only $0.50 a month to do the same thing.** That immediately saves you money. Say you buy three hundred dollars of crypto a month, making a one hundred dollar purchase of the top three cryptos from coinbase.com. That's $8.97 in fees.  Wildly, three $51 purchases would *also cost* $8.97 in fees!  A smart investor knows they should DCA though, so they're surely buying at least bi-weekly to spread out those gains. That's $17.94 in fees per month!

Those same purchases will cost you $1.50 and $3.00 respectively, on CoinbasePro, saving *a ton of money* which you can use to buy more. This app enables you to schedule any number of orders to be executed automatically, at those sweet, Coinbase Pro rates.

If you *weren't* DCA'ing because the fees were too high, now you can.

# Testing

If you want to play around with this before you put all your moneyz in it, use the sandbox API for coinbase, it's enabled by default in the app.py file.

`auth_client = cbpro.AuthenticatedClient(key, b64secret, passphrase, api_url="https://api-public.sandbox.pro.coinbase.com")`

CBPro's sandbox comes with a account that has around 200K, it's imagination money, but it's fun to play with the orders.

# Usage

The app has two main components-- Prices and Orders. There's not a whole lot more to it currently. Plans are to implement Binance and CoinMarketCap's APIs next. Most of the functionality exists in the orders endpoint.

### Recurring Orders
![Image of Orders](https://i.imgur.com/ADCnFbq.png)

### Order History
![Image of OrderHistory](https://i.imgur.com/QdQSUsN.png)

### Creating an Order
![Image of Ordering](https://i.imgur.com/iUbpZ9j.png)

## Prices

The Prices page is merely there as an experiment. You can configure pairs in the `cb_coins` list and it will show up in the Prices page, and order menus. This page will turn into a quick recap of prices. I learned templates doing this, it was fun.

## Orders

The orders page, naturally, handles the orders. The top half contains a nav menu with two different tables, one to display all currently configured recurring orders, the other to display a table with all order entries. The lower half of the page contains an order form. Currently, it's only possible to place market orders. You can make one time purchases right there, or set up recurring orders on a daily, weekly or monthly schedule. I have a bootstrap calendar in there right now that I'll hook up for more advanced scheduling.

Once orders are created, they are immediately executed and the entry is written to the 'order_history' table. For recurring orders, the 'recurring_orders' table is updated to include the new order, which lists information including the next time the job will be run. This table will be read by the order scheduler to create apscheduler jobs.

Should you wish to pause a recurring order, the 'Deactivate' button can be used. This will deactivate the order until you reactivate it, or delete it, whatever. Once it's reactivated, the job will need to be recreated if the date is past the "Next Run" date, otherwise it continues as normal. I'll probably do some ajax stuff to check if the orders overdue, and to auto reschedule or something.

To ensure jobs are run on schedule, each order is assigned a unique UUID. This  is used as the 'ID' parameter for each apscheduler job, which makes it easy to check if an order is scheduled. When an order is deactivated, the corresponding job is removed from the scheduler. When reactivated or created, it's added. Should the app be stopped, apscheduler will not be running and the orders will not be executed. Orders will be rescheduled automatically upon restart, though if the date is past the "Next Run" date of any of the orders, they'll need to be remade again.


## Setup

### Prerequisites

You'll probably want a virtualenv set up, so [do that](https://pythonbasics.org/virtualenv/)

recur uses the CoinbasePro API, so obviously that's a requirement. It's recommended to use keys which *only* have 'Trade' permissions, just in case! These API keys can be set up from https://pro.coinbase.com/profile/api

Yeah, I know putting API keys in a file sucks, but since we need to do this all without user interaction, we can't have prompt for a pass to decrypt them or anything. I need some vault thing like ansible I think, or some other kms that let's a user put a pass in once or something. I don't know, suggestions welcome.

### Hosting

You can host it locally or remotely. Because API keys are hardcoded in the script, it's only recommended to use this on a LAN. A kms is probably on the list. It's still possible to secure-ishly host it on AWS, Vultr, or any other VPS as well if you want. Here's an idea-- host it on Vultr for $5.00 a month, restrict access to your home IP, use keys with limited permissions, then donate all the cash you save.

In all seriousness, there are some considerations for how to host it. The scheduler is only running when the flask app is running. The orders are written to a database, but if flask isn't running then the scheduler isn't either, so if the times / triggers are hit the orders won't execute. This means you want it hosted somewhere with high availability, at least during the timeframes your purchases are scheduled. If you host it on your daily machine, know that turning off or rebooting the device means the app will need to be restarted.

I run recur on an Ubuntu 18.04 vm hosted on an ESXi box at home, it has very little memory and storage dedicated. As long as it stays up, the orders fire.

### Install

Install is easy. Clone the repo, and edit the app.py file to include your API keys. (Again, I'd recommend using keys with 'Trade' permissions *only*, that's good opsec)

Run a virtualenv, install the requirements and run the app. There's an init_db.py script to create the tables and insert a dummy order for testing.

```
virtualenv -p python3 venv
source venv/bin/activate
git clone
cd recur
pip install -r requirements.txt
python3 init_db.py
python3 app.py runserver
```

That *should* work. I think. If it doesn't I'm sure you can figure it out.

Then, just visit http://loalhost:5000/

Let me know of any issues you find, I'm sure there are lots!

## v.0.1 Current Issues:

Don't put anything nasty in the params, they're sure to break, lol

Reactivating an order is a bit weird if it's overdue, I don't think it will work. I have a solution. I will add it soon-ish.


## Todo:

- [ ] Add config file
- [ ] Display 'Account Balance' (For fiat check)
- [ ] 'Auto-buy' based on market cap, fiat and DCA
- [ ] 'Attempt Undercut' button
- [ ] Fault tolerance
- [ ] Input sanitizing / validation
- [ ] Configurable 'watchlist'
- [ ] Additional API integrations (Bibance, Gemini, CoinMarketCap)
- [ ] Twillio / SNS integration for purchase alerts?
- [ ] Export 'Order History'
- [x] Capture Order Details
- [ ] 'Clear Orders' button
- [x] 'Delete' button
- [ ] 'Reactivate' button checks (for rescheduling discrepancies)
- [ ] KMS?
- [ ] Refactor SQL stuff?

## Obvious Disclaimer

Look, this script just schedules some orders with apscheduler and fires them via CBPro's Py API. I've done a lot of testing to iron out kinks and I'm preeeetty sure that it's not going to double buy, or sell, and that when it restarts it should kick back off with things getting rescheduled. There are a few more items to take care of, but it's useable. Be gentle with it, don't limit test it. It exists on an isolated VM on my ESXi box, one connection in allowed, from only my workstation. If you want it to do more, I happily accept pull requests! There's a lot to do with other API integration, etc.

### Donations?

I'm going to keep updating this, at least until it's not profitable to use the APIs like we can. If you want to donate to the project to buy me some coffee and make the code better, feel free!

##### NANO:
nano_36fgx5eg46ms747kzty36f4gfoy7yzeryo1ndqahc7945f1dzk5y9917g5eh
##### ADA:
addr1q8asj830pmmz99fnfuj8cmfre7h0phwjx389gdy5amjsxruuc3d90nf8nsczcc89z6cr3gsusk0fe04raacmm24q7zgsykj90d
##### ETH:
0xa1c5230870A2a3b9d099e6ac47cF687d3a5ecFb4
##### BTC:
36AFc1ciCCBTp2yjio271ncv8CHPydnFo8
