from rdflib import Graph, Namespace
import os

# Namespaces
RECIPE = Namespace("http://example.org/recipe/")
INGREDIENT = Namespace("http://example.org/ingredient/")
CUISINE = Namespace("http://example.org/cuisine/")

def load_graph():
   
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ttl_path = os.path.join(script_dir, "..", "output", "recipes.ttl")
    
    print(f"Loading RDF data from: {ttl_path}")
    g = Graph()
    g.parse(ttl_path, format="turtle")
    print(f"✓ Loaded {len(g)} triples\n")
    return g


def run_query(graph, query_name, query):
   
    print("=" * 70)
    print(f"QUERY: {query_name}")
    print("=" * 70)
    print(f"SPARQL:\n{query}\n")
    print("RESULTS:")
    print("-" * 70)
    
    results = graph.query(query)
    
    if len(results) == 0:
        print("  (No results found)")
    else:
        for i, row in enumerate(results, 1):
            # Format each result nicely
            values = [str(val) for val in row]
            print(f"  {i}. {' | '.join(values)}")
    
    print(f"\n  → Found {len(results)} results\n")
    return results


def main():
    print("\n" + "=" * 70)
    print("SPARQL QUERY RUNNER FOR RECIPE KNOWLEDGE GRAPH")
    print("=" * 70 + "\n")
    
    # Load the RDF graph
    g = load_graph()
    
    # 1
    query1 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?title ?servings ?time
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        OPTIONAL { ?r recipe:servings ?servings }
        OPTIONAL { ?r recipe:readyInMinutes ?time }
    }
    ORDER BY ?title
    """
    run_query(g, "List All Recipes (with servings and cook time)", query1)
    
   # 2
    query2 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?title
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:hasDiet recipe:diet_vegan .
    }
    ORDER BY ?title
    """
    run_query(g, "Find All VEGAN Recipes", query2)
    
    # 3
    query3 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?title
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:hasDiet recipe:diet_gluten_free .
    }
    ORDER BY ?title
    """
    run_query(g, "Find All GLUTEN-FREE Recipes", query3)
    
    # 4
    query4 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?title ?time
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:readyInMinutes ?time .
        FILTER (?time < 30)
    }
    ORDER BY ?time
    """
    run_query(g, "Find Quick Recipes (under 30 minutes)", query4)
    
    # 5
    query5 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX cuisine: <http://example.org/cuisine/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?title ?cuisineName
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:hasCuisine ?cuisine .
        ?cuisine rdfs:label ?cuisineName .
    }
    ORDER BY ?cuisineName ?title
    """
    run_query(g, "Find Recipes by Cuisine", query5)
    
    # 6
    query6 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?ingredientName
    WHERE {
        ?ing a recipe:Ingredient .
        ?ing rdfs:label ?ingredientName .
    }
    ORDER BY ?ingredientName
    LIMIT 30
    """
    run_query(g, "List Unique Ingredients (first 30)", query6)
    
    # 7
    query7 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX ingredient: <http://example.org/ingredient/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?title
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:hasIngredient ?ing .
        ?ing rdfs:label ?ingName .
        FILTER (CONTAINS(LCASE(?ingName), "garlic"))
    }
    ORDER BY ?title
    """
    run_query(g, "Find Recipes Containing GARLIC", query7)
    
    # 8
    query8 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?title ?calories
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:hasNutrition ?n .
        ?n recipe:calories ?calories .
    }
    ORDER BY ?calories
    """
    run_query(g, "Find Recipes with Calorie Counts (sorted low to high)", query8)
    
    # 9
    query9 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?title ?calories
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:hasNutrition ?n .
        ?n recipe:calories ?calories .
        FILTER (?calories < 300)
    }
    ORDER BY ?calories
    """
    run_query(g, "Find LOW-CALORIE Recipes (under 300 kcal)", query9)
    
    # 10
    query10 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?dietName (COUNT(?r) as ?count)
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:hasDiet ?diet .
        ?diet rdfs:label ?dietName .
    }
    GROUP BY ?dietName
    ORDER BY DESC(?count)
    """
    run_query(g, "Count Recipes by Diet Type", query10)
    
    # 11
    query11 = """
    PREFIX recipe: <http://example.org/recipe/>
    
    SELECT ?title ?time
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:readyInMinutes ?time .
        ?r recipe:hasDiet recipe:diet_vegan .
        FILTER (?time < 30)
    }
    ORDER BY ?time
    """
    run_query(g, "Find QUICK VEGAN Recipes (under 30 min)", query11)
    
    # 12
    query12 = """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?title ?protein ?calories
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:hasNutrition ?n .
        ?n recipe:calories ?calories .
        ?n recipe:protein ?protein .
        FILTER (?calories < 500 && ?protein > 15)
    }
    ORDER BY DESC(?protein)
    """
    run_query(g, "RECOMMENDATION: High Protein (>15g), Low Calorie (<500)", query12)
    
    print("\n" + "=" * 70)
   
    print("=" * 70)
    print("ALL QUERIES COMPLETE!")

if __name__ == "__main__":
    main()