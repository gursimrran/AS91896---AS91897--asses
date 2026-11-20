"""Flask  web application for Case & Charm Co to manage products, cart session and orders."""

import json, datetime
import sqlite3

from flask import Flask, render_template, request,session, flash, redirect, url_for

def initialise_database():
    """Creates the SQLite database and the orders table if it does not exist."""

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
    """Loads product or add-on data from a JSON file.
    
    Args:
        filename (str): Name of the JSON file in the data folder.

    Returns:
        dict: Item names mapped to a dict containing 'price' and 'stock'.     
    
    """
    with open(f'data/{filename}') as file:
        products = json.load(file)
    return products  

def calculate_total(cart):
    """Calculates the total cost, product subtotal, and add-on subtotal.

    Args:
       cart (dict): Item names mapped to the dict containing 'price' and 'quantity'.

    Returns:
       tuple: The total, product_subtotal and addon_subtotal.    
    
    """

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
    """Loads the product data and the cart totals so that it can display on the home page."""
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
    """Displays the about page."""
    return render_template('about.html')

@app.route('/checkout', methods=['POST'])
def checkout():
    """Checks the order, it updates the stock in JSON files, saves to SQLite, and creates an invoice."""
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
    cases = load_data('iphone_cases.json')
    charms = load_data('phone_charms.json')
    addons = load_data('addons.json')

    for item, details in cart.items():
        if item in cases:

            cases[item]['stock'] -= details['quantity']
        elif item in charms:
             charms[item]['stock'] -= details['quantity']
        elif item in addons:
             addons[item]['stock'] -= details['quantity']
    

    with open('data/iphone_cases.json', 'w') as file:
         json.dump(cases, file, indent=4)

    with open('data/phone_charms.json', 'w') as file:
        json.dump(charms, file, indent=4)

    with open('data/addons.json', 'w') as file:
         json.dump(addons, file, indent=4)
    


    invoice_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    """Displays the invoice page using the invoice dict saved in the session."""
    invoice = session.get('invoice')

    if not invoice:
        flash("No invoice available. Please complete checkout first.")
        return redirect(url_for('index'))

    return render_template('invoice.html', **invoice)



@app.route('/orders')
def order_history():
    """Gets all the past orders from the database and displays the order history page."""
    with sqlite3.connect('case_charm.db') as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM orders ORDER BY order_id DESC")
        orders = cursor.fetchall()

    return render_template('order_history.html', orders=orders)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Checks the available stock and it adds the selected product and quantity to the session cart."""
    product = request.form['product']
    quantity = int(request.form['quantity'])

    cases = load_data('iphone_cases.json')
    charms = load_data('phone_charms.json')
    addons = load_data('addons.json')

    cart = session.get('cart', {})

    if product in cases:
       price = cases[product]['price']
       stock = cases[product]['stock']
    elif product in charms:
        price = charms[product]['price']
        stock = charms[product]['stock']
    elif product in addons:
        price = addons[product]['price']
        stock = addons[product]['stock']
    else:
        flash("Invalid product selected.")
        return redirect(url_for('index'))

    current_quantity = cart.get(product, {}).get('quantity', 0)

    if quantity < 1:
        flash("Please enter a valid quantity.")
        return redirect(url_for('index'))

    if current_quantity + quantity > stock:
       flash(f"Only {stock - current_quantity} {product}(s) available.")
       return redirect(url_for('index'))

    
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
    """Adds the selected add-ons to the session cart."""
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
    """Removes an item from the session cart.

    Args:
        item (str): Name of the item so it can remove from the cart dict.

    Returns:
        Response: Redirects back to the home page.    
    
    """
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
    """Clears the current cart and selected add-ons from the session."""
    session.pop('cart', None)
    session.pop('selected_addons', None)
    session.modified = True

    flash("Your order has been cancelled.")

    return redirect(url_for('index'))

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    """Deletes an order from the database by using its ID.

    Args: 
        order_id (int): The ID of the order to delete.

    Returns:
        Response: Redirects back to the order history page.    
    
    
    """
    with sqlite3.connect('case_charm.db') as conn:
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM orders WHERE order_id = ?",
            (order_id,)
        )

        conn.commit()

    flash("Order deleted successfully.")
    return redirect(url_for('order_history'))

if __name__ == '__main__':
    initialise_database()
    app.run(debug=True, port=5001)


