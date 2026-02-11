import os
import sqlite3
from datetime import datetime, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for, flash, g, jsonify
)
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB upload limit

DATABASE = os.path.join(app.root_path, "stock_compliance.db")
UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stock_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS recipe_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_item_id INTEGER NOT NULL,
            stock_product_id INTEGER NOT NULL,
            quantity_used REAL NOT NULL DEFAULT 1.0,
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id),
            FOREIGN KEY (stock_product_id) REFERENCES stock_products(id),
            UNIQUE(menu_item_id, stock_product_id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            stock_product_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            order_date DATE NOT NULL,
            upload_batch TEXT,
            FOREIGN KEY (site_id) REFERENCES sites(id),
            FOREIGN KEY (stock_product_id) REFERENCES stock_products(id)
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity_sold REAL NOT NULL,
            sale_date DATE NOT NULL,
            upload_batch TEXT,
            FOREIGN KEY (site_id) REFERENCES sites(id),
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
        );

        -- Maps stock site names (from orders) to a canonical site name
        -- so orders and sales can be linked even when naming differs
        CREATE TABLE IF NOT EXISTS site_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_name TEXT UNIQUE NOT NULL,
            sales_name TEXT NOT NULL
        );

        -- Maps platform-specific menu item names to canonical recipe names
        CREATE TABLE IF NOT EXISTS menu_item_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            platform_item_name TEXT NOT NULL,
            canonical_menu_item TEXT NOT NULL,
            UNIQUE(platform, platform_item_name)
        );

        CREATE INDEX IF NOT EXISTS idx_orders_site_date
            ON orders(site_id, order_date);
        CREATE INDEX IF NOT EXISTS idx_sales_site_date
            ON sales(site_id, sale_date);
    """)
    db.commit()


with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"csv", "xlsx", "xls"}


def read_upload(file_storage):
    """Read an uploaded CSV or Excel file into a pandas DataFrame."""
    filename = file_storage.filename.lower()
    if filename.endswith(".csv"):
        return pd.read_csv(file_storage, low_memory=False)
    else:
        return pd.read_excel(file_storage)


def get_or_create(db, table, name_value):
    """Get ID for a name in a lookup table, creating it if it doesn't exist."""
    row = db.execute(
        f"SELECT id FROM {table} WHERE LOWER(name) = LOWER(?)", (name_value.strip(),)
    ).fetchone()
    if row:
        return row["id"]
    cursor = db.execute(
        f"INSERT INTO {table} (name) VALUES (?)", (name_value.strip(),)
    )
    return cursor.lastrowid


def get_date_range():
    """Return the 30-day rolling window (start, end) based on today."""
    end = datetime.now().date()
    start = end - timedelta(days=30)
    return start.isoformat(), end.isoformat()


def resolve_site_name(db, raw_name):
    """Look up the canonical site name via the alias table.
    If an alias exists, use the sales_name. Otherwise use the raw name as-is."""
    alias = db.execute(
        "SELECT sales_name FROM site_aliases WHERE LOWER(stock_name) = LOWER(?)",
        (raw_name.strip(),)
    ).fetchone()
    if alias:
        return alias["sales_name"]
    return raw_name.strip()


def resolve_menu_item_name(db, platform, raw_name):
    """Look up the canonical menu item name via the alias table.
    Returns the canonical name if found, otherwise returns the raw name."""
    alias = db.execute(
        "SELECT canonical_menu_item FROM menu_item_aliases "
        "WHERE LOWER(platform) = LOWER(?) AND LOWER(platform_item_name) = LOWER(?)",
        (platform.strip(), raw_name.strip())
    ).fetchone()
    if alias:
        return alias["canonical_menu_item"]
    return raw_name.strip()


def resolve_site_from_platform(db, raw_name):
    """Resolve a platform site name (e.g. 'Athenian - Evesham') to canonical.
    Uses the site_aliases table. Falls back to raw name."""
    alias = db.execute(
        "SELECT sales_name FROM site_aliases WHERE LOWER(stock_name) = LOWER(?)",
        (raw_name.strip(),)
    ).fetchone()
    if alias:
        return alias["sales_name"]
    return raw_name.strip()


# Items that should be skipped entirely during sales import (no stock impact)
SKIP_ITEMS = {
    # Sauce choices within items (£0 modifiers - not separate sauce pots)
    "tzatziki (dairy)", "gyros sauce", "gyros sauce (vegan)",
    "athenian sauce (vegan)", "chilli mayo (vegan)", "chili mayo (vegan)",
    "truffle mayo (vegan)", "no sauce",
    # Removals
    "remove tomatoes", "remove onions", "remove lettuce", "remove fries",
    # Drink choices within meal deals (£0 modifiers)
    "coca-cola", "coca cola zero", "coke zero", "diet coke",
    "sprite", "fanta", "fanta orange", "sparkling water", "still water",
    # Meal deal wrapper lines (components are tracked via modifiers)
    "gyros meal for 1 \U0001f929", "gyros meal for 2 \U0001f46f\u200d\u2640\ufe0f",
    "super combo for 4 \U0001f9d1\u200d\U0001f9d1\u200d\U0001f9d2\u200d\U0001f9d2",
}


def parse_order_csv(file_storage):
    """Parse the supplier order CSV format.

    This file has a date range string in the very first cell (row 0),
    then the actual column headers on row 1, and data from row 2 onwards.
    Columns used: Account (site), Description (product), Qty (quantity).
    Negative quantities are kept (they net off as credits).
    """
    filename = file_storage.filename.lower()
    if filename.endswith(".csv"):
        # Read raw to grab the date range from the first row
        import io
        raw = file_storage.read()
        file_storage.seek(0)
        lines = raw.decode("utf-8", errors="replace").splitlines()

        date_range_text = lines[0].split(",")[0].strip().strip('"') if lines else ""

        # Now read the actual data, skipping the first row (date range header)
        df = pd.read_csv(io.BytesIO(raw), skiprows=1)
    else:
        df = pd.read_excel(file_storage, skiprows=1)
        date_range_text = ""

    return df, date_range_text


# ---------------------------------------------------------------------------
# Routes — Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    db = get_db()
    date_start, date_end = get_date_range()

    # Per-site, per-product: total ordered
    ordered = db.execute("""
        SELECT s.name AS site, sp.name AS product,
               SUM(o.quantity) AS total_ordered
        FROM orders o
        JOIN sites s ON o.site_id = s.id
        JOIN stock_products sp ON o.stock_product_id = sp.id
        WHERE o.order_date BETWEEN ? AND ?
        GROUP BY o.site_id, o.stock_product_id
    """, (date_start, date_end)).fetchall()

    # Per-site, per-stock-product: expected usage via recipe mapping
    expected = db.execute("""
        SELECT s.name AS site, sp.name AS product,
               SUM(sa.quantity_sold * rm.quantity_used) AS expected_usage
        FROM sales sa
        JOIN sites s ON sa.site_id = s.id
        JOIN recipe_mappings rm ON sa.menu_item_id = rm.menu_item_id
        JOIN stock_products sp ON rm.stock_product_id = sp.id
        WHERE sa.sale_date BETWEEN ? AND ?
        GROUP BY sa.site_id, rm.stock_product_id
    """, (date_start, date_end)).fetchall()

    # Build lookup: (site, product) -> {ordered, expected, variance}
    data = {}
    for row in ordered:
        key = (row["site"], row["product"])
        data[key] = {"ordered": row["total_ordered"], "expected": 0}

    for row in expected:
        key = (row["site"], row["product"])
        if key in data:
            data[key]["expected"] = row["expected_usage"]
        else:
            data[key] = {"ordered": 0, "expected": row["expected_usage"]}

    # Calculate variances and build site summaries
    site_summaries = {}
    product_details = {}

    for (site, product), vals in data.items():
        ordered_qty = vals["ordered"]
        expected_qty = vals["expected"]
        variance = ordered_qty - expected_qty
        if expected_qty > 0:
            variance_pct = (variance / expected_qty) * 100
        elif ordered_qty > 0:
            variance_pct = 100.0
        else:
            variance_pct = 0.0

        # Accumulate site-level summary (sum of absolute variances)
        if site not in site_summaries:
            site_summaries[site] = {
                "total_ordered": 0,
                "total_expected": 0,
                "product_count": 0,
                "worst_variance_pct": 0,
            }
        summary = site_summaries[site]
        summary["total_ordered"] += ordered_qty
        summary["total_expected"] += expected_qty
        summary["product_count"] += 1
        if abs(variance_pct) > abs(summary["worst_variance_pct"]):
            summary["worst_variance_pct"] = variance_pct

        # Product-level detail for drill-down
        if site not in product_details:
            product_details[site] = []
        product_details[site].append({
            "product": product,
            "ordered": round(ordered_qty, 1),
            "expected": round(expected_qty, 1),
            "variance": round(variance, 1),
            "variance_pct": round(variance_pct, 1),
        })

    # Build sorted site list
    sites_list = []
    for site, summary in site_summaries.items():
        total_ord = summary["total_ordered"]
        total_exp = summary["total_expected"]
        overall_var = total_ord - total_exp
        if total_exp > 0:
            overall_var_pct = (overall_var / total_exp) * 100
        elif total_ord > 0:
            overall_var_pct = 100.0
        else:
            overall_var_pct = 0.0

        sites_list.append({
            "name": site,
            "total_ordered": round(total_ord, 1),
            "total_expected": round(total_exp, 1),
            "overall_variance": round(overall_var, 1),
            "overall_variance_pct": round(overall_var_pct, 1),
            "worst_product_variance_pct": round(summary["worst_variance_pct"], 1),
            "product_count": summary["product_count"],
        })

    # Sort by absolute worst product variance (biggest outliers first)
    sites_list.sort(key=lambda x: abs(x["worst_product_variance_pct"]), reverse=True)

    # Count totals for the header
    total_sites = db.execute("SELECT COUNT(*) as c FROM sites").fetchone()["c"]
    total_orders = db.execute(
        "SELECT COUNT(*) as c FROM orders WHERE order_date BETWEEN ? AND ?",
        (date_start, date_end)
    ).fetchone()["c"]
    total_sales = db.execute(
        "SELECT COUNT(*) as c FROM sales WHERE sale_date BETWEEN ? AND ?",
        (date_start, date_end)
    ).fetchone()["c"]
    total_mappings = db.execute("SELECT COUNT(*) as c FROM recipe_mappings").fetchone()["c"]

    return render_template(
        "dashboard.html",
        sites=sites_list,
        product_details=product_details,
        date_start=date_start,
        date_end=date_end,
        total_sites=total_sites,
        total_orders=total_orders,
        total_sales=total_sales,
        total_mappings=total_mappings,
    )


# ---------------------------------------------------------------------------
# Routes — Site drill-down
# ---------------------------------------------------------------------------

@app.route("/site/<site_name>")
def site_detail(site_name):
    db = get_db()
    date_start, date_end = get_date_range()

    site = db.execute("SELECT * FROM sites WHERE name = ?", (site_name,)).fetchone()
    if not site:
        flash(f"Site '{site_name}' not found.", "error")
        return redirect(url_for("dashboard"))

    ordered = db.execute("""
        SELECT sp.name AS product, SUM(o.quantity) AS total_ordered
        FROM orders o
        JOIN stock_products sp ON o.stock_product_id = sp.id
        WHERE o.site_id = ? AND o.order_date BETWEEN ? AND ?
        GROUP BY o.stock_product_id
    """, (site["id"], date_start, date_end)).fetchall()

    expected = db.execute("""
        SELECT sp.name AS product,
               SUM(sa.quantity_sold * rm.quantity_used) AS expected_usage
        FROM sales sa
        JOIN recipe_mappings rm ON sa.menu_item_id = rm.menu_item_id
        JOIN stock_products sp ON rm.stock_product_id = sp.id
        WHERE sa.site_id = ? AND sa.sale_date BETWEEN ? AND ?
        GROUP BY rm.stock_product_id
    """, (site["id"], date_start, date_end)).fetchall()

    # Merge
    products = {}
    for row in ordered:
        products[row["product"]] = {"ordered": row["total_ordered"], "expected": 0}
    for row in expected:
        if row["product"] in products:
            products[row["product"]]["expected"] = row["expected_usage"]
        else:
            products[row["product"]] = {"ordered": 0, "expected": row["expected_usage"]}

    details = []
    for product, vals in products.items():
        variance = vals["ordered"] - vals["expected"]
        if vals["expected"] > 0:
            variance_pct = (variance / vals["expected"]) * 100
        elif vals["ordered"] > 0:
            variance_pct = 100.0
        else:
            variance_pct = 0.0
        details.append({
            "product": product,
            "ordered": round(vals["ordered"], 1),
            "expected": round(vals["expected"], 1),
            "variance": round(variance, 1),
            "variance_pct": round(variance_pct, 1),
        })

    details.sort(key=lambda x: abs(x["variance_pct"]), reverse=True)

    return render_template(
        "site_detail.html",
        site_name=site_name,
        details=details,
        date_start=date_start,
        date_end=date_end,
    )


# ---------------------------------------------------------------------------
# Routes — Upload Orders
# ---------------------------------------------------------------------------

@app.route("/upload/orders", methods=["GET", "POST"])
def upload_orders():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not allowed_file(file.filename):
            flash("Please upload a CSV or Excel file.", "error")
            return redirect(request.url)

        # User provides the date for this file since it's in the header row
        date_from = request.form.get("date_from", "").strip()
        date_to = request.form.get("date_to", "").strip()

        if not date_from or not date_to:
            flash("Please enter the date range this file covers.", "error")
            return redirect(request.url)

        try:
            df, date_range_text = parse_order_csv(file)
        except Exception as e:
            flash(f"Error reading file: {e}", "error")
            return redirect(request.url)

        # Expected columns from the supplier format
        site_col = "Account"
        product_col = "Description"
        quantity_col = "Qty"

        for col in [site_col, product_col, quantity_col]:
            if col not in df.columns:
                flash(f"Column '{col}' not found in file. Available columns: {', '.join(df.columns)}", "error")
                return redirect(request.url)

        # Use the midpoint of the date range as the order_date for all rows
        order_date = date_from

        db = get_db()
        batch = datetime.now().isoformat()
        inserted = 0
        skipped_no_alias = set()
        errors = []

        for idx, row in df.iterrows():
            try:
                raw_site = str(row[site_col]).strip()
                product_name = str(row[product_col]).strip()
                qty_str = str(row[quantity_col]).strip().replace(",", "").replace(" ", "")
                quantity = float(qty_str)

                if pd.isna(row[site_col]) or pd.isna(row[product_col]) or not raw_site or not product_name:
                    continue

                # Resolve site name via alias dictionary
                site_name = resolve_site_name(db, raw_site)

                site_id = get_or_create(db, "sites", site_name)
                product_id = get_or_create(db, "stock_products", product_name)

                db.execute(
                    "INSERT INTO orders (site_id, stock_product_id, quantity, order_date, upload_batch) VALUES (?, ?, ?, ?, ?)",
                    (site_id, product_id, quantity, order_date, batch),
                )
                inserted += 1
            except Exception as e:
                errors.append(f"Row {idx + 2}: {e}")

        db.commit()

        flash(f"Uploaded {inserted} order records for period {date_from} to {date_to}.", "success")
        if date_range_text:
            flash(f"Date range found in file header: {date_range_text}", "info")
        if errors:
            flash(f"{len(errors)} rows had errors. First few: {'; '.join(errors[:3])}", "warning")
        return redirect(url_for("dashboard"))

    return render_template("upload_orders.html")


# ---------------------------------------------------------------------------
# Routes — Upload Deliveroo Sales
# ---------------------------------------------------------------------------

@app.route("/upload/deliveroo", methods=["GET", "POST"])
def upload_deliveroo():
    """Upload Deliveroo sales CSV.
    Expected columns: Restaurant name, Category, Item name, Quantity, Price, Subtotal
    """
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not allowed_file(file.filename):
            flash("Please upload a CSV or Excel file.", "error")
            return redirect(request.url)

        date_from = request.form.get("date_from", "").strip()
        date_to = request.form.get("date_to", "").strip()
        if not date_from or not date_to:
            flash("Please enter the date range this sales file covers.", "error")
            return redirect(request.url)

        try:
            df = read_upload(file)
        except Exception as e:
            flash(f"Error reading file: {e}", "error")
            return redirect(request.url)

        # Validate columns
        required_cols = {"Restaurant name", "Item name", "Quantity"}
        if not required_cols.issubset(set(df.columns)):
            flash(
                f"Missing columns. Need: {required_cols}. Found: {', '.join(df.columns)}",
                "error",
            )
            return redirect(request.url)

        db = get_db()
        batch = datetime.now().isoformat()
        inserted = 0
        skipped = 0
        unmatched = set()
        errors = []

        for idx, row in df.iterrows():
            try:
                raw_site = str(row["Restaurant name"]).strip()
                raw_item = str(row["Item name"]).strip()
                quantity = float(row["Quantity"])

                if pd.isna(row["Restaurant name"]) or pd.isna(row["Item name"]) or not raw_site or not raw_item:
                    continue

                # Skip items with no stock impact
                if raw_item.lower() in SKIP_ITEMS:
                    skipped += 1
                    continue

                # Resolve site name
                site_name = resolve_site_from_platform(db, raw_site)

                # Resolve menu item name via alias
                canonical_item = resolve_menu_item_name(db, "deliveroo", raw_item)

                # Check if this canonical item has any recipe mappings
                mi_row = db.execute(
                    "SELECT id FROM menu_items WHERE LOWER(name) = LOWER(?)",
                    (canonical_item,)
                ).fetchone()

                if not mi_row:
                    unmatched.add(raw_item)
                    skipped += 1
                    continue

                has_recipe = db.execute(
                    "SELECT 1 FROM recipe_mappings WHERE menu_item_id = ?",
                    (mi_row["id"],)
                ).fetchone()

                if not has_recipe:
                    # Item exists but no recipe = no stock impact (e.g. oregano fries)
                    skipped += 1
                    continue

                site_id = get_or_create(db, "sites", site_name)

                db.execute(
                    "INSERT INTO sales (site_id, menu_item_id, quantity_sold, sale_date, upload_batch) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (site_id, mi_row["id"], quantity, date_from, batch),
                )
                inserted += 1

                # Batch commit every 500 rows to avoid large transactions
                if inserted % 500 == 0:
                    db.commit()
            except Exception as e:
                errors.append(f"Row {idx + 2}: {e}")

        db.commit()

        flash(f"Deliveroo: imported {inserted} stock-relevant sales records. {skipped} skipped (no stock impact).", "success")
        if errors:
            flash(f"{len(errors)} rows had errors. First few: {'; '.join(errors[:5])}", "warning")
        if unmatched:
            sorted_unmatched = sorted(unmatched)
            flash(
                f"Unmatched items (need aliases): {', '.join(sorted_unmatched[:15])}"
                + (f" ... and {len(sorted_unmatched) - 15} more" if len(sorted_unmatched) > 15 else ""),
                "warning",
            )
        return redirect(url_for("dashboard"))

    return render_template("upload_deliveroo.html")


# ---------------------------------------------------------------------------
# Routes — Upload Sales (generic)
# ---------------------------------------------------------------------------

@app.route("/upload/sales", methods=["GET", "POST"])
def upload_sales():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not allowed_file(file.filename):
            flash("Please upload a CSV or Excel file.", "error")
            return redirect(request.url)

        site_col = request.form.get("site_col", "").strip()
        item_col = request.form.get("item_col", "").strip()
        quantity_col = request.form.get("quantity_col", "").strip()
        date_col = request.form.get("date_col", "").strip()

        if not all([site_col, item_col, quantity_col, date_col]):
            flash("Please fill in all column name fields.", "error")
            return redirect(request.url)

        try:
            df = read_upload(file)
        except Exception as e:
            flash(f"Error reading file: {e}", "error")
            return redirect(request.url)

        for col in [site_col, item_col, quantity_col, date_col]:
            if col not in df.columns:
                flash(f"Column '{col}' not found in file. Available columns: {', '.join(df.columns)}", "error")
                return redirect(request.url)

        db = get_db()
        batch = datetime.now().isoformat()
        inserted = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                site_name = str(row[site_col]).strip()
                item_name = str(row[item_col]).strip()
                quantity = float(row[quantity_col])
                date_val = pd.to_datetime(row[date_col]).date().isoformat()

                if pd.isna(row[site_col]) or pd.isna(row[item_col]) or not site_name or not item_name:
                    continue

                site_id = get_or_create(db, "sites", site_name)
                item_id = get_or_create(db, "menu_items", item_name)

                db.execute(
                    "INSERT INTO sales (site_id, menu_item_id, quantity_sold, sale_date, upload_batch) VALUES (?, ?, ?, ?, ?)",
                    (site_id, item_id, quantity, date_val, batch),
                )
                inserted += 1
            except Exception as e:
                errors.append(f"Row {idx + 2}: {e}")

        db.commit()
        flash(f"Uploaded {inserted} sales records.", "success")
        if errors:
            flash(f"{len(errors)} rows had errors. First few: {'; '.join(errors[:3])}", "warning")
        return redirect(url_for("dashboard"))

    return render_template("upload_sales.html")


# ---------------------------------------------------------------------------
# Routes — Recipe Mappings
# ---------------------------------------------------------------------------

@app.route("/mappings")
def mappings():
    db = get_db()
    rows = db.execute("""
        SELECT rm.id, mi.name AS menu_item, sp.name AS stock_product,
               rm.quantity_used
        FROM recipe_mappings rm
        JOIN menu_items mi ON rm.menu_item_id = mi.id
        JOIN stock_products sp ON rm.stock_product_id = sp.id
        ORDER BY mi.name, sp.name
    """).fetchall()

    menu_items = db.execute("SELECT * FROM menu_items ORDER BY name").fetchall()
    stock_products = db.execute("SELECT * FROM stock_products ORDER BY name").fetchall()

    return render_template(
        "mappings.html",
        mappings=rows,
        menu_items=menu_items,
        stock_products=stock_products,
    )


@app.route("/mappings/add", methods=["POST"])
def add_mapping():
    db = get_db()
    menu_item_name = request.form.get("menu_item", "").strip()
    stock_product_name = request.form.get("stock_product", "").strip()
    quantity_used = request.form.get("quantity_used", "1")

    if not menu_item_name or not stock_product_name:
        flash("Both menu item and stock product are required.", "error")
        return redirect(url_for("mappings"))

    try:
        quantity_used = float(quantity_used)
    except ValueError:
        flash("Quantity must be a number.", "error")
        return redirect(url_for("mappings"))

    menu_item_id = get_or_create(db, "menu_items", menu_item_name)
    stock_product_id = get_or_create(db, "stock_products", stock_product_name)

    try:
        db.execute(
            "INSERT INTO recipe_mappings (menu_item_id, stock_product_id, quantity_used) VALUES (?, ?, ?)",
            (menu_item_id, stock_product_id, quantity_used),
        )
        db.commit()
        flash(f"Mapping added: {menu_item_name} uses {quantity_used}x {stock_product_name}", "success")
    except sqlite3.IntegrityError:
        flash(f"Mapping already exists for {menu_item_name} -> {stock_product_name}. Delete it first to update.", "warning")

    return redirect(url_for("mappings"))


@app.route("/mappings/delete/<int:mapping_id>", methods=["POST"])
def delete_mapping(mapping_id):
    db = get_db()
    db.execute("DELETE FROM recipe_mappings WHERE id = ?", (mapping_id,))
    db.commit()
    flash("Mapping deleted.", "success")
    return redirect(url_for("mappings"))


@app.route("/mappings/upload", methods=["POST"])
def upload_mappings():
    """Bulk upload recipe mappings from CSV. Columns: menu_item, stock_product, quantity_used"""
    file = request.files.get("file")
    if not file or not allowed_file(file.filename):
        flash("Please upload a CSV or Excel file.", "error")
        return redirect(url_for("mappings"))

    try:
        df = read_upload(file)
    except Exception as e:
        flash(f"Error reading file: {e}", "error")
        return redirect(url_for("mappings"))

    required = {"menu_item", "stock_product", "quantity_used"}
    if not required.issubset(set(df.columns)):
        flash(f"File must have columns: menu_item, stock_product, quantity_used. Found: {', '.join(df.columns)}", "error")
        return redirect(url_for("mappings"))

    db = get_db()
    inserted = 0
    for _, row in df.iterrows():
        try:
            mi_id = get_or_create(db, "menu_items", str(row["menu_item"]).strip())
            sp_id = get_or_create(db, "stock_products", str(row["stock_product"]).strip())
            qty = float(row["quantity_used"])
            db.execute(
                "INSERT OR REPLACE INTO recipe_mappings (menu_item_id, stock_product_id, quantity_used) VALUES (?, ?, ?)",
                (mi_id, sp_id, qty),
            )
            inserted += 1
        except Exception:
            continue

    db.commit()
    flash(f"Uploaded {inserted} recipe mappings.", "success")
    return redirect(url_for("mappings"))


# ---------------------------------------------------------------------------
# Routes — Site Alias Dictionary
# ---------------------------------------------------------------------------

@app.route("/site-aliases")
def site_aliases():
    db = get_db()
    aliases = db.execute(
        "SELECT * FROM site_aliases ORDER BY stock_name"
    ).fetchall()
    return render_template("site_aliases.html", aliases=aliases)


@app.route("/site-aliases/upload", methods=["POST"])
def upload_site_aliases():
    """Upload a CSV mapping stock site names to sales site names.
    Expected columns: stock_name, sales_name"""
    file = request.files.get("file")
    if not file or not allowed_file(file.filename):
        flash("Please upload a CSV or Excel file.", "error")
        return redirect(url_for("site_aliases"))

    try:
        df = read_upload(file)
    except Exception as e:
        flash(f"Error reading file: {e}", "error")
        return redirect(url_for("site_aliases"))

    # Flexible column name matching
    col_map = {}
    for col in df.columns:
        lower = col.strip().lower().replace(" ", "_")
        if "stock" in lower:
            col_map["stock_name"] = col
        elif "sales" in lower:
            col_map["sales_name"] = col

    if "stock_name" not in col_map or "sales_name" not in col_map:
        flash(
            f"File must have a 'stock name' column and a 'sales name' column. "
            f"Found columns: {', '.join(df.columns)}",
            "error",
        )
        return redirect(url_for("site_aliases"))

    db = get_db()
    inserted = 0
    updated = 0
    for _, row in df.iterrows():
        stock = str(row[col_map["stock_name"]]).strip()
        sales = str(row[col_map["sales_name"]]).strip()
        if not stock or stock == "nan" or not sales or sales == "nan":
            continue

        existing = db.execute(
            "SELECT id FROM site_aliases WHERE LOWER(stock_name) = LOWER(?)",
            (stock,),
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE site_aliases SET sales_name = ? WHERE id = ?",
                (sales, existing["id"]),
            )
            updated += 1
        else:
            db.execute(
                "INSERT INTO site_aliases (stock_name, sales_name) VALUES (?, ?)",
                (stock, sales),
            )
            inserted += 1

    db.commit()
    flash(f"Site dictionary updated: {inserted} added, {updated} updated.", "success")
    return redirect(url_for("site_aliases"))


@app.route("/site-aliases/add", methods=["POST"])
def add_site_alias():
    stock_name = request.form.get("stock_name", "").strip()
    sales_name = request.form.get("sales_name", "").strip()

    if not stock_name or not sales_name:
        flash("Both stock name and sales name are required.", "error")
        return redirect(url_for("site_aliases"))

    db = get_db()
    try:
        db.execute(
            "INSERT INTO site_aliases (stock_name, sales_name) VALUES (?, ?)",
            (stock_name, sales_name),
        )
        db.commit()
        flash(f"Alias added: '{stock_name}' -> '{sales_name}'", "success")
    except sqlite3.IntegrityError:
        flash(f"Alias for '{stock_name}' already exists. Delete it first to update.", "warning")

    return redirect(url_for("site_aliases"))


@app.route("/site-aliases/delete/<int:alias_id>", methods=["POST"])
def delete_site_alias(alias_id):
    db = get_db()
    db.execute("DELETE FROM site_aliases WHERE id = ?", (alias_id,))
    db.commit()
    flash("Alias deleted.", "success")
    return redirect(url_for("site_aliases"))


# ---------------------------------------------------------------------------
# Routes — Menu Item Aliases
# ---------------------------------------------------------------------------

@app.route("/menu-aliases")
def menu_aliases():
    db = get_db()
    aliases = db.execute(
        "SELECT * FROM menu_item_aliases ORDER BY platform, platform_item_name"
    ).fetchall()
    return render_template("menu_aliases.html", aliases=aliases)


@app.route("/menu-aliases/add", methods=["POST"])
def add_menu_alias():
    platform = request.form.get("platform", "").strip()
    platform_item = request.form.get("platform_item_name", "").strip()
    canonical = request.form.get("canonical_menu_item", "").strip()

    if not all([platform, platform_item, canonical]):
        flash("All fields are required.", "error")
        return redirect(url_for("menu_aliases"))

    db = get_db()
    try:
        db.execute(
            "INSERT OR REPLACE INTO menu_item_aliases (platform, platform_item_name, canonical_menu_item) "
            "VALUES (?, ?, ?)",
            (platform, platform_item, canonical),
        )
        db.commit()
        flash(f"Alias added: [{platform}] '{platform_item}' -> '{canonical}'", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")

    return redirect(url_for("menu_aliases"))


@app.route("/menu-aliases/delete/<int:alias_id>", methods=["POST"])
def delete_menu_alias(alias_id):
    db = get_db()
    db.execute("DELETE FROM menu_item_aliases WHERE id = ?", (alias_id,))
    db.commit()
    flash("Alias deleted.", "success")
    return redirect(url_for("menu_aliases"))


# ---------------------------------------------------------------------------
# Routes — Data Management
# ---------------------------------------------------------------------------

@app.route("/data")
def data_management():
    db = get_db()
    order_batches = db.execute("""
        SELECT upload_batch, COUNT(*) as record_count,
               MIN(order_date) as date_from, MAX(order_date) as date_to
        FROM orders
        WHERE upload_batch IS NOT NULL
        GROUP BY upload_batch
        ORDER BY upload_batch DESC
    """).fetchall()

    sales_batches = db.execute("""
        SELECT upload_batch, COUNT(*) as record_count,
               MIN(sale_date) as date_from, MAX(sale_date) as date_to
        FROM sales
        WHERE upload_batch IS NOT NULL
        GROUP BY upload_batch
        ORDER BY upload_batch DESC
    """).fetchall()

    return render_template("data.html", order_batches=order_batches, sales_batches=sales_batches)


@app.route("/data/delete-batch", methods=["POST"])
def delete_batch():
    batch = request.form.get("batch")
    data_type = request.form.get("type")

    db = get_db()
    if data_type == "orders":
        db.execute("DELETE FROM orders WHERE upload_batch = ?", (batch,))
    elif data_type == "sales":
        db.execute("DELETE FROM sales WHERE upload_batch = ?", (batch,))
    db.commit()

    flash(f"Deleted {data_type} batch.", "success")
    return redirect(url_for("data_management"))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
