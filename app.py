#!/usr/bin/env python3
import sqlite3
import time
import uuid
import csv
from io import StringIO 
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import BaseJobStore
import apiconfig as cfg

from flask import Flask, render_template, request, url_for, flash, redirect, make_response 
from flask_script import Manager, Server
from werkzeug.exceptions import abort



######################################

# apscheduler
scheduler = BackgroundScheduler()

######################################

# Get all pairs for currency, e.g. ETH-USD
def get_Coinbase_Coins(curr, select):
    pairs = []
    try:
        products = cfg.public_client.get_products()
        for product in products:
             if product['id'].endswith(curr):
                 pairs.append(product)
    except Exception as e:
        print(e)

    return pairs

# Update Prices for Currency Pairs
def update_Coin_Prices(coins):
    prices = {}
    for coin in coins:
        #print("[!] Fetching new prices for: %s" % coin)
        prices[coin] = cfg.public_client.get_product_ticker(product_id=coin)
        prices[coin]['volume'] = "${:,.2f}".format(float(prices[coin]['volume']) * float(prices[coin]['price']))

    # Add to price_history
    sql_Update_Price_History(prices)
    return prices

def get_Prices(coins):
    prices = sql_Get_Prices(coins)
    if prices:
        return prices
    else:
        return

def get_DB_Connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Update price_history table
def sql_Update_Price_History(prices):
    conn = get_DB_Connection()
    
    for coin in prices:
        #print("inserting: " + prices[coin]['price'])
        conn.execute('INSERT INTO price_history (time, asset, price, volume) VALUES (?,?,?,?)', (prices[coin]['time'], coin, prices[coin]['price'], prices[coin]['volume']))
        conn.commit()
    
    conn.close()
    return

# Get price_history table
def sql_Get_Prices(coins):
    conn = get_DB_Connection()    
    try:
        # Should grab the last len(X) entries from the price_history table, which chould hopefully grab the prices... accurately
        #print(len(coins))
        prices = conn.execute('SELECT * FROM price_history ORDER BY id DESC LIMIT ?', (len(coins), )).fetchall()
        conn.close()
        return prices
    except Exception as e:
        conn.close()
        print("[!] Failed price retrieval from price_history:")
        print(e)
    
    return False
    

# Get order details by ID
def sql_Get_Order_By_Id(order_id):
    conn = get_DB_Connection()
    order = conn.execute('SELECT * FROM recurring_orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    if order is None:
        abort(404)
    return order

def sql_Get_All_Orders():
    conn = get_DB_Connection()
    recurring_orders = conn.execute('SELECT * FROM recurring_orders').fetchall()
    order_history = conn.execute('SELECT * FROM order_history').fetchall()
    conn.close()
    return recurring_orders,order_history

def sql_Update_Next_Run(order_id, nr):
    conn = get_DB_Connection()
    conn.execute('UPDATE recurring_orders SET next_run = ? WHERE id = ?', (nr, order_id))
    conn.commit()
    conn.close()

def sql_Update_Active(order_id):
    conn = get_DB_Connection()
    conn.execute('UPDATE recurring_orders SET active = ? WHERE id = ?', ('Active',order_id))
    conn.commit()
    conn.close()
    flash('Order "{}" was successfully reactivated.'.format(order_id), 'success')
    order_Scheduler()

def sql_Delete_Order(id):
    try:
        order = sql_Get_Order_By_Id(id)
        conn = get_DB_Connection()
        conn.execute('DELETE FROM recurring_orders WHERE id = ?', (id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print("[%s] : Error! Could not delete order:  %s. Details: %s" % (time.time(), id, e))
        return False

    if (order_Remover(order)):
        return True
    else:
        return False

def sql_Update_Order(current_time, next_run, asset, quantity, filled, order, order_details):
    conn = get_DB_Connection()
    conn.execute('UPDATE recurring_orders SET last_run = ?, next_run = ? WHERE id = ?', (current_time, next_run, order['id']))
    conn.execute('INSERT INTO order_history (created, side, asset, quantity, total, frequency, exchange, type, order_details) VALUES (?,?,?,?,?,?,?,?,?)', (time.time(), "Buy", asset, quantity, filled, order['frequency'], order['exchange'], order['type'], str(order_details[0])))
    conn.commit()
    conn.close()

def sql_Update_Order_OneTime(current_time, id, asset, quantity, filled, frequency, order_details):
    conn = get_DB_Connection()
    # If there's an ID, this is coming from reactivate_run (probably) and needs to have the corresponding recurring order updated
    if id >= 0:
        print("[%s]: Updating scheduled order" % str(current_time))
        next_run = current_time + cfg.intervals[frequency]
        conn.execute('UPDATE recurring_orders SET last_run = ?, next_run = ? WHERE id = ?', (current_time, next_run, id))
    try:
        conn.execute('INSERT INTO order_history (created, side, asset, quantity, total, frequency, exchange, type, order_details) VALUES (?,?,?,?,?,?,?,?,?)', (time.time(), "Buy", asset, quantity, filled, frequency, "Coinbase", "Market", str(order_details)))
    except Exception as e:
        raise

    conn.commit()
    conn.close()


def order_Remover(order):
    try:
        if scheduler.get_job(order['uuid']):
            scheduler.remove_job(order['uuid'])
    except Exception as e:
        print("[%s] : Error! Could not remove order:  %s. Details: %s" % (time.time(), order, e))
        return False

# Order Schedule Handler
def order_Scheduler():

    # Read the orders from the database
    all_orders = sql_Get_All_Orders()
    recurring_orders = all_orders[0]

    #  This will only ever run once, at startup
    # It will populate and start the scheduler
    if not scheduler.running:
        print("[%s] : Starting scheduler..." % time.time())
        # Iterate through table entries to make sure everything is rescheduled after restart
        for order in recurring_orders:
            if order['active'] == 'Active':
                next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(order['next_run']))
                scheduler.add_job(scheduled_Order_Execute, 'date', args=[order], run_date=next_run, id=order['uuid'], misfire_grace_time=None)
                print("[%s] : Order created in scheduler: %s" % (time.time(), order['uuid']))
        try:
            scheduler.start()
            print("[%s] : Scheduler started" % time.time())
            return True
        except Exception as e:
            print("[%s] : Scheduler was unable to be started" % time.time())
            print("[%s] : Exception: %s" % (time.time(), e))
            return False
    else:
        # Call this when we need to schedule or reschedule / update orders
        # Basically, ever time you need to call the scheduler you'll be hitting here
        #
        # For each order in the recurring table
        for order in recurring_orders:
            # If the order's UUID doesn't exist in the scheduler, add it
            # Placing an order executes it, so new db entries start 'Active'
            if not scheduler.get_job(order['uuid']):
                # Quick check to make sure things don't get out of sync between the scheduler and the database entries
                if order['active'] == 'Active':
                    next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(order['next_run']))
                    scheduler.add_job(scheduled_Order_Execute, 'date', args=[order], run_date=next_run, id=order['uuid'], misfire_grace_time=None)
                    print("[%s] : Order created in scheduler: %s" % (time.time(), order['uuid']))

            # If the order exists, let's update it in case anything changed with the order it's based on
            if scheduler.get_job(order['uuid']):
                # Make sure it's not supposed to be set to inactive
                if 'Inactive' in order['active']:
                    scheduler.remove_job(order['uuid'])
                else:
                    # Check if the order has never been run (new order!)
                    if order['last_run'] == None:
                        onetime_order_execute(order['asset'], order['quantity'], order['frequency'], order['id'])
                    next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(order['next_run']))
                    scheduler.reschedule_job(order['uuid'], trigger='date', run_date=next_run)

    print("[%s] : Current jobs:" % time.time())
    print(scheduler.get_jobs())

def balance_Check():
    accounts = cfg.auth_client.get_accounts()
    return accounts

# Order totaller
def order_Totals():
    orderTotals = sql_Get_All_Orders()
    wT = 0
    mT = 0
    for order in orderTotals[0]:
        if order["active"] == "Active":
            if order["frequency"] == "Weekly":
                wT += order["quantity"]
                mT += (order["quantity"] * 4)
            elif order["frequency"] == "Monthly":
                wT += (order["quantity"] / 4)
                mT += order["quantity"]
            elif order["frequency"] == "Bi-Daily":
                wT += (order["quantity"] * 3.5)
                mT += (order["quantity"] * 15)
            elif order["frequency"] == "Bi-Weekly":
                wT += (order["quantity"] / 2)
                mT += (order["quantity"] * 2)

    return wT,mT




#### Used for firing scheduled orders
def scheduled_Order_Execute(order):

    print("[+] Order: " + str(order['id']) + " " + order['side'] + " "  + order['asset'] + " " + str(order['quantity']))
    quantity = order['quantity']
    asset = order['asset']
    balances = balance_Check()
    for cash in balances:
        #if cash['currency'] == 'EUR':
        if cash['currency'] == 'USD':
            if float(cash['balance']) >= float(quantity):
                print("Balance OK")
                res = cfg.auth_client.place_market_order(asset, "buy", funds=quantity)

                # Check for an error
                if not 'message' in res:
                    # Time calculations for order 'last_run' and 'next_run'
                    current_time = time.time()
                    next_run = current_time + cfg.intervals[order['frequency']]

                    # Sleep a moment, then get the order details and print them
                    print("[%s]: Sleeping 5... waiting for order details." % str(current_time))
                    time.sleep(5)
                    order_details = list(cfg.auth_client.get_fills(order_id=res["id"]))
                    print("[%s]: Fired Order:\n%s\n" % (current_time, order_details))

                    # Check for the fee and size
                    # Sometimes this fails because coinbase :shrug
                    try:
                        fee = order_details[0]['fill_fees']
                        filled = order_details[0]['filled_size']
                    # Error, estimating fees
                    except Exception as e:
                        print("[!]: 'order_details' list cast error, unable to retrieve fee / filled")
                        # Default maker / taker fee
                        fee = quantity * .005
                        filled = quantity - fee

                    # If there's no errors, the order worked and we can update the database
                    print("[%s]: Order executed" % str(current_time))
                    sql_Update_Order(current_time, next_run, asset, quantity, filled, order, order_details)

                else:
                    print("[%s]: Something went wrong!" % str(current_time))
                    print(res['message'])



# Used for firing a one time order
# Also used when reactivating orders that were overdue
def onetime_order_execute(asset, quantity, frequency, id):

    balances = balance_Check()
    for cash in balances:
        #if asset['currency'] == 'EUR':
        if cash["currency"] == "USD":
            if float(cash["balance"]) >= float(quantity):
                current_time = time.time()
                print("[%s]: Balance OK! Buying $%s of %s" % (str(current_time), str(quantity), asset))

                # Sleep a moment, then get the order details and print them
                print("[%s]: Sleeping 5... waiting for order details." % str(current_time))
                time.sleep(5)

                res = cfg.auth_client.place_market_order(asset, "buy", funds=quantity)
                print("[%s]: Fired Order:\n%s\n" % (current_time, res))
                #order_details = sql_Get_Order_By_Id(res["id"])

                order_details = list(cfg.auth_client.get_fills(order_id=res["id"]))
                print(order_details)
                try:
                    fee = order_details[0]['fill_fees']
                    filled = order_details[0]['filled_size']
                except Exception as e:
                    print("[!]: 'order_details' list cast error, unable to retrieve fee / filled")
                    # Default maker / taker fee
                    fee = quantity * .005
                    filled = quantity - fee

                if "message" in res:
                    print("[%s]: Something went wrong!" % str(current_time))
                    print(res['message'])
                elif "created_at" in res:
                    print("[%s]: Order executed" % str(current_time))
                    sql_Update_Order_OneTime(current_time, id, asset, quantity, filled, frequency, order_details)
                    return order_details,current_time


#def order_Totals(orders):


######################################
# Server stuff


'''
@app.context_processor
def utility_processor():
    def is_order_overdue(next_run):
        t = time.time()
        if t > next_run:
            return True
        return False
'''
class CustomServer(Server):
    def __call__(self, app, *args, **kwargs):
        order_Scheduler()
        return Server.__call__(self, app, *args, **kwargs)

app = Flask(__name__)
manager = Manager(app)
manager.add_command('runserver', CustomServer())
app.config['SECRET_KEY'] = 'changeme'

@app.template_filter('timefilter')
def time_filter(val):
    try:
        r = time.ctime(val)
        return r
    except Exception as e:
        print(val)
    return val



@app.route('/')
def index():
    prices = get_Prices(cfg.cb_coins)    
    if prices:
        return render_template('index.html', cb_coins=prices, update=0)
    else:
        print("[!] No prices found in table, attempting update and refresh")
        return update_Prices()        

@app.route('/updatePrices')
def update_Prices():
    print("[!] Updating prices...")
    prices = update_Coin_Prices(cfg.cb_coins) 
    return render_template('index.html', cb_coins=prices, update=1)

@app.route('/orders')
def orders():
    all_orders = sql_Get_All_Orders()
    balances = balance_Check()
    print(balances)
    order_totals_fiat = order_Totals()
    return render_template('orders.html', order_history=all_orders[1], recurring_orders=all_orders[0], cb_coins=cfg.cb_coins, balances=balances, ctime=time.time(), order_Totals=order_totals_fiat)
    #return render_template('orders.html', order_history=all_orders[1], recurring_orders=all_orders[0], cb_coins=cfg.cb_coins, balances=balances, ctime=time.time(), order_totals=order_totals_fiat)

@app.route('/export')
def export_orders():
    all_orders = sql_Get_All_Orders()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerows(all_orders[1])
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=report.csv'
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/<int:order_id>', methods=('POST','GET'))
def order_edit(order_id):

    order = sql_Get_Order_By_Id(order_id)

    if request.method == 'POST':
        if request.form['asset'] not in cfg.cb_coins:
            flash('Choose an asset!', 'danger')
            return render_template('order_edit.html', order=order)

        if 'quantity' in request.form:
            quantity = request.form['quantity'] + ".00"

            if float(quantity) >= 10.00:

                conn = get_DB_Connection()
                conn.execute('UPDATE recurring_orders SET quantity = ? WHERE id = ?', (quantity,order_id))
                conn.commit()
                conn.close()
                flash('Order "{}" was successfully updated.'.format(order_id), 'success')
                return redirect(url_for('orders'))
            else:
                flash('Minimum order is 10.00', 'danger')
        else:
            flash('Provide a quantity', 'danger')
        return render_template('order_edit.html', order=order)
    else:
        return render_template('order_edit.html', order=order)

@app.route('/order_create', methods=('POST','GET'))
def order_create():

    if request.method =='GET':
        return redirect(url_for('orders'))

    if request.method == 'POST':
        if request.form['asset'] not in cfg.cb_coins:
            flash('Choose an asset!', 'danger')
            return redirect(url_for('orders'))

        if 'quantity' in request.form:
            quantity = request.form['quantity'] + ".00"

            if float(quantity) >= 10.00:
                side = request.form['side']
                asset = request.form['asset']
                exchange = request.form['exchange']
                type = "Market"

                if 'oneTimeRadio' in request.form:
                    frequency = "Once"
                    onetime_order_execute(asset, quantity, frequency, -1)
                    return redirect(url_for('orders'))

                if 'recurringRadio' in request.form:
                    frequency = request.form['freqRadios']
                    active = "Active"
                    conn = get_DB_Connection()
                    created = time.time()
                    u = str(uuid.uuid4())
                    conn.execute('INSERT INTO recurring_orders (created, last_run, next_run, side, asset, quantity, frequency, active, exchange, type, uuid) VALUES (?,?,?,?,?,?,?,?,?,?,?)', (created, None, None, side, asset, quantity, frequency, active, exchange, type, u))
                    conn.commit()
                    conn.close()
                    print("[%s] : Order created in database: %s" % (time.time(), u))

                    order_Scheduler()
                    return redirect(url_for('orders'))
            else:
                flash('Minimum order is 10.00', 'danger')
                return redirect(url_for('orders'))
        else:
            flash('Provide an amount in USD', 'danger')
            return redirect(url_for('orders'))

@app.route('/<int:id>/deactivate', methods=('POST','GET'))
def deactivate(id):
    conn = get_DB_Connection()
    conn.execute('UPDATE recurring_orders SET active = ? WHERE id = ?', ('Inactive',id))
    conn.commit()
    conn.close()
    flash('Order "{}" was successfully deactivated.'.format(id), 'success')
    order_Scheduler()
    return redirect(url_for('orders'))

@app.route('/<int:id>/reactivate', methods=('POST','GET'))
def reactivate(id):
    order = sql_Get_Order_By_Id(id)
    sql_Update_Active(id)
    flash('Order "{}" was successfully reactivated.'.format(id), 'success')
    return redirect(url_for('orders'))

@app.route('/<int:id>/reactivate_run', methods=('POST','GET'))
def reactivate_run(id):
    order = sql_Get_Order_By_Id(id)
    onetime_order_execute(order['asset'], order['quantity'], order['frequency'], id)
    sql_Update_Active(id)
    order_Scheduler()
    return redirect(url_for('orders'))

@app.route('/<int:id>/delete', methods=('POST','GET'))
def deleteOrder(id):
    deleted = sql_Delete_Order(id)
    if deleted:
        flash('Order "{}" was successfully deleted.'.format(id), 'success')
    else:
        flash('Order "{}" was unable to be deleted.'.format(id), 'error')

    return redirect(url_for('orders'))




if __name__ == "__main__":
    manager.run()
