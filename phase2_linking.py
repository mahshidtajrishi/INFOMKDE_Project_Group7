"""
PHASE 2: Ingredient Linking
Creates owl:sameAs links between equivalent ingredients across the three datasets.
"""

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, SKOS
from datetime import datetime
from collections import defaultdict
from phase1_merge import OUTPUT_TTL as INPUT_TTL
import re


# ==================== CONFIGURATION ====================

# Input file (from Phase 1)
# INPUT_TTL = 'unified_recipes_v1.ttl'

# Output files
OUTPUT_TTL = 'unified_recipes/unified_recipes_v2_linked.ttl'
MAPPINGS_TTL = 'unified_recipes/ingredient_mappings.ttl'

# Namespace definitions
FOOD = Namespace("http://data.lirmm.fr/ontologies/food#")
INGREDIENT = Namespace("http://example.org/food/ingredient/")
DBPEDIA = Namespace("http://dbpedia.org/resource/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
PROV = Namespace("http://www.w3.org/ns/prov#")


# ==================== UTILITY FUNCTIONS ====================

def normalize_label(label):
    """
    Normalize ingredient label for comparison.
    """
    # Convert to lowercase
    text = str(label).lower().strip()

    # Remove spaces and special characters
    text = re.sub(r'[^a-z0-9]', '', text)

    return text


def extract_ingredients_by_source(graph):
    """
    Extract all ingredients from the graph, grouped by source.

    Returns:
        dict: {
            'local': [(uri, label, normalized), ...],
            'dbpedia': [(uri, label, normalized), ...],
            'wikidata': [(uri, label, normalized), ...],
            'obo': [(uri, label, normalized), ...]
        }
    """
    print("\nExtracting ingredients from unified graph...")

    ingredients = {
        'local': [],      # example.org/food/ingredient/*
        'dbpedia': [],    # dbpedia.org/resource/*
        'wikidata': [],   # wikidata.org/entity/*
        'obo': []         # purl.obolibrary.org/obo/*
    }

    # Query for all ingredients with labels
    query = """
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?ingredient ?label
    WHERE {
        ?ingredient a food:Ingredient .
        OPTIONAL { ?ingredient rdfs:label ?label }
    }
    """

    results = graph.query(query)

    for row in results:
        uri = str(row.ingredient)
        label = str(row.label) if row.label else ""

        # Skip if no label
        if not label:
            continue

        normalized = normalize_label(label)

        # Categorize by URI pattern
        if 'example.org/food/ingredient' in uri:
            ingredients['local'].append((uri, label, normalized))
        elif 'dbpedia.org' in uri:
            ingredients['dbpedia'].append((uri, label, normalized))
        elif 'wikidata.org' in uri:
            ingredients['wikidata'].append((uri, label, normalized))
        elif 'purl.obolibrary.org/obo' in uri:
            ingredients['obo'].append((uri, label, normalized))

    print(f"  Local ingredients:   {len(ingredients['local']):>6,}")
    print(f"  DBpedia ingredients: {len(ingredients['dbpedia']):>6,}")
    print(f"  Wikidata ingredients:{len(ingredients['wikidata']):>6,}")
    print(f"  OBO ingredients:     {len(ingredients['obo']):>6,}")

    return ingredients


def find_exact_matches(ingredients):
    """
    Find exact matches between local and external ingredients.

    Returns:
        list: [(local_uri, external_uri, confidence, match_type), ...]
    """
    print("\nFinding exact matches...")

    matches = []

    # Build lookup dictionaries for fast matching
    local_by_normalized = defaultdict(list)
    for uri, label, normalized in ingredients['local']:
        local_by_normalized[normalized].append((uri, label))

    # Match against DBpedia
    for uri, label, normalized in ingredients['dbpedia']:
        if normalized in local_by_normalized:
            for local_uri, local_label in local_by_normalized[normalized]:
                matches.append((
                    local_uri,
                    uri,
                    1.0,  # confidence
                    'exact_match',
                    f'"{local_label}" ↔ "{label}"'
                ))

    # Match against Wikidata
    for uri, label, normalized in ingredients['wikidata']:
        if normalized in local_by_normalized:
            for local_uri, local_label in local_by_normalized[normalized]:
                matches.append((
                    local_uri,
                    uri,
                    1.0,
                    'exact_match',
                    f'"{local_label}" ↔ "{label}"'
                ))

    # Match against OBO
    for uri, label, normalized in ingredients['obo']:
        if normalized in local_by_normalized:
            for local_uri, local_label in local_by_normalized[normalized]:
                matches.append((
                    local_uri,
                    uri,
                    1.0,
                    'exact_match',
                    f'"{local_label}" ↔ "{label}"'
                ))

    print(f"  Found {len(matches):,} exact matches")

    return matches


def find_fuzzy_matches(ingredients, threshold=0.8):
    """
    Find fuzzy matches using Levenshtein distance.

    Returns:
        list: [(local_uri, external_uri, confidence, match_type, description), ...]
    """
    from Levenshtein import distance as levenshtein_distance
    
    matches = []
    checked_pairs = set()
    
    # Combine external sources
    external = ingredients['dbpedia'] + ingredients['wikidata'] + ingredients['obo']
    
    for local_uri, local_label, local_norm in ingredients['local']:
        for ext_uri, ext_label, ext_norm in external:
            pair = tuple(sorted([local_uri, ext_uri]))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)
            
            # Calculate similarity
            dist = levenshtein_distance(local_norm, ext_norm)
            max_len = max(len(local_norm), len(ext_norm))
            if max_len == 0:
                continue
            similarity = 1.0 - (dist / max_len)
            
            if similarity >= threshold:
                matches.append((
                    local_uri,
                    ext_uri,
                    similarity,
                    'fuzzy_levenshtein',
                    f'"{local_label}" ↔ "{ext_label}"'
                ))
    
    print(f"  Found {len(matches):,} fuzzy matches")
    return matches


def create_mapping_graph(matches):
    """
    Create a separate graph with all ingredient mappings.

    Returns:
        Graph: RDF graph with owl:sameAs triples
    """
    print("\nCreating mapping graph...")

    mapping_graph = Graph()

    # Bind namespaces
    mapping_graph.bind("owl", OWL)
    mapping_graph.bind("skos", SKOS)
    mapping_graph.bind("prov", PROV)
    mapping_graph.bind("food", FOOD)

    # Add metadata
    mapping_uri = URIRef("http://example.org/ingredient-mappings")
    mapping_graph.add((mapping_uri, RDF.type, OWL.Ontology))
    mapping_graph.add((mapping_uri, RDFS.label, Literal("Ingredient Mappings", lang="en")))
    mapping_graph.add((mapping_uri, RDFS.comment, Literal(
        "Ingredient alignment mappings between local and external knowledge bases.",
        lang="en"
    )))
    mapping_graph.add((mapping_uri, PROV.generatedAtTime, Literal(
        datetime.now().isoformat(),
        datatype=URIRef("http://www.w3.org/2001/XMLSchema#dateTime")
    )))

    # Add mappings
    for local_uri, external_uri, confidence, match_type, description in matches:
        local_ref = URIRef(local_uri)
        external_ref = URIRef(external_uri)

        # Add owl:sameAs for high confidence matches
        if confidence >= 0.9:
            mapping_graph.add((local_ref, OWL.sameAs, external_ref))
        # Add skos:closeMatch for medium confidence
        elif confidence >= 0.7:
            mapping_graph.add((local_ref, SKOS.closeMatch, external_ref))
        # Add skos:relatedMatch for lower confidence
        else:
            mapping_graph.add((local_ref, SKOS.relatedMatch, external_ref))

    print(f"  Added {len(matches):,} mapping triples")

    return mapping_graph


def print_sample_mappings(matches, n=10):
    """
    Print sample mappings for verification.
    """
    print(f"\nSample Mappings (showing first {n}):")
    print("-" * 80)

    for i, (local_uri, external_uri, confidence, match_type, description) in enumerate(matches[:n], 1):
        # Shorten URIs for display
        local_short = local_uri.split('/')[-1]
        external_short = '/'.join(external_uri.split('/')[-2:])

        print(f"{i:2d}. {description}")
        print(f"    {local_short} ↔ {external_short}")
        print(f"    Confidence: {confidence:.2f} | Type: {match_type}")
        print()


# ==================== MAIN LINKING FUNCTION ====================

def link_ingredients():
    """
    Main function to link ingredients across datasets.
    """
    print("="*80)
    print("PHASE 2: INGREDIENT LINKING")
    print("="*80)

    # Load unified graph from Phase 1
    print(f"\n[1/6] Loading unified graph from {INPUT_TTL}...")
    unified = Graph()
    try:
        unified.parse(INPUT_TTL, format='turtle')
        print(f"  ✓ Loaded {len(unified):,} triples")
    except Exception as e:
        print(f"  ✗ Error loading graph: {e}")
        return

    # Extract ingredients
    print("\n[2/6] Extracting ingredients...")
    ingredients = extract_ingredients_by_source(unified)

    # Find exact matches
    print("\n[3/6] Finding exact matches...")
    exact_matches = find_exact_matches(ingredients)

    # Find fuzzy matches (optional)
    print("\n[4/6] Finding fuzzy matches...")
    fuzzy_matches = find_fuzzy_matches(ingredients, threshold=0.8)

    # Combine all matches
    all_matches = exact_matches + fuzzy_matches

    print(f"\n  Total matches found: {len(all_matches):,}")

    # Create mapping graph
    print("\n[5/6] Creating mapping graph...")
    mapping_graph = create_mapping_graph(all_matches)

    # Add mappings to unified graph
    print("\n[6/6] Adding mappings to unified graph...")
    unified += mapping_graph

    print(f"  ✓ Unified graph now has {len(unified):,} triples")

    # Save mapping graph separately
    print(f"\nSaving mapping graph to {MAPPINGS_TTL}...")
    try:
        mapping_graph.serialize(destination=MAPPINGS_TTL, format='turtle')
        print(f"  ✓ Saved {len(mapping_graph):,} mapping triples")
    except Exception as e:
        print(f"  ✗ Error saving mappings: {e}")

    # Save enhanced unified graph
    print(f"\nSaving enhanced unified graph to {OUTPUT_TTL}...")
    try:
        unified.serialize(destination=OUTPUT_TTL, format='turtle')
        print(f"  ✓ Saved {len(unified):,} triples")
    except Exception as e:
        print(f"  ✗ Error saving unified graph: {e}")

    # Print sample mappings
    print_sample_mappings(all_matches, n=10)

    # Statistics
    print("\n" + "="*80)
    print("LINKING STATISTICS")
    print("="*80)
    print(f"\nExact matches:  {len(exact_matches):>6,}")
    print(f"Fuzzy matches:  {len(fuzzy_matches):>6,}")
    print(f"Total matches:  {len(all_matches):>6,}")
    print("\nMapping confidence distribution:")

    high_conf = sum(1 for _, _, c, _, _ in all_matches if c >= 0.9)
    med_conf = sum(1 for _, _, c, _, _ in all_matches if 0.7 <= c < 0.9)
    low_conf = sum(1 for _, _, c, _, _ in all_matches if c < 0.7)

    print(f"  High (≥0.9):   {high_conf:>6,} (owl:sameAs)")
    print(f"  Medium (0.7+): {med_conf:>6,} (skos:closeMatch)")
    print(f"  Low (<0.7):    {low_conf:>6,} (skos:relatedMatch)")

    print("\n" + "="*80)
    print("PHASE 2 COMPLETE!")
    print("="*80)
    print(f"\n  Output files:")
    print(f"    - {OUTPUT_TTL} (unified graph with links)")
    print(f"    - {MAPPINGS_TTL} (mappings only)")
    print("\n  ✓ Ingredients are now linked across datasets")
    print("  ✓ Ready for Phase 3 (Provenance) or querying")
    print("\n" + "="*80)


def run_verification_queries(graph_path):
    """
    Run SPARQL queries to verify the linking worked.
    """
    print("\n" + "="*80)
    print("VERIFICATION QUERIES")
    print("="*80)

    graph = Graph()
    graph.parse(graph_path, format='turtle')

    # Query 1: Count owl:sameAs links
    print("\n[Query 1] Count owl:sameAs links:")
    query1 = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT (COUNT(*) as ?count)
    WHERE {
        ?s owl:sameAs ?o .
    }
    """
    result = list(graph.query(query1))
    print(f"  Result: {int(result[0][0]):,} owl:sameAs triples")

    # Query 2: Sample linked ingredients
    print("\n[Query 2] Sample linked ingredients:")
    query2 = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?local ?localLabel ?external
    WHERE {
        ?local owl:sameAs ?external .
        OPTIONAL { ?local rdfs:label ?localLabel }
    }
    LIMIT 5
    """
    results = graph.query(query2)
    for i, row in enumerate(results, 1):
        local = str(row.local).split('/')[-1]
        external = '/'.join(str(row.external).split('/')[-2:])
        label = str(row.localLabel) if row.localLabel else "N/A"
        print(f"  {i}. {label}: {local} ↔ {external}")

    # Query 3: Find recipes using linked ingredients
    print("\n[Query 3] Recipes using ingredients with external links:")
    query3 = """
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX schema: <https://schema.org/>

    SELECT DISTINCT ?recipe ?recipeName (COUNT(?linkedIngredient) as ?linkedCount)
    WHERE {
        ?recipe a food:Recipe ;
                schema:name ?recipeName .
        ?recipe food:hasIngredient|food:ingredient ?ingLine .
        ?ingLine food:ingredient ?ingredient .
        ?ingredient owl:sameAs ?external .
        BIND(?ingredient as ?linkedIngredient)
    }
    GROUP BY ?recipe ?recipeName
    ORDER BY DESC(?linkedCount)
    LIMIT 5
    """
    results = graph.query(query3)
    for i, row in enumerate(results, 1):
        name = str(row.recipeName)
        count = int(row.linkedCount)
        print(f"  {i}. {name}: {count} linked ingredients")

    print("\n" + "="*80)


# ==================== MAIN ====================

def main():
    """
    Main execution function.
    """
    start_time = datetime.now()

    # Link ingredients
    link_ingredients()

    # Run verification queries
    run_verification_queries(OUTPUT_TTL)

    # Calculate execution time
    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\nExecution time: {elapsed:.1f} seconds")


if __name__ == "__main__":
    main()
