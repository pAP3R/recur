## recur, a CBPro recurring order scheduler

recur is a web-based order scheduler created to enable users to schedule recurring orders through CoinbasePro, a feature currently only available on regular Coinbase. By using CBPro over the native order scheduler in Coinbase.com, it's possible to save a significant sum of money, depending on the DCA strategy being used.

### How much money does it save?

Assuming you have four $25 purchases a month, occurring at regular intervals through Coinbase's "Recurring Orders" feature, you're currently paying **$7.96 a month in fees**.

However, each of those same purchases only costs twelve cents through Coinbase Pro, at the highest fee tier. **That's only $0.50 a month to do the same thing.**

If you buy three hundred dollars of crypto a month, making a one hundred dollar purchase of the top three cryptos from coinbase.com. That's $8.97 in fees. A smart investor knows they should DCA though, so they're surely buying at least bi-weekly to spread out those gains. Equaling $17.94 in fees per month!

Those same purchases will cost you only $1.50 and $3.00 respectively, through CoinbasePro, saving *a ton of money* which you can use to buy more crypto with. This app enables you to schedule any number of orders to be executed automatically, at those sweet, Coinbase Pro rates.

Using this is also totally free. There's very little reason *not* to use this if you already have recurring orders. If you *weren't* DCA'ing because the fees were too high, now you can.

# Usage

The app has two main components-- Prices and Orders. There's not a whole lot more to it currently. Plans are to implement Binance and CoinMarketCap's APIs next. Most of the functionality exists in the orders endpoint.

### Recurring Orders
![Image of Orders](https://i.imgur.com/ADCnFbq.png)

### Order History
![Image of OrderHistory](https://i.imgur.com/QdQSUsN.png)

### Creating an Order
![Image of Ordering](https://i.imgur.com/iUbpZ9j.png)

#### Prices

The Prices page is merely there as an experiment. You can configure pairs in the `cb_coins` list and it will show up in the Prices page, and order menus. This page will turn into a quick recap of prices. I learned templates doing this, it was fun.

#### Orders

The orders page, naturally, handles the orders. The top half contains a nav menu with two different tables, one to display all currently configured recurring orders, the other to display a table with all order entries. The lower half of the page contains an order form. Currently, it's only possible to place market orders. You can make one time purchases right there, or set up recurring orders on a daily, weekly or monthly schedule. I have a bootstrap calendar in there right now that I'll hook up for more advanced scheduling.

Orders are created within the 'Create Order' form, obviously. Select your target asset, enter an amount you want to spend and select whether you'd like this to be a recurring order or a one time thing. Both options **place** the order, but a recurring order will create a new entry in the recurring orders table, as well as an entry in the order history.

Should you wish to pause a recurring order, the 'Deactivate' button can be used. This will make it so that even if the orders "trigger" (scheduled date) fires, no order will be run. You can also reactivate a scheduled order if you change your mind. However, orders which are overdue will need to be recreated. I have a solution, will get to it soon.

**Remember:** If the app is not running, the orders will not fire.


## Setup

### Prerequisites

You'll probably want a virtualenv set up, so [do that](https://pythonbasics.org/virtualenv/)

Next, you'll need to set up the CBPro API if you haven't (https://pro.coinbase.com/profile/api). It's recommended to use keys which *only* have 'Trade' permissions.

Yeah, I know putting API keys in a file sucks, but since we need to do this all without user interaction, we can't have prompt for a pass to decrypt them or anything. I need some vault thing like ansible I think, or some other kms that let's a user put a pass in once or something. I don't know, suggestions welcome.

### Hosting

You can host it locally or remotely. It will just run a tiny little web server, so you don't need much, just a machine that stays on. Best to host it on your own machine or a LAN machine though, becasue of the keys. It's still possible to secure-ishly host it on AWS, Vultr, or any other VPS as well if you want. Here's an idea-- host it on Vultr for $5.00 a month, restrict access to your home IP, use keys with limited permissions, then donate all the cash you save.

I run recur on an Ubuntu 18.04 vm hosted on an ESXi box at home, it has very little memory and storage dedicated. As long as it stays up, the orders fire.

### Install

Install is easy. Clone the repo, and edit the apiconfig.py file to include your API keys and whatever fiat / coin pairs you want to see.

Run a virtualenv, install the requirements and run the app. There's an init_db.py script to create the tables and insert a dummy order for testing.

```
virtualenv -p python3 venv
source venv/bin/activate
git clone
cd recur
pip install -r requirements.txt
python3 init_db.py
python3 app.py runserver --host 0.0.0.0 --threaded --no-reload
```

Then, just visit http://loalhost:5000/

Let me know of any issues you find.

## Issues Fixed / Features Added:

- Minimum order check of 10.00 was broken
- Orders which were not immediately filled in the initial server response to the `cfg.auth_client.place_market_order()` call were not properly written to the 'order_history' table.
- Reworked table inserts to first call `cfg.auth_client.get_fills()` to retrieve the fee and size. Will add calc for fee totals vs. what would normally be paid
- Fixed edit button
- Fixed an issue with orders firing-- two variables were improperly named causing scheduled orders to break
- Reactivating orders that are past due *should* work now



## Todo:

- [x] Add config file
- [x] Display 'Account Balance' (For fiat check)
- [ ] Scheduled order total (weekly / monthly)
- [ ] More timing options
- [ ] 'Auto-buy' option based on market cap, fiat and DCA
- [ ] 'Attempt Undercut' button
- [ ] Fault tolerance
- [ ] Input sanitizing / validation
- [ ] Configurable 'watchlist'
- [ ] Additional API integrations (Binance, Gemini, CoinMarketCap)
- [ ] Twillio / SNS integration for purchase alerts?
- [ ] Export 'Order History'
- [x] Capture Order Details
- [ ] 'Clear Orders' button
- [x] 'Delete' button
- [x] 'Edit' button
- [x] 'Reactivate' button checks (for rescheduling discrepancies)
- [ ] KMS?
- [ ] Refactor SQL stuff?

## Obvious Disclaimer

Look, this script just schedules some orders with apscheduler and fires them via CBPro's Py API. I've done a lot of testing to iron out kinks and things are pretty smooth. There plenty more to add on, and it's more than useable right now. Don't limit test it. It exists on an isolated VM on my ESXi box, one connection in allowed, from only my workstation. If you want it to do more, I happily accept pull requests! There's a lot to do with other API integration, etc.

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
