# Portfolio Lens API

This directory contains the FastAPI service and deterministic portfolio risk engine. Setup and API examples are in the repository-root README.

Run from the repository root:

```powershell
python -m uvicorn institutional_predictor.app:app --host 127.0.0.1 --port 8001
```

`POST /api/analyze` calculates exposures, mutual-fund overlap, issuer concentration, and INR stress results from the user-supplied JSON. Submitted holdings are not saved by this endpoint. Its constituent and source inputs are assumptions supplied by the user, not data fetched or verified by the service.
