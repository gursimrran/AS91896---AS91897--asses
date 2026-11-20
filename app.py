import json, datetime
import sqlite3

from flask import Flask, render_template, request,session, flash, redirect, url_for

def initialise_database():
    with sqlite3.connect('case_charm.db') as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT,
                customer_name TEXT,
                items TEXT,
                addons TEXT,
                total REAL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')            
                   

app = Flask(__name__)
app.secret_key= 'your_secret_key'

def load_data(filename):
    with open(f'data/{filename}') as file:
        products = json.load(file)
    return products  

def calculate_total(cart):

    product_subtotal = 0
    addon_subtotal = 0

    addons = load_data('addons.json')

    for item, details in cart.items():
        subtotal = details['price'] * details['quantity']

        if item in addons:
            addon_subtotal += subtotal
        else:
            product_subtotal += subtotal

    total = product_subtotal + addon_subtotal

    return total, product_subtotal, addon_subtotal

@app.route('/')
def index():
    cases = load_data('iphone_cases.json')
    charms = load_data('phone_charms.json')
    addons = load_data('addons.json')
    cart = session.get('cart', {})

    total, product_subtotal, addon_subtotal = calculate_total(cart)

    if total > 100:
        flash("You are ordering a lot! Consider calling us for a special deal.")

    
    return render_template('index1.html', cases=cases, charms=charms, addons=addons, cart=cart, cart_total=total, product_subtotal=product_subtotal, addon_subtotal=addon_subtotal)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/checkout', methods=['POST'])
def checkout():
    customer_name= request.form['customer_name'].strip().title()

    cart = session.get('cart', {})

    # Check if cart is empty
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for('index'))
    
    # Check if the customer name has been entered
    if not customer_name:
        flash("Customer name is required.")
        return redirect(url_for('index'))
    
    total, product_subtotal, addon_subtotal =  calculate_total(cart)

    invoice_date = datetime.datetime.now(). strftime('%Y-%m-%d %H:%M:%S')
    invoice_number = f"INV_{customer_name.replace(' ','_')}_{invoice_date}"

    # Save order to SQLite database
    with sqlite3.connect('case_charm.db') as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO orders (invoice_number, customer_name, items, addons, total)
            VALUES (?, ?, ?, ?, ?)
        ''', (invoice_number, customer_name, json.dumps(cart), json.dumps({}), total))

        conn.commit()

    session['invoice'] = {
        'customer_name': customer_name,
        'cart': cart,
        'cart_total': total,
        'product_subtotal': product_subtotal,
        'addon_subtotal': addon_subtotal,
        'invoice_date': invoice_date,
        'invoice_number': invoice_number
    }

    return redirect(url_for('view_invoice'))


@app.route('/invoice')
def view_invoice():
    invoice = session.get('invoice')

    if not invoice:
        flash("No invoice available. Please complete checkout first.")
        return redirect(url_for('index'))

    return render_template('invoice.html', **invoice)



@app.route('/orders')
def order_history():
    with sqlite3.connect('case_charm.db') as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM orders ORDER BY order_id DESC")
        orders = cursor.fetchall()

    return render_template('order_history.html', orders=orders)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product = request.form['product']
    quantity = int(request.form['quantity'])

    cases = load_data('iphone_cases.json')
    charms = load_data('phone_charms.json')
    addons = load_data('addons.json')

    cart = session.get('cart', {})

    if product in cases:
        price = cases[product]['price']
    elif product in charms:
        price = charms [product]['price']
    elif product in addons:
        price = addons [product]['price']
    else:
        flash("Invaild product selected.")
        return redirect (url_for('index'))  
    
    cart = session.get('cart', {})

    if product in cart:
        cart[product]['quantity'] += quantity 
    else:
        cart[product] = {
            'price': price,
            'quantity': quantity 
        }           

    session['cart'] = cart
    session.modified = True  

    flash(f"{quantity} {product}(s) added to cart.")  
    return redirect(url_for('index'))



@app.route('/select_addon', methods=['POST'])
def select_addon():
    selected_addons = request.form.getlist('addons')

    addons = load_data('addons.json')
    cart = session.get('cart', {})

    for addon in selected_addons:
        if addon in addons:
            price = addons[addon]['price']

            if addon in cart:
                cart[addon]['quantity'] += 1
            else:
                cart[addon] = {
                    'price': price,
                    'quantity': 1
                }

    session['cart'] = cart
    session.modified = True

    flash("Selected add-ons added to cart.")
    return redirect(url_for('index'))
   

@app.route('/remove_from_cart/<item>')
def remove_from_cart(item):
    cart = session.get('cart', {})

    if item in cart:
        del cart[item]
        session['cart'] = cart
        session.modified = True 
        flash(f"{item} removed from cart.")
    else:
        flash("Item not found in cart.")    

    return redirect(url_for('index'))   


@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    session.pop('cart', None)
    session.pop('selected_addons', None)
    session.modified = True

    flash("Your order has been cancelled.")

    return redirect(url_for('index'))

if __name__ == '__main__':
    initialise_database()
    app.run(debug=True)


