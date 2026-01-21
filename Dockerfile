FROM astral/uv:python3.13-alpine

RUN apk add --no-cache \
    ffmpeg \
    dcron \
    sqlite \
    sqlite-libs

WORKDIR /app

COPY main.py /app/main.py
RUN chmod +x /app/main.py

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /data/db /data/media /data/logs

ENTRYPOINT ["/app/entrypoint.sh"]
