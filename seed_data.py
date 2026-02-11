"""
Seed script: populates stock products, menu items, recipe mappings,
site aliases, and platform menu-item aliases from the COGS spreadsheet data.

Run with: python seed_data.py
"""

import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), "stock_compliance.db")


def get_or_create(db, table, name_value):
    row = db.execute(
        f"SELECT id FROM {table} WHERE LOWER(name) = LOWER(?)", (name_value.strip(),)
    ).fetchone()
    if row:
        return row[0]
    cursor = db.execute(f"INSERT INTO {table} (name) VALUES (?)", (name_value.strip(),))
    return cursor.lastrowid


def seed():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys=ON")

    # ------------------------------------------------------------------
    # Ensure menu_item_aliases table exists
    # ------------------------------------------------------------------
    db.executescript("""
        CREATE TABLE IF NOT EXISTS menu_item_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            platform_item_name TEXT NOT NULL,
            canonical_menu_item TEXT NOT NULL,
            UNIQUE(platform, platform_item_name)
        );
    """)

    # ------------------------------------------------------------------
    # Stock products (the things we track inventory of)
    # ------------------------------------------------------------------
    STOCK_PRODUCTS = [
        "Halal Chicken Gyros Flakes",
        "The Athenian Pork Gyros Flakes",
        "Halloumi Block",
        "Choriatiki Pitta Bread",
        "Athenian Sauce",
        "Tzatziki Sauce",
        "Chilli Mayo",
        "Gyros Sauce",
        "The Athenian Courgette Fritters",
        "The Athenian Tomato Fritters",
        "Vegan Salted Caramel Brownie",
        "Vegan Gyros",
        "Heura Chick'n Fillet Burger",  # Mighty Chicken
    ]

    for sp in STOCK_PRODUCTS:
        get_or_create(db, "stock_products", sp)

    # ------------------------------------------------------------------
    # Menu items and recipe mappings from COGS spreadsheet
    # Key: menu item name (canonical, from COGS sheet)
    # Value: dict of {stock_product: quantity_used}
    #
    # Units from COGS:
    #   Chicken = kg (0.11 per wrap, 0.165 per box)
    #   Pork = kg (same as chicken)
    #   Halloumi = kg (0.09 wrap, 0.12 fries, 0.15 box)
    #   Pitta = units (1 per wrap/box)
    #   Sauces = kg (0.025 default in wraps, 0.05 in regular/beast wraps)
    #   Courgette/Tomato Fritters = kg
    #   Vegan Gyros = kg
    #   Brownie = units (1 per serve)
    # ------------------------------------------------------------------
    RECIPES = {
        # --- Light Wraps ---
        "Light Halal Chicken Gyros Wrap": {
            "Halal Chicken Gyros Flakes": 0.08,
            "Choriatiki Pitta Bread": 1,
        },
        "Light Pork Gyros Wrap": {
            "The Athenian Pork Gyros Flakes": 0.08,
            "Choriatiki Pitta Bread": 1,
        },
        "Light Mighty Vegan Gyros Wrap": {
            "Vegan Gyros": 0.08,
            "Choriatiki Pitta Bread": 1,
        },
        "Light Halloumi Wrap": {
            "Halloumi Block": 0.09,
            "Choriatiki Pitta Bread": 1,
        },

        # --- Regular Wraps ---
        "Pork Gyros Wrap": {
            "The Athenian Pork Gyros Flakes": 0.11,
            "Choriatiki Pitta Bread": 1,
        },
        "Mighty Vegan Gyros Wrap": {
            "Vegan Gyros": 0.11,
            "Choriatiki Pitta Bread": 1,
        },
        "Grilled Halloumi Souvlaki Wrap": {
            "Halloumi Block": 0.09,
            "Choriatiki Pitta Bread": 1,
        },
        "Chicken Gyros Wrap": {
            "Halal Chicken Gyros Flakes": 0.11,
            "Choriatiki Pitta Bread": 1,
        },
        "Chicken Halloumi Gyros Wrap": {
            "Halal Chicken Gyros Flakes": 0.08,
            "Halloumi Block": 0.04,
            "Choriatiki Pitta Bread": 1,
        },

        # --- Beast Wraps ---
        "The Beast Halal Chicken Gyros Wrap": {
            "Halal Chicken Gyros Flakes": 0.11,
            "Halloumi Block": 0.04,
            "Choriatiki Pitta Bread": 1,
        },
        "The Beast Pork Gyros Wrap": {
            "The Athenian Pork Gyros Flakes": 0.11,
            "Halloumi Block": 0.04,
            "Choriatiki Pitta Bread": 1,
        },

        # --- Beast Boxes ---
        "The Beast Pork Gyros Box": {
            "The Athenian Pork Gyros Flakes": 0.165,
            "Halloumi Block": 0.04,
            "Choriatiki Pitta Bread": 1,
        },
        "The Beast Halal Chicken Gyros Box": {
            "Halal Chicken Gyros Flakes": 0.165,
            "Halloumi Block": 0.04,
            "Choriatiki Pitta Bread": 1,
        },

        # --- Regular Boxes ---
        "Mighty Vegan Gyros Box": {
            "Vegan Gyros": 0.165,
            "Choriatiki Pitta Bread": 1,
        },
        "Halal Chicken Gyros Box": {
            "Halal Chicken Gyros Flakes": 0.165,
            "Choriatiki Pitta Bread": 1,
        },
        "Grilled Halloumi Cheese Super Souvlaki Box": {
            "Halloumi Block": 0.15,
            "Choriatiki Pitta Bread": 1,
        },
        "Pork Gyros Box": {
            "The Athenian Pork Gyros Flakes": 0.165,
            "Choriatiki Pitta Bread": 1,
        },
        "Mixed Gyros Box": {
            "Halal Chicken Gyros Flakes": 0.0825,
            "The Athenian Pork Gyros Flakes": 0.0825,
            "Choriatiki Pitta Bread": 1,
        },

        # --- Light Boxes ---
        "Light Mighty Vegan Box": {
            "Vegan Gyros": 0.08,
            "Choriatiki Pitta Bread": 1,
        },
        "Light Chicken Box": {
            "Halal Chicken Gyros Flakes": 0.08,
            "Choriatiki Pitta Bread": 1,
        },
        "Light Halloumi Box": {
            "Halloumi Block": 0.075,
            "Choriatiki Pitta Bread": 1,
        },
        "Light Pork Box": {
            "The Athenian Pork Gyros Flakes": 0.08,
            "Choriatiki Pitta Bread": 1,
        },
        "Light Mixed Box": {
            "Halal Chicken Gyros Flakes": 0.04,
            "The Athenian Pork Gyros Flakes": 0.04,
            "Choriatiki Pitta Bread": 1,
        },

        # --- Sides ---
        "Halloumi Fries": {
            "Halloumi Block": 0.12,
        },
        "Tomato Croquettes": {
            "The Athenian Tomato Fritters": 0.11,
        },
        "Oregano Fries": {
            # Uses potato fries + oregano, no tracked stock items
        },
        "Courgette Fritters": {
            "The Athenian Courgette Fritters": 0.11,
        },
        "Sweet Potato Fries": {
            # Uses sweet potato fries, not a tracked stock item currently
        },
        "Loaded Gyros Fries": {
            "Halal Chicken Gyros Flakes": 0.04,
            # Also uses fries + sauce but those aren't tracked stock
        },
        "Pita with Tzatziki": {
            "Choriatiki Pitta Bread": 1,
            "Tzatziki Sauce": 0.1,
        },

        # --- Sauces (sold separately) ---
        "Athenian Sauce 2oz": {
            "Athenian Sauce": 0.05,
        },
        "Tzatziki Sauce 2oz": {
            "Tzatziki Sauce": 0.05,
        },
        "Chilli Mayo 2oz": {
            "Chilli Mayo": 0.05,
        },
        "Gyros Sauce 2oz": {
            "Gyros Sauce": 0.05,
        },

        # --- Desserts ---
        "Vegan Salted Caramel Chocolate Brownie": {
            "Vegan Salted Caramel Brownie": 1,
        },

        # --- Modifiers (extras) ---
        "Add Extra Chicken": {
            "Halal Chicken Gyros Flakes": 0.05,
        },
        "Add Extra Pork": {
            "The Athenian Pork Gyros Flakes": 0.05,
        },
        "Add Extra Halloumi": {
            "Halloumi Block": 0.03,
        },
    }

    for menu_item_name, ingredients in RECIPES.items():
        mi_id = get_or_create(db, "menu_items", menu_item_name)
        for stock_product_name, qty in ingredients.items():
            sp_id = get_or_create(db, "stock_products", stock_product_name)
            db.execute("""
                INSERT OR REPLACE INTO recipe_mappings (menu_item_id, stock_product_id, quantity_used)
                VALUES (?, ?, ?)
            """, (mi_id, sp_id, qty))

    # ------------------------------------------------------------------
    # Deliveroo menu item aliases
    # Maps Deliveroo's item names -> canonical recipe names
    # ------------------------------------------------------------------
    DELIVEROO_ALIASES = {
        # --- Regular Wraps ---
        "Regular Chicken Gyros Wrap": "Chicken Gyros Wrap",
        "Regular Halal Chicken Gyros Wrap": "Chicken Gyros Wrap",
        "Regular Pork Gyros Wrap": "Pork Gyros Wrap",
        "Regular Grilled Halloumi Wrap": "Grilled Halloumi Souvlaki Wrap",
        "Regular Grilled Halloumi Cheese Souvlaki Wrap": "Grilled Halloumi Souvlaki Wrap",
        "Regular Mighty Vegan Gyros Wrap": "Mighty Vegan Gyros Wrap",
        "Mighty Vegan Gyros Wrap": "Mighty Vegan Gyros Wrap",

        # --- Light Wraps ---
        "Light Halal Chicken Gyros Wrap": "Light Halal Chicken Gyros Wrap",
        "Light Chicken Gyros Wrap": "Light Halal Chicken Gyros Wrap",
        "Light Pork Gyros Wrap": "Light Pork Gyros Wrap",
        "Light Mighty Vegan Gyros Wrap": "Light Mighty Vegan Gyros Wrap",
        "Light Halloumi Wrap": "Light Halloumi Wrap",

        # --- Beast Wraps ---
        "The Beast Halal Chicken Gyros Wrap": "The Beast Halal Chicken Gyros Wrap",
        "The Beast Chicken Gyros Wrap": "The Beast Halal Chicken Gyros Wrap",
        "The Beast Pork Gyros Wrap": "The Beast Pork Gyros Wrap",

        # --- Regular Boxes ---
        "Chicken Gyros Box": "Halal Chicken Gyros Box",
        "Halal Chicken Gyros Box": "Halal Chicken Gyros Box",
        "Pork Gyros Box": "Pork Gyros Box",
        "Grilled Halloumi Box": "Grilled Halloumi Cheese Super Souvlaki Box",
        "Halloumi Box": "Grilled Halloumi Cheese Super Souvlaki Box",
        "Grilled Halloumi Cheese Box": "Grilled Halloumi Cheese Super Souvlaki Box",
        "Grilled Halloumi  Box": "Grilled Halloumi Cheese Super Souvlaki Box",
        "Mighty Vegan Gyros Box": "Mighty Vegan Gyros Box",
        "Mixed Gyros Box": "Mixed Gyros Box",

        # --- Beast Boxes ---
        "The Beast Halal Chicken Gyros Box": "The Beast Halal Chicken Gyros Box",
        "The Beast Chicken Gyros Box": "The Beast Halal Chicken Gyros Box",
        "The Beast Pork Gyros Box": "The Beast Pork Gyros Box",

        # --- Sides ---
        "Halloumi Fries": "Halloumi Fries",
        "Oregano Fries": "Oregano Fries",
        "Courgette Fritters - aka Greek \"Falafel\"": "Courgette Fritters",
        "Courgette Fritters": "Courgette Fritters",
        "Tomato Croquettes": "Tomato Croquettes",
        "Tomato Croquettes - Tomatokeftedes": "Tomato Croquettes",
        "Sweet Potato Fries": "Sweet Potato Fries",
        "Pita & Tzatziki": "Pita with Tzatziki",
        "Gyros Loaded Fries": "Loaded Gyros Fries",

        # --- Sauces (sold separately as 2oz pots) ---
        "Athenian Sauce": "Athenian Sauce 2oz",
        "Athenian Sauce 2oz (Vegan)": "Athenian Sauce 2oz",
        "Athenian Sauce 2oz (Vegan)(Side)": "Athenian Sauce 2oz",
        "Tzatziki Sauce": "Tzatziki Sauce 2oz",
        "Tzatziki 2oz": "Tzatziki Sauce 2oz",
        "Tzatziki 2oz (Dairy)(Side)": "Tzatziki Sauce 2oz",
        "Chilli Mayo (2oz) (Vegan) (Side)": "Chilli Mayo 2oz",
        "Chilli Mayo (2oz) (Vegan)": "Chilli Mayo 2oz",
        "Gyros Sauce 2oz (Vegan)": "Gyros Sauce 2oz",
        "Gyros Sauce 2oz (Vegan)(Side)": "Gyros Sauce 2oz",

        # --- Desserts ---
        "Vegan Salted Caramel Chocolate Brownie": "Vegan Salted Caramel Chocolate Brownie",
        "Vegan Belgian Chocolate Fudge Cake": "Vegan Belgian Chocolate Fudge Cake",

        # --- Modifiers (extras that affect stock) ---
        "Add Extra Halloumi": "Add Extra Halloumi",
        "Add Halloumi (Dairy)": "Add Extra Halloumi",
        "Add Extra Chicken": "Add Extra Chicken",
        "Add Extra Pork": "Add Extra Pork",

        # --- Meal deals (the deal itself - components come as modifiers) ---
        # Meal deal line items don't directly use stock; their modifier lines do.
        # We alias the modifier selections so they resolve to canonical items.
        # The meal deal wrapper itself is ignored for stock purposes.

        # --- Zero-stock modifiers (sauce choices, removals, drinks) ---
        # These are deliberately NOT aliased. If they appear and have no alias,
        # the system ignores them for stock calculations. This includes:
        # Tzatziki (Dairy), Gyros Sauce, Athenian Sauce (Vegan), Chilli Mayo (Vegan),
        # Chili Mayo (Vegan), Truffle Mayo (Vegan),
        # Remove Tomatoes, Remove Onions, Remove Lettuce, Remove Fries, No Sauce,
        # Coca-Cola, Diet Coke, Coke Zero, Coca Cola Zero, Sprite, Fanta, Fanta Orange,
        # Sparkling Water, Still Water
    }

    for platform_name, canonical_name in DELIVEROO_ALIASES.items():
        try:
            db.execute("""
                INSERT OR REPLACE INTO menu_item_aliases
                (platform, platform_item_name, canonical_menu_item)
                VALUES (?, ?, ?)
            """, ("deliveroo", platform_name, canonical_name))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Site aliases (Deliveroo site names -> canonical)
    # ------------------------------------------------------------------
    SITE_ALIASES = {
        "Athenian - Evesham": "Evesham",
        "The Athenian - Bermondsey": "Bermondsey",
        "Athenian - Broxbourne": "Broxbourne",
        "Athenian - Colchester": "Colchester",
        "Athenian - Macclesfield": "Macclesfield",
        "Athenian - Potters Bar": "Potters Bar",
        "Athenian - Lancaster": "Lancaster",
        "The Athenian (Huddersfield)": "Huddersfield",
        "Athenian - Dover": "Dover",
    }

    for stock_name, sales_name in SITE_ALIASES.items():
        existing = db.execute(
            "SELECT id FROM site_aliases WHERE LOWER(stock_name) = LOWER(?)",
            (stock_name,),
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE site_aliases SET sales_name = ? WHERE id = ?",
                (sales_name, existing[0]),
            )
        else:
            db.execute(
                "INSERT INTO site_aliases (stock_name, sales_name) VALUES (?, ?)",
                (stock_name, sales_name),
            )

    db.commit()
    db.close()

    print("Seed data loaded successfully.")
    print(f"  - {len(STOCK_PRODUCTS)} stock products")
    print(f"  - {len(RECIPES)} menu items with recipes")
    print(f"  - {len(DELIVEROO_ALIASES)} Deliveroo item aliases")
    print(f"  - {len(SITE_ALIASES)} site aliases")


if __name__ == "__main__":
    seed()
