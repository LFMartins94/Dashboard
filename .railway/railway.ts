import { defineRailway, preserve, project, service } from "railway/iac";

export default defineRailway(() => {
  const contaviewWeb = service("contaview-web", {
    replicas: { "sfo": 1 },
    healthcheck: "/saude/aplicacao/",
    healthcheckTimeout: 120,
    preDeploy: "python web/manage.py migrate --noinput",
    env: { DATABASE_URL: preserve(), DJANGO_ALLOWED_HOSTS: preserve(), DJANGO_CSRF_TRUSTED_ORIGINS: preserve(), DJANGO_DATABASE_CONN_MAX_AGE: preserve(), DJANGO_SECRET_KEY: preserve(), DJANGO_SECURE_SSL_REDIRECT: preserve(), DJANGO_SETTINGS_MODULE: preserve(), OPENAI_API_KEY: preserve(), PORT: "8000" },
  });

  return project("ContaView", {
    resources: [contaviewWeb],
  });
});
