import os
import traceback
import json
from typing import Optional, List, Dict, Any
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from SPARQLWrapper import SPARQLWrapper, JSON


SPARQL_ENDPOINT = os.getenv("SPARQL_ENDPOINT", "http://localhost:3030/dataset/sparql")

app = FastAPI(
    title="Recipe Recommendation API",
    description="""
    REST API for querying the Recipe Knowledge Graph.
    
    This API provides access to:
    - 10,000+ recipes from MealDB, RecipesNLG, and Spoonacular
    - 16,000+ ingredients with external links
    - External KB links (DBpedia, Wikidata, FoodOn)
    - Video tutorials for 55+ recipes
    - Full recipe instructions and nutrition information
    
    **Group 7**: Maddy (MealDB) • Radis (RecipesNLG) • Sanjana (Spoonacular)
    """
)

sparql = SPARQLWrapper(SPARQL_ENDPOINT)
sparql.setReturnFormat(JSON)

@app.get("/", tags=["Info"])
async def root():
    return {
        "name": app.title,
        "endpoints": {
            "recipes": "Return recipes based on filters."
        }
    }

@app.get('/recipes')
async def get_recipes(
        name: Optional[str] = Query(None, description="Substring of recipe label"),
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
    filter_clause = ""
    if name:
        # case‑insensitive filter on rdfs:label
        filter_clause = f'FILTER(CONTAINS(LCASE(STR(?recipeName)), LCASE("{name}")))'

    query = f"""
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?recipe 
		?recipeName 
        (GROUP_CONCAT(DISTINCT ?ingL; separator=", ") AS ?ingredients) 
        ?instructions
    WHERE {{
        ?recipe a food:Recipe ;
                rdfs:label ?recipeName ;
                food:ingredient ?ing ;
                schema:recipeInstructions ?instructions .
        ?ing rdfs:label ?ingL
    }}
    GROUP BY ?recipe ?recipeName ?instructions
    ORDER BY ?recipe ?recipeName
    """
    
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()
        rows = recipe_row2json(results["results"]["bindings"]) # type:ignore
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.format_exc())



def recipe_row2json(rows: list):
    json_rows = []
    for row in rows:
        json_rows.append({
            'recipeURI': row['recipe']['value'],
            'name': row['recipeName']['value'],
            'ingredients': set(row.get("ingredients", {}).get("value").split(',')),
            'instructions': row.get('instructions', {}).get('value').split('\n')
        })
    return json_rows