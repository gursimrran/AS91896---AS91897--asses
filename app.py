import json 

from flask import Flask, render_template, request,session, flash, redirect, url_for

app = Flask(__name__)
app.secret_key= 'your_secret_key'

def load_data(filename):
    with open(f'data/{filename}') as file:
        products = json.load(file)
    return products  

def calculate_total(cart):
    total = sum(
        item['price'] * item['quantity']
        for item in cart.values()
    ) 
    return total

@app.route('/')
def index():
    cases = load_data('iphone_cases.json')
    charms = load_data('phone_charms.json')
    addons = load_data('addons.json')
    cart = session.get('cart', {})

    total = calculate_total(cart)

    
    return render_template('index1.html', cases=cases, charms=charms, addons=addons, cart=cart, cart_total=total)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/checkout')
def checkout():
    return render_template('invoice.html')

@app.route('/orders')
def order_history():
    return render_template('order_history.html')

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

if __name__ == '__main__':
    app.run(debug=True)


