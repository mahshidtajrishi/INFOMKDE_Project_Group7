"""
Script 1: Fetch Recipe Data from Spoonacular API
"""
from dotenv import load_dotenv
load_dotenv()

import requests
import json
import os

API_KEY = os.getenv("SPOONACULAR_API_KEY")
if not API_KEY:
    raise ValueError("SPOONACULAR_API_KEY not found in environment variables")


# How many recipes to fetch
NUMBER_OF_RECIPES = 15

def fetch_recipes(api_key, number=10):
    """Fetch recipes from Spoonacular API with full information."""
    print(f"Fetching {number} recipes from Spoonacular...")
    
    url = "https://api.spoonacular.com/recipes/complexSearch"
    
    params = {
        "apiKey": api_key,
        "number": number,
        "addRecipeInformation": True,
        "addRecipeNutrition": True,
        "fillIngredients": True,
        "instructionsRequired": True
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Successfully fetched {len(data.get('results', []))} recipes!")
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching data: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return None


def save_to_json(data, filename):
    """Save data to a JSON file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    filepath = os.path.join(data_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Data saved to: {filepath}")
    return filepath


def main():
    print("=" * 60)
    print("SPOONACULAR RECIPE DATA FETCHER")
    print("=" * 60)
    
    # Fetch recipes
    data = fetch_recipes(API_KEY, NUMBER_OF_RECIPES)
    
    if data:
        # Save raw data
        save_to_json(data, "spoonacular_recipes_raw.json")
        
        # Print summary
        print("\n" + "=" * 60)
        print("RECIPES FETCHED:")
        print("=" * 60)
        
        for i, recipe in enumerate(data.get('results', []), 1):
            title = recipe.get('title', 'Unknown')
            cuisines = ', '.join(recipe.get('cuisines', [])) or 'Not specified'
            time = recipe.get('readyInMinutes', '?')
            print(f"{i:2}. {title}")
            print(f"    Cuisine: {cuisines} | Time: {time} mins")
        
        print("\n✓ Next step: Run 'python convert_to_rdf.py' to create RDF triples!")


if __name__ == "__main__":
    main()
