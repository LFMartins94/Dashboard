FROM node:24-alpine AS interface

WORKDIR /aplicacao
COPY package.json package-lock.json ./
RUN npm ci
COPY web/templates ./web/templates
COPY web/nucleo ./web/nucleo
COPY web/interface ./web/interface
COPY scripts/copiar_htmx.mjs ./scripts/copiar_htmx.mjs
RUN npm run build

FROM python:3.13-slim AS aplicacao

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=configuracao.settings.producao \
    PORT=8000

WORKDIR /aplicacao
RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=interface /aplicacao/web/static/css/contaview.css ./web/static/css/contaview.css
COPY --from=interface /aplicacao/web/static/vendor/htmx.min.js ./web/static/vendor/htmx.min.js

RUN DJANGO_SETTINGS_MODULE=configuracao.settings.compilacao \
    python web/manage.py collectstatic --noinput

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/saude/aplicacao/', timeout=3)"

CMD ["gunicorn", "--chdir", "web", "configuracao.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
