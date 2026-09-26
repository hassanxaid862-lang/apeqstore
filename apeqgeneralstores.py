import streamlit as st
import sqlite3
import pandas as pd
import json
import random
import base64
from datetime import datetime
import streamlit.components.v1 as components

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="APEQ MARKET PLACE",
    page_icon="🛍️",
    layout="wide"
)

DB_FILE = "apeqstore.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Customers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            created_at TEXT
        )
    ''')
    
    # Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL,
            description TEXT NOT NULL,
            in_stock INTEGER DEFAULT 1,
            created_at TEXT
        )
    ''')
    
    # Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            landmark TEXT,
            latitude REAL,
            longitude REAL,
            items_json TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TEXT
        )
    ''')
    
    # Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS site_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT DEFAULT 'APEQ MARKET PLACE',
            store_description TEXT DEFAULT 'Your ultimate destination for quality products at unbeatable prices.',
            admin_password TEXT DEFAULT 'admin123',
            phone TEXT DEFAULT '0794551087',
            email TEXT DEFAULT 'support@apeqstore.com',
            facebook TEXT DEFAULT 'https://facebook.com',
            instagram TEXT DEFAULT 'https://instagram.com',
            whatsapp TEXT DEFAULT 'https://wa.me/254794551087'
        )
    ''')

    # Reviews Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reviewer_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT NOT NULL,
            created_at TEXT
        )
    ''')

    # Check and add store_description column if missing
    cursor.execute("PRAGMA table_info(site_settings)")
    cols = [column[1] for column in cursor.fetchall()]
    if 'store_description' not in cols:
        cursor.execute("ALTER TABLE site_settings ADD COLUMN store_description TEXT DEFAULT 'Your ultimate destination for quality products at unbeatable prices.'")

    # Seed settings if empty
    cursor.execute("SELECT COUNT(*) FROM site_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO site_settings (store_name, store_description, admin_password, phone, email, facebook, instagram, whatsapp)
            VALUES ('APEQ MARKET PLACE', 'Your ultimate destination for quality products at unbeatable prices.', 'admin123', '0778899112', 'support@apeqstore.com', 'https://facebook.com', 'https://instagram.com', 'https://wa.me/254778899112')
        ''')
        
    conn.commit()
    conn.close()

init_db()

# Initialize Session States
if 'cart' not in st.session_state:
    st.session_state.cart = {}

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if 'customer_logged_in' not in st.session_state:
    st.session_state.customer_logged_in = False

if 'current_customer_phone' not in st.session_state:
    st.session_state.current_customer_phone = ""

if 'active_nav' not in st.session_state:
    st.session_state.active_nav = "Storefront"

if 'last_order' not in st.session_state:
    st.session_state.last_order = None

if 'user_lat' not in st.session_state:
    st.session_state.user_lat = 0.0

if 'user_lng' not in st.session_state:
    st.session_state.user_lng = 0.0

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_settings():
    conn = get_db_connection()
    setting = conn.execute("SELECT * FROM site_settings LIMIT 1").fetchone()
    conn.close()
    return dict(setting) if setting else {
        'store_name': 'APEQ MARKET PLACE',
        'store_description': 'Your ultimate destination for quality products at unbeatable prices.',
        'admin_password': 'admin123',
        'phone': '0794551087',
        'email': 'support@apeqstore.com',
        'facebook': 'https://facebook.com',
        'instagram': 'https://instagram.com',
        'whatsapp': 'https://wa.me/254778899112'
    }

def update_settings(store_name, store_description, admin_password, phone, email, facebook, instagram, whatsapp):
    conn = get_db_connection()
    conn.execute('''
        UPDATE site_settings SET store_name=?, store_description=?, admin_password=?, phone=?, email=?, facebook=?, instagram=?, whatsapp=? WHERE id=1
    ''', (store_name, store_description, admin_password, phone, email, facebook, instagram, whatsapp))
    conn.commit()
    conn.close()

def register_or_login_customer(phone, password, name=""):
    conn = get_db_connection()
    cust = conn.execute("SELECT * FROM customers WHERE phone=?", (phone,)).fetchone()
    if cust:
        if cust['password'] == password:
            conn.close()
            return True, cust['name'] or name
        else:
            conn.close()
            return False, "Incorrect password for this phone number."
    else:
        conn.execute("INSERT INTO customers (phone, password, name, created_at) VALUES (?, ?, ?, ?)",
                     (phone, password, name, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return True, name

def get_products():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(p) for p in products]

def add_product(title, price, image_data, description, in_stock):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO products (title, price, image, description, in_stock, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, price, image_data, description, 1 if in_stock else 0, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def toggle_stock(product_id, current_stock):
    conn = get_db_connection()
    new_stock = 0 if current_stock == 1 else 1
    conn.execute("UPDATE products SET in_stock=? WHERE id=?", (new_stock, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

def delete_all_products():
    conn = get_db_connection()
    conn.execute("DELETE FROM products")
    conn.commit()
    conn.close()

def create_order(name, phone, landmark, lat, lng, items, total):
    conn = get_db_connection()
    order_code = f"APEQ-{random.randint(100000, 999999)}"
    conn.execute('''
        INSERT INTO orders (order_code, customer_name, customer_phone, landmark, latitude, longitude, items_json, total_amount, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
    ''', (order_code, name, phone, landmark, lat, lng, json.dumps(items), total, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    return order_code

def get_orders():
    conn = get_db_connection()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(o) for o in orders]

def delete_order(order_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM orders WHERE id=?", (order_id,))
    conn.commit()
    conn.close()

def search_customer_orders(phone, product_name=""):
    conn = get_db_connection()
    orders = conn.execute("SELECT * FROM orders WHERE customer_phone=? ORDER BY id DESC", (phone.strip(),)).fetchall()
    conn.close()
    result = [dict(o) for o in orders]
    if product_name:
        filtered = []
        for o in result:
            items = json.loads(o['items_json'])
            if any(product_name.lower() in item['title'].lower() for item in items):
                filtered.append(o)
        return filtered
    return result

def update_order_status(order_id, status):
    conn = get_db_connection()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()

def add_review(name, rating, comment):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO reviews (reviewer_name, rating, comment, created_at)
        VALUES (?, ?, ?, ?)
    ''', (name, rating, comment, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_reviews():
    conn = get_db_connection()
    reviews = conn.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in reviews]

def delete_review(review_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM reviews WHERE id=?", (review_id,))
    conn.commit()
    conn.close()

def generate_receipt_text(order_code, name, phone, landmark, items, total_amount, date_str):
    receipt = f"""
==================================================
              APEQ MARKET PLACE
            OFFICIAL ORDER RECEIPT
==================================================
Order Code   : {order_code}
Date         : {date_str}
Customer     : {name}
Phone Number : {phone}
Address      : {landmark or 'N/A'}
Payment Type : PAYMENT AFTER DELIVERY
--------------------------------------------------
ITEMS ORDERED:
"""
    for idx, item in enumerate(items, 1):
        qty = item.get('quantity', 1)
        price = item.get('price', 0.0)
        receipt += f"{idx}. {item['title']} (x{qty}) - KSh {price * qty:,.2f}\n"

    receipt += f"""--------------------------------------------------
TOTAL AMOUNT DUE : KSh {total_amount:,.2f}
==================================================
Thank you for shopping with APEQ MARKET PLACE!
For inquiries: {settings.get('phone', '')} | {settings.get('email', '')}
==================================================
"""
    return receipt

# Fetch active settings
settings = get_settings()
STORE_NAME = settings.get('store_name', 'APEQ MARKET PLACE')
STORE_DESC = settings.get('store_description', 'Your ultimate destination for quality products at unbeatable prices.')
ADMIN_PASSWORD = settings.get('admin_password', 'admin123')

# Total Cart Count
total_cart_items = sum(item['quantity'] for item in st.session_state.cart.values())

# ==========================================
# NAVIGATION & SIDEBAR
# ==========================================
st.sidebar.title(f"🛍️ {STORE_NAME}")

nav_options = ["Storefront", "Track / My Orders", f"Cart ({total_cart_items})", "Customer Reviews"]

if st.session_state.admin_logged_in:
    nav_options.append("Admin Portal")

# Sidebar navigation synchronization
selected_nav = st.sidebar.radio("Navigate", nav_options, index=nav_options.index(st.session_state.active_nav) if st.session_state.active_nav in nav_options else 0)
st.session_state.active_nav = selected_nav

# Customer Session Box
st.sidebar.divider()
if st.session_state.customer_logged_in:
    st.sidebar.success(f"👤 Account: {st.session_state.current_customer_phone}")
    if st.sidebar.button("Logout Account"):
        st.session_state.customer_logged_in = False
        st.session_state.current_customer_phone = ""
        st.rerun()

# Social Media & Contact Panel
st.sidebar.markdown("### 🌐 Social & Support")
st.sidebar.markdown(f"📞 **Phone:** {settings.get('phone', '')}")
st.sidebar.markdown(f"✉️ **Email:** {settings.get('email', '')}")

st.sidebar.markdown("**Connect with Us:**")
c_soc1, c_soc2, c_soc3 = st.sidebar.columns(3)
with c_soc1:
    if settings.get('whatsapp'):
        st.markdown(f"[💬 WhatsApp]({settings.get('whatsapp')})")
with c_soc2:
    if settings.get('facebook'):
        st.markdown(f"[📘 Facebook]({settings.get('facebook')})")
with c_soc3:
    if settings.get('instagram'):
        st.markdown(f"[📷 Instagram]({settings.get('instagram')})")

st.sidebar.divider()

# Staff Login Panel
if not st.session_state.admin_logged_in:
    with st.sidebar.expander("🔒 Staff Access"):
        admin_key_input = st.text_input("Enter Admin Password", type="password")
        if st.button("Login to Admin Portal"):
            if admin_key_input == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("Admin unlocked!")
                st.rerun()
            else:
                st.error("Invalid Password")
else:
    if st.sidebar.button("Logout Admin"):
        st.session_state.admin_logged_in = False
        st.rerun()

# ==========================================
# VIEW 1: STOREFRONT
# ==========================================
if st.session_state.active_nav == "Storefront":
    st.title(f"🛒 {STORE_NAME}")
    st.markdown(f"*{STORE_DESC}*")
    st.info("🚚 **PAYMENT AFTER DELIVERY** — Shop with confidence and pay when your order arrives!")
    
    search_query = st.text_input("🔍 Search products by name...", "")
    products = get_products()
    
    if search_query:
        products = [p for p in products if search_query.lower() in p['title'].lower()]
    
    if not products:
        st.info("No products currently available in the store.")
    else:
        cols = st.columns(3)
        for idx, prod in enumerate(products):
            col = cols[idx % 3]
            with col:
                st.image(prod['image'], use_container_width=True)
                st.subheader(prod['title'])
                st.write(f"**Price:** KSh {prod['price']:,.2f}")
                st.caption(prod['description'])
                
                if prod['in_stock']:
                    st.success("In Stock")
                    if st.button("Add to Cart 🛒", key=f"add_{prod['id']}"):
                        pid = prod['id']
                        if pid in st.session_state.cart:
                            st.session_state.cart[pid]['quantity'] += 1
                        else:
                            st.session_state.cart[pid] = {'product': prod, 'quantity': 1}
                        
                        st.session_state.active_nav = f"Cart ({sum(item['quantity'] for item in st.session_state.cart.values())})"
                        st.toast(f"Added {prod['title']}! Opening Cart...", icon="🛒")
                        st.rerun()
                else:
                    st.error("Out of Stock")

# ==========================================
# VIEW 2: CART & CHECKOUT
# ==========================================
elif st.session_state.active_nav.startswith("Cart"):
    st.title("🛒 Shopping Cart & Checkout")
    
    if not st.session_state.cart and not st.session_state.last_order:
        st.info("Your cart is empty. Return to the storefront to add items.")
        if st.button("← Back to Storefront"):
            st.session_state.active_nav = "Storefront"
            st.rerun()
    else:
        if st.session_state.cart:
            total_amount = 0.0
            st.subheader("Selected Items")
            
            items_to_delete = []
            for pid, cart_item in list(st.session_state.cart.items()):
                prod = cart_item['product']
                qty = cart_item['quantity']
                item_total = prod['price'] * qty
                total_amount += item_total
                
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                with c1:
                    st.write(f"**{prod['title']}**")
                with c2:
                    st.write(f"KSh {prod['price']:,.2f} x {qty}")
                with c3:
                    new_qty = st.number_input("Qty", min_value=1, value=qty, key=f"qty_{pid}")
                    st.session_state.cart[pid]['quantity'] = new_qty
                with c4:
                    if st.button("❌", key=f"del_cart_{pid}"):
                        items_to_delete.append(pid)

            for pid in items_to_delete:
                del st.session_state.cart[pid]
                st.rerun()

            st.divider()
            st.markdown(f"### Total Amount: **KSh {total_amount:,.2f}**")
            st.success("💳 **PAYMENT AFTER DELIVERY** — No advance payment required!")
            st.divider()
            
            st.subheader("Checkout & Delivery Details")
            
            # --- GOOGLE MAPS / GPS PERMISSION SECTION ---
            st.markdown("#### 📍 Delivery Location Access")
            st.caption("Grant location access to share your exact GPS location for fast delivery.")
            
            # HTML/JS component for browser Geolocation request
            geo_script = """
            <script>
            function getLocation() {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(showPosition, showError);
                } else {
                    alert("Geolocation is not supported by this browser.");
                }
            }
            function showPosition(position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                window.parent.postMessage({
                    type: "streamlit:setComponentValue",
                    value: {lat: lat, lng: lng}
                }, "*");
            }
            function showError(error) {
                alert("Location request denied or unavailable.");
            }
            </script>
            <button onclick="getLocation()" style="
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                font-size: 14px;
            ">📍 Share My Current Location (Google Maps GPS)</button>
            """
            
            location_data = components.html(geo_script, height=60)
            
            if location_data:
                st.session_state.user_lat = location_data.get('lat', 0.0)
                st.session_state.user_lng = location_data.get('lng', 0.0)
                st.success(f"Location Captured! Latitude: {st.session_state.user_lat}, Longitude: {st.session_state.user_lng}")

            # Optional Map Preview
            if st.session_state.user_lat != 0.0 and st.session_state.user_lng != 0.0:
                df_loc = pd.DataFrame({'lat': [st.session_state.user_lat], 'lon': [st.session_state.user_lng]})
                st.map(df_loc, zoom=14)

            # --- FORM CHECKOUT ---
            with st.form("checkout_form"):
                c_name = st.text_input("Full Name *")
                c_phone = st.text_input("Phone Number *", value=st.session_state.current_customer_phone)
                c_pass = st.text_input("Account Password (to log in later or track order) *", type="password")
                c_landmark = st.text_area("Delivery Landmark / House Number / Street Name")
                
                # Auto-populated or manual fallback
                c_lat = st.number_input("Latitude (Auto-filled via GPS)", value=float(st.session_state.user_lat), format="%.6f")
                c_lng = st.number_input("Longitude (Auto-filled via GPS)", value=float(st.session_state.user_lng), format="%.6f")
                
                submit_order = st.form_submit_button("Place Order Now")
                
                if submit_order:
                    if not c_name or not c_phone or not c_pass:
                        st.error("Please fill in Name, Phone Number, and Password.")
                    else:
                        success, msg = register_or_login_customer(c_phone, c_pass, c_name)
                        if not success:
                            st.error(msg)
                        else:
                            st.session_state.customer_logged_in = True
                            st.session_state.current_customer_phone = c_phone
                            
                            items_summary = [
                                {
                                    'id': item['product']['id'],
                                    'title': item['product']['title'],
                                    'price': item['product']['price'],
                                    'quantity': item['quantity']
                                } for item in st.session_state.cart.values()
                            ]
                            now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                            order_code = create_order(
                                c_name, c_phone, c_landmark,
                                c_lat if c_lat != 0.0 else None,
                                c_lng if c_lng != 0.0 else None,
                                items_summary, total_amount
                            )
                            st.session_state.cart = {}
                            st.session_state.last_order = {
                                'code': order_code,
                                'name': c_name,
                                'phone': c_phone,
                                'landmark': c_landmark,
                                'items': items_summary,
                                'total': total_amount,
                                'date': now_str
                            }
                            st.rerun()

        # Display Receipt Outside Form
        if st.session_state.last_order:
            lo = st.session_state.last_order
            st.balloons()
            st.success(f"Order Placed Successfully! Order Code: **{lo['code']}**")
            st.info("🚚 **PAYMENT AFTER DELIVERY:** You will pay when your package arrives.")
            
            receipt_txt = generate_receipt_text(lo['code'], lo['name'], lo['phone'], lo['landmark'], lo['items'], lo['total'], lo['date'])
            st.subheader("📄 Your Official Receipt")
            st.code(receipt_txt, language="text")
            
            st.download_button(
                label="🖨️ Download Official Receipt (TXT)",
                data=receipt_txt,
                file_name=f"Receipt_{lo['code']}.txt",
                mime="text/plain"
            )

# ==========================================
# VIEW 3: TRACK / MY ORDERS
# ==========================================
elif st.session_state.active_nav == "Track / My Orders":
    st.title("📦 Order Tracking & Automatic Receipts")
    
    if not st.session_state.customer_logged_in:
        st.subheader("Login to View Your Orders")
        with st.form("login_form"):
            l_phone = st.text_input("Phone Number")
            l_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                success, msg = register_or_login_customer(l_phone, l_pass)
                if success:
                    st.session_state.customer_logged_in = True
                    st.session_state.current_customer_phone = l_phone
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error(msg)
                    
        st.divider()
        st.subheader("Or Search Order History by Details")
        s_phone = st.text_input("Enter Phone Number", key="s_phone")
        s_product = st.text_input("Product Name (Optional)", key="s_product")
        
        if st.button("Search Orders"):
            if s_phone:
                found_orders = search_customer_orders(s_phone, s_product)
                if found_orders:
                    st.success(f"Found {len(found_orders)} order(s):")
                    for ord_item in found_orders:
                        items = json.loads(ord_item['items_json'])
                        with st.expander(f"Order {ord_item['order_code']} - {ord_item['status']} (KSh {ord_item['total_amount']:,.2f})"):
                            st.write(f"**Date:** {ord_item['created_at']}")
                            st.write(f"**Address:** {ord_item['landmark']}")
                            st.write("**Items:**")
                            for it in items:
                                st.write(f"- {it['title']} x {it.get('quantity', 1)} (KSh {it['price']:,.2f})")
                                
                            receipt_data = generate_receipt_text(
                                ord_item['order_code'], ord_item['customer_name'],
                                ord_item['customer_phone'], ord_item['landmark'],
                                items, ord_item['total_amount'], ord_item['created_at']
                            )
                            st.download_button(
                                label="🖨️ Download Receipt",
                                data=receipt_data,
                                file_name=f"Receipt_{ord_item['order_code']}.txt",
                                mime="text/plain",
                                key=f"dl_unlog_{ord_item['id']}"
                            )
                else:
                    st.error("No matching orders found.")
            else:
                st.warning("Please enter your Phone Number to search.")
    else:
        st.subheader(f"My Orders History ({st.session_state.current_customer_phone})")
        filter_prod = st.text_input("Filter orders by Product Name")
        my_orders = search_customer_orders(st.session_state.current_customer_phone, filter_prod)
        
        if not my_orders:
            st.info("No past orders found for your account.")
        else:
            for ord_item in my_orders:
                items = json.loads(ord_item['items_json'])
                with st.expander(f"Order {ord_item['order_code']} — Status: `{ord_item['status']}` — KSh {ord_item['total_amount']:,.2f}"):
                    st.write(f"**Placed On:** {ord_item['created_at']}")
                    st.write(f"**Address/Landmark:** {ord_item['landmark']}")
                    st.write("**Items Ordered:**")
                    for it in items:
                        st.write(f"- {it['title']} x {it.get('quantity', 1)} (KSh {it['price']:,.2f})")
                    
                    receipt_data = generate_receipt_text(
                        ord_item['order_code'], ord_item['customer_name'],
                        ord_item['customer_phone'], ord_item['landmark'],
                        items, ord_item['total_amount'], ord_item['created_at']
                    )
                    st.download_button(
                        label="🖨️ Download Receipt",
                        data=receipt_data,
                        file_name=f"Receipt_{ord_item['order_code']}.txt",
                        mime="text/plain",
                        key=f"dl_log_{ord_item['id']}"
                    )

# ==========================================
# VIEW 4: CUSTOMER REVIEWS
# ==========================================
elif st.session_state.active_nav == "Customer Reviews":
    st.title("⭐ Customer Reviews & Feedback")
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.subheader("Leave a Review")
        with st.form("review_form"):
            r_name = st.text_input("Your Name *")
            r_rating = st.slider("Rating (Stars)", min_value=1, max_value=5, value=5)
            r_comment = st.text_area("Your Feedback / Review *")
            
            if st.form_submit_button("Submit Review"):
                if r_name and r_comment:
                    add_review(r_name, r_rating, r_comment)
                    st.success("Thank you! Your review has been submitted.")
                    st.rerun()
                else:
                    st.error("Please enter both your name and review comment.")

    with col2:
        st.subheader("What Other Customers Say")
        reviews = get_reviews()
        if not reviews:
            st.info("No reviews yet. Be the first to leave one!")
        else:
            for rev in reviews:
                stars = "⭐" * rev['rating']
                with st.chat_message("user"):
                    st.write(f"**{rev['reviewer_name']}** — {stars}")
                    st.write(rev['comment'])
                    st.caption(f"Posted on: {rev['created_at']}")

# ==========================================
# VIEW 5: ADMIN PORTAL
# ==========================================
elif st.session_state.active_nav == "Admin Portal" and st.session_state.admin_logged_in:
    st.title("⚙️ Admin Management Portal")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Manage Orders", "Manage Products", "Manage Reviews", "Store & Admin Settings"])
    
    # --- Tab 1: Orders Management ---
    with tab1:
        st.subheader("All Customer Orders")
        orders = get_orders()
        if not orders:
            st.info("No orders found.")
        else:
            filter_status = st.selectbox("Filter by Status", ["All", "Pending", "Out for Delivery", "Delivered", "Cancelled"])
            if filter_status != "All":
                orders = [o for o in orders if o['status'] == filter_status]
                
            for ord_item in orders:
                items = json.loads(ord_item['items_json'])
                with st.expander(f"Order {ord_item['order_code']} - {ord_item['customer_name']} [{ord_item['status']}]"):
                    st.write(f"**Phone:** {ord_item['customer_phone']}")
                    st.write(f"**Landmark:** {ord_item['landmark']}")
                    st.write(f"**Total:** KSh {ord_item['total_amount']:,.2f}")
                    st.write(f"**Created At:** {ord_item['created_at']}")
                    
                    if ord_item['latitude'] and ord_item['longitude']:
                        st.write("**Customer GPS Location (Google Maps Pin):**")
                        maps_url = f"https://www.google.com/maps?q={ord_item['latitude']},{ord_item['longitude']}"
                        st.markdown(f"👉 [Open Direct Location on Google Maps]({maps_url})")
                        
                        df_map = pd.DataFrame({'lat': [ord_item['latitude']], 'lon': [ord_item['longitude']]})
                        st.map(df_map, zoom=13)
                    
                    st.write("**Items:**")
                    for it in items:
                        qty = it.get('quantity', 1)
                        st.write(f"- {it['title']} (KSh {it['price']:,.2f} x {qty})")
                    
                    receipt_data = generate_receipt_text(
                        ord_item['order_code'], ord_item['customer_name'],
                        ord_item['customer_phone'], ord_item['landmark'],
                        items, ord_item['total_amount'], ord_item['created_at']
                    )
                    st.download_button(
                        label="🖨️ Print / Download Receipt",
                        data=receipt_data,
                        file_name=f"Receipt_{ord_item['order_code']}.txt",
                        mime="text/plain",
                        key=f"dl_admin_{ord_item['id']}"
                    )
                    
                    c_st, c_del = st.columns([3, 1])
                    with c_st:
                        new_status = st.selectbox(
                            "Update Status",
                            ["Pending", "Out for Delivery", "Delivered", "Cancelled"],
                            index=["Pending", "Out for Delivery", "Delivered", "Cancelled"].index(ord_item['status']),
                            key=f"status_select_{ord_item['id']}"
                        )
                        if st.button("Save Status", key=f"btn_stat_{ord_item['id']}"):
                            update_order_status(ord_item['id'], new_status)
                            st.success("Status updated!")
                            st.rerun()
                    with c_del:
                        if st.button("Delete Order", key=f"btn_del_ord_{ord_item['id']}"):
                            delete_order(ord_item['id'])
                            st.rerun()

    # --- Tab 2: Products Management ---
    with tab2:
        st.subheader("Add New Product")
        with st.form("add_product_form"):
            p_title = st.text_input("Product Title *")
            p_price = st.number_input("Price (KSh) *", min_value=0.0, step=100.0)
            
            img_method = st.radio("Image Source", ["Upload File", "Image URL"], horizontal=True)
            p_image_url = ""
            uploaded_file = None
            
            if img_method == "Upload File":
                uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png", "webp"])
            else:
                p_image_url = st.text_input("Image Web URL")

            p_desc = st.text_area("Description")
            p_stock = st.checkbox("In Stock", value=True)
            
            if st.form_submit_button("Save Product"):
                final_image = ""
                if img_method == "Upload File" and uploaded_file is not None:
                    bytes_data = uploaded_file.getvalue()
                    base64_img = base64.b64encode(bytes_data).decode()
                    file_type = uploaded_file.type
                    final_image = f"data:{file_type};base64,{base64_img}"
                elif img_method == "Image URL" and p_image_url:
                    final_image = p_image_url

                if p_title and p_price and final_image:
                    add_product(p_title, p_price, final_image, p_desc, p_stock)
                    st.success("Product added successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in the required fields and provide an image.")
                    
        st.divider()
        col_hdr1, col_hdr2 = st.columns([3, 1])
        with col_hdr1:
            st.subheader("Existing Products")
        with col_hdr2:
            if st.button("⚠️ Clear All Products"):
                delete_all_products()
                st.success("All products cleared!")
                st.rerun()

        prods = get_products()
        if not prods:
            st.info("No products currently in stock.")
        else:
            for p in prods:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                with col1:
                    st.write(f"**{p['title']}**")
                with col2:
                    st.write(f"KSh {p['price']:,.2f}")
                with col3:
                    stock_text = "In Stock" if p['in_stock'] else "Out of Stock"
                    if st.button(f"Toggle ({stock_text})", key=f"tog_{p['id']}"):
                        toggle_stock(p['id'], p['in_stock'])
                        st.rerun()
                with col4:
                    if st.button("Delete", key=f"del_prod_{p['id']}"):
                        delete_product(p['id'])
                        st.rerun()

    # --- Tab 3: Reviews Management ---
    with tab3:
        st.subheader("Manage Customer Reviews")
        all_reviews = get_reviews()
        if not all_reviews:
            st.info("No reviews available.")
        else:
            for rev in all_reviews:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{rev['reviewer_name']}** ({rev['rating']} Stars) — *{rev['created_at']}*")
                    st.write(f'"{rev["comment"]}"')
                with col2:
                    if st.button("Delete Review", key=f"del_rev_{rev['id']}"):
                        delete_review(rev['id'])
                        st.success("Review removed!")
                        st.rerun()
                st.divider()

    # --- Tab 4: Store & Admin Settings ---
    with tab4:
        st.subheader("Store Profile & Security Settings")
        curr_set = get_settings()
        
        with st.form("settings_form"):
            s_name = st.text_input("Business / Store Name", value=curr_set.get('store_name', 'APEQ MARKET PLACE'))
            s_desc = st.text_area("Business Description (Appears below business name)", value=curr_set.get('store_description', 'Your ultimate destination for quality products at unbeatable prices.'))
            s_pass = st.text_input("Admin Password", value=curr_set.get('admin_password', 'admin123'), type="password")
            
            st.divider()
            st.subheader("Contact & Social Links")
            s_phone = st.text_input("Phone Number", value=curr_set.get('phone', ''))
            s_email = st.text_input("Support Email", value=curr_set.get('email', ''))
            s_fb = st.text_input("Facebook URL", value=curr_set.get('facebook', ''))
            s_ig = st.text_input("Instagram URL", value=curr_set.get('instagram', ''))
            s_wa = st.text_input("WhatsApp Link", value=curr_set.get('whatsapp', ''))
            
            if st.form_submit_button("Save All Settings"):
                update_settings(s_name, s_desc, s_pass, s_phone, s_email, s_fb, s_ig, s_wa)
                st.success("Settings updated successfully!")
                st.rerun()
