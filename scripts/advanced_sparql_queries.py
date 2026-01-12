

from rdflib import Graph, Namespace
import os

RECIPE = Namespace("http://example.org/recipe/")
INGREDIENT = Namespace("http://example.org/ingredient/")
CUISINE = Namespace("http://example.org/cuisine/")


def load_graph():
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try enhanced ontology first, fall back to basic
    enhanced_path = os.path.join(script_dir, "..", "output", "recipes_with_ontology.ttl")
    basic_path = os.path.join(script_dir, "..", "output", "recipes.ttl")
    
    g = Graph()
    if os.path.exists(enhanced_path):
        g.parse(enhanced_path, format="turtle")
        print(f"Loaded enhanced ontology: {len(g)} triples")
    else:
        g.parse(basic_path, format="turtle")
        print(f"Loaded basic RDF: {len(g)} triples")
    
    return g


def run_query(graph, query_name, query, description=""):
   
    print("\n" + "=" * 80)
    print(f"QUERY: {query_name}")
    print("=" * 80)
    if description:
        print(f"Description: {description}")
    print(f"\nSPARQL:\n{query}")
    print("\nRESULTS:")
    print("-" * 80)
    
    try:
        results = graph.query(query)
        if len(results) == 0:
            print("  (No results)")
        else:
            for i, row in enumerate(results, 1):
                values = [str(v) if v else "NULL" for v in row]
                print(f"  {i}. {' | '.join(values)}")
        print(f"\n  → {len(results)} results")
    except Exception as e:
        print(f"  ERROR: {e}")


def main():
    print("\n" + "=" * 80)
    print("ADVANCED SPARQL QUERIES - INFOMKDE PROJECT")
    print("Demonstrating: Property Paths, Negation, Aggregates, Subqueries")
    print("=" * 80)
    
    g = load_graph()
    
    # ================================================================
    # AGGREGATES: COUNT, AVG, SUM, GROUP BY, HAVING
    # ================================================================
    
    run_query(g, "AGGREGATE 1: Count recipes per diet type",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?dietName (COUNT(?r) AS ?recipeCount)
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:hasDiet ?diet .
        ?diet rdfs:label ?dietName .
    }
    GROUP BY ?dietName
    ORDER BY DESC(?recipeCount)
    """,
    "Uses GROUP BY and COUNT aggregate")
    
    
    run_query(g, "AGGREGATE 2: Average calories per cuisine",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?cuisineName (AVG(?cal) AS ?avgCalories) (COUNT(?r) AS ?numRecipes)
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:hasCuisine ?cuisine .
        ?cuisine rdfs:label ?cuisineName .
        ?r recipe:hasNutrition ?n .
        ?n recipe:calories ?cal .
    }
    GROUP BY ?cuisineName
    HAVING (COUNT(?r) >= 1)
    ORDER BY ?avgCalories
    """,
    "Uses AVG, COUNT, GROUP BY, and HAVING")
    
    
    run_query(g, "AGGREGATE 3: Total and average protein per recipe",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT 
        (COUNT(?r) AS ?totalRecipes)
        (AVG(?protein) AS ?avgProtein)
        (MIN(?protein) AS ?minProtein)
        (MAX(?protein) AS ?maxProtein)
        (SUM(?protein) AS ?totalProtein)
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:hasNutrition ?n .
        ?n recipe:protein ?protein .
    }
    """,
    "Uses multiple aggregates: COUNT, AVG, MIN, MAX, SUM")
    
    
    run_query(g, "AGGREGATE 4: Count ingredients per recipe (sorted)",
    """
    PREFIX recipe: <http://example.org/recipe/>
    
    SELECT ?title (COUNT(?ing) AS ?ingredientCount)
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:hasIngredient ?ing .
    }
    GROUP BY ?r ?title
    ORDER BY DESC(?ingredientCount)
    LIMIT 10
    """,
    "Shows recipes with most ingredients")
    
    
    
    run_query(g, "NEGATION 1: Recipes WITHOUT any cuisine specified",
    """
    PREFIX recipe: <http://example.org/recipe/>
    
    SELECT ?title
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        FILTER NOT EXISTS { ?r recipe:hasCuisine ?cuisine }
    }
    ORDER BY ?title
    """,
    "Uses FILTER NOT EXISTS to find recipes missing cuisine data")
    
    
    run_query(g, "NEGATION 2: Non-vegan recipes (using MINUS)",
    """
    PREFIX recipe: <http://example.org/recipe/>
    
    SELECT ?title
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        MINUS { ?r recipe:hasDiet recipe:diet_vegan }
    }
    ORDER BY ?title
    """,
    "Uses MINUS operator for set difference")
    
    
    run_query(g, "NEGATION 3: Recipes that are gluten-free but NOT vegan",
    """
    PREFIX recipe: <http://example.org/recipe/>
    
    SELECT ?title
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:hasDiet recipe:diet_gluten_free .
        FILTER NOT EXISTS { ?r recipe:hasDiet recipe:diet_vegan }
    }
    ORDER BY ?title
    """,
    "Combines positive pattern with negation")
    
    
    run_query(g, "NEGATION 4: Ingredients not used in any recipe",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?ingredientName
    WHERE {
        ?ing a recipe:Ingredient .
        ?ing rdfs:label ?ingredientName .
        FILTER NOT EXISTS {
            ?recipe recipe:hasIngredient ?ing .
        }
    }
    LIMIT 20
    """,
    "Finds orphan ingredients (if any)")
    
    
    
    
    run_query(g, "OPTIONAL 1: Recipes with optional nutrition info",
    """
    PREFIX recipe: <http://example.org/recipe/>
    
    SELECT ?title ?calories ?protein
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        OPTIONAL {
            ?r recipe:hasNutrition ?n .
            ?n recipe:calories ?calories .
            ?n recipe:protein ?protein .
        }
    }
    ORDER BY ?title
    LIMIT 15
    """,
    "Uses OPTIONAL for left outer join")
    
    
    run_query(g, "OPTIONAL 2: Recipes with multiple optional fields",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?title ?cuisineName ?dietName ?time
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        OPTIONAL { 
            ?r recipe:hasCuisine ?cuisine .
            ?cuisine rdfs:label ?cuisineName .
        }
        OPTIONAL {
            ?r recipe:hasDiet ?diet .
            ?diet rdfs:label ?dietName .
        }
        OPTIONAL { ?r recipe:readyInMinutes ?time }
    }
    ORDER BY ?title
    LIMIT 10
    """,
    "Multiple OPTIONAL patterns")
    
    
   
    
    run_query(g, "PROPERTY PATH 1: All types of a recipe (using /)",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?title ?type
    WHERE {
        ?r recipe:title "Corn Avocado Salsa"^^<http://www.w3.org/2001/XMLSchema#string> .
        ?r rdf:type ?type .
    }
    """,
    "Shows all rdf:type values for a specific recipe")
    
    
    run_query(g, "PROPERTY PATH 2: Recipes connected through shared ingredients",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?title1 ?title2 ?sharedIngredient
    WHERE {
        ?r1 a recipe:Recipe .
        ?r1 recipe:title ?title1 .
        ?r2 a recipe:Recipe .
        ?r2 recipe:title ?title2 .
        ?r1 recipe:hasIngredient ?ing .
        ?r2 recipe:hasIngredient ?ing .
        ?ing rdfs:label ?sharedIngredient .
        FILTER (?r1 != ?r2)
        FILTER (STR(?title1) < STR(?title2))
    }
    ORDER BY ?sharedIngredient
    LIMIT 20
    """,
    "Finds recipe pairs that share ingredients")
    
    
    run_query(g, "PROPERTY PATH 3: Alternative paths (|)",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?title ?label
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r (recipe:hasCuisine | recipe:hasDiet) ?category .
        ?category rdfs:label ?label .
    }
    ORDER BY ?title
    LIMIT 20
    """,
    "Uses | for alternative property paths")
    
    
    run_query(g, "PROPERTY PATH 4: Inverse path (^)",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?ingredientName (COUNT(?r) AS ?usedInRecipes)
    WHERE {
        ?ing a recipe:Ingredient .
        ?ing rdfs:label ?ingredientName .
        ?ing ^recipe:hasIngredient ?r .
    }
    GROUP BY ?ing ?ingredientName
    ORDER BY DESC(?usedInRecipes)
    LIMIT 15
    """,
    "Uses ^ for inverse property path (hasIngredient reversed)")
    
    
    
    
    run_query(g, "SUBQUERY 1: Recipes with above-average calories",
    """
    PREFIX recipe: <http://example.org/recipe/>
    
    SELECT ?title ?calories
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:hasNutrition ?n .
        ?n recipe:calories ?calories .
        {
            SELECT (AVG(?c) AS ?avgCal)
            WHERE {
                ?rec recipe:hasNutrition ?nut .
                ?nut recipe:calories ?c .
            }
        }
        FILTER (?calories > ?avgCal)
    }
    ORDER BY DESC(?calories)
    """,
    "Uses subquery to calculate average, then filters")
    
    
    run_query(g, "SUBQUERY 2: Most popular ingredient",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?ingredientName ?count
    WHERE {
        {
            SELECT ?ing (COUNT(?r) AS ?count)
            WHERE {
                ?r recipe:hasIngredient ?ing .
            }
            GROUP BY ?ing
            ORDER BY DESC(?count)
            LIMIT 10
        }
        ?ing rdfs:label ?ingredientName .
    }
    ORDER BY DESC(?count)
    """,
    "Subquery finds top ingredients, outer query gets labels")
    
    
    
    
    run_query(g, "RECOMMENDATION 1: Similar recipes by shared ingredients",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?similarRecipe (COUNT(?sharedIng) AS ?sharedIngredients)
    WHERE {
        # Start with a specific recipe
        ?source recipe:title "Garlicky Kale"^^<http://www.w3.org/2001/XMLSchema#string> .
        ?source recipe:hasIngredient ?sharedIng .
        
        # Find other recipes with same ingredients
        ?similar recipe:hasIngredient ?sharedIng .
        ?similar recipe:title ?similarRecipe .
        
        FILTER (?source != ?similar)
    }
    GROUP BY ?similar ?similarRecipe
    ORDER BY DESC(?sharedIngredients)
    LIMIT 5
    """,
    "Content-based recommendation using ingredient overlap")
    
    
    run_query(g, "RECOMMENDATION 2: Healthy quick vegan meals",
    """
    PREFIX recipe: <http://example.org/recipe/>
    
    SELECT ?title ?time ?calories ?protein
    WHERE {
        ?r a recipe:Recipe .
        ?r recipe:title ?title .
        ?r recipe:readyInMinutes ?time .
        ?r recipe:hasDiet recipe:diet_vegan .
        ?r recipe:hasNutrition ?n .
        ?n recipe:calories ?calories .
        ?n recipe:protein ?protein .
        
        FILTER (?time <= 30)
        FILTER (?calories < 400)
    }
    ORDER BY ?time
    """,
    "Multi-criteria filtering for personalized recommendations")
    
    
    run_query(g, "RECOMMENDATION 3: Find substitutes (same cuisine, similar calories)",
    """
    PREFIX recipe: <http://example.org/recipe/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?alternative ?altCalories ?cuisineName
    WHERE {
        # Original recipe
        ?original recipe:title "Corn Avocado Salsa"^^<http://www.w3.org/2001/XMLSchema#string> .
        ?original recipe:hasCuisine ?cuisine .
        ?original recipe:hasNutrition ?origNut .
        ?origNut recipe:calories ?origCal .
        
        # Find alternatives in same cuisine
        ?alt recipe:hasCuisine ?cuisine .
        ?alt recipe:title ?alternative .
        ?alt recipe:hasNutrition ?altNut .
        ?altNut recipe:calories ?altCalories .
        ?cuisine rdfs:label ?cuisineName .
        
        # Similar calorie range (within 100 kcal)
        FILTER (?alt != ?original)
        FILTER (ABS(?altCalories - ?origCal) < 100)
    }
    ORDER BY ?altCalories
    """,
    "Finds recipe alternatives with similar nutritional profile")
    
    
  
    
    print("\n" + "=" * 80)
    print("CONSTRUCT QUERY: Generate similarity relationships")
    print("=" * 80)
    print("Description: Creates recipe:similarTo triples based on shared ingredients")
    
    construct_query = """
    PREFIX recipe: <http://example.org/recipe/>
    
    CONSTRUCT {
        ?r1 recipe:similarTo ?r2 .
    }
    WHERE {
        ?r1 a recipe:Recipe .
        ?r2 a recipe:Recipe .
        ?r1 recipe:hasIngredient ?ing .
        ?r2 recipe:hasIngredient ?ing .
        FILTER (?r1 != ?r2)
    }
    LIMIT 20
    """
    print(f"\nSPARQL:\n{construct_query}")
    
    try:
        result_graph = g.query(construct_query)
        print(f"\n  → CONSTRUCT would generate new similarity triples")
    except Exception as e:
        print(f"  Note: CONSTRUCT query demonstration (result: {e})")
    
    
    print("\n" + "=" * 80)
   
    print("=" * 80)
    


if __name__ == "__main__":
    main()
