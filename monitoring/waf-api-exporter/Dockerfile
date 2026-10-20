FROM python:3.12-slim
RUN pip install --no-cache-dir requests==2.32.3 prometheus-client==0.21.1
COPY exporter.py /app/exporter.py
USER nobody
EXPOSE 9466
CMD ["python", "-u", "/app/exporter.py"]
