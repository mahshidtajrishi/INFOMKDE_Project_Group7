# diagnose_duplicates.py
from pyoxigraph import Store
from pathlib import Path

DB_PATH = Path("oxigraph_db")

def diagnose():
    store = Store(path=str(DB_PATH))
    
    # Check for duplicate nutrition URIs for Honey Teriyaki Salmon
    query = """
    PREFIX schema: <https://schema.org/>
    PREFIX ex: <http://example.org/food/>
    
    SELECT ?recipe ?name ?nutrition ?calories ?protein ?fat WHERE {
        ?recipe a schema:Recipe ;
                schema:name ?name ;
                schema:nutrition ?nutrition .
        ?nutrition schema:calories ?calories ;
                   schema:proteinContent ?protein ;
                   schema:fatContent ?fat .
        FILTER(CONTAINS(?name, "Honey Teriyaki Salmon"))
    } ORDER BY ?recipe ?calories
    """
    
    print("=== Nutrition triples for Honey Teriyaki Salmon ===\n")
    results = list(store.query(query))
    
    if not results:
        print("No results found!")
        return
    
    for row in results:
        recipe = row['recipe'].value
        name = row['name'].value
        nutrition = row['nutrition'].value
        calories = row['calories'].value
        protein = row['protein'].value
        fat = row['fat'].value
        
        print(f"Recipe URI: {recipe}")
        print(f"Name: {name}")
        print(f"Nutrition URI: {nutrition}")
        print(f"Calories: {calories}, Protein: {protein}, Fat: {fat}")
        print("-" * 80)
    
    print(f"\nTotal rows returned: {len(results)}")
    
    # Count distinct recipes
    count_query = """
    PREFIX schema: <https://schema.org/>
    SELECT (COUNT(DISTINCT ?recipe) AS ?count) WHERE {
        ?recipe a schema:Recipe ;
                schema:name ?name .
        FILTER(CONTAINS(?name, "Honey Teriyaki Salmon"))
    }
    """
    count_result = list(store.query(count_query))
    print(f"Distinct recipe URIs: {count_result[0]['count'].value}")
    
    # Check how many nutrition URIs exist per recipe
    nutrition_count_query = """
    PREFIX schema: <https://schema.org/>
    SELECT ?recipe (COUNT(?nutrition) AS ?nut_count) WHERE {
        ?recipe a schema:Recipe ;
                schema:name ?name ;
                schema:nutrition ?nutrition .
        FILTER(CONTAINS(?name, "Honey Teriyaki Salmon"))
    } GROUP BY ?recipe
    """
    nut_counts = list(store.query(nutrition_count_query))
    print(f"\nNutrition URIs per recipe:")
    for row in nut_counts:
        print(f"  {row['recipe'].value}: {row['nut_count'].value} nutrition URIs")

if __name__ == "__main__":
    diagnose()