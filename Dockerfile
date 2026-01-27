FROM python:3.13

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app



COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m playwright install --with-deps chromium

COPY . /app

ENV CONFIG_PATH=/app/config/config.yaml
ENTRYPOINT ["python", "/app/main.py"]
CMD ["checkin", "run", "--cookie","session=xxx", "--api-user" ,""]
