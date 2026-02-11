"""
Generate sample CSV files to test the Stock Compliance app.
Creates: sample_orders.csv, sample_sales.csv, sample_mappings.csv
"""
import csv
import random
from datetime import datetime, timedelta

SITES = [
    "Manchester Central", "London Bridge", "Birmingham New St",
    "Leeds City", "Liverpool One", "Bristol Temple", "Edinburgh Royal",
    "Glasgow Central", "Cardiff Bay", "Sheffield Meadowhall",
]

# Stock products (what gets ordered from supplier)
STOCK_PRODUCTS = [
    "Chicken Breast 2kg",
    "Beef Patties (box 40)",
    "Burger Buns (pack 12)",
    "Lettuce (case)",
    "Tomatoes (box 5kg)",
    "Chips 2.5kg (frozen)",
    "Cooking Oil 5L",
    "Cheese Slices (pack 100)",
]

# Menu items (what gets sold)
MENU_ITEMS = [
    "Chicken Burger",
    "Classic Beef Burger",
    "Cheeseburger",
    "Chicken Wrap",
    "Loaded Fries",
    "Side Salad",
]

# Recipe mappings: menu_item -> [(stock_product, qty_used)]
RECIPES = {
    "Chicken Burger": [("Chicken Breast 2kg", 1), ("Burger Buns (pack 12)", 1), ("Lettuce (case)", 0.5), ("Tomatoes (box 5kg)", 0.3)],
    "Classic Beef Burger": [("Beef Patties (box 40)", 1), ("Burger Buns (pack 12)", 1), ("Lettuce (case)", 0.5), ("Tomatoes (box 5kg)", 0.3)],
    "Cheeseburger": [("Beef Patties (box 40)", 1), ("Burger Buns (pack 12)", 1), ("Cheese Slices (pack 100)", 1), ("Lettuce (case)", 0.3)],
    "Chicken Wrap": [("Chicken Breast 2kg", 1.5), ("Lettuce (case)", 0.5), ("Tomatoes (box 5kg)", 0.2)],
    "Loaded Fries": [("Chips 2.5kg (frozen)", 2), ("Cheese Slices (pack 100)", 0.5), ("Cooking Oil 5L", 0.1)],
    "Side Salad": [("Lettuce (case)", 1), ("Tomatoes (box 5kg)", 0.5)],
}


def generate_dates(n=30):
    end = datetime.now().date()
    return [(end - timedelta(days=i)).isoformat() for i in range(n)]


def generate_orders(filename="sample_orders.csv"):
    dates = generate_dates()
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Restaurant", "Product", "Qty", "Order Date"])
        for site in SITES:
            # Each site orders weekly (pick ~4 order dates in the 30 days)
            order_dates = random.sample(dates, 4)
            for order_date in order_dates:
                for product in STOCK_PRODUCTS:
                    # Base quantity + site-specific variance
                    base = random.randint(5, 30)
                    # Some sites over-order, some under-order
                    if site in ("Manchester Central", "London Bridge"):
                        # These sites over-order by ~40%
                        qty = int(base * random.uniform(1.3, 1.5))
                    elif site in ("Sheffield Meadowhall", "Cardiff Bay"):
                        # These sites under-order by ~30%
                        qty = int(base * random.uniform(0.6, 0.8))
                    else:
                        # Normal sites
                        qty = int(base * random.uniform(0.9, 1.1))
                    writer.writerow([site, product, qty, order_date])
    print(f"Generated {filename}")


def generate_sales(filename="sample_sales.csv"):
    dates = generate_dates()
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Restaurant", "Item Name", "Qty Sold", "Sale Date"])
        for site in SITES:
            for sale_date in dates:
                for item in MENU_ITEMS:
                    qty = random.randint(10, 60)
                    writer.writerow([site, item, qty, sale_date])
    print(f"Generated {filename}")


def generate_mappings(filename="sample_mappings.csv"):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["menu_item", "stock_product", "quantity_used"])
        for menu_item, ingredients in RECIPES.items():
            for stock_product, qty in ingredients:
                writer.writerow([menu_item, stock_product, qty])
    print(f"Generated {filename}")


if __name__ == "__main__":
    generate_orders()
    generate_sales()
    generate_mappings()
    print("\nDone! Upload these files to the app:")
    print("  1. sample_mappings.csv  -> Recipe Mappings (bulk upload)")
    print("  2. sample_orders.csv    -> Upload Orders (columns: Restaurant, Product, Qty, Order Date)")
    print("  3. sample_sales.csv     -> Upload Sales (columns: Restaurant, Item Name, Qty Sold, Sale Date)")
