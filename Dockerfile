FROM astral/uv:python3.13-alpine

ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache \
    ffmpeg \
    sqlite \
    sqlite-libs

WORKDIR /app

COPY --chmod=0755 main.py entrypoint.sh healthcheck.sh /app/

RUN mkdir -p /data/db /data/media /data/logs

HEALTHCHECK --interval=1h --timeout=30s --start-period=5m --retries=1 \
  CMD /app/healthcheck.sh

ENTRYPOINT ["/app/entrypoint.sh"]
