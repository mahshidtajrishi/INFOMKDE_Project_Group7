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


# Namespaces
RECIPE = Namespace("http://example.org/recipe/")
INGREDIENT = Namespace("http://example.org/ingredient/")
USDA = Namespace("http://example.org/usda/")
FOODON = Namespace("http://purl.obolibrary.org/obo/") 

def load_rdf_as_triples(rdf_path):
    """
    Load RDF file and convert to list of (head, relation, tail) triples.
    """
    print(f"Loading RDF from: {rdf_path}")
    g = Graph()
    g.parse(rdf_path, format="turtle")
    print(f"Loaded {len(g)} RDF triples")
    
    # Convert RDF to simple triples
    triples = []
    entity_labels = {}  # Map URIs to human-readable labels
    
    # First pass: collect labels
    for s, p, o in g.triples((None, RDFS.label, None)):
        entity_labels[str(s)] = str(o)
    
    # Second pass: extract meaningful triples for embedding
    # We focus on object properties (entity-to-entity relationships)
    relations_to_include = [
        str(RECIPE.hasIngredient),
        str(RECIPE.hasCuisine),
        str(RECIPE.hasDiet),
        str(RECIPE.hasNutrition),
        str(RDF.type),
        str(OWL.sameAs),
        str(RDFS.subClassOf),
    ]
    
    for s, p, o in g:
        # Skip literals (we only want entity-entity relationships for embeddings)
        if isinstance(o, Literal):
            continue
        
        # Skip blank nodes for cleaner embeddings
        if str(s).startswith("_:") or str(o).startswith("_:"):
            continue
            
        s_str = str(s)
        p_str = str(p)
        o_str = str(o)
        
        # Include relevant relationships
        if p_str in relations_to_include or p_str.startswith(str(RECIPE)):
            triples.append((s_str, p_str, o_str))
    
    print(f"Extracted {len(triples)} entity-entity triples for embedding")
    return triples, entity_labels


def create_triples_factory(triples):
    """
    Convert triples list to PyKEEN TriplesFactory.
    """
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
    """
    Train a RotatE model on the knowledge graph.
    """
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
    """
    Extract entity embeddings from trained model.
    """
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


def find_similar_entities(query_entity, entity_to_embedding, entity_labels, top_k=10):
    """
    Find entities most similar to the query entity.
    """
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
    """
    Find recipes that might work well with a given ingredient based on embedding similarity.
    """
    if ingredient_uri not in entity_to_embedding:
        return []
    
    ingredient_embedding = entity_to_embedding[ingredient_uri].reshape(1, -1)
    
    # Find all recipe URIs
    recipe_uris = set()
    for h, r, t in triples:
        if 'Recipe' in h or '/recipe/' in h:
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
    """
    Predict what entities might complete a triple (head, relation, ?).
    """
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
    """
    Save embeddings to a file for later use.
    """
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
    print("=" * 70)
    
    # Find input file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try different input files in order of preference
    possible_inputs = [
        os.path.join(script_dir, "..", "output", "recipes_with_foodon.ttl"),
        os.path.join(script_dir, "..", "output", "recipes_with_usda.ttl"),
        os.path.join(script_dir, "..", "output", "recipes_integrated.ttl"),
        os.path.join(script_dir, "..", "output", "recipes_with_ontology.ttl"),
        os.path.join(script_dir, "..", "output", "recipes.ttl"),
    ]
    
    input_path = None
    for path in possible_inputs:
        if os.path.exists(path):
            input_path = path
            break
    
    if not input_path:
        print("ERROR: No RDF file found in output directory!")
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
    
    # Find a recipe to use as query
    recipe_entities = [e for e in entity_to_embedding.keys() if '/recipe/' in e.lower() and 'Recipe' not in e]
    
    if recipe_entities:
        query_recipe = recipe_entities[0]
        query_label = entity_labels.get(query_recipe, query_recipe.split('/')[-1])
        
        print(f"\nFinding recipes similar to: {query_label}")
        print("-" * 50)
        
        similar = find_similar_entities(query_recipe, entity_to_embedding, entity_labels, top_k=5)
        for i, (entity, label, sim) in enumerate(similar, 1):
            # Only show recipes
            if '/recipe/' in entity.lower() or 'Recipe' in entity:
                print(f"  {i}. {label} (similarity: {sim:.3f})")
    
    # Find similar ingredients
    ingredient_entities = [e for e in entity_to_embedding.keys() if '/ingredient/' in e.lower()]
    
    if ingredient_entities:
        query_ingredient = ingredient_entities[0]
        query_label = entity_labels.get(query_ingredient, query_ingredient.split('/')[-1])
        
        print(f"\nFinding ingredients similar to: {query_label}")
        print("-" * 50)
        
        similar = find_similar_entities(query_ingredient, entity_to_embedding, entity_labels, top_k=5)
        for i, (entity, label, sim) in enumerate(similar, 1):
            if '/ingredient/' in entity.lower():
                print(f"  {i}. {label} (similarity: {sim:.3f})")
    
    # Print summary
    print("\n" + "=" * 70)
    print("EMBEDDING GENERATION COMPLETE!")
    print("=" * 70)
   


if __name__ == "__main__":
    main()
