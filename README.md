# Cinéma Horaire

Ce projet affiche les horaires des films pour le Cinéma Centre-Ville.

## Fichiers

- `horaire_films.html` : page web dynamique
- `films.json` : données des films
- `update_films.py` : script Python pour mise à jour
- `.github/workflows/update-films.yml` : automatisation via GitHub Actions

## Déploiement

1. Créez un dépôt GitHub.
2. Téléversez tous les fichiers.
3. Activez GitHub Pages dans les paramètres.
4. La page sera disponible à `https://<utilisateur>.github.io/<dépôt>/horaire_films.html`.

## Automatisation

Le fichier `update-films.yml` exécute le script toutes les 5 minutes pour mettre à jour `films.json`.
