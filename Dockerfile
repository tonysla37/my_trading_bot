# Utiliser une image Python de base
FROM python:3.9

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires dans le conteneur
COPY requirements.txt requirements.txt
COPY . .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port sur lequel Flask sera exécuté
EXPOSE 7777

# Commande pour lancer l'application Flask
CMD ["python", "app.py"]