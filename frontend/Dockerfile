FROM python:3.11-slim
WORKDIR /app
COPY frontend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY frontend /app/frontend
WORKDIR /app/frontend
EXPOSE 8050
CMD ["python", "app.py"]
