"""Interface console interactive robuste et fluide pour BiblioIIT (Module E)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
import os
import sqlite3
import sys

from depot_sqlite import DepotSQLite
from modeles import Livre
from regles import (
    ErreurBiblioIIT,
    ErreurValidation,
    formater_date,
    normaliser_code_livre,
    normaliser_matricule,
)
from service import ServiceBibliotheque


class _ActionAnnulee(Exception):
    """Signal interne lorsqu'une action en cours est annulée par l'utilisateur."""


def _activer_couleurs_windows() -> bool:
    """Active les séquences ANSI sous Windows si la sortie est un terminal."""
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        os.system("")
    return True


COULEURS_ACTIVES = _activer_couleurs_windows()


def _style(texte: str, code: str) -> str:
    if not COULEURS_ACTIVES:
        return texte
    return f"\033[{code}m{texte}\033[0m"


def _gras(texte: str) -> str:
    return _style(texte, "1")


def _cyan(texte: str) -> str:
    return _style(texte, "36")


def _vert(texte: str) -> str:
    return _style(texte, "32")


def _jaune(texte: str) -> str:
    return _style(texte, "33")


def _rouge(texte: str) -> str:
    return _style(texte, "31")


def _gris(texte: str) -> str:
    return _style(texte, "90")


def _effacer_ecran(interactif: bool) -> None:
    """Efface l'écran uniquement en session terminal interactive."""
    if interactif and sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def _pause(
    entree: Callable[[str], str],
    interactif: bool,
) -> None:
    """Attend une validation de l'utilisateur avant de réafficher le menu."""
    if not interactif:
        return
    try:
        entree(_gris("\nAppuyez sur Entrée pour revenir au menu..."))
    except (EOFError, KeyboardInterrupt):
        pass


def _demander_champ(
    libelle: str,
    entree: Callable[[str], str],
    sortie: Callable[[str], None],
    validateur: Callable[[str], str] | None = None,
) -> str:
    """Demande une saisie avec validation inline et réessai (vide ou 'q' pour annuler)."""
    while True:
        try:
            valeur = entree(libelle).strip()
        except KeyboardInterrupt as exc:
            sortie("")
            raise _ActionAnnulee() from exc
        except EOFError as exc:
            raise _ActionAnnulee() from exc

        if not valeur or valeur.lower() == "q":
            raise _ActionAnnulee()

        if validateur is None:
            return valeur

        try:
            return validateur(valeur)
        except ErreurValidation as err:
            sortie(_rouge(f"  ✗ {err} (réessayez ou appuyez sur Entrée pour annuler)"))


def _demander_annee(
    entree: Callable[[str], str],
    sortie: Callable[[str], None],
) -> int:
    """Demande une année valide avec réessai inline."""

    def _valider_annee(brut: str) -> str:
        try:
            annee = int(brut)
        except ValueError as exc:
            raise ErreurValidation("L'année doit être un nombre entier (ex. 2024).") from exc
        if annee < 1450 or annee > 2100:
            raise ErreurValidation("L'année doit être comprise entre 1450 et 2100.")
        return str(annee)

    return int(
        _demander_champ(
            "Année de publication (ex. 2024) : ",
            entree,
            sortie,
            validateur=_valider_annee,
        )
    )


def _afficher_banniere(
    service: ServiceBibliotheque,
    sortie: Callable[[str], None],
    horloge: Callable[[], date],
) -> None:
    tous = service.lister_livres()
    actifs = service.lister_emprunts_actifs()
    retards = service.lister_retards(date_reference=horloge())
    disponibles = len(tous) - len(actifs)

    ligne = "═" * 62
    sortie(_cyan(f"╔{ligne}╗"))
    sortie(
        _cyan("║")
        + _gras("   BiblioIIT — Gestion interactive de la bibliothèque").ljust(62)
        + _cyan("║")
    )
    sortie(_cyan(f"╚{ligne}╝"))
    stats = (
        f"  Catalogue : {_gras(str(len(tous)))}  │  "
        f"Disponibles : {_vert(str(disponibles))}  │  "
        f"Empruntés : {_jaune(str(len(actifs)))}  │  "
        f"Retards : {_rouge(str(len(retards))) if retards else _vert('0')}"
    )
    sortie(stats)


def _afficher_menu(sortie: Callable[[str], None]) -> None:
    sortie(_gris("─" * 64))
    sortie(f"  {_gras('1.')} Rechercher un livre       {_gras('5.')} Tout le catalogue")
    sortie(f"  {_gras('2.')} Emprunter un livre        {_gras('6.')} Emprunts en cours")
    sortie(f"  {_gras('3.')} Rendre un livre           {_gras('7.')} Ajouter un livre")
    sortie(f"  {_gras('4.')} Voir les retards          {_gras('0.')} Quitter {_gris('(ou q)')}")
    sortie(_gris("─" * 64))


def _afficher_tableau_livres(
    livres: list[Livre],
    service: ServiceBibliotheque,
    sortie: Callable[[str], None],
    horloge: Callable[[], date],
) -> None:
    if not livres:
        sortie(_jaune("  Aucun livre trouvé."))
        return

    aujourd_hui = horloge()
    en_tete = f"  {'Code':<6} {'Titre':<32} {'Auteur':<20} {'Année':<6} {'Statut'}"
    sortie("")
    sortie(_gras(en_tete))
    sortie(_gris("  " + "─" * 80))

    for livre in livres:
        emprunt = service.obtenir_emprunt_actif(livre.code)
        if emprunt is None:
            statut = _vert("Disponible")
        elif emprunt.est_en_retard(date_reference=aujourd_hui):
            jours = emprunt.jours_de_retard(date_reference=aujourd_hui)
            statut = _rouge(f"En retard ({jours} j) — {emprunt.matricule}")
        else:
            date_ret = formater_date(emprunt.date_retour_prevue)
            statut = _jaune(f"Emprunté ({emprunt.matricule}, retour {date_ret})")

        titre = livre.titre if len(livre.titre) <= 30 else livre.titre[:29] + "…"
        auteur = livre.auteur if len(livre.auteur) <= 18 else livre.auteur[:17] + "…"
        sortie(f"  {livre.code:<6} {titre:<32} {auteur:<20} {livre.annee:<6} {statut}")


def _action_rechercher(
    service: ServiceBibliotheque,
    entree: Callable[[str], str],
    sortie: Callable[[str], None],
    horloge: Callable[[], date],
) -> None:
    mot_cle = _demander_champ(
        "Mot-clé (titre, auteur ou code — Entrée pour annuler) : ",
        entree,
        sortie,
    )
    livres = service.rechercher_livres(mot_cle)
    _afficher_tableau_livres(livres, service, sortie, horloge)


def _action_emprunter(
    service: ServiceBibliotheque,
    entree: Callable[[str], str],
    sortie: Callable[[str], None],
    horloge: Callable[[], date],
) -> None:
    disponibles = [
        livre
        for livre in service.lister_livres()
        if service.obtenir_emprunt_actif(livre.code) is None
    ]
    if not disponibles:
        sortie(_jaune("  Tous les livres du catalogue sont actuellement empruntés."))
        return

    sortie(_gras("\n  Livres disponibles :"))
    for livre in disponibles:
        sortie(f"    • {livre.code} — {livre.titre} ({livre.auteur}, {livre.annee})")
    sortie("")

    code_livre = _demander_champ(
        "Code du livre (ex. L002 — Entrée pour annuler) : ",
        entree,
        sortie,
        validateur=normaliser_code_livre,
    )
    matricule = _demander_champ(
        "Matricule étudiant (ex. E2026-001 — Entrée pour annuler) : ",
        entree,
        sortie,
        validateur=normaliser_matricule,
    )
    emprunt = service.emprunter_livre(code_livre, matricule, date_emprunt=horloge())
    date_prevue = formater_date(emprunt.date_retour_prevue)
    sortie(_vert(f"\n  ✓ Emprunt enregistré. Retour prévu le {date_prevue}."))


def _action_rendre(
    service: ServiceBibliotheque,
    entree: Callable[[str], str],
    sortie: Callable[[str], None],
    horloge: Callable[[], date],
) -> None:
    actifs = service.lister_emprunts_actifs()
    if not actifs:
        sortie(_jaune("  Aucun livre n'est actuellement emprunté."))
        return

    sortie(_gras("\n  Livres actuellement empruntés :"))
    for livre, emprunt in actifs:
        date_prevue = formater_date(emprunt.date_retour_prevue)
        sortie(
            f"    • {livre.code} — {livre.titre} "
            f"(par {emprunt.matricule}, retour prévu le {date_prevue})"
        )
    sortie("")

    code_livre = _demander_champ(
        "Code du livre à rendre (Entrée pour annuler) : ",
        entree,
        sortie,
        validateur=normaliser_code_livre,
    )
    livre, _ = service.rendre_livre(code_livre, date_retour=horloge())
    sortie(_vert(f"\n  ✓ Retour enregistré pour « {livre.titre} »."))


def _action_retards(
    service: ServiceBibliotheque,
    sortie: Callable[[str], None],
    horloge: Callable[[], date],
) -> None:
    retards = service.lister_retards(date_reference=horloge())
    if not retards:
        sortie(_vert("\n  ✓ Aucun retard en cours."))
        return
    sortie(_rouge(_gras(f"\n  {len(retards)} emprunt(s) en retard :")))
    for retard in retards:
        sortie(_rouge(retard.formater_ligne()))


def _action_catalogue(
    service: ServiceBibliotheque,
    sortie: Callable[[str], None],
    horloge: Callable[[], date],
) -> None:
    _afficher_tableau_livres(service.lister_livres(), service, sortie, horloge)


def _action_emprunts_en_cours(
    service: ServiceBibliotheque,
    sortie: Callable[[str], None],
    horloge: Callable[[], date],
) -> None:
    actifs = service.lister_emprunts_actifs()
    if not actifs:
        sortie(_jaune("\n  Aucun emprunt en cours."))
        return
    aujourd_hui = horloge()
    en_tete = f"  {'Code':<6} {'Titre':<30} {'Matricule':<12} {'Emprunté le':<13} {'Retour prévu'}"
    sortie("")
    sortie(_gras(en_tete))
    sortie(_gris("  " + "─" * 78))
    for livre, emprunt in actifs:
        titre = livre.titre if len(livre.titre) <= 28 else livre.titre[:27] + "…"
        retour = formater_date(emprunt.date_retour_prevue)
        if emprunt.est_en_retard(date_reference=aujourd_hui):
            retour = _rouge(f"{retour} ({emprunt.jours_de_retard(aujourd_hui)} j retard)")
        sortie(
            f"  {livre.code:<6} {titre:<30} {emprunt.matricule:<12} "
            f"{formater_date(emprunt.date_emprunt):<13} {retour}"
        )


def _action_ajouter_livre(
    service: ServiceBibliotheque,
    entree: Callable[[str], str],
    sortie: Callable[[str], None],
) -> None:
    sortie(_gris("\n  (Appuyez sur Entrée ou tapez 'q' à tout moment pour annuler)"))
    code = _demander_champ(
        "Code du livre (ex. L007) : ",
        entree,
        sortie,
        validateur=normaliser_code_livre,
    )
    titre = _demander_champ("Titre : ", entree, sortie)
    auteur = _demander_champ("Auteur : ", entree, sortie)
    annee = _demander_annee(entree, sortie)

    livre = service.ajouter_livre(code=code, titre=titre, auteur=auteur, annee=annee)
    sortie(_vert(f"\n  ✓ Livre ajouté : {livre.code} — {livre.titre} ({livre.annee})."))


def executer_session(
    service: ServiceBibliotheque,
    entree: Callable[[str], str] = input,
    sortie: Callable[[str], None] = print,
    horloge: Callable[[], date] = date.today,
    mode_interactif: bool | None = None,
) -> None:
    """Lance la boucle interactive de l'application console."""
    interactif = (
        (entree is input and sortie is print)
        if mode_interactif is None
        else mode_interactif
    )

    while True:
        _effacer_ecran(interactif)
        _afficher_banniere(service, sortie, horloge)
        _afficher_menu(sortie)

        try:
            choix = entree("Votre choix : ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            sortie(_cyan("\nAu revoir et bonne lecture !"))
            return

        if choix in ("0", "q", "quitter", "exit"):
            sortie(_cyan("Au revoir et bonne lecture !"))
            return

        if not choix:
            continue

        try:
            if choix == "1":
                _action_rechercher(service, entree, sortie, horloge)
            elif choix == "2":
                _action_emprunter(service, entree, sortie, horloge)
            elif choix == "3":
                _action_rendre(service, entree, sortie, horloge)
            elif choix == "4":
                _action_retards(service, sortie, horloge)
            elif choix == "5":
                _action_catalogue(service, sortie, horloge)
            elif choix == "6":
                _action_emprunts_en_cours(service, sortie, horloge)
            elif choix == "7":
                _action_ajouter_livre(service, entree, sortie)
            else:
                sortie(_rouge("  ✗ Choix invalide. Veuillez saisir un chiffre entre 0 et 7."))
        except _ActionAnnulee:
            sortie(_gris("  Action annulée."))
        except ErreurBiblioIIT as erreur:
            sortie(_rouge(f"\n  ✗ Impossible : {erreur}"))
        except sqlite3.Error as erreur_bd:
            sortie(_rouge(f"\n  ✗ Erreur de base de données : {erreur_bd}"))

        _pause(entree, interactif)


def main() -> None:
    """Point d'entrée principal de l'application console BiblioIIT."""
    try:
        with DepotSQLite("biblio_iit.db") as depot:
            depot.peupler_catalogue_initial()
            service = ServiceBibliotheque(depot)
            executer_session(service)
    except sqlite3.Error as erreur:
        print(_rouge(f"Erreur critique SQLite : {erreur}"))
        sys.exit(1)


if __name__ == "__main__":
    main()
