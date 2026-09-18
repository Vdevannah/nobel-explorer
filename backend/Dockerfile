# 1. Start with Python
FROM python:3.12-slim

# 2. Create a working directory inside the container
WORKDIR /app

# 3. Copy dependency list first
COPY requirements.txt .

# 4. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy backend application code
COPY backend ./backend

# 6. Document the FastAPI port
EXPOSE 8000

# 7. Start FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]