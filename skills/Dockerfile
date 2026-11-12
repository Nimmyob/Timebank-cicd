FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -u 10001 app && chown -R app /app
USER 10001
EXPOSE 5001
CMD ["gunicorn", "-b", "0.0.0.0:5001", "-w", "2", "app:app"]
