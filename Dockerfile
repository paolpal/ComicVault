# Usa un'immagine base di Python
FROM python:3.9-slim

# Imposta la directory di lavoro all'interno del container
WORKDIR /app

# Copia il file requirements.txt nel container
COPY requirements.txt .

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il contenuto del progetto nella directory di lavoro del container
COPY . .

# Esponi la porta su cui Flask sarà in esecuzione
EXPOSE 5000

# Comando per avviare l'app Flask
CMD ["python", "run.py"]

