from rdflib import Graph

g = Graph()
g.parse('../output/recipes_with_foodon.ttl', format='turtle')

query = """
PREFIX recipe: <http://example.org/recipe/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?recipe ?title ?ingName
WHERE {
    ?recipe a recipe:Recipe .
    ?recipe recipe:title ?title .
    ?recipe recipe:hasIngredient ?ing .
    ?ing rdfs:label ?ingName .
    FILTER (CONTAINS(LCASE(?ingName), "chicken"))
}
LIMIT 10
"""

print("Recipes with 'chicken' as ingredient:")
print("-" * 50)
count = 0
for row in g.query(query):
    print(f"{row.title} -> {row.ingName}")
    count += 1

print(f"\nFound {count} results")