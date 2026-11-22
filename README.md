# BiblioIIT - Gestion de la bibliothèque

Application console Python développée en équipe pour gérer le catalogue, les emprunts, les retours et le suivi des retards de la bibliothèque de l'Institut Ivoirien de Technologie (IIT).

## Architecture et répartition des modules

| Module | Branche | Membre | Rôle |
| --- | --- | --- | --- |
| `regles.py` | `feature/regles` | A | Constantes, validations, calcul des dates de retour/retards et exceptions métier |
| `modeles.py` | `feature/modeles` | B | Modèles de données (`Livre`, `Emprunt`, `Retard`) et formatage |
| `depot_sqlite.py` | `feature/base` | C | Persistance SQLite, schéma, requêtes paramétrées et catalogue initial |
| `service.py` | `feature/service` | D | Logique applicative (recherche, emprunt, retour, suivi des retards) |
| `console.py` | `feature/menu` | E | Interface console interactive |

## Lancer l'application

```bash
python console.py
```

### Exemple de session

```text
=== BiblioIIT ===
1. Rechercher un livre   2. Emprunter
3. Rendre                4. Retards   0. Quitter
Votre choix : 1
Mot-clé : Kourouma
  L004  Allah n'est pas obligé — Ahmadou Kourouma (2000)
  L002  Les Soleils des indépendances — Ahmadou Kourouma (1968)
Votre choix : 2
Code du livre : L002
Matricule : E2026-001
Emprunt enregistré. Retour prévu le 15/10/2026.
Votre choix : 2
Code du livre : L002
Matricule : E2026-002
Impossible : Le livre « Les Soleils des indépendances » est déjà emprunté
```
