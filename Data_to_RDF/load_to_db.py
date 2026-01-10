# load_to_db.py
from pyoxigraph import Store
from pathlib import Path

DB_PATH = Path("oxigraph_db")
TTL_FILE = Path("output/knowledge_graph.ttl")

def load_graph_to_oxigraph():
    """
    Loads the generated knowledge_graph.ttl into an on-disk Oxigraph store.
    """
    if not TTL_FILE.exists():
        print(f"Error: {TTL_FILE} not found!")
        print("Run 'python app.py convert' or 'python app.py all' first.")
        return False

    print(f"Loading {TTL_FILE} into Oxigraph database...")

    # Create or open the persistent store
    store = Store(path=str(DB_PATH))

    # Clear existing data (remove if you want to append instead)
    store.clear()

    # Correct way: open file in binary mode and use bulk_load with format
    with open(TTL_FILE, "rb") as f:
        store.bulk_load(f, "text/turtle")

    triple_count = len(store)
    print(f"Success! Loaded {triple_count} triples into Oxigraph.")
    print(f"Database stored in: {DB_PATH.resolve()}")
    print("Your graph database is now ready for SPARQL queries!")
    return True

# Test query function (unchanged)
def test_query():
    store = Store(path=str(DB_PATH))

    # Total triples
    results = list(store.query("SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"))
    count = results[0]['count'].value
    print(f"Total triples in DB: {count}")

    # Sample recipes
    results = store.query("""
        PREFIX schema: <https://schema.org/>
        SELECT ?recipe ?name WHERE {
            ?recipe a schema:Recipe .
            ?recipe schema:name ?name .
        } LIMIT 10
    """)
    print("\nSample recipes in the graph:")
    for row in results:
        print(f" - {row['name'].value}")