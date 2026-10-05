FROM python:3.10-slim

WORKDIR /app

# System dependencies for compiling chroma/sqlite if needed
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run DB Setup to create the initial read/write database before locking it down
RUN python db_setup.py

CMD ["python", "sql_agent.py"]
