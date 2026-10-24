# Build from the repo root: docker build -f apps/api/Dockerfile .
FROM python:3.12-slim
WORKDIR /srv
COPY packages/trustfit_engine packages/trustfit_engine
COPY apps/api apps/api
COPY config config
COPY seed seed
COPY db db
RUN pip install --no-cache-dir ./packages/trustfit_engine ./apps/api
ENV CONFIG_DIR=/srv/config
WORKDIR /srv/apps/api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
