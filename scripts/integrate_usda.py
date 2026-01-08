import requests
import time
import re
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
import os
import json
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

USDA_API_KEY = os.getenv("USDA_API_KEY")  # Get API key from environment variable
if not USDA_API_KEY:
    raise ValueError("USDA_API_KEY not found in .env file")


# Namespaces
RECIPE = Namespace("http://example.org/recipe/")
INGREDIENT = Namespace("http://example.org/ingredient/")
USDA = Namespace("http://example.org/usda/")
DBPEDIA = Namespace("http://dbpedia.org/resource/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")


def clean_ingredient_name(name):
    """Clean ingredient name for better API matching."""
    name = name.lower().strip()
    
    # Remove common prefixes/suffixes
    patterns_to_remove = [
        r'^\d+[\d./]*\s*',       # Numbers at start
        r'\s*\(.*?\)',           # Parentheses content
        r'\s*,.*$',              # Everything after comma
        r'^(fresh|dried|ground|chopped|minced|diced|sliced|whole|raw|cooked)\s+',
        r'\s+(fresh|dried|ground|chopped|minced|diced|sliced|whole|raw|cooked)$',
        r'^(a|an|the)\s+',
        r'\s+\*\d+$',            # *1, *2 suffixes
        r'^optional:\s*',
        r'^additional\s+',
        r'\s+to\s+taste$',
        r'\s+or\s+.*$',
        r'^\d+\s*(oz|ounce|lb|pound|cup|tbsp|tsp|g|gram|kg|ml|l)\s+',
        r'\s+for\s+.*$',
    ]
    
    for pattern in patterns_to_remove:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    return name.strip()


def search_usda_food(ingredient_name, api_key):
    """
    Search USDA FoodData Central for an ingredient.
    Returns food data if found, None otherwise.
    """
    clean_name = clean_ingredient_name(ingredient_name)
    if not clean_name or len(clean_name) < 2:
        return None
    
    # USDA FoodData Central API
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    
    params = {
        "api_key": api_key,
        "query": clean_name,
        "dataType": ["Foundation", "SR Legacy"],  # Most reliable nutrition data
        "pageSize": 5
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            if "foods" in data and data["foods"]:
                # Find best match - prefer exact matches
                for food in data["foods"]:
                    food_desc = food.get("description", "").lower()
                    
                    # Check if it's a good match
                    if clean_name in food_desc or food_desc in clean_name:
                        return food
                
                # If no exact match, return first result
                return data["foods"][0]
                
        elif response.status_code == 403:
            print("  ⚠ API key invalid or rate limited")
            return None
            
    except Exception as e:
        print(f"  Error searching USDA: {e}")
    
    return None


def get_nutrient_value(food_data, nutrient_name):
    """Extract a specific nutrient value from USDA food data."""
    nutrients = food_data.get("foodNutrients", [])
    
    for nutrient in nutrients:
        name = nutrient.get("nutrientName", "").lower()
        if nutrient_name.lower() in name:
            return {
                "value": nutrient.get("value"),
                "unit": nutrient.get("unitName", "")
            }
    return None


def add_usda_nutrition_to_graph(g, ingredient_uri, food_data):
    """
    Add USDA nutritional data to an ingredient in the graph.
    """
    if not food_data:
        return 0
    
    triples_added = 0
    fdc_id = food_data.get("fdcId")
    
    # Add USDA food ID link
    if fdc_id:
        usda_uri = URIRef(f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{fdc_id}/nutrients")
        g.add((ingredient_uri, OWL.sameAs, usda_uri))
        g.add((ingredient_uri, USDA.fdcId, Literal(fdc_id, datatype=XSD.integer)))
        triples_added += 2
    
    # Add USDA description
    description = food_data.get("description")
    if description:
        g.add((ingredient_uri, USDA.usdaDescription, Literal(description, lang="en")))
        triples_added += 1
    
    # Create a detailed nutrition node
    nutrition_node = BNode()
    g.add((ingredient_uri, USDA.hasDetailedNutrition, nutrition_node))
    g.add((nutrition_node, RDF.type, USDA.DetailedNutritionInfo))
    triples_added += 2
    
    # Key nutrients to extract
    nutrients_to_add = [
        ("Energy", "energy", "kcal"),
        ("Protein", "protein", "g"),
        ("Total lipid (fat)", "totalFat", "g"),
        ("Carbohydrate, by difference", "carbohydrates", "g"),
        ("Fiber, total dietary", "fiber", "g"),
        ("Sugars, total", "sugars", "g"),
        ("Calcium", "calcium", "mg"),
        ("Iron", "iron", "mg"),
        ("Magnesium", "magnesium", "mg"),
        ("Phosphorus", "phosphorus", "mg"),
        ("Potassium", "potassium", "mg"),
        ("Sodium", "sodium", "mg"),
        ("Zinc", "zinc", "mg"),
        ("Vitamin C", "vitaminC", "mg"),
        ("Vitamin A", "vitaminA", "IU"),
        ("Vitamin B-6", "vitaminB6", "mg"),
        ("Vitamin B-12", "vitaminB12", "mcg"),
        ("Vitamin D", "vitaminD", "IU"),
        ("Vitamin E", "vitaminE", "mg"),
        ("Vitamin K", "vitaminK", "mcg"),
        ("Folate", "folate", "mcg"),
        ("Thiamin", "thiamin", "mg"),
        ("Riboflavin", "riboflavin", "mg"),
        ("Niacin", "niacin", "mg"),
        ("Cholesterol", "cholesterol", "mg"),
        ("Fatty acids, total saturated", "saturatedFat", "g"),
        ("Fatty acids, total monounsaturated", "monounsaturatedFat", "g"),
        ("Fatty acids, total polyunsaturated", "polyunsaturatedFat", "g"),
    ]
    
    for usda_name, prop_name, unit in nutrients_to_add:
        nutrient = get_nutrient_value(food_data, usda_name)
        if nutrient and nutrient["value"] is not None:
            prop = USDA[prop_name]
            value = nutrient["value"]
            g.add((nutrition_node, prop, Literal(value, datatype=XSD.float)))
            triples_added += 1
    
    return triples_added


def define_usda_ontology(g):
    """Add USDA ontology definitions to the graph."""
    
    # Define the DetailedNutritionInfo class
    g.add((USDA.DetailedNutritionInfo, RDF.type, OWL.Class))
    g.add((USDA.DetailedNutritionInfo, RDFS.label, Literal("Detailed Nutrition Information", lang="en")))
    g.add((USDA.DetailedNutritionInfo, RDFS.comment, Literal(
        "Detailed nutritional information from USDA FoodData Central, including vitamins and minerals.", lang="en")))
    
    # Define properties
    properties = [
        ("fdcId", "USDA FDC ID", "Unique identifier in USDA FoodData Central"),
        ("usdaDescription", "USDA Description", "Official USDA food description"),
        ("hasDetailedNutrition", "has detailed nutrition", "Links to detailed USDA nutrition data"),
        ("energy", "Energy", "Energy content in kcal per 100g"),
        ("protein", "Protein", "Protein content in grams per 100g"),
        ("totalFat", "Total Fat", "Total fat content in grams per 100g"),
        ("carbohydrates", "Carbohydrates", "Carbohydrate content in grams per 100g"),
        ("fiber", "Dietary Fiber", "Dietary fiber in grams per 100g"),
        ("sugars", "Sugars", "Total sugars in grams per 100g"),
        ("calcium", "Calcium", "Calcium in mg per 100g"),
        ("iron", "Iron", "Iron in mg per 100g"),
        ("magnesium", "Magnesium", "Magnesium in mg per 100g"),
        ("phosphorus", "Phosphorus", "Phosphorus in mg per 100g"),
        ("potassium", "Potassium", "Potassium in mg per 100g"),
        ("sodium", "Sodium", "Sodium in mg per 100g"),
        ("zinc", "Zinc", "Zinc in mg per 100g"),
        ("vitaminC", "Vitamin C", "Vitamin C in mg per 100g"),
        ("vitaminA", "Vitamin A", "Vitamin A in IU per 100g"),
        ("vitaminB6", "Vitamin B-6", "Vitamin B-6 in mg per 100g"),
        ("vitaminB12", "Vitamin B-12", "Vitamin B-12 in mcg per 100g"),
        ("vitaminD", "Vitamin D", "Vitamin D in IU per 100g"),
        ("vitaminE", "Vitamin E", "Vitamin E in mg per 100g"),
        ("vitaminK", "Vitamin K", "Vitamin K in mcg per 100g"),
        ("folate", "Folate", "Folate in mcg per 100g"),
        ("thiamin", "Thiamin", "Thiamin (B1) in mg per 100g"),
        ("riboflavin", "Riboflavin", "Riboflavin (B2) in mg per 100g"),
        ("niacin", "Niacin", "Niacin (B3) in mg per 100g"),
        ("cholesterol", "Cholesterol", "Cholesterol in mg per 100g"),
        ("saturatedFat", "Saturated Fat", "Saturated fat in grams per 100g"),
        ("monounsaturatedFat", "Monounsaturated Fat", "Monounsaturated fat in grams per 100g"),
        ("polyunsaturatedFat", "Polyunsaturated Fat", "Polyunsaturated fat in grams per 100g"),
    ]
    
    for prop_name, label, comment in properties:
        prop = USDA[prop_name]
        g.add((prop, RDF.type, OWL.DatatypeProperty))
        g.add((prop, RDFS.label, Literal(label, lang="en")))
        g.add((prop, RDFS.comment, Literal(comment, lang="en")))
    
    # hasDetailedNutrition is an ObjectProperty
    g.add((USDA.hasDetailedNutrition, RDF.type, OWL.ObjectProperty))
    
    return g


def main():
    print("=" * 70)
    print("USDA FOODDATA CENTRAL INTEGRATION")
    print("Adding Detailed Nutrition Data to Ingredients")
    print("=" * 70)
    
    # Check API key
    if USDA_API_KEY == "YOUR_API_KEY_HERE":
        print("\n⚠️  ERROR: You need to set your USDA API key!")
        print("1. Get a free key at: https://fdc.nal.usda.gov/api-key-signup.html")
        print("2. Open this file and replace 'YOUR_API_KEY_HERE' with your key")
        print("3. Run this script again")
        return
    
    # Load the graph
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try to load the integrated file first (with DBpedia links)
    integrated_path = os.path.join(script_dir, "..", "output", "recipes_integrated.ttl")
    ontology_path = os.path.join(script_dir, "..", "output", "recipes_with_ontology.ttl")
    output_path = os.path.join(script_dir, "..", "output", "recipes_with_usda.ttl")
    
    if os.path.exists(integrated_path):
        input_path = integrated_path
        print(f"\nLoading integrated RDF (with DBpedia links): {input_path}")
    else:
        input_path = ontology_path
        print(f"\nLoading RDF from: {input_path}")
    
    g = Graph()
    g.parse(input_path, format="turtle")
    original_count = len(g)
    print(f"Loaded {original_count} triples")
    
    # Add USDA ontology definitions
    print("\nAdding USDA ontology definitions...")
    g = define_usda_ontology(g)
    
    # Find all ingredients
    print("\nFinding ingredients...")
    ingredients = {}
    
    for ing in g.subjects(RDF.type, RECIPE.Ingredient):
        labels = list(g.objects(ing, RDFS.label))
        if labels:
            label = str(labels[0])
            ingredients[ing] = label
    
    print(f"Found {len(ingredients)} unique ingredients")
    
    # Search USDA for each ingredient
    print("\n" + "-" * 70)
    print("Searching USDA FoodData Central...")
    print("-" * 70)
    
    usda_matches = 0
    total_nutrition_triples = 0
    processed = 0
    
    # Process ingredients (with rate limiting)
    for ing_uri, label in list(ingredients.items())[:50]:  # Limit to 50 to avoid rate limits
        processed += 1
        clean_label = clean_ingredient_name(label)
        
        if len(clean_label) < 2:
            continue
        
        # Search USDA
        food_data = search_usda_food(clean_label, USDA_API_KEY)
        
        if food_data:
            triples = add_usda_nutrition_to_graph(g, ing_uri, food_data)
            if triples > 0:
                usda_matches += 1
                total_nutrition_triples += triples
                print(f"  ✓ {clean_label} → {food_data.get('description', 'Unknown')[:50]}... ({triples} nutrients)")
        
        # Progress update
        if processed % 10 == 0:
            print(f"\n  Progress: {processed}/{min(len(ingredients), 50)} ingredients processed...")
            print(f"  Matches so far: {usda_matches}\n")
        
        # Rate limiting - USDA allows 1000 requests/hour
        time.sleep(0.5)
    
    # Bind namespaces
    g.bind("recipe", RECIPE)
    g.bind("ingredient", INGREDIENT)
    g.bind("usda", USDA)
    g.bind("dbpedia", DBPEDIA)
    g.bind("wikidata", WIKIDATA)
    g.bind("owl", OWL)
    
    # Save enhanced graph
    print(f"\nSaving to: {output_path}")
    g.serialize(destination=output_path, format="turtle")
    
    new_count = len(g)
    added = new_count - original_count
    
    # Print summary
    print("\n" + "=" * 70)
    print("USDA INTEGRATION SUMMARY")
    print("=" * 70)
    print(f"Original triples:          {original_count}")
    print(f"New triples:               {new_count}")
    print(f"Triples added:             {added}")
    print(f"")
    print(f"Ingredients processed:     {processed}")
    print(f"USDA matches found:        {usda_matches}")
    print(f"Nutrition triples added:   {total_nutrition_triples}")
    print(f"")
    print(f"✓ Enhanced RDF saved to: {output_path}")
    
    # Show example queries
    print("\n" + "=" * 70)
    
    print("=" * 70)
   
   
if __name__ == "__main__":
    main()
