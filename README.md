# FlowGuard

FlowGuard is a FastAPI backend with a Streamlit frontend.

## Project structure

```
app/
  api/        # API route handlers
  db/         # Database setup
  models/     # SQLAlchemy models
  schemas/    # Pydantic schemas
  services/   # Business logic
  main.py     # FastAPI entry point
frontend/
  streamlit_app.py
tests/
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run API
uvicorn app.main:app --reload

# Run frontend
streamlit run frontend/streamlit_app.py
```

## Health check

```bash
curl http://localhost:8000/health
```
