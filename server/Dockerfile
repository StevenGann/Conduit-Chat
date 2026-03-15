FROM python:3.12-slim

WORKDIR /app

RUN useradd -m -u 1000 conduit

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server/ .
COPY web/ /app/static/

RUN mkdir -p /app/data && chown -R conduit:conduit /app
COPY server/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "conduit.main:app", "--host", "0.0.0.0", "--port", "8080"]
