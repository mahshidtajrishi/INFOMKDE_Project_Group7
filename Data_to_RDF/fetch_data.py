# fetch_data.py - IMPROVED with more ingredients
import requests
import json
import time
from pathlib import Path

THE_MEAL_DB_BASE = "https://www.themealdb.com/api/json/v1/1"
USDA_BASE = "https://api.nal.usda.gov/fdc/v1"
USDA_API_KEY = "Kg7O4cLC23aColD2W92d4ydbhE89Nx0pNShcvdKX"

BASE_DIR = Path("fetched_data")
THEMEALDB_DIR = BASE_DIR / "themealdb"
USDA_DIR = BASE_DIR / "usda"

THEMEALDB_DIR.mkdir(parents=True, exist_ok=True)
USDA_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT = 30
DELAY_USDA = 0.8  # Reduced since you have a real API key

def save_json(data, filepath: Path):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved: {filepath}")

def fetch_get(url, filepath: Path, params=None, retries=4):
    # Check if file already exists
    if filepath.exists():
        print(f"Already exists (skipping download): {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Corrupted JSON, re-downloading: {filepath}")

    # If not exists or corrupted, download
    print(f"Downloading: {filepath.name} from {url}")
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()
            save_json(data, filepath)
            return data
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    print(f"Failed to fetch {url}")
    return None

# TheMealDB functions
def fetch_themealdb_categories():
    return fetch_get(f"{THE_MEAL_DB_BASE}/categories.php", THEMEALDB_DIR / "all_categories.json")

def fetch_themealdb_ingredients_list():
    return fetch_get(f"{THE_MEAL_DB_BASE}/list.php?i=list", THEMEALDB_DIR / "ingredients_list.json")

def fetch_themealdb_random_meal():
    return fetch_get(f"{THE_MEAL_DB_BASE}/random.php", THEMEALDB_DIR / "random_meal.json")

def fetch_themealdb_search(term):
    safe = term.replace(" ", "_")
    return fetch_get(f"{THE_MEAL_DB_BASE}/search.php", THEMEALDB_DIR / f"search_{safe}.json", {"s": term})

def fetch_themealdb_by_ingredient(ing):
    safe = ing.replace(" ", "_")
    return fetch_get(f"{THE_MEAL_DB_BASE}/filter.php", THEMEALDB_DIR / f"filter_ingredient_{safe}.json", {"i": ing})

def fetch_themealdb_by_category(cat):
    safe = cat.replace(" ", "_")
    return fetch_get(f"{THE_MEAL_DB_BASE}/filter.php", THEMEALDB_DIR / f"filter_category_{safe}.json", {"c": cat})

# USDA functions
def usda_search(query, page=1):
    safe = query.replace(" ", "_").replace("/", "_")
    params = {
        "api_key": USDA_API_KEY,
        "query": query,
        "pageNumber": page,
        "pageSize": 50,
        "dataType": ["Foundation", "SR Legacy"]
    }
    return fetch_get(f"{USDA_BASE}/foods/search", USDA_DIR / f"search_{safe}_page{page}.json", params)

def usda_food_details(fdc_id):
    params = {"api_key": USDA_API_KEY}
    return fetch_get(f"{USDA_BASE}/food/{fdc_id}", USDA_DIR / f"food_details_{fdc_id}.json", params)

# Main fetch function
def fetch_useful_dataset():
    print("="*60)
    print("FETCHING THEMEALDB DATA")
    print("="*60)
    
    fetch_themealdb_categories()
    fetch_themealdb_ingredients_list()
    fetch_themealdb_random_meal()
    fetch_themealdb_search("pasta")
    fetch_themealdb_search("salmon")
    fetch_themealdb_search("chicken")
    fetch_themealdb_by_category("Vegetarian")
    fetch_themealdb_by_category("Seafood")

    print("\n" + "="*60)
    print("FETCHING USDA SEARCH DATA (Common Ingredients)")
    print("="*60)
    
    # Expanded list of common ingredients for better matching
    common_ingredients = [
        # Proteins
        "chicken breast", "salmon", "egg", "beef", "pork", "tofu", 
        "shrimp", "cod", "tuna", "turkey", "bacon",
        
        # Dairy
        "milk", "cheese", "butter", "yogurt", "cream", "mozzarella", 
        "parmesan", "cheddar",
        
        # Vegetables
        "tomato", "onion", "garlic", "carrot", "potato", "broccoli", 
        "spinach", "bell pepper", "cucumber", "lettuce", "mushroom",
        
        # Grains & Pasta
        "rice", "pasta", "bread", "flour", "oats", "noodles",
        
        # Legumes
        "beans", "lentils", "chickpeas",
        
        # Oils & Fats
        "olive oil", "vegetable oil", "coconut oil",
        
        # Herbs & Spices (these are low priority, fetch last)
        "basil", "parsley", "ginger",
        
        # Fruits
        "banana", "apple", "lemon", "avocado",
        
        # Condiments
        "soy sauce", "honey", "sugar", "salt"
    ]
    
    for ingredient in common_ingredients:
        usda_search(ingredient)
        time.sleep(DELAY_USDA)

    print("\n" + "="*60)
    print("FETCHING DETAILED USDA NUTRITION DATA")
    print("="*60)
    print("Extracting FDC IDs from search results and fetching details...\n")
    
    # Get FDC IDs from all search results
    fdc_ids_to_fetch = set()
    
    for search_file in USDA_DIR.glob("search_*.json"):
        try:
            with open(search_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                foods = data.get("foods", [])
                if foods:
                    # Get the first (most relevant) result
                    fdc_id = foods[0].get("fdcId")
                    if fdc_id:
                        fdc_ids_to_fetch.add(fdc_id)
        except Exception as e:
            print(f"Error reading {search_file}: {e}")
    
    print(f"Found {len(fdc_ids_to_fetch)} unique foods to fetch detailed data for...\n")
    
    # Fetch details for all collected IDs
    for idx, fdc_id in enumerate(sorted(fdc_ids_to_fetch), 1):
        details_file = USDA_DIR / f"food_details_{fdc_id}.json"
        if not details_file.exists():
            print(f"[{idx}/{len(fdc_ids_to_fetch)}] Fetching FDC ID: {fdc_id}")
            usda_food_details(fdc_id)
            time.sleep(DELAY_USDA)
        else:
            print(f"[{idx}/{len(fdc_ids_to_fetch)}] Already have FDC ID: {fdc_id}")
    
    # Count final results
    search_count = len(list(USDA_DIR.glob("search_*.json")))
    details_count = len(list(USDA_DIR.glob("food_details_*.json")))
    
    print("\n" + "="*60)
    print("FETCHING COMPLETE!")
    print("="*60)
    print(f"TheMealDB files: {len(list(THEMEALDB_DIR.glob('*.json')))}")
    print(f"USDA search files: {search_count}")
    print(f"USDA detail files: {details_count}")
    print(f"\nYou now have nutrition data for {details_count} ingredients!")
    print("\nNext step: python app.py convert")
    print("="*60)