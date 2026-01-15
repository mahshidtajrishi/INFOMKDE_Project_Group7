"""
PHASE 1: Simple Union Merge
Combines three recipe knowledge graphs (MealDB, RecipesNLG, Spoonacular) into one unified graph.
"""

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
from datetime import datetime
import os


# ==================== CONFIGURATION ====================

# Input files
MEALDB_TTL = 'output/knowledge_graph.ttl'
RECIPESNLG_TTL = 'recipesNLG/recipesNLG_knowledge_graph.ttl'
SPOONACULAR_TTL = 'spoonacular_data/recipes_spoonacular.ttl'

# Output file
OUTPUT_TTL = 'unified_recipes/phase1_union_merge_v1.ttl'

# Namespace definitions
FOOD = Namespace("http://data.lirmm.fr/ontologies/food#")
SCHEMA = Namespace("https://schema.org/")
SPOON = Namespace("http://example.org/vocab/spoonacular#")  # Fix for ns1
OWL = Namespace("http://www.w3.org/2002/07/owl#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
PROV = Namespace("http://www.w3.org/ns/prov#")


# ==================== MAIN MERGE FUNCTION ====================

def merge_graphs():
    """
    Merge all three TTL files into a single unified graph.
    """
    print("="*80)
    print("PHASE 1: SIMPLE UNION MERGE")
    print("="*80)
    print()

    # Initialize unified graph
    print("Initializing unified graph...")
    unified = Graph()

    # Bind namespaces
    unified.bind("food", FOOD)
    unified.bind("schema", SCHEMA)
    unified.bind("spoon", SPOON)  # Replace ns1 with spoon
    unified.bind("owl", OWL)
    unified.bind("dcterms", DCTERMS)
    unified.bind("prov", PROV)

    # Track statistics
    stats = {
        'mealdb': {'recipes': 0, 'triples': 0},
        'recipesnlg': {'recipes': 0, 'triples': 0},
        'spoonacular': {'recipes': 0, 'triples': 0},
        'total': {'recipes': 0, 'triples': 0}
    }

    # ===== Load MealDB =====
    print("\n[1/3] Loading MealDB graph...")
    try:
        mealdb = Graph()
        mealdb.parse(MEALDB_TTL, format='turtle')

        # Count recipes
        query = "PREFIX schema: <https://schema.org/> SELECT (COUNT(DISTINCT ?recipe) as ?count) WHERE { ?recipe a schema:Recipe}"
        result = list(mealdb.query(query))
        stats['mealdb']['recipes'] = int(result[0][0])
        stats['mealdb']['triples'] = len(mealdb)

        # Add to unified graph
        unified += mealdb

        print(f"  ✓ Loaded {stats['mealdb']['recipes']:,} recipes")
        print(f"  ✓ Loaded {stats['mealdb']['triples']:,} triples")

    except Exception as e:
        print(f"  ✗ Error loading MealDB")
        raise e

    # ===== Load RecipesNLG =====
    print("\n[2/3] Loading RecipesNLG graph...")
    try:
        recipesnlg = Graph()
        recipesnlg.parse(RECIPESNLG_TTL, format='turtle')

        # Count recipes
        query = "SELECT (COUNT(DISTINCT ?recipe) as ?count) WHERE { ?recipe a <http://data.lirmm.fr/ontologies/food#Recipe> }"
        result = list(recipesnlg.query(query))
        stats['recipesnlg']['recipes'] = int(result[0][0])
        stats['recipesnlg']['triples'] = len(recipesnlg)

        # Add to unified graph
        unified += recipesnlg

        print(f"  ✓ Loaded {stats['recipesnlg']['recipes']:,} recipes")
        print(f"  ✓ Loaded {stats['recipesnlg']['triples']:,} triples")

    except Exception as e:
        print(f"  ✗ Error loading RecipesNLG")
        raise e

    # ===== Load Spoonacular =====
    print("\n[3/3] Loading Spoonacular graph...")
    try:
        spoonacular = Graph()
        spoonacular.parse(SPOONACULAR_TTL, format='turtle')

        # Count recipes
        query = "SELECT (COUNT(DISTINCT ?recipe) as ?count) WHERE { ?recipe a <http://data.lirmm.fr/ontologies/food#Recipe>}"
        result = list(spoonacular.query(query))
        stats['spoonacular']['recipes'] = int(result[0][0])
        stats['spoonacular']['triples'] = len(spoonacular)

        # Add to unified graph (this will merge ns1 namespace)
        unified += spoonacular

        print(f"  ✓ Loaded {stats['spoonacular']['recipes']:,} recipes")
        print(f"  ✓ Loaded {stats['spoonacular']['triples']:,} triples")

    except Exception as e:
        print(f"  ✗ Error loading Spoonacular")
        raise e

    # ===== Add Metadata =====
    print("\n[4/4] Adding metadata...")

    ontology_uri = URIRef("http://example.org/unified-recipe-kg")
    unified.add((ontology_uri, RDF.type, OWL.Ontology))
    unified.add((ontology_uri, RDFS.label, Literal("Unified Recipe Knowledge Graph", lang="en")))
    unified.add((ontology_uri, RDFS.comment, Literal(
        "Merged knowledge graph combining recipes from MealDB, RecipesNLG, and Spoonacular datasets.",
        lang="en"
    )))
    unified.add((ontology_uri, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
    unified.add((ontology_uri, DCTERMS.creator, Literal("MSc Data Science Project", datatype=XSD.string)))

    # Calculate totals
    stats['total']['recipes'] = stats['mealdb']['recipes'] + stats['recipesnlg']['recipes'] + stats['spoonacular']['recipes']
    stats['total']['triples'] = len(unified)

    print(f"  ✓ Added ontology metadata")

    # ===== Serialize =====
    print("\n[5/5] Serializing unified graph...")
    try:
        unified.serialize(destination=OUTPUT_TTL, format='turtle')
        file_size = os.path.getsize(OUTPUT_TTL) / (1024 * 1024)  # MB
        print(f"  ✓ Saved to {OUTPUT_TTL}")
        print(f"  ✓ File size: {file_size:.2f} MB")
    except Exception as e:
        print(f"  ✗ Error serializing")
        raise e

    return unified, stats


def print_statistics(stats):
    """
    Print detailed statistics about the merged graph.
    """
    print("\n" + "="*80)
    print("MERGE STATISTICS")
    print("="*80)

    print("\nDataset Contributions:")
    print("-" * 80)
    print(f"  MealDB:       {stats['mealdb']['recipes']:>8,} recipes  |  {stats['mealdb']['triples']:>12,} triples")
    print(f"  RecipesNLG:   {stats['recipesnlg']['recipes']:>8,} recipes  |  {stats['recipesnlg']['triples']:>12,} triples")
    print(f"  Spoonacular:  {stats['spoonacular']['recipes']:>8,} recipes  |  {stats['spoonacular']['triples']:>12,} triples")
    print("-" * 80)
    print(f"  TOTAL:        {stats['total']['recipes']:>8,} recipes  |  {stats['total']['triples']:>12,} triples")

    print("\nGraph Composition:")
    print("-" * 80)
    mealdb_pct = (stats['mealdb']['recipes'] / stats['total']['recipes'] * 100) if stats['total']['recipes'] > 0 else 0
    recipesnlg_pct = (stats['recipesnlg']['recipes'] / stats['total']['recipes'] * 100) if stats['total']['recipes'] > 0 else 0
    spoonacular_pct = (stats['spoonacular']['recipes'] / stats['total']['recipes'] * 100) if stats['total']['recipes'] > 0 else 0

    print(f"  MealDB:       {mealdb_pct:>6.2f}% of recipes")
    print(f"  RecipesNLG:   {recipesnlg_pct:>6.2f}% of recipes")
    print(f"  Spoonacular:  {spoonacular_pct:>6.2f}% of recipes")

    print("\n" + "="*80)


def run_sample_queries(graph):
    """
    Run sample SPARQL queries to verify the merged graph.
    """
    print("\nSAMPLE QUERIES")
    print("="*80)

    # Query 1: Count ingredients
    print("\n[Query 1] Total unique ingredients:")
    query1 = """
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    SELECT (COUNT(DISTINCT ?ingredient) as ?count)
    WHERE {
        ?ingredient a food:Ingredient .
    }
    """
    result = list(graph.query(query1))
    if result:
        print(f"  Result: {int(result[0][0]):,} unique ingredients")

    # Query 2: Sample recipes from each dataset
    print("\n[Query 2] Sample recipes (5 from each source):")
    query2 = """
    PREFIX schema: <https://schema.org/>
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    SELECT DISTINCT ?recipe ?name
    WHERE {
        ?recipe a food:Recipe,
                schema:Recipe ;
                schema:name ?name .
    }
    LIMIT 15
    """
    results = graph.query(query2)
    for i, row in enumerate(results, 1):
        recipe_uri = str(row.recipe)
        name = str(row.name)
        # Determine source from URI pattern
        if 'recipe' in recipe_uri:
            source = "Unknown"
            if len(name) > 50:
                name = name[:47] + "..."
            print(f"  {i:2d}. {name}")

    # Query 3: Recipes with nutrition data
    print("\n[Query 3] Recipes with nutrition information:")
    query3 = """
    PREFIX schema: <https://schema.org/>
    SELECT (COUNT(DISTINCT ?recipe) as ?count)
    WHERE {
        ?recipe schema:nutrition ?nutrition .
    }
    """
    result = list(graph.query(query3))
    if result:
        print(f"  Result: {int(result[0][0]):,} recipes with nutrition data")

    print("\n" + "="*80)


# ==================== MAIN ====================

def main():
    start_time = datetime.now()

    # Merge graphs
    unified_graph, stats = merge_graphs()

    if unified_graph is None:
        print("\n✗ Merge failed!")
        return

    # Print statistics
    print_statistics(stats)

    # Run sample queries
    run_sample_queries(unified_graph)

    # Calculate execution time
    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "="*80)
    print("PHASE 1 COMPLETE!")
    print("="*80)
    print(f"\n  Execution time: {elapsed:.1f} seconds")
    print(f"  Output file: {OUTPUT_TTL}")
    print(f"\n  ✓ Unified graph ready for Phase 2 (Ingredient Linking)")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
