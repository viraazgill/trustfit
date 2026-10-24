# Build from the repo root: docker build -f apps/api/Dockerfile .
FROM python:3.12-slim
WORKDIR /srv
COPY packages/trustfit_engine packages/trustfit_engine
COPY apps/api apps/api
COPY config config
COPY seed seed
COPY db db
# The [pdf] extra and Chromium let the API print the report pages to PDF.
RUN pip install --no-cache-dir ./packages/trustfit_engine "./apps/api[pdf]" \
    && python -m playwright install --with-deps chromium
ENV CONFIG_DIR=/srv/config SEED_DIR=/srv/seed
WORKDIR /srv/apps/api
EXPOSE 8000
CMD ["sh", "start.sh"]
