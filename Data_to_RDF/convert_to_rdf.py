# convert_to_rdf.py - IMPROVED VERSION
from rdflib import Graph, Literal, RDF, RDFS, URIRef, Namespace
from rdflib.namespace import XSD
import json
from pathlib import Path
import re

SCHEMA = Namespace("https://schema.org/")
EX = Namespace("http://example.org/food/")
FOOD = Namespace("http://data.lirmm.fr/ontologies/food#")

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "knowledge_graph.ttl"

def parse_measure(measure_str: str) -> float:
    """Parse measurements to grams with improved conversions"""
    if not measure_str:
        return 30.0  # Small default for unknown measures
    
    measure_str = measure_str.lower().strip()
    
    # Handle special cases that should be very small amounts
    if any(word in measure_str for word in ['drizzle', 'splash', 'sprinkle', 'garnish', 'to taste', 'to serve', 'handful']):
        return 10.0  # Very small amount for garnishes/drizzles
    
    # Handle fractions
    if '/' in measure_str:
        # Convert fractions like "1/2" to decimal
        fraction_match = re.search(r'(\d+)/(\d+)', measure_str)
        if fraction_match:
            num = float(fraction_match.group(1))
            denom = float(fraction_match.group(2))
            amount = num / denom
            # Get unit after fraction
            unit_match = re.search(r'/\d+\s*(\w+)', measure_str)
            if unit_match:
                unit = unit_match.group(1)
            else:
                return amount * 120  # Assume cup for fractions
    
    # Try to extract number and unit
    match = re.match(r'(\d+\.?\d*)\s*(\w+)', measure_str)
    if not match:
        # Just a number without unit (e.g., "3" for 3 avocados)
        number_match = re.search(r'(\d+\.?\d*)', measure_str)
        if number_match:
            num = float(number_match.group(1))
            # Single-digit numbers are likely item counts (3 avocados, 2 onions, etc.)
            if num <= 10:
                return num * 100  # Average whole item = 100g
            # Large numbers without units are probably milliliters
            elif num >= 100:
                return min(num, 500)  # Cap at 500ml = 500g
            else:
                return num * 15  # Medium numbers = tablespoons
        return 30.0
    
    amount = float(match.group(1))
    unit = match.group(2)
    
    # Comprehensive conversion table (to grams)
    conversions = {
        # Weight
        'g': 1, 'gram': 1, 'grams': 1,
        'kg': 1000, 'kilogram': 1000, 'kilograms': 1000,
        'oz': 28.35, 'ounce': 28.35, 'ounces': 28.35,
        'lb': 453.6, 'lbs': 453.6, 'pound': 453.6, 'pounds': 453.6,
        
        # Volume (more conservative for liquids)
        'cup': 120, 'cups': 120,
        'tbsp': 15, 'tablespoon': 15, 'tablespoons': 15, 'tbs': 15, 'tb': 15,  # Added tbs, tb
        'tsp': 5, 'teaspoon': 5, 'teaspoons': 5, 'ts': 5,  # Added ts
        'ml': 1, 'milliliter': 1, 'milliliters': 1,
        'l': 1000, 'liter': 1000, 'liters': 1000,
        'fl': 30, 'floz': 30,
        
        # Count-based (more conservative)
        'clove': 3, 'cloves': 3,
        'pinch': 0.5, 'dash': 0.5,
        'slice': 15, 'slices': 15,
        'piece': 25, 'pieces': 25,
        'whole': 40,
        'small': 30, 'medium': 60, 'large': 100,
        'fillet': 120, 'fillets': 120,
        'breast': 150, 'breasts': 150,
    }
    
    result = amount * conversions.get(unit, 30)  # Default 30g if unknown
    
    # Cap maximum to prevent absurd values
    # A single ingredient should rarely exceed 500g in a recipe
    return min(result, 500)

def normalize_ingredient(name: str) -> str:
    """Normalize ingredient names for better matching"""
    # Remove parenthetical content
    name = re.sub(r'\s*\(.*?\)', '', name)
    # Remove special characters except spaces
    name = re.sub(r'[^a-zA-Z\s]', '', name.lower())
    # Remove common qualifiers
    qualifiers = ['fresh', 'frozen', 'dried', 'canned', 'chopped', 'sliced', 
                  'diced', 'minced', 'raw', 'cooked', 'whole', 'ground']
    words = name.split()
    words = [w for w in words if w not in qualifiers]
    return ' '.join(words).strip()

def find_best_usda_match(ing_norm: str, usda_lookup: dict) -> dict:
    """Find best USDA match with improved fuzzy matching"""
    # Direct match
    if ing_norm in usda_lookup:
        return usda_lookup[ing_norm]
    
    # Check if ingredient is contained in USDA key
    for usda_key, data in usda_lookup.items():
        if ing_norm in usda_key:
            return data
    
    # Check if USDA key is contained in ingredient
    for usda_key, data in usda_lookup.items():
        if usda_key in ing_norm:
            return data
    
    # Word-by-word matching (for multi-word ingredients)
    ing_words = set(ing_norm.split())
    best_match = None
    best_score = 0
    
    for usda_key, data in usda_lookup.items():
        usda_words = set(usda_key.split())
        # Count matching words
        matching_words = ing_words.intersection(usda_words)
        score = len(matching_words)
        if score > best_score:
            best_score = score
            best_match = data
    
    return best_match if best_score > 0 else None

def estimate_servings(meal_data: dict) -> int:
    """Estimate number of servings based on ingredient quantities"""
    # Count ingredients
    ingredient_count = sum(1 for i in range(1, 21) 
                          if meal_data.get(f"strIngredient{i}") 
                          and meal_data.get(f"strIngredient{i}").strip())
    
    # Look for serving hints in instructions
    instructions = meal_data.get("strInstructions", "").lower()
    
    # Check for explicit serving mentions
    import re
    
    # "divide between X plates/bowls/people"
    divide_match = re.search(r'divide.*?between\s+(\w+)\s+(?:plates|bowls|people|portions|servings)', instructions)
    if divide_match:
        number_word = divide_match.group(1)
        word_to_num = {'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'eight': 8}
        if number_word in word_to_num:
            return word_to_num[number_word]
        try:
            return int(number_word)
        except:
            pass
    
    # "serves X" or "X servings"
    serve_match = re.search(r'serves?\s+(\d+)', instructions)
    if serve_match:
        return int(serve_match.group(1))
    
    serve_match = re.search(r'(\d+)\s+servings?', instructions)
    if serve_match:
        return int(serve_match.group(1))
    
    serve_match = re.search(r'(\d+)\s+people', instructions)
    if serve_match:
        return int(serve_match.group(1))
    
    # Estimate based on ingredient count and typical portions
    if ingredient_count >= 12:
        return 4  # Complex recipes with many ingredients
    elif ingredient_count >= 8:
        return 3  # Medium-complex recipes
    elif ingredient_count >= 5:
        return 2  # Simple recipes
    
    return 2  # Default to 2 servings (safer than 1)

def convert():
    g = Graph()
    g.bind("schema", SCHEMA)
    g.bind("ex", EX)
    g.bind("food", FOOD)

    THEMEALDB_DIR = Path("fetched_data/themealdb")
    USDA_DIR = Path("fetched_data/usda")

    # Build USDA lookup
    usda_lookup = {}
    for file in USDA_DIR.glob("food_details_*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            desc = data.get("description", "").lower()
            norm = normalize_ingredient(desc)
            nutrients = {}
            for nutrient in data.get("foodNutrients", []):
                name = nutrient["nutrient"]["name"].lower()
                amount = nutrient.get("amount")
                unit = nutrient["nutrient"]["unitName"]
                if amount is not None:
                    nutrients[name] = (amount, unit)
            usda_lookup[norm] = {"fdc_id": data["fdcId"], "desc": desc, "nutrients": nutrients}
        except Exception as e:
            print(f"Error loading {file}: {e}")

    print(f"Loaded {len(usda_lookup)} USDA foods for linking.")

    # Collect and deduplicate meals
    all_meals = []
    for file in THEMEALDB_DIR.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            meals = data.get("meals", [])
            if meals:
                all_meals.extend(meals)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    # Deduplicate: keep version with most ingredients
    recipe_dict = {}
    for meal in all_meals:
        recipe_id = meal.get("idMeal")
        if not recipe_id:
            continue
        
        ingredient_count = sum(1 for i in range(1, 21) 
                              if meal.get(f"strIngredient{i}") 
                              and meal.get(f"strIngredient{i}").strip())
        
        # CRITICAL FIX: Skip versions with no ingredients (filter files are incomplete)
        if ingredient_count == 0:
            continue
        
        if recipe_id not in recipe_dict or ingredient_count > recipe_dict[recipe_id]["count"]:
            recipe_dict[recipe_id] = {"meal": meal, "count": ingredient_count}
    
    print(f"Found {len(all_meals)} total entries, deduplicated to {len(recipe_dict)} unique recipes")
    
    matched_ingredients = 0
    total_ingredients = 0
    
    # Process deduplicated recipes
    for recipe_id, recipe_data in recipe_dict.items():
        meal = recipe_data["meal"]
        try:
            recipe_uri = EX[f"recipe/{recipe_id}"]
            g.add((recipe_uri, RDF.type, SCHEMA.Recipe))
            g.add((recipe_uri, SCHEMA.name, Literal(meal.get("strMeal", "Unknown Meal"))))

            # Add properties
            if meal.get("strCategory"):
                g.add((recipe_uri, SCHEMA.recipeCategory, Literal(meal["strCategory"])))
            if meal.get("strArea"):
                g.add((recipe_uri, SCHEMA.recipeCuisine, Literal(meal["strArea"])))
            if meal.get("strTags"):
                for tag in meal["strTags"].split(","):
                    g.add((recipe_uri, SCHEMA.keywords, Literal(tag.strip())))
            if meal.get("strYoutube"):
                g.add((recipe_uri, SCHEMA.video, URIRef(meal["strYoutube"])))
            if meal.get("strSource"):
                g.add((recipe_uri, SCHEMA.url, URIRef(meal["strSource"])))
            if meal.get("strInstructions"):
                instr = meal["strInstructions"]
                g.add((recipe_uri, SCHEMA.recipeInstructions, 
                       Literal(instr[:500] + "..." if len(instr) > 500 else instr)))
            if meal.get("strMealThumb"):
                g.add((recipe_uri, SCHEMA.image, URIRef(meal["strMealThumb"])))

            # Estimate servings
            servings = estimate_servings(meal)
            g.add((recipe_uri, SCHEMA.recipeYield, Literal(servings, datatype=XSD.integer)))

            # Initialize aggregates
            total_calories = 0.0
            total_protein = 0.0
            total_fat = 0.0
            total_carbs = 0.0
            total_fiber = 0.0
            total_sugar = 0.0
            is_vegan = True
            is_vegetarian = True
            is_gluten_free = True

            # Process ingredients
            for i in range(1, 21):
                ing = meal.get(f"strIngredient{i}")
                measure = meal.get(f"strMeasure{i}")
                if not ing or not ing.strip():
                    continue
                
                total_ingredients += 1
                ing_norm = normalize_ingredient(ing)
                ing_uri = EX[f"ingredient/{ing_norm.replace(' ', '_')}"]
                g.add((ing_uri, RDF.type, FOOD.Ingredient))
                g.add((recipe_uri, SCHEMA.recipeIngredient, Literal(f"{measure or ''} {ing}".strip())))

                # Dietary checks
                non_vegan = ['egg', 'chicken', 'beef', 'pork', 'fish', 'milk', 'cheese', 
                            'butter', 'honey', 'gelatin', 'cream', 'yogurt', 'salmon']
                non_vegetarian = ['chicken', 'beef', 'pork', 'fish', 'gelatin', 'salmon', 
                                 'prawn', 'shrimp', 'meat', 'bacon']
                gluten_items = ['wheat', 'flour', 'bread', 'pasta', 'barley', 'semolina', 
                               'noodle', 'soy sauce']
                
                if any(x in ing_norm for x in non_vegan):
                    is_vegan = False
                if any(x in ing_norm for x in non_vegetarian):
                    is_vegetarian = False
                if any(x in ing_norm for x in gluten_items):
                    is_gluten_free = False

                # Find USDA match with improved algorithm
                usda_data = find_best_usda_match(ing_norm, usda_lookup)
                
                if not usda_data:
                    continue
                
                matched_ingredients += 1
                g.add((ing_uri, RDFS.label, Literal(usda_data["desc"])))
                g.add((ing_uri, SCHEMA.nutrition, EX[f"nutrition/{usda_data['fdc_id']}"]))

                nut = usda_data["nutrients"]
                grams = parse_measure(measure)
                scale = grams / 100.0  # USDA is per 100g

                if "energy" in nut:
                    total_calories += nut["energy"][0] * scale
                if "protein" in nut:
                    total_protein += nut["protein"][0] * scale
                if "total lipid (fat)" in nut:
                    total_fat += nut["total lipid (fat)"][0] * scale
                if "carbohydrate, by difference" in nut:
                    total_carbs += nut["carbohydrate, by difference"][0] * scale
                if "fiber, total dietary" in nut:
                    total_fiber += nut["fiber, total dietary"][0] * scale
                if "sugars, total including nlea" in nut:
                    total_sugar += nut["sugars, total including nlea"][0] * scale

            # Add TOTAL nutrition (entire recipe)
            nutrition_uri = EX[f"nutrition/{recipe_id}"]
            g.add((recipe_uri, SCHEMA.nutrition, nutrition_uri))
            g.add((nutrition_uri, RDF.type, SCHEMA.NutritionInformation))
            g.add((nutrition_uri, SCHEMA.servingSize, Literal(f"1/{servings} of recipe")))
            
            # Per-serving values
            per_serving_cal = round(total_calories / servings)
            per_serving_protein = round(total_protein / servings, 1)
            
            # Debug very high calorie recipes
            recipe_name = meal.get("strMeal", "Unknown")
            if per_serving_cal > 2000:
                print(f"  WARNING: {recipe_name} has {per_serving_cal} cal/serving ({servings} servings, {total_calories:.0f} total)")
                
                # Show which ingredients contributed most
                if per_serving_cal > 5000:
                    print(f"    Ingredients breakdown:")
                    for i in range(1, 21):
                        ing = meal.get(f"strIngredient{i}")
                        measure = meal.get(f"strMeasure{i}")
                        if ing and ing.strip():
                            grams = parse_measure(measure)
                            if grams > 200:  # Show ingredients over 200g
                                print(f"      - {measure:20s} {ing:30s} = {grams:.0f}g")
            
            g.add((nutrition_uri, SCHEMA.calories, Literal(per_serving_cal, datatype=XSD.float)))
            g.add((nutrition_uri, SCHEMA.proteinContent, Literal(per_serving_protein, datatype=XSD.float)))
            g.add((nutrition_uri, SCHEMA.fatContent, Literal(round(total_fat / servings, 1), datatype=XSD.float)))
            g.add((nutrition_uri, SCHEMA.carbohydrateContent, Literal(round(total_carbs / servings, 1), datatype=XSD.float)))
            g.add((nutrition_uri, SCHEMA.fiberContent, Literal(round(total_fiber / servings, 1), datatype=XSD.float)))
            g.add((nutrition_uri, SCHEMA.sugarContent, Literal(round(total_sugar / servings, 1), datatype=XSD.float)))

            # Dietary tags
            if is_vegan:
                g.add((recipe_uri, SCHEMA.recipeCategory, Literal("Vegan")))
            if is_vegetarian:
                g.add((recipe_uri, SCHEMA.recipeCategory, Literal("Vegetarian")))
            if is_gluten_free:
                g.add((recipe_uri, SCHEMA.recipeCategory, Literal("Gluten-Free")))

        except Exception as e:
            print(f"Error processing recipe {recipe_id}: {e}")

    match_rate = (matched_ingredients / total_ingredients * 100) if total_ingredients > 0 else 0
    print(f"\nMatched {matched_ingredients}/{total_ingredients} ingredients to USDA data ({match_rate:.1f}%)")
    print(f"Knowledge graph created with {len(g)} triples!")
    g.serialize(destination=OUTPUT_FILE, format="turtle")
    print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    convert()