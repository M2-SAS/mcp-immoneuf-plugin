---
name: comparer-programmes-et-lieux
description: Comparer plusieurs résidences neuves du catalogue M2Immoneuf et les situer sur une carte, avec distances à des lieux de référence (travail, gare, école) et plans PDF.
---

# Comparer des programmes et des lieux

Utilise ce skill quand l’acquéreur compare des résidences ou des zones géographiques, ou demande où se situent les programmes. Pour comparer des logements précis, utilise `compare_lots` (voir le skill `consulter-le-catalogue`).

Pour situer des programmes, appelle `show_programs_map` avec `program_ids` ou `city`. Sans paramètre, tous les programmes du catalogue sont affichés, jusqu’à 12.

Pour comparer de deux à six programmes, appelle `compare_programs` avec les `program.id` renvoyés par `search_lots` ou `get_program`. Si l’acquéreur cite un lieu de référence (travail, gare, école), renseigne `points` avec son nom et ses coordonnées GPS, au plus quatre : les distances à vol d’oiseau jusqu’à chaque programme sont calculées. N’invente pas de coordonnées : si le lieu est ambigu, demande une précision.

Pour recommander, renseigne `recommended_program_id` et deux à quatre `reasons` fondées sur les critères exprimés et les données affichées. Ne recommande que si l’acquéreur le demande.

La carte et le comparatif sont montrés directement à l’utilisateur : ajoute uniquement le contexte nécessaire, sans recopier les prix, distances ou plans. Les plans PDF et le formulaire de mise en relation sont dans l’interface. Pour une demande de rappel, invite l’acquéreur à remplir ce formulaire plutôt que de lui demander ses coordonnées dans la conversation.

Utilise `check_availability` avant une recommandation ferme. Les réservations, paiements et confirmations de rendez-vous se font hors du plugin.
