# OpenHFTA API

Projeto FastAPI do OpenHFTA. A API usa `openhfta_core/` como biblioteca de
domínio e não contém as fórmulas numéricas do núcleo.

Na raiz do repositório:

```bash
python3 -m pip install -r api/requirements.txt
uvicorn api.main:app --reload --port 8000
```

Endpoints principais: `GET /health`, `POST /api/analyze` e
`POST /api/compare`. A documentação interativa fica em `/docs`.
