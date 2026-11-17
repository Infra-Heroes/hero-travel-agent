FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data
WORKDIR /srv
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir . && useradd --system --uid 10001 agent && mkdir -p /data && chown agent /data
COPY docker-entrypoint.sh /docker-entrypoint.sh
EXPOSE 8080
# Starts as root only to take ownership of the mounted volume; the entrypoint then runs
# the server as the unprivileged "agent" user.
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
