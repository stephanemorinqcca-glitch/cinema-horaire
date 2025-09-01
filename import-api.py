<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <title>Exporter films.json depuis Veezi</title>
</head>
<body>
  <h1>Exporter la liste des films</h1>

  <p>
    <label>Date de début :
      <input id="startDate" type="date" />
    </label>
  </p>

  <p>
    <label>Date de fin :
      <input id="endDate" type="date" value="2100-01-01" />
    </label>
  </p>

  <button id="exportBtn">Exporter films.json</button>

  <script>
    // Remplace par ton vrai siteToken
    const token = 'shrfm72nvm2zmr7xpsteck6b64';

    async function fetchSessions(startDate, endDate) {
      const url = new URL('https://api.us.veezi.com/v1/sessions');
      const params = {
        startDate,
        endDate,
        cinemaId: '0',
        includeFilms: 'true'
      };
      Object.entries(params).forEach(([k, v]) =>
        url.searchParams.append(k, v)
      );

      const resp = await fetch(url.toString(), {
        headers: { 'VeeziAccessToken': token }
      });
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`Erreur ${resp.status} : ${txt}`);
      }
      return resp.json();
    }

    function transform(sessions) {
      const byFilm = {};
      sessions.forEach(s => {
        const d = new Date(s.showtime);
        const dateStr = d.toLocaleString('fr-FR', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        });

        if (!byFilm[s.filmId]) {
          byFilm[s.filmId] = {
            titre: s.filmTitle,
            classification: s.rating,
            duree: s.duration,
            genre: s.genres,
            poster: s.filmImageUrl,
            horaire: []
          };
        }
        byFilm[s.filmId].horaire.push(dateStr);
      });

      return {
        cinema: 'Cinéma Centre-Ville',
        films: Object.values(byFilm).map(f => ({
          ...f,
          horaire: f.horaire.sort()
        }))
      };
    }

    function downloadJSON(data) {
      const blob = new Blob(
        [JSON.stringify(data, null, 2)],
        { type: 'application/json' }
      );
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'films.json';
      a.click();
    }

    document.getElementById('exportBtn').onclick = async () => {
      try {
        const start = document.getElementById('startDate').value
          || new Date().toISOString().slice(0, 10);
        const end = document.getElementById('endDate').value;
        const sessions = await fetchSessions(start, end);
        const data = transform(sessions);
        downloadJSON(data);
      } catch (e) {
        alert(e.message);
      }
    };
  </script>
</body>
</html>
