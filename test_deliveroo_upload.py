"""
Test script: runs the Deliveroo data through the parser logic
and reports what matches, what's skipped, and what's unmatched.
"""
import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), "stock_compliance.db")

# All Deliveroo rows from the comprehensive paste
# (restaurant_name, category, item_name, quantity, price, subtotal)
DELIVEROO_DATA = [
    ("Athenian - Evesham", "Souvlaki & Gyros Boxes", "Pork Gyros Box", 2, 15.25, 30.5),
    ("Athenian - Evesham", "Modifiers", "Add Extra Halloumi", 6, 2.5, 15),
    ("Athenian - Evesham", "Modifiers", "Add Extra Pork", 1, 2.9, 2.9),
    ("Athenian - Evesham", "Modifiers", "Remove Tomatoes", 2, 0, 0),
    ("Athenian - Evesham", "Modifiers", "Tzatziki (Dairy)", 18, 0, 0),
    ("Athenian - Evesham", "The Beast - Protein Gyros", "The Beast Halal Chicken Gyros Box", 5, 17.95, 89.75),
    ("Athenian - Evesham", "Souvlaki & Gyros Boxes", "Grilled Halloumi Box", 1, 15.25, 15.25),
    ("Athenian - Evesham", "Modifiers", "Add Extra Chicken", 4, 2.9, 11.6),
    ("Athenian - Evesham", "Modifiers", "Remove Onions", 5, 0, 0),
    ("Athenian - Evesham", "Sauces", "Tzatziki Sauce", 1, 1.5, 1.5),
    ("Athenian - Evesham", "Meal Deals", "Gyros Meal for 1", 12, 15.95, 191.4),
    ("Athenian - Evesham", "Modifiers", "Oregano Fries", 9, 0, 0),
    ("Athenian - Evesham", "Modifiers", "Fanta Orange", 6, 0, 0),
    ("Athenian - Evesham", "Modifiers", "Regular Pork Gyros Wrap", 5, 0, 0),
    ("Athenian - Evesham", "Modifiers", "Remove Tomatoes", 3, 0, 0),
    ("Athenian - Evesham", "Modifiers", "No Sauce", 2, 0, 0),
    ("Athenian - Evesham", "Sauces", "Athenian Sauce", 4, 1.5, 6),
    ("The Athenian - Bermondsey", "Souvlaki & Gyros Boxes", "Chicken Gyros Box", 34, 15.25, 518.5),
    ("The Athenian - Bermondsey", "Modifiers", "Athenian Sauce (Vegan)", 94, 0, 0),
    ("The Athenian - Bermondsey", "The Beast - Protein Gyros", "The Beast Chicken Gyros Box", 15, 17.95, 269.25),
    ("The Athenian - Bermondsey", "Modifiers", "Gyros Sauce (Vegan)", 60, 0, 0),
    ("The Athenian - Bermondsey", "Sides - Meze", "Courgette Fritters - aka Greek \"Falafel\"", 14, 5.25, 73.5),
    ("The Athenian - Bermondsey", "Modifiers", "Athenian Sauce 2oz (Vegan)(Side)", 30, 0, 0),
    ("The Athenian - Bermondsey", "Sides - Meze", "Pita & Tzatziki", 3, 4.75, 14.25),
    ("The Athenian - Bermondsey", "Modifiers", "Gyros Sauce 2oz (Vegan)(Side)", 5, 0, 0),
    ("The Athenian - Bermondsey", "Drinks", "Diet Coke", 4, 2.75, 11),
    ("The Athenian - Bermondsey", "Sides - Meze", "Halloumi Fries", 6, 7.95, 47.7),
    ("The Athenian - Bermondsey", "Regular Gyros", "Regular Pork Gyros Wrap", 13, 9.95, 129.35),
    ("The Athenian - Bermondsey", "Light Gyros Wraps", "Light Mighty Vegan Gyros Wrap", 3, 8.25, 24.75),
    ("The Athenian - Bermondsey", "Modifiers", "Tzatziki (Dairy)", 106, 0, 0),
    ("The Athenian - Bermondsey", "Sides - Meze", "Oregano Fries", 37, 3.95, 146.15),
    ("The Athenian - Bermondsey", "Souvlaki & Gyros Boxes", "Mighty Vegan Gyros Box", 11, 15.25, 167.75),
    ("The Athenian - Bermondsey", "Modifiers", "Remove Tomatoes", 35, 0, 0),
    ("The Athenian - Bermondsey", "Meal Deals", "Gyros Meal for 1", 47, 15.95, 749.65),
    ("The Athenian - Bermondsey", "Modifiers", "Regular Grilled Halloumi Wrap", 9, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Sprite", 8, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Oregano Fries", 55, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Chilli Mayo (2oz) (Vegan) (Side)", 1, 2.5, 2.5),
    ("The Athenian - Bermondsey", "Modifiers", "Regular Chicken Gyros Wrap", 41, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Coke Zero", 25, 0, 0),
    ("Athenian - Broxbourne", "The Beast - Protein Gyros", "The Beast Halal Chicken Gyros Wrap", 2, 14.95, 29.9),
    ("Athenian - Broxbourne", "Modifiers", "Gyros Sauce", 23, 0, 0),
    ("Athenian - Broxbourne", "Sides - Meze", "Oregano Fries", 6, 3.95, 23.7),
    ("Athenian - Broxbourne", "Sides - Meze", "Halloumi Fries", 2, 7.95, 15.9),
    ("Athenian - Broxbourne", "Modifiers", "Tzatziki (Dairy)", 10, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Remove Onions", 41, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Add Extra Chicken", 17, 2.9, 49.3),
    ("The Athenian - Bermondsey", "Modifiers", "Remove Fries", 5, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Add Extra Halloumi", 17, 2.5, 42.5),
    ("The Athenian - Bermondsey", "Modifiers", "Fanta", 23, 0, 0),
    ("Athenian - Evesham", "Modifiers", "Coca-Cola", 5, 0, 0),
    ("Athenian - Evesham", "Modifiers", "Regular Grilled Halloumi Cheese Souvlaki Wrap", 3, 0, 0),
    ("Athenian - Evesham", "Light Gyros Wraps", "Light Halloumi Wrap", 1, 8.25, 8.25),
    ("Athenian - Colchester", "Meal Deals", "Gyros Meal for 2", 2, 30.5, 61),
    ("Athenian - Colchester", "Modifiers", "Oregano Fries", 12, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Grilled Halloumi  Box", 2, 3, 6),
    ("Athenian - Colchester", "Modifiers", "Athenian Sauce (Vegan)", 5, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Remove Tomatoes", 4, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Coca Cola Zero", 5, 0, 0),
    ("Athenian - Macclesfield", "Souvlaki & Gyros Boxes", "Mixed Gyros Box", 3, 15.25, 45.75),
    ("Athenian - Macclesfield", "Modifiers", "Gyros Sauce", 5, 0, 0),
    ("The Athenian - Bermondsey", "Regular Gyros", "Regular Chicken Gyros Wrap", 29, 9.95, 288.55),
    ("The Athenian - Bermondsey", "Plant Based Menu", "Regular Mighty Vegan Gyros Wrap", 14, 9.95, 139.3),
    ("The Athenian - Bermondsey", "Sweet Treats", "Vegan Salted Caramel Chocolate Brownie", 14, 4.95, 69.3),
    ("The Athenian - Bermondsey", "The Beast - Protein Gyros", "The Beast Pork Gyros Wrap", 5, 14.95, 74.75),
    ("Athenian - Colchester", "Meal Deals", "Gyros Meal for 1", 8, 15.95, 127.6),
    ("Athenian - Colchester", "Modifiers", "Halal Chicken Gyros Box", 2, 3, 6),
    ("Athenian - Colchester", "Modifiers", "Remove Lettuce", 1, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Remove Onions", 4, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Gyros Sauce", 8, 0, 0),
    ("Athenian - Evesham", "Souvlaki & Gyros Boxes", "Halal Chicken Gyros Box", 4, 15.25, 61),
    ("Athenian - Evesham", "Modifiers", "Gyros Sauce", 9, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Sparkling Water", 6, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Halloumi Fries", 13, 3, 39),
    ("The Athenian - Bermondsey", "Modifiers", "Tzatziki 2oz (Dairy)(Side)", 16, 0, 0),
    ("Athenian - Macclesfield", "Modifiers", "Add Extra Halloumi", 4, 2.5, 10),
    ("Athenian - Macclesfield", "Modifiers", "Tzatziki (Dairy)", 14, 0, 0),
    ("Athenian - Macclesfield", "Regular Gyros", "Regular Halal Chicken Gyros Wrap", 5, 9.95, 49.75),
    ("Athenian - Macclesfield", "Modifiers", "Remove Onions", 2, 0, 0),
    ("Athenian - Macclesfield", "Modifiers", "Remove Tomatoes", 4, 0, 0),
    ("Athenian - Macclesfield", "Sides - Meze", "Oregano Fries", 4, 3.95, 15.8),
    ("The Athenian - Bermondsey", "Sides - Meze", "Gyros Loaded Fries", 5, 7.5, 37.5),
    ("Athenian - Evesham", "Sweet Treats", "Vegan Belgian Chocolate Fudge Cake", 1, 5.35, 5.35),
    ("The Athenian - Bermondsey", "Souvlaki & Gyros Boxes", "Pork Gyros Box", 11, 15.25, 167.75),
    ("The Athenian - Bermondsey", "Sauces", "Gyros Sauce 2oz (Vegan)", 5, 1.5, 7.5),
    ("The Athenian - Bermondsey", "Sauces", "Tzatziki 2oz", 9, 1.5, 13.5),
    ("The Athenian - Bermondsey", "Sauces", "Athenian Sauce 2oz (Vegan)", 4, 1.5, 6),
    ("The Athenian - Bermondsey", "Modifiers", "Regular Mighty Vegan Gyros Wrap", 13, 0, 0),
    ("The Athenian - Bermondsey", "Sides - Meze", "Tomato Croquettes - Tomatokeftedes", 6, 5.25, 31.5),
    ("The Athenian - Bermondsey", "Regular Gyros", "Regular Grilled Halloumi Wrap", 18, 9.95, 179.1),
    ("Athenian - Broxbourne", "Regular Gyros", "Regular Grilled Halloumi Cheese Souvlaki Wrap", 5, 9.95, 49.75),
    ("The Athenian - Bermondsey", "Souvlaki & Gyros Boxes", "Halloumi Box", 4, 15.25, 61),
    ("Athenian - Evesham", "Sweet Treats", "Vegan Salted Caramel Chocolate Brownie", 2, 4.95, 9.9),
    ("Athenian - Evesham", "Drinks", "Coca Cola Zero", 1, 2.75, 2.75),
    ("Athenian - Evesham", "Sides - Meze", "Gyros Loaded Fries", 5, 7.5, 37.5),
    ("Athenian - Evesham", "Modifiers", "Athenian Sauce (Vegan)", 18, 0, 0),
    ("Athenian - Evesham", "The Beast - Protein Gyros", "The Beast Halal Chicken Gyros Wrap", 2, 14.95, 29.9),
    ("The Athenian - Bermondsey", "The Beast - Protein Gyros", "The Beast Pork Gyros Box", 6, 17.95, 107.7),
    ("The Athenian - Bermondsey", "Modifiers", "Regular Pork Gyros Wrap", 14, 0, 0),
    ("The Athenian - Bermondsey", "Light Gyros Wraps", "Light Halloumi Wrap", 1, 8.25, 8.25),
    ("The Athenian - Bermondsey", "Modifiers", "Remove Lettuce", 10, 0, 0),
    ("The Athenian - Bermondsey", "Drinks", "Sprite", 6, 2.75, 16.5),
    ("Athenian - Macclesfield", "Sides - Meze", "Pita & Tzatziki", 2, 4.75, 9.5),
    ("Athenian - Evesham", "Plant Based", "Mighty Vegan Gyros Box", 1, 15.25, 15.25),
    ("Athenian - Evesham", "Plant Based", "Mighty Vegan Gyros Wrap", 1, 9.95, 9.95),
    ("Athenian - Evesham", "Regular Gyros", "Regular Halal Chicken Gyros Wrap", 7, 9.95, 69.65),
    ("The Athenian - Bermondsey", "Modifiers", "Diet Coke", 15, 0, 0),
    ("Athenian - Evesham", "Modifiers", "Coca Cola Zero", 3, 0, 0),
    ("Athenian - Evesham", "Modifiers", "Regular Halal Chicken Gyros Wrap", 5, 0, 0),
    ("The Athenian - Bermondsey", "Drinks", "Fanta", 2, 2.75, 5.5),
    ("Athenian - Evesham", "Modifiers", "Halloumi Fries", 3, 3, 9),
    ("The Athenian - Bermondsey", "Meal Deals", "Gyros Meal for 2", 14, 30.5, 427),
    ("The Athenian - Bermondsey", "Modifiers", "Tomato Croquettes - Tomatokeftedes", 7, 2, 14),
    ("The Athenian - Bermondsey", "The Beast - Protein Gyros", "The Beast Chicken Gyros Wrap", 9, 14.95, 134.55),
    ("Athenian - Evesham", "Modifiers", "Pork Gyros Box", 1, 3, 3),
    ("Athenian - Broxbourne", "Meal Deals", "Gyros Meal for 1", 5, 15.95, 79.75),
    ("Athenian - Broxbourne", "Modifiers", "Regular Halal Chicken Gyros Wrap", 10, 0, 0),
    ("Athenian - Broxbourne", "Modifiers", "Add Extra Chicken", 1, 2.9, 2.9),
    ("Athenian - Broxbourne", "Modifiers", "Remove Tomatoes", 10, 0, 0),
    ("Athenian - Broxbourne", "Modifiers", "Remove Lettuce", 5, 0, 0),
    ("Athenian - Broxbourne", "Modifiers", "Athenian Sauce (Vegan)", 7, 0, 0),
    ("Athenian - Broxbourne", "Modifiers", "Oregano Fries", 9, 0, 0),
    ("Athenian - Broxbourne", "Modifiers", "Coca Cola Zero", 4, 0, 0),
    ("Athenian - Macclesfield", "Regular Gyros", "Regular Grilled Halloumi Cheese Souvlaki Wrap", 1, 9.95, 9.95),
    ("Athenian - Macclesfield", "Modifiers", "Athenian Sauce (Vegan)", 8, 0, 0),
    ("Athenian - Macclesfield", "Sides - Meze", "Halloumi Fries", 2, 7.95, 15.9),
    ("The Athenian - Bermondsey", "Modifiers", "Tzatziki 2oz (Dairy)(Side)", 4, 1.5, 6),
    ("Athenian - Macclesfield", "Souvlaki & Gyros Boxes", "Halal Chicken Gyros Box", 3, 15.25, 45.75),
    ("Athenian - Macclesfield", "Modifiers", "Add Extra Chicken", 2, 2.9, 5.8),
    ("Athenian - Macclesfield", "Modifiers", "Remove Fries", 1, 0, 0),
    ("Athenian - Macclesfield", "Regular Gyros", "Regular Pork Gyros Wrap", 1, 9.95, 9.95),
    ("Athenian - Macclesfield", "Modifiers", "Remove Fries", 1, 0, 0),
    ("Athenian - Macclesfield", "Drinks", "Fanta Orange", 1, 2.75, 2.75),
    ("Athenian - Broxbourne", "Modifiers", "Still Water", 1, 0, 0),
    ("The Athenian - Bermondsey", "Sweet Treats", "Vegan Belgian Chocolate Fudge Cake", 6, 5.4, 32.4),
    ("The Athenian - Bermondsey", "Modifiers", "Pork Gyros Box", 3, 3, 9),
    ("The Athenian - Bermondsey", "Modifiers", "Mighty Vegan Gyros Box", 3, 3, 9),
    ("Athenian - Colchester", "Modifiers", "Regular Halal Chicken Gyros Wrap", 4, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Still Water", 6, 0, 0),
    ("Athenian - Macclesfield", "Meal Deals", "Gyros Meal for 2", 2, 30.5, 61),
    ("Athenian - Macclesfield", "Modifiers", "Oregano Fries", 2, 0, 0),
    ("Athenian - Macclesfield", "Modifiers", "Regular Halal Chicken Gyros Wrap", 6, 0, 0),
    ("Athenian - Macclesfield", "Modifiers", "Sprite", 2, 0, 0),
    ("Athenian - Macclesfield", "Modifiers", "Fanta Orange", 2, 0, 0),
    ("Athenian - Macclesfield", "Modifiers", "Regular Pork Gyros Wrap", 3, 0, 0),
    ("Athenian - Macclesfield", "Modifiers", "Oregano Fries", 2, 0, 0),
    ("Athenian - Colchester", "The Beast - Protein Gyros", "The Beast Halal Chicken Gyros Box", 3, 17.95, 53.85),
    ("The Athenian - Bermondsey", "Modifiers", "Courgette Fritters - aka Greek \"Falafel\"", 4, 2, 8),
    ("The Athenian - Bermondsey", "Modifiers", "Chilli Mayo (2oz) (Vegan) (Side)", 2, 1, 2),
    ("Athenian - Broxbourne", "Meal Deals", "Gyros Meal for 2", 3, 30.5, 91.5),
    ("Athenian - Broxbourne", "Modifiers", "Remove Onions", 5, 0, 0),
    ("Athenian - Broxbourne", "Modifiers", "Sprite", 1, 0, 0),
    ("Athenian - Broxbourne", "Modifiers", "Fanta Orange", 3, 0, 0),
    ("Athenian - Evesham", "Light Gyros Wraps", "Light Halal Chicken Gyros Wrap", 3, 8.25, 24.75),
    ("Athenian - Evesham", "Modifiers", "Chili Mayo (Vegan)", 5, 1, 5),
    ("Athenian - Evesham", "Sides - Meze", "Oregano Fries", 3, 3.95, 11.85),
    ("Athenian - Broxbourne", "Regular Gyros", "Regular Halal Chicken Gyros Wrap", 13, 9.95, 129.35),
    ("Athenian - Broxbourne", "Modifiers", "Add Extra Halloumi", 4, 2.5, 10),
    ("Athenian - Broxbourne", "Drinks", "Coca-Cola", 3, 2.75, 8.25),
    ("Athenian - Broxbourne", "Sides - Meze", "Gyros Loaded Fries", 5, 7.5, 37.5),
    ("Athenian - Evesham", "Light Gyros Wraps", "Light Mighty Vegan Gyros Wrap", 2, 8.25, 16.5),
    ("The Athenian - Bermondsey", "Modifiers", "Athenian Sauce 2oz (Vegan)(Side)", 3, 1.5, 4.5),
    ("Athenian - Macclesfield", "Souvlaki & Gyros Boxes", "Mighty Vegan Gyros Box", 1, 15.25, 15.25),
    ("The Athenian - Bermondsey", "Light Gyros Wraps", "Light Chicken Gyros Wrap", 2, 8.25, 16.5),
    ("The Athenian - Bermondsey", "Modifiers", "Gyros Sauce 2oz (Vegan)(Side)", 4, 1.5, 6),
    ("Athenian - Colchester", "Souvlaki & Gyros Boxes", "Halal Chicken Gyros Box", 3, 15.25, 45.75),
    ("Athenian - Colchester", "Modifiers", "Tzatziki (Dairy)", 7, 0, 0),
    ("Athenian - Evesham", "Souvlaki & Gyros Boxes", "Mighty Vegan Gyros Box", 1, 15.25, 15.25),
    ("Athenian - Evesham", "Sides - Meze", "Halloumi Fries", 2, 7.95, 15.9),
    ("Athenian - Macclesfield", "Modifiers", "Athenian Sauce 2oz (Vegan)(Side)", 1, 1.4, 1.4),
    ("Athenian - Macclesfield", "Modifiers", "Chili Mayo (Vegan)", 1, 1, 1),
    ("Athenian - Broxbourne", "Souvlaki & Gyros Boxes", "Halal Chicken Gyros Box", 1, 15.25, 15.25),
    ("Athenian - Broxbourne", "Modifiers", "Chili Mayo (Vegan)", 3, 1, 3),
    ("Athenian - Broxbourne", "Modifiers", "Add Halloumi (Dairy)", 1, 2.5, 2.5),
    ("Athenian - Broxbourne", "Drinks", "Coca Cola Zero", 2, 2.75, 5.5),
    ("Athenian - Broxbourne", "Modifiers", "No Sauce", 4, 0, 0),
    ("Athenian - Macclesfield", "Light Gyros Wraps", "Light Halal Chicken Gyros Wrap", 1, 8.25, 8.25),
    ("Athenian - Macclesfield", "Light Gyros Wraps", "Light Pork Gyros Wrap", 2, 8.25, 16.5),
    ("Athenian - Colchester", "Plant Based", "Mighty Vegan Gyros Box", 3, 15.25, 45.75),
    ("Athenian - Colchester", "Modifiers", "Truffle Mayo (Vegan)", 1, 1, 1),
    ("Athenian - Evesham", "Modifiers", "Remove Tomatoes", 1, 0, 0),
    ("Athenian - Evesham", "Modifiers", "Remove Onions", 1, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Add Extra Halloumi", 3, 2.5, 7.5),
    ("Athenian - Colchester", "Modifiers", "Remove Tomatoes", 5, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Coca-Cola", 3, 0, 0),
    ("Athenian - Evesham", "Regular Gyros", "Regular Grilled Halloumi Cheese Souvlaki Wrap", 1, 9.95, 9.95),
    ("The Athenian - Bermondsey", "Drinks", "Coke Zero", 4, 2.75, 11),
    ("The Athenian - Bermondsey", "Sauces", "Chilli Mayo (2oz) (Vegan)", 1, 2.5, 2.5),
    ("Athenian - Colchester", "Modifiers", "Remove Fries", 2, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Add Extra Chicken", 4, 2.9, 11.6),
    ("Athenian - Colchester", "Modifiers", "No Sauce", 3, 0, 0),
    ("Athenian - Colchester", "Sweet Treats", "Vegan Salted Caramel Chocolate Brownie", 2, 4.95, 9.9),
    ("Athenian - Colchester", "Modifiers", "Regular Mighty Vegan Gyros Wrap", 2, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Diet Coke", 2, 0, 0),
    ("Athenian - Broxbourne", "The Beast - Protein Gyros", "The Beast Halal Chicken Gyros Box", 5, 17.95, 89.75),
    ("Athenian - Broxbourne", "Sauces", "Gyros Sauce", 1, 1.5, 1.5),
    ("Athenian - Macclesfield", "Meal Deals", "Gyros Meal for 1", 6, 15.95, 95.7),
    ("Athenian - Macclesfield", "Modifiers", "Oregano Fries", 5, 0, 0),
    ("Athenian - Macclesfield", "Modifiers", "Coca-Cola", 1, 0, 0),
    ("Athenian - Colchester", "Regular Gyros", "Regular Halal Chicken Gyros Wrap", 3, 9.95, 29.85),
    ("Athenian - Colchester", "Sides - Meze", "Halloumi Fries", 1, 7.95, 7.95),
    ("Athenian - Broxbourne", "Modifiers", "Diet Coke", 1, 0, 0),
    ("Athenian - Broxbourne", "Modifiers", "Halloumi Fries", 2, 3, 6),
    ("Athenian - Broxbourne", "Sides - Meze", "Pita & Tzatziki", 2, 4.75, 9.5),
    ("Athenian - Colchester", "Sides - Meze", "Pita & Tzatziki", 1, 4.75, 4.75),
    ("Athenian - Macclesfield", "Modifiers", "Coca Cola Zero", 5, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Chilli Mayo (Vegan)", 3, 1, 3),
    ("Athenian - Macclesfield", "Sweet Treats", "Vegan Salted Caramel Chocolate Brownie", 3, 4.95, 14.85),
    ("Athenian - Macclesfield", "Sides - Meze", "Sweet Potato Fries", 1, 5.25, 5.25),
    ("Athenian - Macclesfield", "Modifiers", "Truffle Mayo (Vegan)", 2, 1, 2),
    ("Athenian - Broxbourne", "NEW: Home Cooked Meals", "Moussaka", 1, 12.5, 12.5),
    ("Athenian - Colchester", "Modifiers", "Sprite", 1, 0, 0),
    ("Athenian - Colchester", "Sides - Meze", "Sweet Potato Fries", 1, 5.25, 5.25),
    ("Athenian - Macclesfield", "Plant Based", "Mighty Vegan Gyros Box", 1, 15.25, 15.25),
    ("The Athenian - Bermondsey", "Meal Deals", "Super Combo for 4", 2, 57.95, 115.9),
    ("Athenian - Macclesfield", "The Beast - Protein Gyros", "The Beast Halal Chicken Gyros Box", 1, 17.95, 17.95),
    ("Athenian - Macclesfield", "Modifiers", "Courgette Fritters", 1, 2, 2),
    ("Athenian - Macclesfield", "Drinks", "Sprite", 1, 2.75, 2.75),
    ("Athenian - Broxbourne", "Modifiers", "Regular Grilled Halloumi Cheese Souvlaki Wrap", 1, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Regular Grilled Halloumi Cheese Souvlaki Wrap", 2, 0, 0),
    ("Athenian - Colchester", "Modifiers", "Fanta Orange", 1, 0, 0),
    ("Athenian - Colchester", "Souvlaki & Gyros Boxes", "Mighty Vegan Gyros Box", 1, 15.25, 15.25),
    ("Athenian - Colchester", "Modifiers", "Chili Mayo (Vegan)", 2, 1, 2),
    ("Athenian - Colchester", "Drinks", "Coca-Cola", 1, 2.75, 2.75),
    ("Athenian - Colchester", "Drinks", "Sprite", 1, 2.75, 2.75),
    ("Athenian - Macclesfield", "Modifiers", "Mighty Vegan Gyros Box", 1, 3, 3),
    ("Athenian - Macclesfield", "Sauces", "Gyros Sauce", 1, 1.5, 1.5),
    ("Athenian - Colchester", "Modifiers", "Gyros Sauce 2oz (Vegan)(Side)", 1, 1.5, 1.5),
    ("Athenian - Broxbourne", "Modifiers", "Remove Fries", 1, 0, 0),
    ("Athenian - Broxbourne", "Modifiers", "Sparkling Water", 1, 0, 0),
    ("Athenian - Evesham", "Drinks", "Fanta Orange", 1, 2.75, 2.75),
    ("Athenian - Broxbourne", "Sweet Treats", "Vegan Belgian Chocolate Fudge Cake", 1, 5.35, 5.35),
    ("Athenian - Broxbourne", "Light Gyros Wraps", "Light Halal Chicken Gyros Wrap", 1, 8.25, 8.25),
    ("Athenian - Macclesfield", "Modifiers", "No Sauce", 1, 0, 0),
    ("The Athenian - Bermondsey", "Modifiers", "Add Halloumi (Dairy)", 1, 2.5, 2.5),
    ("Athenian - Evesham", "Meal Deals", "Gyros Meal for 2", 1, 30.5, 30.5),
    ("Athenian - Evesham", "Modifiers", "Oregano Fries", 1, 0, 0),
    ("Athenian - Evesham", "Modifiers", "Oregano Fries", 1, 0, 0),
    ("Athenian - Evesham", "Sides - Meze", "Pita & Tzatziki", 1, 4.75, 4.75),
    ("Athenian - Potters Bar", "Sides - Meze", "Gyros Loaded Fries", 1, 7.5, 7.5),
    ("Athenian - Potters Bar", "Modifiers", "Gyros Sauce", 6, 0, 0),
    ("Athenian - Potters Bar", "The Beast - Protein Gyros", "The Beast Halal Chicken Gyros Box", 3, 17.95, 53.85),
    ("Athenian - Potters Bar", "Modifiers", "Tzatziki (Dairy)", 9, 0, 0),
    ("Athenian - Lancaster", "Souvlaki & Gyros Boxes", "Halal Chicken Gyros Box", 6, 15.25, 91.5),
    ("Athenian - Lancaster", "Modifiers", "Gyros Sauce", 17, 0, 0),
    ("Athenian - Lancaster", "Light Gyros Wraps", "Light Halal Chicken Gyros Wrap", 7, 8.25, 57.75),
    ("Athenian - Lancaster", "Modifiers", "Remove Tomatoes", 2, 0, 0),
    ("Athenian - Lancaster", "Modifiers", "Remove Onions", 5, 0, 0),
    ("The Athenian (Huddersfield)", "Light Gyros Wraps", "Light Chicken Gyros Wrap", 1, 8.25, 8.25),
    ("The Athenian (Huddersfield)", "Modifiers", "Tzatziki (Dairy)", 10, 0, 0),
    ("Athenian - Dover", "Meal Deals", "Gyros Meal for 2", 5, 30.5, 152.5),
]


def test():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row

    # Load skip items
    SKIP_ITEMS = {
        "tzatziki (dairy)", "gyros sauce", "gyros sauce (vegan)",
        "athenian sauce (vegan)", "chilli mayo (vegan)", "chili mayo (vegan)",
        "truffle mayo (vegan)", "no sauce",
        "remove tomatoes", "remove onions", "remove lettuce", "remove fries",
        "coca-cola", "coca cola zero", "coke zero", "diet coke",
        "sprite", "fanta", "fanta orange", "sparkling water", "still water",
    }

    matched = []
    skipped_no_stock = []
    unmatched = []
    matched_no_recipe = []

    for row in DELIVEROO_DATA:
        site, category, item, qty, price, subtotal = row

        if item.lower() in SKIP_ITEMS:
            skipped_no_stock.append(item)
            continue

        # Check for meal deal wrappers
        item_lower = item.lower()
        if "gyros meal for" in item_lower or "super combo" in item_lower:
            skipped_no_stock.append(item)
            continue

        # Resolve alias
        alias = db.execute(
            "SELECT canonical_menu_item FROM menu_item_aliases "
            "WHERE LOWER(platform) = 'deliveroo' AND LOWER(platform_item_name) = LOWER(?)",
            (item,)
        ).fetchone()

        canonical = alias["canonical_menu_item"] if alias else item

        # Check menu item exists
        mi = db.execute(
            "SELECT id FROM menu_items WHERE LOWER(name) = LOWER(?)",
            (canonical,)
        ).fetchone()

        if not mi:
            unmatched.append((item, canonical, site))
            continue

        # Check recipe exists
        recipe = db.execute(
            "SELECT 1 FROM recipe_mappings WHERE menu_item_id = ?",
            (mi["id"],)
        ).fetchone()

        if not recipe:
            matched_no_recipe.append((item, canonical))
            continue

        # Resolve site
        site_alias = db.execute(
            "SELECT sales_name FROM site_aliases WHERE LOWER(stock_name) = LOWER(?)",
            (site,)
        ).fetchone()
        resolved_site = site_alias["sales_name"] if site_alias else site

        matched.append((resolved_site, canonical, qty))

    db.close()

    print("=" * 70)
    print(f"MATCHED (stock-relevant): {len(matched)} rows")
    print("=" * 70)

    # Aggregate by site and item
    from collections import defaultdict
    site_items = defaultdict(lambda: defaultdict(float))
    for site, item, qty in matched:
        site_items[site][item] += qty

    for site in sorted(site_items):
        print(f"\n  {site}:")
        for item, qty in sorted(site_items[site].items()):
            print(f"    {item}: {qty}")

    print(f"\n{'=' * 70}")
    print(f"SKIPPED (no stock impact): {len(skipped_no_stock)} rows")
    print("=" * 70)

    print(f"\n{'=' * 70}")
    print(f"MATCHED BUT NO RECIPE: {len(matched_no_recipe)} rows")
    print("=" * 70)
    for item, canonical in sorted(set(matched_no_recipe)):
        print(f"  {item} -> {canonical}")

    print(f"\n{'=' * 70}")
    print(f"UNMATCHED (need alias or menu item): {len(unmatched)} rows")
    print("=" * 70)
    seen = set()
    for item, canonical, site in sorted(unmatched):
        key = (item, canonical)
        if key not in seen:
            seen.add(key)
            print(f"  \"{item}\" -> tried \"{canonical}\" (from {site})")

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total rows:           {len(DELIVEROO_DATA)}")
    print(f"  Matched (stock):      {len(matched)}")
    print(f"  Skipped (no stock):   {len(skipped_no_stock)}")
    print(f"  No recipe:            {len(matched_no_recipe)}")
    print(f"  Unmatched:            {len(unmatched)}")


if __name__ == "__main__":
    test()
