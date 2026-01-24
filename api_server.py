from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import recipe_api as api


app = FastAPI(
    title="Recipe Knowledge Graph API",
    description="""
    REST API for querying the Recipe Knowledge Graph.
    provides multiple endpoints.

    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Info"])
async def root():
    return {
        "name": "Recipe Knowledge Graph API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "statistics": "/api/stats",
            "recipes": "/api/recipes",
            "search": "/api/search",
            "recipe_detail": "/api/recipes/{id}",
            "ingredients": "/api/ingredients",
            "ingredient_detail": "/api/ingredients/{id}",
            "videos": "/api/videos",
            "diets": "/api/diets",
            "cuisines": "/api/cuisines",
            "external_links": "/api/external-links",
            "sparql": "/api/sparql"
        }
    }


@app.get("/api/stats", tags=["Statistics"])
async def get_statistics():
    return api.get_statistics()

@app.get("/api/recipes", tags=["Recipes"])
async def get_recipes(
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip")
):
    
    return api.get_all_recipes(limit=limit, offset=offset)


@app.get("/api/recipes/{recipe_id}", tags=["Recipes"])
async def get_recipe(recipe_id: str):
    result = api.get_recipe_by_id(recipe_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/search", tags=["Recipes"])
async def search_recipes(
    ingredient: Optional[str] = Query(None, description="Filter by ingredient"),
    diet: Optional[str] = Query(None, description="Filter by diet type"),
    cuisine: Optional[str] = Query(None, description="Filter by cuisine"),
    max_time: Optional[int] = Query(None, ge=1, description="Max cooking time (minutes)"),
    has_video: Optional[bool] = Query(None, description="Only recipes with videos"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results")
):
   
    return api.search_recipes(
        ingredient=ingredient,
        diet=diet,
        cuisine=cuisine,
        max_time=max_time,
        has_video=has_video,
        limit=limit
    )


@app.get("/api/videos", tags=["Recipes"])
async def get_recipes_with_videos(
    limit: int = Query(100, ge=1, le=200, description="Maximum results")
):
   
    return api.get_recipes_with_videos(limit=limit)




@app.get("/api/ingredients", tags=["Ingredients"])
async def get_ingredients(
    limit: int = Query(500, ge=1, le=5000, description="Maximum results")
):

    return api.get_all_ingredients(limit=limit)


@app.get("/api/ingredients/{ingredient_id}", tags=["Ingredients"])
async def get_ingredient(ingredient_id: str):
    
    result = api.get_ingredient_by_id(ingredient_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result



@app.get("/api/diets", tags=["Categories"])
async def get_diets():
   
    return api.get_all_diets()


@app.get("/api/cuisines", tags=["Categories"])
async def get_cuisines():
    
    return api.get_all_cuisines()




@app.get("/api/external-links", tags=["External Links"])
async def get_external_links():
    
    return api.get_external_links()

@app.post("/api/sparql", tags=["Advanced"])
async def execute_sparql(query: str):
    """
    Example query:
    ```
    PREFIX food: <http://data.lirmm.fr/ontologies/food#>
    SELECT ?recipe ?name WHERE {
        ?recipe a food:Recipe .
        ?recipe schema:name ?name .
    } LIMIT 10
    ```
    """
    result = api.execute_sparql(query)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/sparql", tags=["Advanced"])
async def execute_sparql_get(
    query: str = Query(..., description="SPARQL query string")
):
    """
    Execute a custom SPARQL query (GET method).
    """
    result = api.execute_sparql(query)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.on_event("startup")
async def startup():
    """Load knowledge graph on startup."""
    print("Loading knowledge graph...")
    api.load_graph()
    print("API ready!")


if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("RECIPE KNOWLEDGE GRAPH - REST API SERVER")
    print("=" * 70)
    print("\nStarting server on http://localhost:8001")
    print("API docs: http://localhost:8001/docs")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=8001)