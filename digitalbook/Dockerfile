FROM python:3.9-slim

# Définition du répertoire de travail dans le conteneur
WORKDIR /app

# Définition des variables d'environnement
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie du fichier requirements.txt d'abord pour profiter du cache Docker
COPY ./requirements.txt /app/requirements.txt

# Installation des dépendances Python
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copie du reste du projet
COPY . /app/

# Commande par défaut pour exécuter l'application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
