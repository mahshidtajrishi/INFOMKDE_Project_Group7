
import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

# Spoonacular API endpoints
BASE_URL = "https://api.spoonacular.com"


def fetch_recipes_by_query(query, number=10, offset=0):
    url = f"{BASE_URL}/recipes/complexSearch"
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "query": query,
        "number": number,
        "offset": offset,
        "addRecipeInformation": True,
        "addRecipeNutrition": True,
        "fillIngredients": True,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json().get("results", [])
        elif response.status_code == 402:
            print(f"  ⚠ API quota exceeded!")
            return []
        else:
            print(f"  Error {response.status_code}: {response.text[:100]}")
            return []
    except Exception as e:
        print(f"  Error: {e}")
        return []


def fetch_random_recipes(number=10):
    url = f"{BASE_URL}/recipes/random"
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "number": number,
        "addRecipeInformation": True,
        "addRecipeNutrition": True,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json().get("recipes", [])
        else:
            print(f"  Error {response.status_code}")
            return []
    except Exception as e:
        print(f"  Error: {e}")
        return []


def fetch_recipes_by_cuisine(cuisine, number=10):
    url = f"{BASE_URL}/recipes/complexSearch"
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "cuisine": cuisine,
        "number": number,
        "addRecipeInformation": True,
        "addRecipeNutrition": True,
        "fillIngredients": True,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            return []
    except Exception as e:
        print(f"  Error: {e}")
        return []


def fetch_recipes_by_diet(diet, number=10):
    url = f"{BASE_URL}/recipes/complexSearch"
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "diet": diet,
        "number": number,
        "addRecipeInformation": True,
        "addRecipeNutrition": True,
        "fillIngredients": True,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            return []
    except Exception as e:
        print(f"  Error: {e}")
        return []


def main():
    print("=" * 70)
    print("FETCHING 100+ RECIPES FROM SPOONACULAR")
    print("Scaling up your Knowledge Graph!")
    print("=" * 70)
    
    # Check API key
    if not SPOONACULAR_API_KEY:
        print("\n ERROR: SPOONACULAR_API_KEY not found in .env file!")
        return
    
    print(f"\nAPI Key found: {SPOONACULAR_API_KEY[:10]}...")
    
    all_recipes = []
    seen_ids = set()
    
    # Strategy 1: Fetch by different cuisines
    cuisines = ["Italian", "Mexican", "Indian", "Chinese", "Japanese", 
                "Thai", "Mediterranean", "American", "French", "Greek"]
    
    print("\n" + "-" * 70)
    print("Fetching by cuisine...")
    print("-" * 70)
    
    for cuisine in cuisines:
        print(f"  Fetching {cuisine} recipes...", end=" ")
        recipes = fetch_recipes_by_cuisine(cuisine, number=8)
        new_count = 0
        for r in recipes:
            if r.get("id") not in seen_ids:
                seen_ids.add(r.get("id"))
                all_recipes.append(r)
                new_count += 1
        print(f"Got {new_count} new recipes")
        time.sleep(0.5)  # Rate limiting
    
    print(f"\nTotal after cuisines: {len(all_recipes)} recipes")
    
    # Strategy 2: Fetch by diet types
    diets = ["vegetarian", "vegan", "gluten free", "ketogenic", "paleo"]
    
    print("\n" + "-" * 70)
    print("Fetching by diet type...")
    print("-" * 70)
    
    for diet in diets:
        print(f"  Fetching {diet} recipes...", end=" ")
        recipes = fetch_recipes_by_diet(diet, number=8)
        new_count = 0
        for r in recipes:
            if r.get("id") not in seen_ids:
                seen_ids.add(r.get("id"))
                all_recipes.append(r)
                new_count += 1
        print(f"Got {new_count} new recipes")
        time.sleep(0.5)
    
    print(f"\nTotal after diets: {len(all_recipes)} recipes")
    
    # Strategy 3: Fetch by popular search queries
    queries = ["chicken", "pasta", "salad", "soup", "curry", 
               "stir fry", "breakfast", "dessert", "smoothie", "sandwich"]
    
    print("\n" + "-" * 70)
    print("Fetching by search queries...")
    print("-" * 70)
    
    for query in queries:
        print(f"  Fetching '{query}' recipes...", end=" ")
        recipes = fetch_recipes_by_query(query, number=8)
        new_count = 0
        for r in recipes:
            if r.get("id") not in seen_ids:
                seen_ids.add(r.get("id"))
                all_recipes.append(r)
                new_count += 1
        print(f"Got {new_count} new recipes")
        time.sleep(0.5)
    
    print(f"\nTotal after queries: {len(all_recipes)} recipes")
    
    # Strategy 4: Random recipes to fill in
    if len(all_recipes) < 100:
        remaining = 100 - len(all_recipes)
        print(f"\n" + "-" * 70)
        print(f"Fetching {remaining} random recipes to reach 100...")
        print("-" * 70)
        
        # Fetch in batches of 10
        while len(all_recipes) < 100:
            recipes = fetch_random_recipes(number=10)
            for r in recipes:
                if r.get("id") not in seen_ids:
                    seen_ids.add(r.get("id"))
                    all_recipes.append(r)
                    if len(all_recipes) >= 100:
                        break
            print(f"  Progress: {len(all_recipes)} recipes")
            time.sleep(0.5)
    
    # Save all recipes
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "..", "data", "all_recipes.json")
    
    print(f"\n" + "=" * 70)
    print("SAVING RECIPES")
    print("=" * 70)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_recipes, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(all_recipes)} recipes to: {output_path}")
    
    # Print statistics
    print(f"\n" + "=" * 70)
    print("RECIPE STATISTICS")
    print("=" * 70)
    
    # Count cuisines
    cuisine_counts = {}
    for r in all_recipes:
        for cuisine in r.get("cuisines", ["Unknown"]):
            cuisine_counts[cuisine] = cuisine_counts.get(cuisine, 0) + 1
    
    print("\nCuisines represented:")
    for cuisine, count in sorted(cuisine_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {cuisine}: {count}")
    
    # Count diets
    diet_counts = {}
    for r in all_recipes:
        for diet in r.get("diets", []):
            diet_counts[diet] = diet_counts.get(diet, 0) + 1
    
    print("\nDiets represented:")
    for diet, count in sorted(diet_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {diet}: {count}")
    
    # Count ingredients
    all_ingredients = set()
    for r in all_recipes:
        for ing in r.get("extendedIngredients", []):
            all_ingredients.add(ing.get("name", "").lower())
    
    print(f"\nUnique ingredients: {len(all_ingredients)}")
    
    # Estimate triples
    estimated_triples = len(all_recipes) * 100  # Rough estimate
    print(f"\nEstimated triples after conversion: ~{estimated_triples:,}")
    
    print(f"\n" + "=" * 70)
    print("DATA FETCH COMPLETE!")
    print("=" * 70)
  


if __name__ == "__main__":
    main()