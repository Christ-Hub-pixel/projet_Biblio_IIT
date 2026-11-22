"""Couche service orchestrant la logique métier de BiblioIIT (Module D)."""

from __future__ import annotations

from datetime import date

from depot_sqlite import DepotSQLite
from modeles import Emprunt, Livre, Retard
from regles import (
    EmpruntIntrouvableError,
    ErreurValidation,
    LivreDejaEmprunteError,
    LivreIntrouvableError,
    calculer_date_retour_prevue,
    normaliser_code_livre,
    normaliser_matricule,
    normaliser_mot_cle,
    verifier_limite_emprunts,
)


class ServiceBibliotheque:
    """Expose les cas d'usage principaux de gestion de la bibliothèque."""

    def __init__(self, depot: DepotSQLite) -> None:
        self._depot = depot

    def lister_livres(self, mot_cle: str | None = None) -> list[Livre]:
        """Retourne tous les livres, ou ceux correspondant au mot-clé s'il est fourni."""
        if mot_cle and mot_cle.strip():
            return self.rechercher_livres(mot_cle)
        return self._depot.lister_tous_les_livres()

    def ajouter_livre(self, code: str, titre: str, auteur: str, annee: int) -> Livre:
        """Valide et ajoute un nouveau livre au catalogue."""
        code_propre = normaliser_code_livre(code)
        titre_propre = titre.strip()
        auteur_propre = auteur.strip()
        if not titre_propre:
            raise ErreurValidation("Le titre du livre est obligatoire.")
        if not auteur_propre:
            raise ErreurValidation("Le nom de l'auteur est obligatoire.")
        if annee < 1450 or annee > 2100:
            raise ErreurValidation("L'année de publication est invalide.")
        if self._depot.obtenir_livre(code_propre) is not None:
            raise ErreurValidation(f"Un livre avec le code « {code_propre} » existe déjà.")
        livre = Livre(
            code=code_propre,
            titre=titre_propre,
            auteur=auteur_propre,
            annee=annee,
        )
        self._depot.ajouter_livre(livre)
        return livre

    def obtenir_emprunt_actif(self, code_livre: str) -> Emprunt | None:
        """Retourne l'emprunt actif d'un livre s'il existe."""
        return self._depot.obtenir_emprunt_actif(code_livre)

    def lister_emprunts_actifs(self) -> list[tuple[Livre, Emprunt]]:
        """Retourne les emprunts actifs accompagnés de leur livre."""
        resultat: list[tuple[Livre, Emprunt]] = []
        for emprunt in self._depot.lister_emprunts_actifs():
            livre = self._depot.obtenir_livre(emprunt.code_livre)
            if livre is not None:
                resultat.append((livre, emprunt))
        return resultat

    def rechercher_livres(self, mot_cle: str) -> list[Livre]:
        """Recherche les livres correspondant au mot-clé fourni."""
        terme = normaliser_mot_cle(mot_cle)
        return self._depot.rechercher_livres(terme)

    def emprunter_livre(
        self,
        code_livre: str,
        matricule: str,
        date_emprunt: date | None = None,
    ) -> Emprunt:
        """Enregistre l'emprunt d'un livre pour un étudiant."""
        code = normaliser_code_livre(code_livre)
        mat = normaliser_matricule(matricule)

        livre = self._depot.obtenir_livre(code)
        if livre is None:
            raise LivreIntrouvableError(f"Aucun livre trouvé avec le code « {code} ».")

        if self._depot.obtenir_emprunt_actif(code) is not None:
            raise LivreDejaEmprunteError(
                f"Le livre « {livre.titre} » est déjà emprunté"
            )

        nb_actifs = self._depot.compter_emprunts_actifs_etudiant(mat)
        verifier_limite_emprunts(nb_actifs)

        jour_emprunt = date_emprunt or date.today()
        date_retour_prevue = calculer_date_retour_prevue(jour_emprunt)
        emprunt = Emprunt(
            id=None,
            code_livre=code,
            matricule=mat,
            date_emprunt=jour_emprunt,
            date_retour_prevue=date_retour_prevue,
        )
        return self._depot.enregistrer_emprunt(emprunt)

    def rendre_livre(
        self,
        code_livre: str,
        date_retour: date | None = None,
    ) -> tuple[Livre, Emprunt]:
        """Enregistre le retour d'un livre actuellement emprunté."""
        code = normaliser_code_livre(code_livre)
        livre = self._depot.obtenir_livre(code)
        if livre is None:
            raise LivreIntrouvableError(f"Aucun livre trouvé avec le code « {code} ».")

        emprunt = self._depot.obtenir_emprunt_actif(code)
        if emprunt is None or emprunt.id is None:
            raise EmpruntIntrouvableError(
                f"Le livre « {livre.titre} » n'est pas actuellement emprunté."
            )

        jour_retour = date_retour or date.today()
        self._depot.cloturer_emprunt(emprunt.id, jour_retour)
        emprunt.date_retour_effective = jour_retour
        return livre, emprunt

    def lister_retards(self, date_reference: date | None = None) -> list[Retard]:
        """Retourne la liste des emprunts en retard à la date de référence."""
        ref = date_reference or date.today()
        retards: list[Retard] = []
        for emprunt in self._depot.lister_emprunts_actifs():
            jours = emprunt.jours_de_retard(date_reference=ref)
            if jours > 0:
                livre = self._depot.obtenir_livre(emprunt.code_livre)
                if livre is not None:
                    retards.append(Retard(emprunt=emprunt, livre=livre, jours_retard=jours))
        retards.sort(key=lambda r: (-r.jours_retard, r.livre.code))
        return retards
