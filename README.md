# Cinéma Horaire

Ce projet contient une page HTML qui affiche l'horaire des films avec leurs affiches, ainsi qu'un script Python pour mettre à jour automatiquement les données depuis l'API Veezi.

## Fichiers

- `horaire_films.html` : page web dynamique
- `films.json` : données des films
- `update_films.py` : script Python pour mise à jour
- `README.md` : instructions

## Hébergement sur GitHub Pages

1. Créez un dépôt GitHub (ex. `cinema-horaire`)
2. Ajoutez ces fichiers
3. Activez GitHub Pages dans les paramètres du dépôt
4. Accédez à `https://<utilisateur>.github.io/cinema-horaire/horaire_films.html`

## Mise à jour automatique

Utilisez `cron` ou le Planificateur de tâches pour exécuter `update_films.py` toutes les 5 minutes.
