FROM python:3.13-slim

WORKDIR /api

COPY ./requirements.txt /api/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /api/requirements.txt

# COPY ./api /api
COPY ./unified_recipes/recipe_recommendation_with_axioms_v4.ttl /api/recipe_recommendation_with_axioms_v4.ttl

CMD ["fastapi", "run", "main.py", "--reload", "--port", "8000", "--host", "0.0.0.0"]