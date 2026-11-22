"""Persistance SQLite pour BiblioIIT (Module C)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sqlite3

from modeles import Emprunt, Livre

CATALOGUE_INITIAL: tuple[Livre, ...] = (
    Livre("L001", "Climbié", "Bernard Dadié", 1956),
    Livre("L002", "Les Soleils des indépendances", "Ahmadou Kourouma", 1968),
    Livre("L003", "Une si longue lettre", "Mariama Bâ", 1979),
    Livre("L004", "Allah n'est pas obligé", "Ahmadou Kourouma", 2000),
    Livre("L005", "Clean Code", "Robert C. Martin", 2008),
    Livre("L006", "Introduction à l'algorithmique", "Thomas H. Cormen", 2009),
)


class DepotSQLite:
    """Dépôt SQLite gérant les tables `livres` et `emprunts`."""

    def __init__(self, chemin_bd: str | Path = "biblio_iit.db") -> None:
        self._chemin_bd = str(chemin_bd)
        self._connexion = sqlite3.connect(self._chemin_bd)
        self._connexion.row_factory = sqlite3.Row
        self._connexion.execute("PRAGMA foreign_keys = ON;")
        self.initialiser_schema()

    def __enter__(self) -> DepotSQLite:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.fermer()

    def fermer(self) -> None:
        """Ferme proprement la connexion SQLite."""
        self._connexion.close()

    def initialiser_schema(self) -> None:
        """Crée les tables nécessaires si elles n'existent pas encore."""
        with self._connexion:
            self._connexion.executescript(
                """
                CREATE TABLE IF NOT EXISTS livres (
                    code TEXT PRIMARY KEY,
                    titre TEXT NOT NULL,
                    auteur TEXT NOT NULL,
                    annee INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS emprunts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_livre TEXT NOT NULL,
                    matricule TEXT NOT NULL,
                    date_emprunt TEXT NOT NULL,
                    date_retour_prevue TEXT NOT NULL,
                    date_retour_effective TEXT,
                    FOREIGN KEY (code_livre) REFERENCES livres(code)
                );

                CREATE INDEX IF NOT EXISTS idx_emprunts_code_actif
                    ON emprunts(code_livre, date_retour_effective);
                """
            )

    def peupler_catalogue_initial(self) -> int:
        """Insère le catalogue initial si les livres ne sont pas déjà présents."""
        inseres = 0
        with self._connexion:
            for livre in CATALOGUE_INITIAL:
                curseur = self._connexion.execute(
                    """
                    INSERT OR IGNORE INTO livres (code, titre, auteur, annee)
                    VALUES (?, ?, ?, ?)
                    """,
                    (livre.code, livre.titre, livre.auteur, livre.annee),
                )
                inseres += curseur.rowcount
        return inseres

    def ajouter_livre(self, livre: Livre) -> None:
        """Ajoute un livre dans le catalogue."""
        with self._connexion:
            self._connexion.execute(
                """
                INSERT INTO livres (code, titre, auteur, annee)
                VALUES (?, ?, ?, ?)
                """,
                (livre.code, livre.titre, livre.auteur, livre.annee),
            )

    def obtenir_livre(self, code_livre: str) -> Livre | None:
        """Retourne un livre par son code ou None s'il est introuvable."""
        ligne = self._connexion.execute(
            "SELECT code, titre, auteur, annee FROM livres WHERE code = ?",
            (code_livre,),
        ).fetchone()
        return self._vers_livre(ligne) if ligne else None

    def lister_tous_les_livres(self) -> list[Livre]:
        """Retourne l'ensemble des livres du catalogue."""
        lignes = self._connexion.execute(
            """
            SELECT code, titre, auteur, annee
            FROM livres
            ORDER BY annee DESC, code ASC
            """
        ).fetchall()
        return [self._vers_livre(ligne) for ligne in lignes]

    def rechercher_livres(self, mot_cle: str) -> list[Livre]:
        """Recherche les livres dont le code, le titre ou l'auteur contient le mot-clé."""
        motif = f"%{mot_cle.lower()}%"
        lignes = self._connexion.execute(
            """
            SELECT code, titre, auteur, annee
            FROM livres
            WHERE LOWER(code) LIKE ?
               OR LOWER(titre) LIKE ?
               OR LOWER(auteur) LIKE ?
            ORDER BY annee DESC, code ASC
            """,
            (motif, motif, motif),
        ).fetchall()
        return [self._vers_livre(ligne) for ligne in lignes]

    def obtenir_emprunt_actif(self, code_livre: str) -> Emprunt | None:
        """Retourne l'emprunt actif d'un livre s'il est actuellement emprunté."""
        ligne = self._connexion.execute(
            """
            SELECT id, code_livre, matricule, date_emprunt,
                   date_retour_prevue, date_retour_effective
            FROM emprunts
            WHERE code_livre = ? AND date_retour_effective IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (code_livre,),
        ).fetchone()
        return self._vers_emprunt(ligne) if ligne else None

    def compter_emprunts_actifs_etudiant(self, matricule: str) -> int:
        """Compte les emprunts non restitués d'un étudiant."""
        ligne = self._connexion.execute(
            """
            SELECT COUNT(*) AS total
            FROM emprunts
            WHERE matricule = ? AND date_retour_effective IS NULL
            """,
            (matricule,),
        ).fetchone()
        return int(ligne["total"])

    def enregistrer_emprunt(self, emprunt: Emprunt) -> Emprunt:
        """Persiste un nouvel emprunt et retourne l'objet muni de son identifiant."""
        with self._connexion:
            curseur = self._connexion.execute(
                """
                INSERT INTO emprunts (
                    code_livre, matricule, date_emprunt,
                    date_retour_prevue, date_retour_effective
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    emprunt.code_livre,
                    emprunt.matricule,
                    emprunt.date_emprunt.isoformat(),
                    emprunt.date_retour_prevue.isoformat(),
                    emprunt.date_retour_effective.isoformat()
                    if emprunt.date_retour_effective
                    else None,
                ),
            )
            emprunt.id = curseur.lastrowid
        return emprunt

    def cloturer_emprunt(self, emprunt_id: int, date_retour: date) -> None:
        """Enregistre la date de retour effective d'un emprunt."""
        with self._connexion:
            self._connexion.execute(
                """
                UPDATE emprunts
                SET date_retour_effective = ?
                WHERE id = ?
                """,
                (date_retour.isoformat(), emprunt_id),
            )

    def lister_emprunts_actifs(self) -> list[Emprunt]:
        """Retourne tous les emprunts actuellement en cours, triés par date de retour prévue."""
        lignes = self._connexion.execute(
            """
            SELECT id, code_livre, matricule, date_emprunt,
                   date_retour_prevue, date_retour_effective
            FROM emprunts
            WHERE date_retour_effective IS NULL
            ORDER BY date_retour_prevue ASC, id ASC
            """
        ).fetchall()
        return [self._vers_emprunt(ligne) for ligne in lignes]

    @staticmethod
    def _vers_livre(ligne: sqlite3.Row) -> Livre:
        return Livre(
            code=ligne["code"],
            titre=ligne["titre"],
            auteur=ligne["auteur"],
            annee=int(ligne["annee"]),
        )

    @staticmethod
    def _vers_emprunt(ligne: sqlite3.Row) -> Emprunt:
        retour_eff = ligne["date_retour_effective"]
        return Emprunt(
            id=int(ligne["id"]),
            code_livre=ligne["code_livre"],
            matricule=ligne["matricule"],
            date_emprunt=date.fromisoformat(ligne["date_emprunt"]),
            date_retour_prevue=date.fromisoformat(ligne["date_retour_prevue"]),
            date_retour_effective=date.fromisoformat(retour_eff) if retour_eff else None,
        )
