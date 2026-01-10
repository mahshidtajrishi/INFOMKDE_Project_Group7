#!/usr/bin/env python3
# show_data_structure.py - Complete data structure analysis
from pathlib import Path
import json

def truncate_text(text, max_len=100):
    """Truncate text for display"""
    if not text:
        return ""
    text = str(text)
    return text[:max_len] + "..." if len(text) > max_len else text

print("=" * 100)
print("COMPLETE THEMEALDB DATA STRUCTURE ANALYSIS")
print("=" * 100)

themealdb_files = sorted(Path('fetched_data/themealdb').glob('*.json'))
print(f"\nTotal TheMealDB files: {len(themealdb_files)}\n")

for f in themealdb_files:
    print(f"\n{'='*100}")
    print(f"FILE: {f.name}")
    print("="*100)
    
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
        
        # Show top-level structure
        print(f"Top-level keys: {list(data.keys())}")
        
        if 'meals' in data:
            meals = data['meals']
            if meals and len(meals) > 0:
                print(f"Number of meals: {len(meals)}")
                
                # Show first meal structure
                meal = meals[0]
                print(f"\nFirst meal:")
                print(f"  - ID: {meal.get('idMeal')}")
                print(f"  - Name: {meal.get('strMeal')}")
                print(f"  - Category: {meal.get('strCategory')}")
                print(f"  - Area: {meal.get('strArea')}")
                
                # Show all ingredient/measure pairs
                print(f"\n  Ingredients (showing all non-empty):")
                for i in range(1, 21):
                    ing = meal.get(f'strIngredient{i}')
                    measure = meal.get(f'strMeasure{i}')
                    if ing and ing.strip():
                        print(f"    {i:2d}. '{measure}' -> '{ing}'")
                
                # Show instructions preview
                instructions = meal.get('strInstructions', '')
                print(f"\n  Instructions ({len(instructions)} chars): {truncate_text(instructions, 150)}")
                
            else:
                print("No meals found in this file")
        
        elif 'categories' in data:
            categories = data['categories']
            print(f"Number of categories: {len(categories)}")
            if categories:
                print(f"Sample category: {categories[0]}")
        
        elif 'meals' in data and data['meals'] is None:
            print("meals field is null (no results)")
        
        else:
            print(f"Unexpected structure: {data}")
            
    except Exception as e:
        print(f"ERROR reading file: {e}")

print("\n\n" + "=" * 100)
print("COMPLETE USDA DATA STRUCTURE ANALYSIS")
print("=" * 100)

# First show search files
usda_search_files = sorted(Path('fetched_data/usda').glob('search_*.json'))
print(f"\nTotal USDA search files: {len(usda_search_files)}")

print("\n" + "-"*100)
print("USDA SEARCH FILES (showing first 3 as examples)")
print("-"*100)

for f in usda_search_files[:3]:
    print(f"\nFILE: {f.name}")
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
        print(f"  Top-level keys: {list(data.keys())}")
        
        if 'foods' in data:
            foods = data['foods']
            print(f"  Number of foods: {len(foods)}")
            if foods:
                food = foods[0]
                print(f"  First food:")
                print(f"    - FDC ID: {food.get('fdcId')}")
                print(f"    - Description: {truncate_text(food.get('description'))}")
                print(f"    - Data Type: {food.get('dataType')}")
                
    except Exception as e:
        print(f"  ERROR: {e}")

# Now show detail files
usda_detail_files = sorted(Path('fetched_data/usda').glob('food_details_*.json'))
print(f"\n\nTotal USDA detail files: {len(usda_detail_files)}")

print("\n" + "-"*100)
print("USDA DETAIL FILES (showing first 5 as examples)")
print("-"*100)

for f in usda_detail_files[:5]:
    print(f"\nFILE: {f.name}")
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
        print(f"  FDC ID: {data.get('fdcId')}")
        print(f"  Description: {truncate_text(data.get('description'), 80)}")
        print(f"  Data Type: {data.get('dataType')}")
        
        food_cat = data.get('foodCategory', {})
        if food_cat:
            print(f"  Category: {food_cat.get('description')}")
        
        nutrients = data.get('foodNutrients', [])
        print(f"  Total nutrients: {len(nutrients)}")
        
        # Show key nutrients
        key_nutrients = ['Energy', 'Protein', 'Total lipid (fat)', 'Carbohydrate, by difference']
        print(f"  Key nutrients:")
        for n in nutrients[:10]:  # Check first 10
            nutrient_name = n.get('nutrient', {}).get('name', '')
            if any(key in nutrient_name for key in key_nutrients):
                amount = n.get('amount', 0)
                unit = n.get('nutrient', {}).get('unitName', '')
                print(f"    - {nutrient_name}: {amount} {unit}")
                
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n\n" + "=" * 100)
print("PROBLEM RECIPES - DETAILED ANALYSIS")
print("=" * 100)

problem_recipes = ['Salmon Avocado Salad', 'Salmon noodle soup', 'Salmon Prawn Risotto']

for recipe_name in problem_recipes:
    print(f"\n{'='*100}")
    print(f"RECIPE: {recipe_name}")
    print("="*100)
    
    found = False
    for f in Path('fetched_data/themealdb').glob('*.json'):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            meals = data.get('meals', [])
            for m in meals:
                if m.get('strMeal') == recipe_name:
                    if not found:
                        print(f"Found in: {f.name}")
                        print(f"Recipe ID: {m.get('idMeal')}")
                        print(f"Category: {m.get('strCategory')}")
                        print(f"Area: {m.get('strArea')}")
                        
                        print("\nAll ingredients with measures:")
                        for i in range(1, 21):
                            ing = m.get(f'strIngredient{i}')
                            measure = m.get(f'strMeasure{i}')
                            if ing and ing.strip():
                                print(f"  {i:2d}. Measure: '{measure:30s}' | Ingredient: '{ing}'")
                        
                        instructions = m.get('strInstructions', '')
                        print(f"\nInstructions ({len(instructions)} chars):")
                        print(instructions[:400] + "..." if len(instructions) > 400 else instructions)
                        
                        found = True
                        break
        except:
            pass
    
    if not found:
        print(f"Recipe '{recipe_name}' not found!")

print("\n\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
print(f"TheMealDB files: {len(themealdb_files)}")
print(f"USDA search files: {len(usda_search_files)}")
print(f"USDA detail files: {len(usda_detail_files)}")
print("\nData structure analysis complete!")