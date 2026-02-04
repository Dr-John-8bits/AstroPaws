# Checklist de développement AstroPaws

## Phase 0 - Stabilisation (terminee)
- [x] Corriger la fin de campagne (écran de victoire finale au dernier niveau)
- [x] Uniformiser l'état initial d'une partie (reset centralisé)
- [x] Harmoniser l'eau initiale (`50`) entre démarrage et reset
- [x] Ajouter `requirements.txt`
- [x] Ignorer les fichiers Python temporaires (`__pycache__`, `*.pyc`)
- [x] Valider les flux critiques (victoire finale + game over) via `phase0_smoke_test.py`

## Phase 1 - Arcade (terminee)
- [x] Hyperdrive complet (pickup, touche `J`, dash, invincibilité brève, FX/SFX)
- [x] Audio 8-bit (musiques + SFX essentiels)
- [x] Animations avancées sprites (au-delà de l'orientation et du bob déjà présents)

## Phase 2 - Profondeur (terminee)
- [x] Inertie (accélération/frottement)
- [x] Mécaniques par niveau (gravité locale, croquettes oxydées)
- [x] Boss final (phases + barre de vie + conclusion narrative)

## Phase 3 - Finition (terminee)
- [x] High-scores sauvegardés
- [x] Support manette
- [x] Écran de victoire final + crédits riches
- [x] Filtres CRT / scanlines
- [x] Équilibrage et polish global
