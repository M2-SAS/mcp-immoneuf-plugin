---
name: consulter-le-catalogue
description: Rechercher, comparer et vérifier des logements neufs et terrains en France dans le catalogue M2Immoneuf, jusqu'à la mise en relation client.
---

# Consulter le catalogue M2Immoneuf

Convertis les critères exprimés en filtres disponibles dans `search_lots`. Pour un département ou une zone sans ville précise, utilise `list_cities` avec les critères applicables. Utilise `has_outdoor` pour « avec / sans extérieur », `earliest_delivery_date` et `latest_delivery_date` pour une fenêtre de livraison, et `sort=delivery` pour les livraisons les plus proches d’abord. Garde les critères de l’acquéreur jusqu’à ce qu’il accepte une modification. En l’absence de résultat, présente les pistes d’élargissement renvoyées et laisse l’acquéreur choisir.

Utilise les identifiants du catalogue pour `get_lot` et `get_program`. Appuie chaque prix TTC, caractéristique, échéance de livraison et statut sur la réponse de l’outil. Présente les dispositifs à partir des lots renvoyés par le catalogue. L’éligibilité personnelle et la décision de financement demandent une vérification séparée.

Pour comparer des résidences ou situer des programmes sur une carte, utilise le skill `comparer-programmes-et-lieux`. Compare de deux à quatre lots avec `compare_lots`. Utilise `check_availability` avant une recommandation ferme ou une mise en relation. Si la fiabilité est faible, précise que le statut reste à confirmer. Justifie une recommandation par les critères exprimés et les données des lots. Quand l’interface affiche déjà la liste, la fiche ou le comparatif, ajoute uniquement le contexte nécessaire à l’utilisateur.

Pour une demande de rappel, vérifie si le lot ou le promoteur accepte les mises en relation. Propose le formulaire du comparatif lorsqu’il est présent. En son absence, appelle `create_lead` uniquement après l’accord explicite de l’acquéreur sur la transmission de ses propres coordonnées au conseiller du promoteur concerné. Indique le destinataire et le lot ou programme avant l’envoi. Transmets uniquement les coordonnées et les renseignements utiles que l’acquéreur a fournis pour cette demande. Si la recherche a renvoyé un `search_id`, joins-le lorsque le schéma de `create_lead` l’accepte. Confirme la transmission uniquement si l’outil la confirme. Une demande transmise déclenche une prise de contact éventuelle. Les réservations, paiements et confirmations de rendez-vous se font hors du plugin.
