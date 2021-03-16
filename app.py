#!/usr/bin/env python3
import sqlite3
import time
import uuid
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import BaseJobStore
import apiconfig as cfg


from flask import Flask, render_template, request, url_for, flash, redirect
from flask_script import Manager, Server
from werkzeug.exceptions import abort



######################################

# apscheduler
scheduler = BackgroundScheduler()

######################################



# Get all pairs for currency, e.g. ETH-USD
def get_coinbase_coins(curr, select):
    pairs = []
    try:
        products = cfg.public_client.get_products()
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
        prices[coin] = cfg.public_client.get_product_ticker(product_id=coin)
    return prices

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Get order details by ID
#
def sql_getOrderById(order_id):
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM recurring_orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    if order is None:
        abort(404)
    return order

def sql_getAllOrders():
    conn = get_db_connection()
    recurring_orders = conn.execute('SELECT * FROM recurring_orders').fetchall()
    order_history = conn.execute('SELECT * FROM order_history').fetchall()
    conn.close()
    return recurring_orders,order_history

def sql_updateNextRun(order_id, nr):
    conn = get_db_connection()
    conn.execute('UPDATE recurring_orders SET next_run = ? WHERE id = ?', (nr, order_id))
    conn.commit()
    conn.close()

def sql_updateActive(order_id):
    conn = get_db_connection()
    conn.execute('UPDATE recurring_orders SET active = ? WHERE id = ?', ('Active',order_id))
    conn.commit()
    conn.close()
    flash('Order "{}" was successfully reactivated.'.format(order_id), 'success')
    order_scheduler()


# Order Schedule Handler
def order_scheduler():

    # Read the orders from the database
    all_orders = sql_getAllOrders()
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
                    nr_tmp = c + cfg.intervals[f]
                    next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(nr_tmp))
                    scheduler.add_job(scheduled_order_execute, 'date', args=[order], run_date=next_run, id=order['uuid'])
                else:
                    f = order['frequency']
                    lr = order['last_run']
                    nr_tmp = lr + cfg.intervals[f]
                    next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(nr_tmp))
                    scheduler.add_job(scheduled_order_execute, 'date', args=[order], run_date=next_run, id=order['uuid'])
        try:
            scheduler.start()
            print("[%s] : Scheduler started" % time.time())
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
                    nr_tmp = lr + cfg.intervals[f]
                    next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(nr_tmp))
                    try:
                        scheduler.add_job(scheduled_order_execute, 'date', args=[order], run_date=next_run, id=order['uuid'])
                        print("[%s] : Order created in scheduler: %s" % (time.time(), order['uuid']))
                        sql_updateNextRun(order['id'], nr_tmp)
                        print("[%s] : Updated order's 'next_run': %s" % (time.time(), next_run))

                    except Exception as e:
                        raise
                else:
                    lr = order['last_run']
                    nr_tmp = lr + cfg.intervals[f]
                    next_run = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(nr_tmp))
                    try:
                        scheduler.add_job(scheduled_order_execute, 'date', args=[order], run_date=next_run, id=order['uuid'])
                        print("[%s] : Order created in scheduler: %s" % (time.time(), order['uuid']))
                        sql_updateNextRun(order['id'], nr_tmp)
                        print("[%s] : Updated order's 'next_run': %s" % (time.time(), next_run))
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
    accounts = cfg.auth_client.get_accounts()
    return accounts

def delete_order(id):
    try:
        order = sql_getOrderById(id)
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
    castError = False
    print(str(order['id']) + " " + order['side'] + " "  + order['asset'] + " " + str(order['quantity']))
    quantity = order['quantity']
    asset = order['asset']
    balances = balanceCheck()
    for cash in balances:
        #if cash['currency'] == 'EUR':
        if cash['currency'] == 'USD':
            if float(cash['balance']) >= float(quantity):
                print("Balance OK")
                res = cfg.auth_client.place_market_order(asset, "buy", funds=quantity)
                t = time.time()
                print("[%s]: Fired Order:\n%s\n" % (t, res))
                #order_details = sql_getOrderById(res['id'])

                order_details = list(cfg.auth_client.get_fills(order_id=res["id"]))
                print(order_details)
                try:
                    fee = order_details[0]['fee']
                    filled = order_details[0]['size']
                except Exception as e:
                    print("[!]: 'order_details' list cast error, unable to retrieve fee / filled")

                    # Default maker / taker fee
                    fee = quantity * .005
                    filled = quantity - fee

                if 'message' in res:
                    print("[%s]: Something went wrong!" % str(t))
                    print(res['message'])
                elif 'created_at' in res:
                    print("[%s]: Order executed" % str(t))
                    conn = get_db_connection()
                    conn.execute('UPDATE recurring_orders SET last_run = ? WHERE id = ?', (t, order['id']))
                    conn.execute('INSERT INTO order_history (created, side, asset, quantity, total, frequency, exchange, type, order_details) VALUES (?,?,?,?,?,?,?,?,?,?)', (time.time(), side, asset, quantity, filled, order['frequency'], order['exchange'], order['type'], str(order_details[0])))
                    conn.commit()
                    conn.close()


def onetime_order_execute(asset, quantity, frequency, id):

    balances = balanceCheck()
    for cash in balances:
        #if asset['currency'] == 'EUR':
        if cash["currency"] == "USD":

            if float(cash["balance"]) >= float(quantity):
                print("Balance OK")
                print(quantity)
                print(asset)
                res = cfg.auth_client.place_market_order(asset, "buy", funds=quantity)
                t = time.time()
                print("[%s]: Fired Order:\n%s\n" % (t, res))
                #order_details = sql_getOrderById(res["id"])

                order_details = list(cfg.auth_client.get_fills(order_id=res["id"]))
                print(order_details)
                try:
                    fee = order_details[0]['fee']
                    filled = order_details[0]['size']
                except Exception as e:
                    print("[!]: 'order_details' list cast error, unable to retrieve fee / filled")

                    # Default maker / taker fee
                    fee = quantity * .005
                    filled = quantity - fee

                if "message" in res:
                    print("[%s]: Something went wrong!" % str(t))
                    print(res['message'])
                elif "created_at" in res:
                    print("[%s]: Order executed" % str(t))
                    conn = get_db_connection()
                    if id >= 0:
                        conn.execute('UPDATE recurring_orders SET last_run = ? WHERE id = ?', (t, id))
                        print("[%s]: Updating scheduled order" % str(t))
                    conn.execute('INSERT INTO order_history (created, side, asset, quantity, total, frequency, exchange, type, order_details) VALUES (?,?,?,?,?,?,?,?,?)', (time.time(), "Buy", asset, quantity, filled, frequency, "Coinbase", "Market", str(order_details[0])))
                    conn.commit()
                    conn.close()
                    return order_details,t




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
        order_scheduler()
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
    prices = get_specific_coinbase_coins(cfg.cb_coins)
    return render_template('index.html', cb_coins=prices)

@app.route('/orders')
def orders():
    all_orders = sql_getAllOrders()
    balances = balanceCheck()
    return render_template('orders.html', order_history=all_orders[1], recurring_orders=all_orders[0], cb_coins=cfg.cb_coins, balances=balances, ctime=time.time())


@app.route('/<int:order_id>', methods=('POST','GET'))
def order_edit(order_id):

    order = sql_getOrderById(order_id)

    if request.method == 'POST':
        if request.form['asset'] not in cfg.cb_coins:
            flash('Choose an asset!', 'danger')
            return render_template('order_edit.html', order=order)

        if 'quantity' in request.form:
            quantity = request.form['quantity'] + ".00"

            if float(quantity) >= 10.00:

                conn = get_db_connection()
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
                    conn = get_db_connection()
                    created = time.time()
                    nr = created + cfg.intervals[frequency]
                    u = str(uuid.uuid4())
                    conn.execute('INSERT INTO recurring_orders (created, last_run, next_run, side, asset, quantity, frequency, active, exchange, type, uuid) VALUES (?,?,?,?,?,?,?,?,?,?,?)', (created, None, nr, side, asset, quantity, frequency, active, exchange, type, u))
                    print("[%s] : Order created in database: %s" % (time.time(), u))
                    conn.commit()
                    conn.close()
                    order_scheduler()
                    return redirect(url_for('orders'))
            else:
                flash('Minimum order is 10.00', 'danger')
                return redirect(url_for('orders'))
        else:
            flash('Provide an amount in USD', 'danger')
            return redirect(url_for('orders'))

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
    order = sql_getOrderById(id)
    sql_updateActive(id)
    flash('Order "{}" was successfully reactivated.'.format(id), 'success')
    return redirect(url_for('orders'))

@app.route('/<int:id>/reactivate_run', methods=('POST','GET'))
def reactivate_run(id):
    order = sql_getOrderById(id)
    onetime_order_execute(order['asset'], order['quantity'], order['frequency'], id)
    sql_updateActive(id)
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
