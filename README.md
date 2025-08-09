# 📦 Comic Vault – Docker Guide

Questa guida spiega come avviare e gestire l’applicazione **Comic Vault** con **Docker Compose** in modalità **development** e **production**.

---

## 🚀 Modalità Development

In questa modalità:

* Il codice sorgente viene montato come **volume**.
* Flask gira in `FLASK_ENV=development` con **hot-reload**.
* Non serve ricostruire l'immagine ad ogni modifica al codice Python.

### Avviare l’app

```bash
docker compose up
```

### Avviare in background

```bash
docker compose up -d
```

### Ricostruire l’immagine (solo se cambi `requirements.txt` o `Dockerfile`)

```bash
docker compose up --build
```

### Fermare i container

```bash
docker compose down
```

---

## 🏭 Modalità Production

In questa modalità:

* Il codice viene copiato nell’immagine (niente volume del sorgente).
* Viene usato **Gunicorn** come server.
* Nessun reload automatico.

### Avviare l’app

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

### Avviare in background

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Fermare i container

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

---

## 🔧 Comandi utili

### Vedere i log

```bash
docker compose logs -f
```

### Accedere al container dell’app

```bash
docker compose exec comic-vault bash
```

### Accedere a MongoDB

```bash
docker compose exec comic-vault-db mongosh
```

