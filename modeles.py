"""Modèles de domaine pour BiblioIIT (Module B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from regles import calculer_jours_retard, est_en_retard, formater_date


@dataclass(frozen=True)
class Livre:
    """Représente un livre du catalogue de la bibliothèque."""

    code: str
    titre: str
    auteur: str
    annee: int

    def formater_ligne(self) -> str:
        """Retourne l'affichage console standard d'un livre."""
        return f"  {self.code}  {self.titre} — {self.auteur} ({self.annee})"


@dataclass
class Emprunt:
    """Représente un emprunt d'un livre par un étudiant."""

    id: int | None
    code_livre: str
    matricule: str
    date_emprunt: date
    date_retour_prevue: date
    date_retour_effective: date | None = None

    @property
    def est_actif(self) -> bool:
        """Indique si l'emprunt n'a pas encore été restitué."""
        return self.date_retour_effective is None

    def jours_de_retard(self, date_reference: date | None = None) -> int:
        """Calcule le nombre de jours de retard à la date de référence."""
        return calculer_jours_retard(
            date_retour_prevue=self.date_retour_prevue,
            date_reference=date_reference,
            date_retour_effective=self.date_retour_effective,
        )

    def est_en_retard(self, date_reference: date | None = None) -> bool:
        """Indique si cet emprunt est en retard à la date de référence."""
        return est_en_retard(
            date_retour_prevue=self.date_retour_prevue,
            date_reference=date_reference,
            date_retour_effective=self.date_retour_effective,
        )


@dataclass(frozen=True)
class Retard:
    """Agrège un emprunt en retard, son livre associé et le nombre de jours de retard."""

    emprunt: Emprunt
    livre: Livre
    jours_retard: int

    def formater_ligne(self) -> str:
        """Retourne l'affichage console standard d'un retard."""
        prevue = formater_date(self.emprunt.date_retour_prevue)
        return (
            f"  {self.livre.code}  {self.livre.titre} — {self.emprunt.matricule} "
            f"(prévu le {prevue}, {self.jours_retard} j de retard)"
        )
