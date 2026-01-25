import os
import sys
import numpy as np
from collections import defaultdict

# Check for required packages
try:
    import torch
    from pykeen.pipeline import pipeline
    from pykeen.triples import TriplesFactory
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError as e:
    print("=" * 70)
    print("MISSING REQUIRED PACKAGES")
    print("=" * 70)
    print("\nPlease install the required packages:")
    print("\n    pip install pykeen torch numpy scikit-learn")
    print("\nThen run this script again.")
    print("=" * 70)
    sys.exit(1)

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL


# NEW Namespaces (matching team vocabulary)
FOOD = Namespace("http://data.lirmm.fr/ontologies/food#")
SCHEMA = Namespace("https://schema.org/")
RECIPE_BASE = Namespace("http://example.org/food/recipe/")
INGREDIENT_BASE = Namespace("http://example.org/food/ingredient/")
USDA = Namespace("http://example.org/usda/")
FOODON = Namespace("http://purl.obolibrary.org/obo/")


def load_rdf_as_triples(rdf_path):
    print(f"Loading RDF from: {rdf_path}")
    g = Graph()
    g.parse(rdf_path, format="turtle")
    print(f"Loaded {len(g)} RDF triples")
    
    # Convert RDF to simple triples
    triples = []
    entity_labels = {}  
    
    # First pass: collect labels
    for s, p, o in g.triples((None, RDFS.label, None)):
        entity_labels[str(s)] = str(o)
    
    # Also collect schema:name as labels
    for s, p, o in g.triples((None, SCHEMA.name, None)):
        if str(s) not in entity_labels:
            entity_labels[str(s)] = str(o)
    
    
    relations_to_include = [
        str(FOOD.ingredient),           # NEW: food:ingredient
        str(SCHEMA.recipeCuisine),      # NEW: schema:recipeCuisine
        str(SCHEMA.suitableForDiet),    # NEW: schema:suitableForDiet
        str(SCHEMA.nutrition),          # NEW: schema:nutrition
        str(RDF.type),
        str(OWL.sameAs),
        str(RDFS.subClassOf),
    ]
    
    for s, p, o in g:
        # Skip literals 
        if isinstance(o, Literal):
            continue
       
        if str(s).startswith("_:") or str(o).startswith("_:"):
            continue
            
        s_str = str(s)
        p_str = str(p)
        o_str = str(o)
        
        # Include relevant relationships
        include = False
        
        # Check if it's in our explicit list
        if p_str in relations_to_include:
            include = True
        
        # Include food: namespace properties
        if p_str.startswith(str(FOOD)):
            include = True
        
        # Include schema: namespace properties (but not all)
        if p_str.startswith(str(SCHEMA)) and any(x in p_str for x in ['ingredient', 'cuisine', 'diet', 'nutrition']):
            include = True
        
        # Include example.org/food/ properties
        if 'example.org/food' in p_str:
            include = True
            
        if include:
            triples.append((s_str, p_str, o_str))
    
    print(f"Extracted {len(triples)} entity-entity triples for embedding")
    return triples, entity_labels


def create_triples_factory(triples):
    
    # Convert to numpy array
    triples_array = np.array(triples, dtype=str)
    
    # Create TriplesFactory
    tf = TriplesFactory.from_labeled_triples(triples_array)
    
    print(f"\nTriples Factory Created:")
    print(f"  Entities: {tf.num_entities}")
    print(f"  Relations: {tf.num_relations}")
    print(f"  Triples: {tf.num_triples}")
    
    return tf


def train_rotate_model(triples_factory, epochs=100, embedding_dim=128):
    
    print(f"\n{'=' * 70}")
    print("TRAINING RotatE MODEL")
    print(f"{'=' * 70}")
    print(f"Embedding dimension: {embedding_dim}")
    print(f"Training epochs: {epochs}")
    print("This may take a few minutes...\n")
    
    # Split data for training/testing
    training, testing = triples_factory.split([0.8, 0.2], random_state=42)
    
    # Train RotatE model
    result = pipeline(
        training=training,
        testing=testing,
        model='RotatE',
        model_kwargs={
            'embedding_dim': embedding_dim,
        },
        training_kwargs={
            'num_epochs': epochs,
            'batch_size': 256,
        },
        optimizer='Adam',
        optimizer_kwargs={
            'lr': 0.001,
        },
        negative_sampler='basic',
        negative_sampler_kwargs={
            'num_negs_per_pos': 10,
        },
        random_seed=42,
        device='cpu',  # Use 'cuda' if you have GPU
    )
    
    print(f"\n{'=' * 70}")
    print("TRAINING COMPLETE!")
    print(f"{'=' * 70}")
    
    # Print evaluation metrics
    print("\nEvaluation Metrics:")
    metrics = result.metric_results.to_dict()
    for metric_name, value in list(metrics.items())[:5]:
        if isinstance(value, float):
            print(f"  {metric_name}: {value:.4f}")
    
    return result


def get_entity_embeddings(result, triples_factory):
   
    model = result.model
    
    # Get entity embeddings
    entity_embeddings = model.entity_representations[0]
    embeddings = entity_embeddings(
        torch.arange(triples_factory.num_entities)
    ).detach().numpy()
    
    # Handle complex embeddings (RotatE uses complex numbers)
    if embeddings.dtype == np.complex64 or embeddings.dtype == np.complex128:
        # Convert complex to real by concatenating real and imaginary parts
        embeddings = np.concatenate([embeddings.real, embeddings.imag], axis=1)
    
    # Create entity to embedding mapping
    entity_to_embedding = {}
    for entity_id, entity_label in enumerate(triples_factory.entity_to_id.keys()):
        entity_to_embedding[entity_label] = embeddings[entity_id]
    
    print(f"\nGenerated embeddings for {len(entity_to_embedding)} entities")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    
    return entity_to_embedding, embeddings 

# def normalize_embeddings(entity_to_embedding):
#     norm_embeddings = {}
#     for entity, emb in entity_to_embedding.items():
#     return norm_embeddings

def find_similar_entities(query_entity, entity_to_embedding, entity_labels, top_k=10):
    if query_entity not in entity_to_embedding:
        print(f"Entity not found: {query_entity}")
        return []
    
    query_embedding = entity_to_embedding[query_entity].reshape(1, -1)
    
    # Calculate similarities
    similarities = []
    for entity, embedding in entity_to_embedding.items():
        if entity != query_entity:
            sim = cosine_similarity(query_embedding, embedding.reshape(1, -1))[0][0]
            label = entity_labels.get(entity, entity.split('/')[-1])
            similarities.append((entity, label, sim))
    
    # Sort by similarity
    similarities.sort(key=lambda x: x[2], reverse=True)
    
    return similarities[:top_k]


def find_recipes_by_ingredient_similarity(ingredient_uri, entity_to_embedding, entity_labels, triples, top_k=5):
    
    if ingredient_uri not in entity_to_embedding:
        return []
    
    ingredient_embedding = entity_to_embedding[ingredient_uri].reshape(1, -1)
    
    # Find all recipe URIs (NEW: using food/recipe/ path)
    recipe_uris = set()
    for h, r, t in triples:
        if '/food/recipe/' in h or 'food#Recipe' in t:
            recipe_uris.add(h)
    
    # Calculate similarities
    similarities = []
    for recipe_uri in recipe_uris:
        if recipe_uri in entity_to_embedding:
            recipe_embedding = entity_to_embedding[recipe_uri].reshape(1, -1)
            sim = cosine_similarity(ingredient_embedding, recipe_embedding)[0][0]
            label = entity_labels.get(recipe_uri, recipe_uri.split('/')[-1])
            similarities.append((recipe_uri, label, sim))
    
    similarities.sort(key=lambda x: x[2], reverse=True)
    return similarities[:top_k]


def predict_missing_links(model, triples_factory, head_entity, relation, top_k=10):
    # Get IDs
    if head_entity not in triples_factory.entity_to_id:
        return []
    if relation not in triples_factory.relation_to_id:
        return []
    
    head_id = triples_factory.entity_to_id[head_entity]
    relation_id = triples_factory.relation_to_id[relation]
    
    # Score all possible tails
    head_tensor = torch.tensor([head_id])
    relation_tensor = torch.tensor([relation_id])
    
    # Get scores for all entities as potential tails
    all_entities = torch.arange(triples_factory.num_entities)
    
    scores = []
    id_to_entity = {v: k for k, v in triples_factory.entity_to_id.items()}
    
    for tail_id in range(triples_factory.num_entities):
        triple = torch.tensor([[head_id, relation_id, tail_id]])
        score = model.score_hrt(triple).item()
        entity = id_to_entity[tail_id]
        scores.append((entity, score))
    
    # Sort by score (higher is better for most models)
    scores.sort(key=lambda x: x[1], reverse=True)
    
    return scores[:top_k]


def save_embeddings(entity_to_embedding, entity_labels, output_path):
    
    print(f"\nSaving embeddings to: {output_path}")
    
    # Save as numpy file
    np.savez(
        output_path,
        entities=list(entity_to_embedding.keys()),
        embeddings=np.array(list(entity_to_embedding.values())),
        labels=[entity_labels.get(e, e.split('/')[-1]) for e in entity_to_embedding.keys()]
    )
    print("Embeddings saved!")


def main():
    print("=" * 70)
    print("GRAPH EMBEDDINGS WITH PyKEEN (RotatE)")
    print("=" * 70)
    print("\nUsing NEW vocabulary:")
    print("  - food: <http://data.lirmm.fr/ontologies/food#>")
    print("  - schema: <https://schema.org/>")
    print("=" * 70)
    
    # Find input file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try different input files in order of preference
    # Priority: Complete unified graph with OWL axioms and all external links
    possible_inputs = [
        os.path.join(script_dir, "..", "output", "recipe_recommendation_with_axioms_v4.ttl"),
        os.path.join(script_dir, "..", "output", "recipe_kg_complete.ttl"),
        os.path.join(script_dir, "..", "recipe_kg_complete.ttl"),
        os.path.join(script_dir, "..", "output", "recipe_recommendation_with_OWL.ttl"),
        os.path.join(script_dir, "..", "output", "unified_recipes_v3_normalized.ttl"),
        os.path.join(script_dir, "..", "output", "recipes_converted_fixed.ttl"),
        os.path.join(script_dir, "..", "output", "recipes_with_foodon.ttl"),
    ]
    
    input_path = None
    for path in possible_inputs:
        if os.path.exists(path):
            input_path = path
            break
    
    if not input_path:
        print("ERROR: No RDF file found in output directory!")
        print("Please ensure one of these files exists:")
        for p in possible_inputs:
            print(f"  - {p}")
        return
    
    output_embeddings = os.path.join(script_dir, "..", "output", "recipe_embeddings.npz")
    
    # Step 1: Load RDF and convert to triples
    triples, entity_labels = load_rdf_as_triples(input_path)
    
    if len(triples) < 100:
        print("\nWARNING: Very few triples extracted. Results may not be meaningful.")
    
    # Step 2: Create TriplesFactory
    triples_factory = create_triples_factory(triples)
    
    # Step 3: Train RotatE model
    result = train_rotate_model(
        triples_factory, 
        epochs=50,  # Reduced for faster training
        embedding_dim=64  # Reduced for smaller dataset
    )
    
    # Step 4: Extract embeddings
    entity_to_embedding, embeddings = get_entity_embeddings(result, triples_factory)
    
    # Step 5: Save embeddings
    save_embeddings(entity_to_embedding, entity_labels, output_embeddings)
    
    # Step 6: Demo - Find similar entities
    print("\n" + "=" * 70)
    print("DEMONSTRATION: ENTITY SIMILARITY")
    print("=" * 70)
    
    # Find a recipe to use as query (NEW: using food/recipe/ path)
    recipe_entities = [e for e in entity_to_embedding.keys() 
                       if '/food/recipe/' in e.lower() and 'Recipe' not in e]
    
    if recipe_entities:
        query_recipe = recipe_entities[0]
        query_label = entity_labels.get(query_recipe, query_recipe.split('/')[-1])
        
        print(f"\nFinding recipes similar to: {query_label}")
        print("-" * 50)
        
        similar = find_similar_entities(query_recipe, entity_to_embedding, entity_labels, top_k=5)
        count = 0
        for entity, label, sim in similar:
            # Only show recipes (NEW: using food/recipe/ path)
            if '/food/recipe/' in entity.lower():
                count += 1
                print(f"  {count}. {label} (similarity: {sim:.3f})")
                if count >= 5:
                    break
    
    # Find similar ingredients (NEW: using food/ingredient/ path)
    ingredient_entities = [e for e in entity_to_embedding.keys() 
                          if '/food/ingredient/' in e.lower()]
    
    if ingredient_entities:
        query_ingredient = ingredient_entities[0]
        query_label = entity_labels.get(query_ingredient, query_ingredient.split('/')[-1])
        
        print(f"\nFinding ingredients similar to: {query_label}")
        print("-" * 50)
        
        similar = find_similar_entities(query_ingredient, entity_to_embedding, entity_labels, top_k=5)
        count = 0
        for entity, label, sim in similar:
            if '/food/ingredient/' in entity.lower():
                count += 1
                print(f"  {count}. {label} (similarity: {sim:.3f})")
                if count >= 5:
                    break
    
    # Print summary
    print("\n" + "=" * 70)
    print("EMBEDDING GENERATION COMPLETE!")
    print("=" * 70)
    print(f"Total entities embedded: {len(entity_to_embedding)}")
    print(f"Embedding dimension: {embeddings.shape[1]}")
   

if __name__ == "__main__":
    main()
