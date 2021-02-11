#!/usr/bin/env python3
import cbpro
import sqlite3
import time
import uuid
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import BaseJobStore


from flask import Flask, render_template, request, url_for, flash, redirect
from flask_script import Manager, Server
from werkzeug.exceptions import abort




######################################
# CBPro API Setup
# Public / Auth Client
public_client = cbpro.PublicClient()
key = ''
b64secret = ''
passphrase = ''

# Sandbox
cbpro_api_url = "https://api-public.sandbox.pro.coinbase.com"
# Prod
#cbpro_api_url = "https://api.pro.coinbase.com"
auth_client = cbpro.AuthenticatedClient(key, b64secret, passphrase, api_url=cbpro_api_url)

# Change fiat pairs here

if 'sandbox' in cbpro_api_url:
    cb_coins = [
    'BTC-USD'
    ]
else:
    cb_coins = [
    'ETH-USD',
    'BTC-USD',
    'UNI-USD',
    'LTC-USD',
    'XLM-USD',
    'COMP-USD'
    ]

######################################

# Schedule and Times
# apscheduler
scheduler = BackgroundScheduler()

intervals = {}
intervals['Daily'] = 86400
intervals['Weekly'] = 604800
intervals['Monthly'] = 2592000 # 30 days

######################################



# Get all pairs for currency, e.g. ETH-USD
def get_coinbase_coins(curr, select):
    pairs = []
    try:
        products = public_client.get_products()
        for product in products:
             if product['id'].endswith(curr):
                 pairs.append(product)
    except Exception as e:
        print(e)

    return pairs

# Get ticker for specific currency pairs from an array
def get_specific_coinbase_coins(coins):
    prices = {}
    for coin in coins:
        prices[coin] = public_client.get_product_ticker(product_id=coin)
    return prices

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Get order details by ID
#
def get_order(order_id):
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM recurring_orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    if order is None:
        abort(404)
    return order

def get_all_orders():
    conn = get_db_connection()
    recurring_orders = conn.execute('SELECT * FROM recurring_orders').fetchall()
    order_history = conn.execute('SELECT * FROM order_history').fetchall()
    conn.close()
    return recurring_orders,order_history

# Order Schedule Handler
def order_scheduler():

    # Read the orders from the database
    all_orders = get_all_orders()
    recurring_orders = all_orders[0]

    #  In case the server was restarted or something
    if not scheduler.running:
        print("[%s] : Starting scheduler..." % time.time())
        # Iterate through table entries to make sure everything is rescheduled after restart
        for order in recurring_orders:
            if order['active'] == 'Active':
                # Check to see if the order has ever been run
                if order['last_run'] is None:
                    f = order['frequency']
                    c = order['created']
                    nr_tmp = c + intervals[f]
                    next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(nr_tmp))
                    scheduler.add_job(scheduled_order_execute, 'date', args=[order], run_date=next_run, id=order['uuid'])
                else:
                    f = order['frequency']
                    lr = order['last_run']
                    nr_tmp = lr + intervals[f]
                    next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(nr_tmp))
                    scheduler.add_job(scheduled_order_execute, 'date', args=[order], run_date=next_run, id=order['uuid'])
        try:
            scheduler.start()
            print("[%s] : Scheduler started" % time.time())
            return True
        except Exception as e:
            print("[%s] : Scheduler was unable to be started" % time.time())
            print("[%s] : Exception: %s" % (time.time(), e))
            return False


    # For each order in the recurring table
    for order in recurring_orders:
        # If the order's UUID doesn't exist in the scheduler, add it
        # Placing an order executes it, so new db entries start 'Active'
        if not scheduler.get_job(order['uuid']):
            # Quick check to make sure things don't get out of sync between the scheduler and the database entries
            if order['active'] == 'Active':
                f = order['frequency']
                c = order['created']
                if order['last_run'] is None:
                    print("Order never run! Running now!")
                    res = onetime_order_execute(order['asset'], order['quantity'], order['frequency'], order['id'])
                    lr = res[1]
                    nr_tmp = lr + intervals[f]
                    next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(nr_tmp))
                    try:
                        scheduler.add_job(scheduled_order_execute, 'date', args=[order], run_date=next_run, id=order['uuid'])
                        print("[%s] : Order created in scheduler: %s" % (time.time(), order['uuid']))
                    except Exception as e:
                        raise
                else:
                    lr = order['last_run']
                    nr_tmp = lr + intervals[f]
                    next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(nr_tmp))
                    try:
                        scheduler.add_job(scheduled_order_execute, 'date', args=[order], run_date=next_run, id=order['uuid'])
                        print("[%s] : Order created in scheduler: %s" % (time.time(), order['uuid']))
                    except Exception as e:
                        raise

        # It exists in the scheduler
        else:
            # Make sure it's not supposed to be set to inactive
            if 'Inactive' in order['active']:
                scheduler.remove_job(order['uuid'])

    print("[%s] : Current jobs:" % time.time())
    print(scheduler.get_jobs())

def balanceCheck():
    accounts = auth_client.get_accounts()
    return accounts

def delete_order(id):
    try:
        order = get_order(id)
        conn = get_db_connection()
        conn.execute('DELETE FROM recurring_orders WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        if scheduler.get_job(order['uuid']):
            scheduler.remove_job(order['uuid'])
        return True
    except Exception as e:
        print("[%s] : Error! Could not delete order:  %s. Details: %s" % (time.time(), id, e))
        return False



#### These are the same
def scheduled_order_execute(order):
    print(str(order['id']) + " " + order['side'] + " " + str(order['quantity']))
    balances = balanceCheck()
    for asset in balances:
        #if asset['currency'] == 'EUR':
        if asset['currency'] == 'USD':
            if float(asset['balance']) >= float(quantity):
                print("Balance OK")
                res = auth_client.place_market_order(product_id, side, funds=quantity)
                t = time.time()
                print(res)
                order_details = auth_client.get_order(res['id'])

                if res['message']:
                    print('Something went wrong!')
                    print(res['message'])
                elif 'created_at' in res:
                    print("Order executed")
                    conn = get_db_connection()
                    conn.execute('UPDATE recurring_orders SET last_run = ? WHERE id = ?', (t, order['id']))
                    conn.execute('INSERT INTO order_history (created, side, asset, quantity, total, frequency, exchange, type, order_details) VALUES (?,?,?,?,?,?,?,?,?,?)', (time.time(), order['side'], order['asset'], order['quantity'], order_details['filled_size'], order['frequency'], order['exchange'], order['type'], str(order_details)))
                    conn.commit()
                    conn.close()


def onetime_order_execute(asset, quantity, frequency, id):
    balances = balanceCheck()
    for account in balances:
        #if asset['currency'] == 'EUR':
        if account["currency"] == "USD":
            if float(account["balance"]) >= float(quantity):
                print("Balance OK")
                print(quantity)
                print(asset)
                res = auth_client.place_market_order(asset, "buy", funds=quantity)
                t = time.time()
                print(res)
                order_details = auth_client.get_order(res["id"])


                if "message" in res:
                    print("Something went wrong!")
                    print(res['message'])
                elif "created_at" in res:
                    print("Order executed")
                    conn = get_db_connection()
                    if id >= 0:
                        conn.execute('UPDATE recurring_orders SET last_run = ? WHERE id = ?', (t, id))
                    conn.execute('INSERT INTO order_history (created, side, asset, quantity, total, frequency, exchange, type, order_details) VALUES (?,?,?,?,?,?,?,?,?)', (time.time(), "Buy", asset, quantity, order_details['filled_size'], frequency, "Coinbase", "Market", str(order_details)))
                    conn.commit()
                    conn.close()
                    return order_details,t



######################################
# Server stuff


class CustomServer(Server):
    def __call__(self, app, *args, **kwargs):
        order_scheduler()
        return Server.__call__(self, app, *args, **kwargs)

app = Flask(__name__)
manager = Manager(app)
manager.add_command('runserver', CustomServer())
app.config['SECRET_KEY'] = 'changeme'

'''
@app.context_processor
def utility_processor():
    def is_order_overdue(next_run):
        t = time.time()
        if t > next_run:
            return True
        return False
'''

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
    prices = get_specific_coinbase_coins(cb_coins)
    return render_template('index.html', cb_coins=prices)

@app.route('/orders', methods=('GET', 'POST'))
def orders():

    if request.method == 'POST':

        if request.form['asset'] not in cb_coins:
            flash('Choose an asset!', 'danger')

        if 'quantity' in request.form:
            side = request.form['side']
            asset = request.form['asset']
            quantity = request.form['quantity']
            exchange = request.form['exchange']
            type = "Market"

            if 'oneTimeRadio' in request.form:
                frequency = "Once"
                onetime_order_execute(asset, quantity, frequency, -1)

            if 'recurringRadio' in request.form:
                frequency = request.form['freqRadios']
                active = "Active"
                conn = get_db_connection()
                created = time.time()
                nr = created + intervals[frequency]
                u = str(uuid.uuid4())
                conn.execute('INSERT INTO recurring_orders (created, last_run, next_run, side, asset, quantity, frequency, active, exchange, type, uuid) VALUES (?,?,?,?,?,?,?,?,?,?,?)', (created, None, nr, side, asset, quantity, frequency, active, exchange, type, u))
                print("[%s] : Order created in database: %s" % (time.time(), u))
                conn.commit()
                conn.close()
                order_scheduler()
        else:
            flash('Provide an amount in USD', 'danger')

    all_orders = get_all_orders()
    return render_template('orders.html', order_history=all_orders[1], recurring_orders=all_orders[0], cb_coins=cb_coins)


@app.route('/<int:order_id>', methods=('POST','GET'))
def order_edit(order_id):
    order = get_order(order_id)
    if request.method == 'POST':
        # # TODO:
        # Add Edit UPDATE statement
        all_orders = get_all_orders()
        return render_template('orders.html', order_history=all_orders[1], recurring_orders=all_orders[0], cb_coins=cb_coins)
    else:
        return render_template('order_edit.html', order=order)


@app.route('/<int:id>/reactivate_run')
def reactivate_run(asset, frequency, id):
    onetime_order_execute(asset, quantity, frequency, id)
    all_orders = get_all_orders()
    return render_template('orders.html', order_history=all_orders[1], recurring_orders=all_orders[0], cb_coins=cb_coins)


@app.route('/order_create')
def order_create():
    return render_template('order_create.html', cb_coins=cb_coins)

@app.route('/<int:id>/deactivate', methods=('POST','GET'))
def deactivate(id):
    conn = get_db_connection()
    conn.execute('UPDATE recurring_orders SET active = ? WHERE id = ?', ('Inactive',id))
    conn.commit()
    conn.close()
    flash('Order "{}" was successfully deactivated.'.format(id), 'success')
    order_scheduler()
    return redirect(url_for('orders'))

@app.route('/<int:id>/reactivate', methods=('POST','GET'))
def reactivate(id):

    order = get_order(id)
    #overdue = is_order_overdue(order['next_run'])
    conn = get_db_connection()
    conn.execute('UPDATE recurring_orders SET active = ? WHERE id = ?', ('Active',id))
    conn.commit()
    conn.close()
    flash('Order "{}" was successfully reactivated.'.format(id), 'success')
    order_scheduler()
    return redirect(url_for('orders'))

@app.route('/<int:id>/delete', methods=('POST','GET'))
def delete(id):
    deleted = delete_order(id)
    if deleted:
        flash('Order "{}" was successfully deleted.'.format(id), 'success')
    else:
        flash('Order "{}" was unable to be deleted.'.format(id), 'error')

    return redirect(url_for('orders'))



if __name__ == "__main__":
    manager.run()
