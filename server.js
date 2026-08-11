const express = require('express');
const app = express();

app.get('/api', (req, res) => {
  res.json({ message: "API opérationnelle" });
});

// Nécessaire pour l'exécution locale
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Serveur sur le port ${PORT}`));

// ESSENTIEL pour Vercel :
module.exports = app;