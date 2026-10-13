FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gfortran make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY api/requirements.txt api/requirements.txt
RUN python -m pip install --prefix=/install -r api/requirements.txt

COPY Makefile hfta.py ./
COPY src ./src
COPY openhfta_core ./openhfta_core
COPY api ./api
COPY prns ./prns
RUN make

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgfortran5 libgomp1 libquadmath0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

WORKDIR /app
COPY --from=build /install /usr/local
COPY --from=build /app/libopenytwcore.so /app/libopenytwcore.so
COPY --from=build /app/openhfta_core /app/openhfta_core
COPY --from=build /app/api /app/api
COPY --from=build /app/prns /app/prns

USER app
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
