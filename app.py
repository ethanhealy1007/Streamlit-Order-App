"""Campus Store Order Entry: a Streamlit app connected to Supabase.

DATA 4000 - Build and Publish a Streamlit Order Entry App
Run locally with:  streamlit run app.py
"""

import hmac
from decimal import Decimal

import streamlit as st

import database as db
from config import get_app_password

st.set_page_config(page_title="Campus Store Order Entry", page_icon="🛒", layout="wide")

CURRENCY = "$%.2f"  # Streamlit column format for prices and totals


def money(value):
    """Convert a price from Supabase (number or text) to an exact Decimal."""
    return Decimal(str(value))


# ---------------------------------------------------------------------------
# Access control: runs BEFORE any database access
# ---------------------------------------------------------------------------

def require_password():
    """Stop the app unless the viewer enters the password stored in secrets."""
    expected = get_app_password()
    if not expected:
        st.error("This app's access password has not been configured. "
                 "Add APP_PASSWORD to the deployment secrets.")
        st.stop()

    if st.session_state.get("authenticated"):
        return

    with st.form("login"):
        entered = st.text_input("App password", type="password")
        submitted = st.form_submit_button("Enter")
    if submitted:
        # compare_digest checks the password without leaking timing information
        if hmac.compare_digest(entered.encode(), expected.encode()):
            st.session_state.authenticated = True
            st.rerun()
        st.error("Incorrect password.")
    st.stop()


# ---------------------------------------------------------------------------
# Loading data from Supabase
# ---------------------------------------------------------------------------

def load_all_data():
    """Retrieve customers, products, and orders from Supabase into session state."""
    st.session_state.customers = db.get_customers()
    st.session_state.products = db.get_products()
    st.session_state.orders = db.get_orders()


def order_to_row(order):
    """Turn an order from Supabase (with embedded names) into a display row."""
    unit_price = money(order["unit_price"])  # the STORED sale price
    return {
        "Order ID": order["order_id"],
        "Customer": (order.get("customers") or {}).get("name", "Unknown"),
        "Product": (order.get("products") or {}).get("product_name", "Unknown"),
        "Quantity": order["quantity"],
        "Unit Price": float(unit_price),
        "Total": float(unit_price * order["quantity"]),
        "Order Date": order["order_date"],
    }


def show_order_table(rows):
    """Display order rows with currency formatting."""
    st.dataframe(
        rows,
        hide_index=True,
        column_config={
            "Unit Price": st.column_config.NumberColumn(format=CURRENCY),
            "Total": st.column_config.NumberColumn(format=CURRENCY),
        },
    )


# ---------------------------------------------------------------------------
# Saving an order
# ---------------------------------------------------------------------------

def submit_order(customer_id, product_id, quantity, reviewed_price, confirmed,
                 customers_by_id, products_by_id):
    """Validate, re-check the price, insert, and verify. Runs only on Submit."""
    if not confirmed:
        st.warning("Please check the confirmation box before submitting. No order was saved.")
        return
    if customer_id not in customers_by_id or product_id not in products_by_id:
        st.error("Please select an existing customer and product. No order was saved.")
        return
    if type(quantity) is not int or quantity <= 0:
        st.error("Quantity must be a positive whole number. No order was saved.")
        return

    # Always get the CURRENT price from Supabase at the moment of submission
    try:
        current_price = db.get_product_price(product_id)
    except Exception:
        st.error("Could not reach the database to check the current price. No order was saved.")
        return
    if current_price is None:
        st.error("That product no longer exists. Select Refresh Data. No order was saved.")
        return

    # Price changed since the user reviewed it: show the new price, require re-confirmation
    if money(current_price) != reviewed_price:
        products_by_id[product_id]["price"] = current_price
        st.session_state.price_notice = {
            "product_id": product_id,
            "text": (f"The price of {products_by_id[product_id]['product_name']} changed from "
                     f"${reviewed_price:.2f} to ${money(current_price):.2f}. "
                     "Review the updated total and confirm again. No order was saved."),
        }
        st.session_state.confirm_round += 1  # new checkbox key = unchecked
        st.rerun()

    try:
        saved = db.insert_order(customer_id, product_id, quantity, current_price)
    except Exception:
        # Generic message only: never show the URL or key
        st.error("The order could not be saved to the database. Please try again. "
                 "No order was saved.")
        return

    order_id = saved["order_id"]

    # Verification: a NEW query for the order the database just created
    try:
        verified = db.get_order(order_id)
    except Exception:
        verified = None

    st.session_state.last_result = {"order_id": order_id, "verified": verified}
    st.session_state.price_notice = None
    st.session_state.confirm_round += 1  # clears the confirmation for the next order

    try:
        st.session_state.orders = db.get_orders()  # update Order History
    except Exception:
        st.session_state.history_error = True
    st.rerun()


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("🛒 Campus Store Order Entry")
st.write("Create orders for existing customers. Customers, products, and order history "
         "are retrieved live from the Supabase database, and every saved order is "
         "verified by querying the database again. All records are fictional classroom data.")

require_password()

# Session defaults
st.session_state.setdefault("confirm_round", 0)
st.session_state.setdefault("price_notice", None)
st.session_state.setdefault("last_result", None)

refresh_clicked = st.button("🔄 Refresh Data")
if refresh_clicked or "customers" not in st.session_state:
    try:
        load_all_data()
        st.session_state.history_error = False
    except Exception:
        st.error("Could not load data from Supabase. Check the connection settings "
                 "and select Refresh Data to try again.")
        st.stop()
    if refresh_clicked:
        st.toast("Data refreshed from Supabase.")

customers = st.session_state.customers
products = st.session_state.products
customers_by_id = {c["customer_id"]: c for c in customers}
products_by_id = {p["product_id"]: p for p in products}

# --- 1. Customers and products ---------------------------------------------
left, right = st.columns(2)
with left:
    st.subheader("Customers")
    st.dataframe(
        [{"Customer ID": c["customer_id"], "Name": c["name"]} for c in customers],
        hide_index=True,
    )
with right:
    st.subheader("Products")
    st.dataframe(
        [{"Product ID": p["product_id"], "Product": p["product_name"],
          "Category": p["category"], "Price": float(money(p["price"]))} for p in products],
        hide_index=True,
        column_config={"Price": st.column_config.NumberColumn(format=CURRENCY)},
    )

# --- 2. Order entry ----------------------------------------------------------
st.header("Place an Order")
pick_customer, pick_product, pick_quantity = st.columns(3)
with pick_customer:
    customer_id = st.selectbox(
        "Customer",
        options=list(customers_by_id),  # the IDs are what we keep...
        format_func=lambda i: f"{customers_by_id[i]['name']} (ID {i})",  # ...names are what we show
        index=None,
        placeholder="Choose a customer",
    )
with pick_product:
    product_id = st.selectbox(
        "Product",
        options=list(products_by_id),
        # Name + ID only: a label that included the price would change when the
        # price changes, which makes Streamlit treat it as a new (empty) widget
        format_func=lambda i: f"{products_by_id[i]['product_name']} (ID {i})",
        index=None,
        placeholder="Choose a product",
    )
with pick_quantity:
    # min_value=1 and step=1 prevent zero, negative, and decimal quantities
    quantity = st.number_input("Quantity", min_value=1, step=1, value=1)

if customer_id is None or product_id is None:
    st.info("Select a customer and a product to review the order.")
else:
    customer = customers_by_id[customer_id]
    product = products_by_id[product_id]
    unit_price = money(product["price"])
    total = unit_price * quantity

    st.subheader("Review Order")
    st.dataframe(
        [{"Customer": customer["name"], "Product": product["product_name"],
          "Quantity": quantity, "Unit Price": float(unit_price), "Total": float(total)}],
        hide_index=True,
        column_config={
            "Unit Price": st.column_config.NumberColumn(format=CURRENCY),
            "Total": st.column_config.NumberColumn(format=CURRENCY),
        },
    )

    notice = st.session_state.price_notice
    if notice and notice["product_id"] == product_id:
        st.warning(notice["text"])

    # The key includes every order detail, so changing ANY of them (or a price
    # change, or a completed order) produces a fresh, unchecked box.
    confirmed = st.checkbox(
        "I have reviewed this order and confirm it is correct.",
        key=(f"confirm_{customer_id}_{product_id}_{quantity}_{unit_price}_"
             f"{st.session_state.confirm_round}"),
    )

    # Inserting happens ONLY inside this button's click; ordinary reruns skip it
    if st.button("Submit Order", type="primary"):
        submit_order(customer_id, product_id, quantity, unit_price, confirmed,
                     customers_by_id, products_by_id)

# --- 3. Verification ---------------------------------------------------------
result = st.session_state.last_result
if result:
    st.header("Verification")
    if result["verified"]:
        st.success(f"Order {result['order_id']} was saved and verified in Supabase.")
        show_order_table([order_to_row(result["verified"])])
    else:
        st.warning(f"Order {result['order_id']} was saved, but it could not be retrieved "
                   "for verification. It was not submitted again.")

# --- 4. Order history (with customer filter: extra credit) -------------------
st.header("Order History")
if st.session_state.get("history_error"):
    st.warning("Order history could not be updated. Select Refresh Data to try again.")

filter_choice = st.selectbox(
    "Filter by customer",
    options=["All customers"] + list(customers_by_id),
    format_func=lambda i: i if i == "All customers" else f"{customers_by_id[i]['name']} (ID {i})",
)
orders = sorted(st.session_state.orders, key=lambda o: o["order_id"], reverse=True)
if filter_choice != "All customers":
    orders = [o for o in orders if o["customer_id"] == filter_choice]

history_rows = [order_to_row(o) for o in orders]
total_value = sum(money(o["unit_price"]) * o["quantity"] for o in orders)

count_col, value_col = st.columns(2)
count_col.metric("Orders", len(history_rows))
value_col.metric("Total value (stored sale prices)", f"${total_value:,.2f}")
show_order_table(history_rows)
