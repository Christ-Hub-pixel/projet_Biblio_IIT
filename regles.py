"""Règles métier, validations et exceptions pour BiblioIIT (Module A)."""

from __future__ import annotations

from datetime import date, timedelta
import re

DUREE_EMPRUNT_JOURS: int = 14
MAX_EMPRUNTS_ACTIFS: int = 3
FORMAT_DATE_AFFICHAGE: str = "%d/%m/%Y"

PATTERN_CODE_LIVRE = re.compile(r"^L\d{3,}$")
PATTERN_MATRICULE = re.compile(r"^E\d{4}-\d{3}$")


class ErreurBiblioIIT(Exception):
    """Classe de base pour toutes les erreurs métier de BiblioIIT."""


class ErreurValidation(ErreurBiblioIIT):
    """Levée lorsqu'une entrée utilisateur ne respecte pas le format attendu."""


class LivreIntrouvableError(ErreurBiblioIIT):
    """Levée lorsqu'un code de livre n'existe pas dans le catalogue."""


class LivreDejaEmprunteError(ErreurBiblioIIT):
    """Levée lorsqu'un livre demandé est déjà emprunté."""


class EmpruntIntrouvableError(ErreurBiblioIIT):
    """Levée lorsqu'aucun emprunt actif n'est trouvé pour un livre donné."""


class LimiteEmpruntsAtteinteError(ErreurBiblioIIT):
    """Levée lorsqu'un étudiant a atteint le plafond d'emprunts actifs."""


def normaliser_code_livre(code: str) -> str:
    """Nettoie et valide un code de livre (ex. L002)."""
    code_propre = code.strip().upper()
    if not PATTERN_CODE_LIVRE.match(code_propre):
        raise ErreurValidation(
            f"Code de livre invalide : « {code} » (format attendu : L001)."
        )
    return code_propre


def normaliser_matricule(matricule: str) -> str:
    """Nettoie et valide un matricule étudiant (ex. E2026-001)."""
    matricule_propre = matricule.strip().upper()
    if not PATTERN_MATRICULE.match(matricule_propre):
        raise ErreurValidation(
            f"Matricule invalide : « {matricule} » (format attendu : E2026-001)."
        )
    return matricule_propre


def normaliser_mot_cle(mot_cle: str) -> str:
    """Nettoie et valide un mot-clé de recherche."""
    mot_propre = mot_cle.strip()
    if not mot_propre:
        raise ErreurValidation("Le mot-clé de recherche ne peut pas être vide.")
    return mot_propre


def calculer_date_retour_prevue(
    date_emprunt: date,
    duree_jours: int = DUREE_EMPRUNT_JOURS,
) -> date:
    """Calcule la date de retour prévue à partir de la date d'emprunt."""
    if duree_jours <= 0:
        raise ErreurValidation("La durée d'emprunt doit être strictement positive.")
    return date_emprunt + timedelta(days=duree_jours)


def calculer_jours_retard(
    date_retour_prevue: date,
    date_reference: date | None = None,
    date_retour_effective: date | None = None,
) -> int:
    """Retourne le nombre de jours de retard (0 si le livre n'est pas en retard)."""
    if date_retour_effective is not None:
        return 0
    ref = date_reference or date.today()
    ecart = (ref - date_retour_prevue).days
    return max(0, ecart)


def est_en_retard(
    date_retour_prevue: date,
    date_reference: date | None = None,
    date_retour_effective: date | None = None,
) -> bool:
    """Indique si un emprunt est en retard à la date de référence."""
    return (
        calculer_jours_retard(
            date_retour_prevue=date_retour_prevue,
            date_reference=date_reference,
            date_retour_effective=date_retour_effective,
        )
        > 0
    )


def verifier_limite_emprunts(
    nb_emprunts_actifs: int,
    max_emprunts: int = MAX_EMPRUNTS_ACTIFS,
) -> None:
    """Vérifie que l'étudiant n'a pas atteint la limite d'emprunts actifs."""
    if nb_emprunts_actifs >= max_emprunts:
        raise LimiteEmpruntsAtteinteError(
            f"Limite d'emprunts atteinte ({max_emprunts} livres maximum simultanément)."
        )


def formater_date(valeur: date) -> str:
    """Formate une date au format français JJ/MM/AAAA."""
    return valeur.strftime(FORMAT_DATE_AFFICHAGE)
