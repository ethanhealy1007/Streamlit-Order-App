# Campus Store Order Entry: Streamlit + Supabase

A Streamlit web app that creates orders for existing customers in a Supabase database. Users pick a customer and product by name, enter a quantity, review the order, confirm it, and submit. Every saved order is verified by querying the database again, and the Order History updates automatically.

**Live app:** https://YOUR-APP-NAME.streamlit.app

**Access:** the app is protected by a password that is checked on the server before any database access. The password is provided privately through the course submission page.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit interface (this assignment) |
| `database.py` | Supabase API functions (class file, plus `get_product_price`, `insert_order`, and `get_order`) |
| `config.py` | Reads credentials from Streamlit secrets, falling back to a local `.env` |
| `requirements.txt` | Packages required to run the app |
| `.env.example` | Example local configuration (placeholders only) |
| `.streamlit/secrets.toml.example` | Example deployment secrets (placeholders only) |
| `.gitignore` | Excludes `.env`, `.streamlit/secrets.toml`, `.venv/`, and `__pycache__/` |
| `sql/`, `data/`, `01_check_connection.py`, `02_import_data.py` | Class files to create and load the fictional classroom database |

## Run Locally

1. Create the Supabase tables with `sql/01_create_tables.sql` (SQL Editor), if you have not already.
2. Create and activate a virtual environment and install the packages:
   ```
   python -m venv .venv
   .venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your Supabase URL, `sb_secret_` key, and an app password.
4. Load the sample data if the tables are empty: `python 02_import_data.py`
5. Start the app:
   ```
   streamlit run app.py
   ```

## Deploy (Streamlit Community Cloud)

1. Push this repository to GitHub (never commit `.env` or `.streamlit/secrets.toml`).
2. At [share.streamlit.io](https://share.streamlit.io), choose **Create app** and select this repository, the `main` branch, and `app.py` as the entry point.
3. Under **Advanced settings → Secrets**, paste the three settings from `.streamlit/secrets.toml.example` with real values.
4. Deploy, then open the app and enter the password.

## How It Works

- **Access control:** `require_password()` runs before any database call. It compares the entered password to `APP_PASSWORD` from the deployment secrets using `hmac.compare_digest`, and stops the app if no password is configured.
- **Display:** customers, products, and orders are retrieved through the Supabase API (`get_customers`, `get_products`, `get_orders`) and kept in `st.session_state`. **Refresh Data** retrieves them again. Prices use a currency column format.
- **Order entry:** dropdowns show names (for example, "Taylor Chen (ID 3)") but return the IDs, which are used for the insert. The quantity uses `st.number_input(min_value=1, step=1)`, so zero, negative, and decimal values cannot be entered. A review table shows customer, product, quantity, unit price, and total.
- **Confirmation and duplicate prevention:** the order is inserted only inside the **Submit Order** button's click, and only if the confirmation box is checked. The checkbox key includes the customer, product, quantity, price, and an order counter, so changing any detail, completing an order, or a price change produces a fresh, unchecked box. Ordinary reruns, refreshes, and widget changes never reach the insert.
- **Price check:** at submission, `get_product_price()` retrieves the current price from Supabase. If it differs from the reviewed price, the app shows the new price, unchecks the confirmation, and saves nothing until the user confirms again.
- **Save:** `insert_order()` saves the IDs, quantity, today's date, and the current price; the database generates `order_id`. A success message appears only after the insert returns the new row. Errors show a generic message and never credentials.
- **Verification:** `get_order()` sends a new query for the generated `order_id`, and the verification table calculates the total from the stored `unit_price`. If that query fails, the app explains that the order was saved but could not be verified, and does not resubmit.
- **Order History (with extra credit):** the full history from Supabase, newest first, updated after each successful order and on Refresh Data. A customer filter shows only that customer's orders, plus their count and total value at stored sale prices.

## Testing Results (deployed app)

| # | Test | Expected result | Result |
|---|---|---|---|
| 1 | Open the deployed app | Interface loads after authorized access (wrong password is rejected) | ☐ |
| 2 | View customers and products | Records are retrieved from Supabase | ☐ |
| 3 | Try an invalid quantity (0, negative, decimal) | Input is prevented by the number input | ☐ |
| 4 | Submit without confirmation | Warning shown; no order is inserted | ☐ |
| 5 | Confirm and submit a valid order | Exactly one order is inserted | ☐ |
| 6 | View the verification table | Newly saved order is retrieved from Supabase | ☐ |
| 7 | Refresh or interact with another widget | Previously submitted order is not inserted again | ☐ |
| 8 | Refresh order history | Saved order remains visible | ☐ |
| EC | Filter order history by customer | Only that customer's orders and their total value are shown | ☐ |

### Screenshots

Order entry interface:

![Order entry interface](screenshots/order-entry.png)

Successfully verified order:

![Verified order](screenshots/verified-order.png)

## References

Techniques beyond the earlier class material:

- Streamlit session state and `st.rerun()`: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
- Streamlit column formatting (`st.column_config.NumberColumn`): https://docs.streamlit.io/develop/api-reference/data/st.column_config/st.column_config.numbercolumn
- Streamlit secrets management: https://docs.streamlit.io/develop/concepts/connections/secrets-management
- Python `hmac.compare_digest` for the password check: https://docs.python.org/3/library/hmac.html#hmac.compare_digest
- Supabase embedded selects (`customers(name)`, used in the class `database.py`): https://supabase.com/docs/reference/python/select
