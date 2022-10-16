## recur, a CBPro recurring order scheduler

recur is a web-based order scheduler created to enable users to schedule recurring orders through CoinbasePro ~~a feature currently only available on regular Coinbase~~. By using CBPro over the native order scheduler in Coinbase.com, it's possible to save a significant sum of money, depending on the DCA strategy being used. Is this still true in October 2022? Idk.

### How much money does it save?

**~~September~~ October 2022 Update** 
I have no idea if this saves money anymore, ha. It still works though, so that's good.

*Original:*
Assuming you have four $25 purchases a month, occurring at regular intervals through Coinbase's "Recurring Orders" feature, you're currently paying **$7.96 a month in fees**.

However, each of those same purchases only costs twelve cents through Coinbase Pro, at the highest fee tier. **That's only $0.50 a month to do the same thing.**

If you buy three hundred dollars of crypto a month, making a one hundred dollar purchase of the top three cryptos from coinbase.com. That's $8.97 in fees. A smart investor knows they should DCA though, so they're surely buying at least bi-weekly to spread out those gains. Equaling $17.94 in fees per month!

Those same purchases will cost you only $1.50 and $3.00 respectively, through CoinbasePro, saving *a ton of money* which you can use to buy more crypto with. This app enables you to schedule any number of orders to be executed automatically, at those sweet, Coinbase Pro rates.

Using this is also totally free. There's very little reason *not* to use this if you already have recurring orders. If you *weren't* DCA'ing because the fees were too high, now you can.

# Usage

### Recurring Orders
![Image of Orders](https://i.imgur.com/2h5UdHs.jpeg)

### Order History
![Image of OrderHistory](https://i.imgur.com/vdBMDLQ.jpg)

#### Prices

The Prices page is merely there as an experiment. You can configure pairs in the `cb_coins` list and it will show up in the Prices page, and order menus. This page will turn into a quick recap of prices. I began the project with this to learn templates, it was fun.

#### Orders

Couple crude options for setting up orders on a schedule-- may or may not hook the bootstrap calendar up. Orders are placed at the time of creation, an option to NOT do that could probably be made.

Should you wish to pause a recurring order, the 'Deactivate' button can be used. This will make it so that even if the orders "trigger" (scheduled date) fires, no order will be run. 

You can also reactivate a scheduled order if you change your mind. Orders which are overdue can be de-activated and re-activated, which will trigger them and **all other enabled and overdue orders to fire.**


## Setup

### Prerequisites

You'll probably want a virtualenv set up, so [do that](https://pythonbasics.org/virtualenv/)

Next, you'll need to set up the CBPro API if you haven't (https://pro.coinbase.com/profile/api). It's recommended to use keys which *only* have 'Trade' permissions.

Data encrypted at rest, what's that? Drop your keyz in the file

### Hosting

It's a flask web app, so if you don't know how to do that, start there

### Install

Clone the repo, and edit the apiconfig.py file to include your API keys and whatever fiat / coin pairs you want to see.

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

RUns on http://loalhost:5000/

## Issues Fixed / Features Added:

- Minimum order check of 10.00 was broken
- Orders which were not immediately filled in the initial server response to the `cfg.auth_client.place_market_order()` call were not properly written to the 'order_history' table.
- Reworked table inserts to first call `cfg.auth_client.get_fills()` to retrieve the fee and size. Will add calc for fee totals vs. what would normally be paid
- Fixed edit button
- Fixed an issue with orders firing-- two variables were improperly named causing scheduled orders to break
- Reactivating orders that are past due *should* work now
- RIP, orders fired twice. Fixed via running with the `--no-reload` or `use_reloader=False` flags. Will migrate scheduler startup into `before_first_request()`
- Added `misfire_grace_time=3600` to the `add_job()` calls due to a few misses (https://stackoverflow.com/questions/41428118/apscheduler-missing-jobs-after-adding-misfire-grace-time)
- Changed `misfire_grace_time=3600` to `None`
- Refactored / Consolidated a lot of the SQL stuff, probably more to go, but it makes it easier to manage overall
- Added placeholders for order totals
- Added a small `time.sleep(x)` to purchases to help obtain order details, can't remember how long lol
- Made it dark now, weeeew
- Added tabulation / table nav
- Added export for order history
- Made a table for prices, prevents querying for prices every times the "prices" page loads


## Todo:

- [x] Add config file
- [x] Display 'Account Balance' (For fiat check)
- [x] Scheduled order total (weekly / monthly)
- [x] More timing options
- [ ] Fault tolerance...?
- [ ] Input sanitizing / validation (lol)
- [ ] Configurable 'watchlist'
- [ ] Additional API integrations (Binance, Gemini, CoinMarketCap)
- [ ] Twillio / SNS integration for purchase alerts?
- [x] Export 'Order History' (as csv)
- [x] Capture Order Details
- [ ] 'Clear Orders' button
- [x] 'Delete' button
- [x] 'Edit' button
- [x] 'Reactivate' button checks (for rescheduling discrepancies)
- [x] DARK mode ~~
- [x] Table navigation
- [ ] Historical Prices
- [x] Added price_history table / update prices button
- [ ] Break current_prices / price_history into separate tables?
- [ ] Add "last lookup" timestamp to prices
- [x] Fixed Balances


### Donations?  :3 

##### ADA:
addr1q8asj830pmmz99fnfuj8cmfre7h0phwjx389gdy5amjsxruuc3d90nf8nsczcc89z6cr3gsusk0fe04raacmm24q7zgsykj90d
##### ETH:
0xa1c5230870A2a3b9d099e6ac47cF687d3a5ecFb4
##### BTC:
36AFc1ciCCBTp2yjio271ncv8CHPydnFo8
