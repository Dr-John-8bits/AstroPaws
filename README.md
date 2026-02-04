# AstroPaws 🐾🚀

![Work in progress](https://img.shields.io/badge/status-work--in--progress-yellow)
![Licence](https://img.shields.io/badge/license-CC--BY--NC--4.0-blue)
![Made with Python](https://img.shields.io/badge/made%20with-Python-blue)

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Synopsis du jeu](#synopsis-du-jeu)
- [Contrôles du jeu](#contrôles-du-jeu)
- [Mode d'emploi](#mode-demploi)
- [Développement en cours](#développement-en-cours)
- [Roadmap à court terme](#roadmap-à-court-terme)
- [Checklist](#checklist)
- [Installation](#installation)
- [Création & Musique](#création--musique)
- [Licence](#licence)
- [Crédits & Feedbacks](#crédits--feedbacks)

**AstroPaws** est un jeu vidéo rétro inspiré du style Atari 7800.  
Vous incarnez AstroPaws, un courageux chat astronaute qui explore l’espace pour collecter des croquettes cosmiques et créer la légendaire "pâtée de l’espace".

🎮 **Fonctionnalités :**
- Graphismes simples et pixelisés façon Atari.
- Contrôles fluides et gameplay accessible.
- Ennemis robotiques et dangers spatiaux.
- Système de score et d'explosions vintage.
- Jeu 100 % open source sous licence CC BY-NC 4.0.

## Synopsis du jeu :

**Lointain secteur L-88.**  
Depuis la station Alpha-Felis, un signal d’alerte retentit dans le vide spatial : la dernière réserve de Pâtée Galactique™ a disparu !

Le Capitaine AstroPaws — félin gourmet et astronaute légendaire — s’élance dans le cosmos avec son Jetpack Cosmique. Sa mission ? Récupérer les sept ingrédients sacrés pour concocter la légendaire pâtée de l’espace.

Mais l’univers est loin d’être paisible…  
Chiens errants, rats mutants, et souris robotiques patrouillent les confins stellaires. Chaque tir d’eau est précieux, chaque croquette compte, et chaque réserve d’eau sauvée peut faire la différence.

Parviendrez-vous à éviter les collisions, à viser juste, à gérer vos ressources, et à vaincre les gardiens de l’espace pour restaurer le festin sacré ?

🧪 Collecte. 💧 Précision. 🐾 Survie.  
Bienvenue dans **AstroPaws: Gourmet Quest**.

➡️ Retrouvez tous les détails du gameplay dans le fichier [GAMEPLAY.md](GAMEPLAY.md).

🎮 **Contrôles du jeu :**

- Flèches du clavier : déplacer AstroPaws dans l’espace.
- Barre espace : tirer un jet d’eau vers l’avant.
- Flèche directionnelle + espace : tirer un jet d’eau dans la direction choisie.

## 📘 Mode d'emploi

Un manuel complet est disponible pour découvrir l’univers, les objectifs, les commandes et les ennemis du jeu.

➡️ [Lire le mode d’emploi officiel](MANUAL.md)

Tout cela est en cours d’élaboration et le jeu va évoluer rapidement, avec des nouveautés prévues chaque semaine.

🚧 **Développement en cours :**

AstroPaws est actuellement en phase de construction et d’expérimentation.  
Le jeu est loin d’être terminé : il s’agit des premières étapes d’un projet qui va évoluer régulièrement, avec des améliorations chaque semaine.  
Tout le développement est disponible en ligne en toute transparence pour partager l’avancée du projet avec la communauté.

## 🗺️ Roadmap à court terme :

### ✅ Terminés

#### Mécanique de base
- Déplacements orthogonaux + diagonaux avec wrap-around
- Tirs directionnels, gestion de l’eau, des croquettes et du score
- Vies, explosions et conditions de game-over

#### Progression & niveaux
- Structure `levels.py` (seuils 25/80/120, teintes de fond par niveau)
- Transitions cinématiques (mort animée → ingrédients → intro niveau → warp)
- HUD “Level X” en bas-droite

#### Écrans & menus
- Menu principal, Story (scrolling), Info (icônes + légendes animées), Pause, Game-Over

#### Ingrédients
- Chargement et mapping des sprites réels (poulet, thon, carotte, fragment)
- Affichage HUD & Pause : icône générique + icônes spécifiques, animations de zoom et clignotement

---

### 🟡 Prochaines étapes critiques

#### Hyperdrive (dash)
- Acquisition (icône à ramasser), compteur de charges, icône et HUD
- Activation J : dash ×3 speed + invincibilité courte + particules + son
- Recharge automatique (cooldown ~60 s) ou via item

#### Transformation “Super Chayen” & boss final
- Activation (touche K ou déclenchement boss) : sprite spécial + aura, boost, invincibilité
- Durée (3–5 s) et cooldown
- Boss final “Impératrice Zibeline” : phases de combat, barre de vie, récompense ultime (4ᵉ ingrédient)

#### Audio / Musique 8-bit
- Boucles de fond (menu, niveaux 1→4, boss)
- Jingles (intro niveau, victoire, warp, game-over)
- SFX (tir eau, explosion, collecte, dash, pause, game-over)

#### Niveau 4 – Gameplay plateforme
- Implémentation plateforme 2D (gravité, sauts, collision sol & plateformes)
- Environnement spécifique, power-ups, pièges
- Intro niv 4, transitions, HUD adapté

---

### 🟢 Polish & extensions

#### Inertie & mouvement fluide
- Remplacer le déplacement “à vitesse fixe” par un modèle (vx, vy) + accélération/friction
- Sensation de glisse et d’élan

#### Effet de gravité planétaire
- Lorsqu’une planète s’approche (< seuil), appliquer une force gravitationnelle simple
- Limiter aux planètes les plus proches ou à une fréquence réduite pour préserver les perf.

#### Croquettes oxydées
- À partir du niveau 3, les croquettes laissées trop longtemps deviennent "oxydées".
- Si elles sont mangées dans cet état, elles retirent des points ou ralentissent AstroPaws.

#### Graphismes & filtres rétros
- Scanlines/CRT filter, particules additionnelles, variation d’éclairage

#### UI avancée
- Mini-carte ou radar
- Options sonores, configuration des touches, sous-titres

#### Tests & équilibre
- Ajuster spawn rates, scoring, puissances dash/shield
- Optimisation perf., corrections de bugs

#### Fonctionnalités secondaires
- Sauvegarde high-scores
- Écrans de crédits, tutoriels intégrés

## ✅ Checklist

La checklist de suivi (phase 0 -> phase 3) est maintenue ici :

- [CHECKLIST.md](CHECKLIST.md)
- Validation automatique Phase 0 : `python3 phase0_smoke_test.py`
- Génération du pack audio 8-bit : `python3 tools/generate_audio.py`

💾 **Installation :**

Clonez ce dépôt :

```bash
git clone https://github.com/Dr-John-8bit/AstroPaws
```

🎨 Création & Musique :

Ce jeu est développé par Dr John 8bit.
La bande-son et les bruitages sont faits maison pour une immersion totale dans l’univers d’AstroPaws.

## 📋 Crédits & Feedbacks

- [CREDITS.md](CREDITS.md) : toutes les personnes ayant contribué au jeu ou aidé par leurs idées.
- [FEEDBACK.md](FEEDBACK.md) : compilation des suggestions reçues durant le développement.

🧩 Licence :

Ce projet est sous licence Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0).
Vous êtes libres de le modifier et de le partager en citant l’auteur, mais l’utilisation commerciale est interdite.

⸻

🐈‍⬛ “AstroPaws partira à la conquête de la galaxie, une croquette à la fois !”
