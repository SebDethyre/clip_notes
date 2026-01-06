# 📋 ClipNotes

> Un gestionnaire de presse-papier intelligent et ergonomique à portée de curseur

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)](https://pypi.org/project/PyQt6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![ClipNotes Demo](docs/demo.gif)

## ✨ Qu'est-ce que ClipNotes ?

**ClipNotes** est un gestionnaire de presse-papier nouvelle génération qui apparaît instantanément autour de votre curseur dans une interface radiale élégante. Fini les allers-retours fastidieux pour copier vos liens, commandes, snippets de code ou templates favoris !

### 🎯 Pourquoi ClipNotes ?

- **⚡ Instantané** : Apparaît là où se trouve votre curseur
- **🎨 Élégant** : Interface radiale moderne avec animations fluides et effets néon
- **🔧 Polyvalent** : 3 types d'actions par clip (copie, terminal, exécution)
- **🖼️ Visuel** : Utilisez des emojis ou vos propres images comme icônes
- **🎭 Personnalisable** : Couleurs, opacités, néons configurables
- **💾 Organisé** : Système de stockage pour sauvegarder/restaurer des groupes de clips
- **⌨️ Accessible** : Navigation complète au clavier (flèches + Entrée)
- **🔒 Discret** : Fenêtre légère et transparente qui disparaît quand vous n'en avez pas besoin
- **🚀 Productif** : Accès ultra-rapide par raccourci clavier

**Cas d'usage typiques :**
- Développeurs : commandes git, snippets de code, URLs de repos, lancement d'applications
- DevOps : commandes SSH, chemins serveurs, configurations, scripts d'automatisation
- Designers : codes couleur, liens Figma/Adobe, textes récurrents
- Rédacteurs : templates d'emails, phrases types, liens de références
- Tous : URLs fréquentes, numéros de téléphone, adresses email

---

## 🚀 Installation

### Prérequis

- **Python 3.8+**
- **Linux** (testé sur Ubuntu 22.04+, compatible X11 et Wayland)
- Environnement graphique (GNOME, KDE, XFCE, etc.)

### Dépendances système

```bash
# Installation des outils requis
sudo apt update
sudo apt install python3-pip python3-venv

# Pour PyQt6
sudo apt install python3-pyqt6 python3-pyqt6.qtsvg
```

### Installation de ClipNotes

1. **Cloner le dépôt**
   ```bash
   git clone https://github.com/votre-username/clipnotes.git
   cd clipnotes
   ```

2. **Créer un environnement virtuel**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Installer les dépendances Python**
   ```bash
   pip install -r requirements.txt
   ```

   **Contenu de `requirements.txt` :**
   ```
   PyQt6>=6.0.0
   pyperclip>=1.8.2
   Pillow>=9.0.0
   ```

4. **Configurer le script de lancement**
   ```bash
   # Rendre le script exécutable
   chmod +x launch_clipnotes.sh
   
   # Adapter le chemin dans le script (remplacer par votre chemin)
   nano launch_clipnotes.sh
   # Modifier: source ~/votre_venv/bin/activate
   #          cd /chemin/vers/clipnotes
   ```

5. **Configurer le raccourci clavier**

   **GNOME :**
   - Paramètres → Clavier → Raccourcis personnalisés
   - Ajouter un nouveau raccourci :
     - **Nom** : ClipNotes
     - **Commande** : `/chemin/vers/clipnotes/launch_clipnotes.sh`
     - **Raccourci** : `Super+V` (ou votre choix)

   **KDE :**
   - Paramètres système → Raccourcis → Raccourcis personnalisés
   - Édition → Nouveau → Commande shell globale
   - Configurer comme ci-dessus

   **XFCE :**
   - Paramètres → Clavier → Raccourcis d'applications
   - Ajouter avec la même configuration

---

## 📖 Guide d'utilisation

### Lancement rapide

1. **Appuyez sur votre raccourci clavier** (ex: `Super+V`)
2. Le menu radial apparaît **autour de votre curseur**
3. Cliquez sur un clip pour l'utiliser (action configurée : copie, terminal ou exécution)
4. Le menu se ferme automatiquement

### Interface

```
          📦 (Stockage)
              ↑
    ⚙️ ←   [CENTRE]   → ➖
              ↓
          ✏️ (Modifier)
              ↓
          ➕ (Ajouter)
```

Le menu est organisé en **cercle** avec :
- **Centre** : Indicateur de mode + icône du clip survolé
- **Périmètre** : Vos clips étiquetés avec des emojis ou images
- **Boutons de contrôle** : ➕ Ajouter, ✏️ Modifier, ➖ Supprimer, ⚙️ Configuration, 📦 Stockage

---

### ➕ Ajouter un nouveau clip

1. **Appuyez sur le raccourci** pour ouvrir ClipNotes
2. **Cliquez sur ➕** (bouton "Ajouter")
3. Une fenêtre contextuelle s'ouvre :
   - **Icône** : 
     - Choisissez un emoji via le bouton "😀 Emojis"
     - Ou cliquez sur "🖼️ Image" pour utiliser votre propre image (transformée en thumbnail rond)
   - **Nom du clip** : Texte descriptif qui apparaîtra en tooltip
   - **Contenu** : Le texte/commande que vous voulez sauvegarder
   - **Action (slider)** :
     - 📋 **Copy** : Copie le contenu dans le presse-papier
     - 💻 **Term** : Ouvre un nouveau terminal et exécute la commande
     - 🚀 **Exec** : Exécute la commande en arrière-plan
   - **Bouton "Ajouter"** : Valide et enregistre

4. Votre nouveau clip apparaît immédiatement dans le menu !

**💡 Astuces** :
- Utilisez des emojis pour catégoriser visuellement :
  - 🔗 pour les liens
  - 🐍 pour Python
  - 🐳 pour Docker
  - 💾 pour les commandes système
  - 📧 pour les emails
- Ou utilisez vos propres images (logos, photos, captures d'écran)
- Les couleurs des zones changent selon l'action (orange=copy, vert=term, bleu=exec)

---

### ✏️ Modifier un clip existant

**Activer le mode modification :**
1. **Appuyez sur le raccourci** pour ouvrir ClipNotes
2. **Cliquez sur ✏️** (bouton "Modifier")
3. Le centre du menu s'illumine en **orange** 🟠 avec l'icône ✏️
4. **Cliquez sur le clip** que vous voulez modifier

**Fenêtre d'édition :**
- Les champs sont **pré-remplis** avec les valeurs actuelles
- Le slider est positionné sur l'action actuelle
- Modifiez le nom, l'icône, le contenu et/ou l'action
- Cliquez sur **"Modifier"** pour sauvegarder

**Note :** Si vous changez l'image d'un clip, l'ancien thumbnail est automatiquement supprimé.

**Quitter le mode modification :**
- **Cliquez à nouveau sur ✏️** pour désactiver le mode
- Ou cliquez ailleurs pour fermer le menu

---

### ➖ Supprimer un clip

**Activer le mode suppression :**
1. **Appuyez sur le raccourci** pour ouvrir ClipNotes
2. **Cliquez sur ➖** (bouton "Supprimer")
3. Le centre du menu s'illumine en **rouge** 🔴 avec l'icône ➖
4. **Cliquez sur le clip** à supprimer

**Confirmation :**
- Une boîte de dialogue apparaît : *"Supprimer le clip '[nom]' ?"*
- **Yes** : Le clip et son thumbnail (si image) sont définitivement supprimés
- **No** : Annulation, le clip est conservé

**Quitter le mode suppression :**
- **Cliquez à nouveau sur ➖** pour désactiver le mode
- Ou cliquez ailleurs pour fermer le menu

---

### 📦 Stockage : Sauvegarder et restaurer des clips

Le système de stockage permet de conserver des clips pour différents contextes.

**Stocker des clips :**
1. Cliquez sur **📦** dans le menu principal
2. Un sous-menu radial apparaît avec :
   - **💾 Stocker des clips (Activer le mode stockage)** : Bascule en mode de stockage séquentiel des clips, par simple click
   - **📋 Clips stockés** : Accès à la fenêtre des clips stockés

**Menu de stockage :**
Chaque clip est repésenté selon son ordre de stockage. Il est possible pour chacun de :
- ↩️ : le restaurer
- ✏️ : l'éditer
- 🗑️ : le supprimer définitivement


---

### 📋 Utiliser un clip

**Trois types d'actions possibles :**

1. **📋 Copy (Copier)** :
   - Cliquez sur le clip
   - Le contenu est copié dans le presse-papier
   - Collez avec `Ctrl+V` où vous voulez
   - Les sauts de ligne sont préservés

2. **💻 Term (Terminal)** :
   - Cliquez sur le clip
   - Un nouveau terminal s'ouvre
   - La commande est exécutée
   - Le terminal reste ouvert après l'exécution

3. **⚡ Exec (Exécution)** :
   - Cliquez sur le clip
   - La commande est exécutée en arrière-plan
   - Aucune fenêtre n'apparaît
   - Parfait pour lancer des applications (VSCode, navigateur, etc.)

**Indicateurs visuels :**
- La couleur de la zone du clip indique son action :
  - 🟠 Orange = Copy
  - 🟢 Vert = Term
  - 🔵 Bleu = Exec
- L'icône du clip survolé apparaît au centre du menu
- Un tooltip affiche le contenu complet au survol

---

### ⌨️ Navigation au clavier

ClipNotes est entièrement utilisable au clavier, sans jamais toucher la souris !

**Touches disponibles :**
- **Flèche droite (→)** : Passer au bouton suivant (sens horaire)
- **Flèche gauche (←)** : Passer au bouton précédent (sens anti-horaire)
- **Entrée** : Activer le bouton sélectionné
- **Échap** : Fermer le menu

**Comment ça marche :**

1. **Ouvrir le menu** : Appuyez sur votre raccourci clavier (ex: `Super+V`)
2. **Première navigation** : Appuyez sur `→` ou `←`
   - Le focus s'initialise automatiquement :
     - Sur le **premier clip** s'il y en a
     - Sur le bouton **➕** s'il n'y a pas de clips
3. **Naviguer** : Utilisez `→` et `←` pour parcourir tous les boutons
4. **Activer** : Appuyez sur `Entrée` pour déclencher l'action du bouton sélectionné
5. **Annuler** : Appuyez sur `Échap` pour fermer le menu

**Indicateurs visuels :**
- **Cercle de focus** : Un cercle blanc lumineux entoure le bouton actuellement sélectionné
- **Icône centrale** : L'icône du bouton sélectionné apparaît en grand au centre du menu (si activé dans la config)
- **Tooltip** : Le nom et le contenu du clip s'affichent en dessous du menu

**Exemple de workflow 100% clavier :**
```
1. Super+V          → Ouvrir ClipNotes
2. →                → Aller au premier clip
3. → → →            → Naviguer jusqu'au clip voulu
4. Entrée           → Copier le clip
5. Ctrl+V           → Coller ailleurs
```

**Astuce :** La navigation au clavier est particulièrement utile quand :
- Vous êtes en train de taper et ne voulez pas lâcher le clavier
- Vous utilisez un laptop sans souris
- Vous voulez gagner en rapidité (pas besoin de viser avec la souris)
- Vous préférez garder les mains sur le clavier pour rester concentré

---

### ⚙️ Configuration avancée

Cliquez sur **⚙️** dans le menu principal pour accéder aux options :

**🎨 Couleurs :**
- **Couleur du fond du menu** : Personnaliser le gris de fond
- **Couleurs par action** :
  - Couleur des zones "Copy" (défaut : orange)
  - Couleur des zones "Term" (défaut : vert)
  - Couleur des zones "Exec" (défaut : bleu)
  - Palette complète disponible (rouges, oranges, jaunes, verts, bleus, violets, gris) + ouleurs personnalisées

**🔆 Opacités :**
- **Opacité du menu** : Régler la transparence globale (0-100%)
- **Opacité des zones** :
  - Opacité de base (zones non survolées)
  - Opacité au survol

**⚡ Options :**
- **Icône centrale** : Afficher/masquer l'icône du clip survolé au centre
- **Néon central** : Activer/désactiver l'effet néon pulsé au centre
- **Couleur du néon** : Changer la couleur de l'effet lumineux
- **Vitesse du néon** : Contrôler la vitesse du battement lumineux

**Sauvegarde :**
- Toutes les modifications sont sauvegardées dans `config.json`
- Les paramètres persistent entre les sessions

---

## 🎨 Fonctionnalités avancées

### Tracking du curseur

ClipNotes utilise un système innovant pour apparaître exactement où se trouve votre curseur :

**Comment ça marche :**
- Un **overlay invisible** transparent couvre tout votre écran
- Cet overlay capture la position du curseur en temps réel
- Dès que vous appelez ClipNotes, le menu apparaît aux coordonnées capturées

**Pourquoi c'est malin :**
- Fonctionne sur **X11 et Wayland** sans dépendance externe
- Pas besoin de droits administrateur spéciaux
- Compatible avec tous les environnements de bureau (GNOME, KDE, XFCE, etc.)

**Le défi technique :**
- L'overlay subit les marges du système (barres Ubuntu, zones réservées)
- Ces marges créent un décalage entre la position "théorique" et la position "réelle"
- Solution : système de **corrections calibrées** pour compenser ces marges
- L'écran est divisé en 4 quadrants (gauche/droite/haut/bas) avec une correction spécifique pour chaque

**Avantages :**
- ✅ Aucune dépendance système complexe
- ✅ Fonctionne partout où PyQt6 fonctionne
- ✅ Rafraîchissement ultra-rapide (~60 FPS)
- ✅ Pas de latence perceptible

---

### Animations

- **Ouverture** : Effet de zoom élégant avec courbe InBack
- **Fermeture** : Animation de réduction douce
- **Néon pulsé** : Effet lumineux lors des modes modification/suppression
- **Survol** : Mise en évidence des boutons au passage de la souris

### Gestion intelligente des instances

ClipNotes gère automatiquement les instances multiples :
- **Un seul menu à la fois** : Relancer le raccourci ferme l'ancien et ouvre un nouveau menu
- **Pas de doublons** : Le système de verrouillage empêche les conflits
- **Fermeture propre** : Les ressources sont libérées correctement
- **Lock file** : Fichier `.clipnotes.lock` contenant le PID du processus actif

### Persistance des données

- Tous vos clips sont sauvegardés dans **`clip_notes.json`**
- Format structuré et lisible :
  ```json
  [
    {
      "alias": "🐍 venv",
      "action": "copy",
      "string": "python3 -m venv venv && source venv/bin/activate"
    },
    {
      "alias": "thumbnails/abc123.png",
      "action": "exec",
      "string": "code ."
    }
  ]
  ```
- Thumbnails stockés dans le dossier `thumbnails/` avec noms hashés
- Configuration dans `config.json`
- Groupes de stockage dans `stored_clips.json`
- Rechargement automatique à chaque ouverture

### Support des images

- **Thumbnails ronds** : Vos images sont automatiquement transformées en cercles
- **Optimisation** : Redimensionnement intelligent avec remplissage
- **Gestion automatique** : Création, suppression et mise à jour des thumbnails
- **Hash MD5** : Nommage unique pour éviter les conflits
- **Format PNG** : Conservation de la transparence

### Tri intelligent

Les clips sont automatiquement triés :
1. Par type d'action (Copy → Term → Exec)
2. Alphabétiquement à l'intérieur de chaque groupe
3. Les boutons spéciaux restent toujours en position fixe

---

## 🛠️ Architecture technique

### Structure du projet

```
clipnotes/
├── ClipNotesWindow.py      # Application principale (menu radial, animations)
├── utils.py                 # Fonctions utilitaires (fichiers, emojis, commandes)
├── ui/
│   ├── __init__.py
│   └── EmojiSelector.py     # Sélecteur d'emojis avec pagination
├── launch_clipnotes.sh      # Script de lancement avec gestion d'instances
├── clip_notes.json          # Fichier de données (vos clips)
├── config.json              # Configuration (couleurs, opacités, etc.)
├── stored_clips.json        # Groupes de clips sauvegardés
├── thumbnails/              # Dossier des miniatures d'images
├── emojis.txt               # Liste des emojis disponibles
├── seguiemj.ttf             # Police pour le rendu des emojis
├── requirements.txt         # Dépendances Python
└── README.md                # Ce fichier
```

### Technologies utilisées

- **PyQt6** : Interface graphique et animations
- **Pyperclip** : Gestion du presse-papier système
- **Pillow (PIL)** : Rendu des emojis et traitement d'images
- **JSON** : Format de stockage des données
- **CursorTracker** : Overlay invisible pour capturer la position du curseur

### Concepts clés

1. **Menu radial** : Fenêtre `FramelessWindowHint` + `WindowStaysOnTopHint` avec positionnement dynamique autour du curseur
2. **Animations Qt** : `QPropertyAnimation` pour les effets visuels fluides (zoom, néon, couleurs)
3. **Gestion d'état** : Modes (normal/modification/suppression/stockage) avec indicateurs visuels au centre
4. **Lock file** : Fichier `.clipnotes.lock` contenant le PID pour éviter les instances multiples
5. **CursorTracker** : Widget invisible plein écran qui capture la position du curseur en temps réel
   - Overlay transparent couvrant tout l'écran
   - Récupération des coordonnées via `mouseMoveEvent`
   - Système de corrections pour compenser les marges Ubuntu (zones non-cliquables)
   - Calibration manuelle des offsets (gauche/droite/haut/bas)
   - Rafraîchissement à ~60 FPS via QTimer
6. **Système d'actions** : Architecture modulaire permettant d'associer différentes fonctions (copy/term/exec) aux clips
7. **Thumbnails** : Génération automatique de miniatures rondes avec masque circulaire
8. **Configuration dynamique** : Chargement et sauvegarde des paramètres en JSON

---

## 🛠️ Troubleshooting

### Calibration du positionnement (si le menu n'apparaît pas exactement au curseur)

**Symptôme :** Le menu radial n'apparaît pas pile sur votre curseur, il y a un décalage.

**Cause :** L'overlay utilisé pour capturer la position du curseur subit les marges du système (barres Ubuntu, zones non-cliquables). Ces marges varient selon votre configuration (taille des barres, résolution, etc.).

**Solution :** Ajuster les valeurs de correction dans le code

Le système utilise 4 valeurs de correction pour compenser les marges :

```python
# Dans ClipNotesWindow.py ou le fichier de configuration du tracker
self.x_correction_left = 200    # Correction à gauche
self.x_correction_right = -200  # Correction à droite
self.y_correction_top = 200     # Correction en haut
self.y_correction_bottom = 80   # Correction en bas
```

**Comment calibrer :**

1. **Méthode manuelle** :
   - Lancez ClipNotes
   - Notez où le menu apparaît par rapport à votre curseur
   - Si le menu est trop à gauche : augmentez `x_correction_left`
   - Si le menu est trop à droite : diminuez `x_correction_right` (valeur négative)
   - Si le menu est trop haut : augmentez `y_correction_top`
   - Si le menu est trop bas : augmentez `y_correction_bottom`
   - Testez plusieurs positions (centre, bords, coins) pour trouver les bonnes valeurs

2. **Outil de calibration** (en développement) :
   - Un script automatisé est en cours de développement pour calculer automatiquement les corrections optimales
   - Cet outil affichera des repères visuels pour aider à mesurer les décalages

**Note :** Ces valeurs sont spécifiques à votre configuration système. Si vous changez la résolution, la taille des barres ou le thème, vous devrez peut-être recalibrer.

---

### Le raccourci clavier ne fonctionne pas

**Vérifications :**

1. **Tester le script manuellement** :
   ```bash
   cd /chemin/vers/clipnotes
   ./launch_clipnotes.sh
   ```
   Si ça marche → problème de configuration du raccourci

2. **Vérifier le chemin** dans le raccourci clavier :
   - Utiliser le **chemin absolu complet** du script
   - Exemple : `/home/votre_user/clipnotes/launch_clipnotes.sh`

3. **Permissions** :
   ```bash
   ls -la launch_clipnotes.sh
   # Doit afficher : -rwxr-xr-x (exécutable)
   ```

4. **Tester avec une autre touche** : Certaines combinaisons sont déjà prises

---

### Erreur "ModuleNotFoundError: No module named 'PyQt6'"

**Solution :**
```bash
# Vérifier l'activation de l'environnement virtuel
source venv/bin/activate

# Réinstaller les dépendances
pip install --upgrade -r requirements.txt
```

---

### Erreur "No module named 'ui'"

**Cause :** Structure de dossiers incorrecte.

**Solution :**
```bash
# Vérifier la structure
ls -la ui/
# Doit contenir : __init__.py et EmojiSelector.py

# Si __init__.py manque :
touch ui/__init__.py
```

---

### Le menu est lent à apparaître

**Diagnostic :**
```bash
# Vérifier si plusieurs instances tournent
ps aux | grep ClipNotesWindow

# Nettoyer les processus zombies
pkill -f ClipNotesWindow
rm .clipnotes.lock
```

**Optimisation :**
- Vérifier que le CursorTracker ne subit pas de lag (rafraîchissement à 60 FPS)
- Si le problème persiste, vérifier les pilotes graphiques

---

### Les emojis ne s'affichent pas correctement

**Causes possibles :**
1. Police `seguiemj.ttf` manquante → Vérifier qu'elle est dans le dossier
2. Pillow mal installé → `pip install --upgrade Pillow`

**Test :**
```bash
python3 -c "from PIL import Image; print('Pillow OK')"
```

---

### Les images ne deviennent pas des thumbnails ronds

**Vérifications :**
1. Le dossier `thumbnails/` doit exister (créé automatiquement normalement)
2. Permissions d'écriture :
   ```bash
   ls -ld thumbnails/
   # Devrait afficher drwxr-xr-x
   ```

3. Si le dossier manque :
   ```bash
   mkdir thumbnails
   chmod 755 thumbnails
   ```

---

### Erreur "Permission denied" sur clip_notes.json

**Solution :**
```bash
chmod 644 clip_notes.json
chmod 644 config.json
chmod 644 stored_clips.json
```

---

### Le contenu copié a des `\n` au lieu de sauts de ligne

**Normal !** Les `\n` sont affichés dans le fichier JSON mais correctement convertis lors de l'utilisation.

**Si problème :**
- Vérifier que `paperclip_copy()` dans `utils.py` contient bien :
  ```python
  formatted_string = string.replace(r'\n', '\n')
  ```

---

### Les couleurs ne changent pas après configuration

**Solution :**
1. Vérifier que `config.json` existe et est bien formé
2. Fermer complètement ClipNotes et le relancer :
   ```bash
   pkill -f ClipNotesWindow
   rm .clipnotes.lock
   ./launch_clipnotes.sh
   ```

---

### Logs et débogage

**Activer les logs :**
```bash
# Lancer en mode debug (premier plan)
cd /chemin/vers/clipnotes
python3 ClipNotesWindow.py

# Les messages s'affichent dans le terminal
```

**Vérifier le lock file :**
```bash
cat .clipnotes.lock
# Affiche le PID du processus en cours
```

**Nettoyer complètement :**
```bash
pkill -9 -f ClipNotesWindow
rm -f .clipnotes.lock
rm -f thumbnails/*.png  # Si besoin de réinitialiser les images
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Signaler des bugs via les Issues
- Proposer des améliorations
- Soumettre des Pull Requests

### Idées d'évolution

- [x] Support de catégories/actions pour organiser les clips (copy/term/exec)
- [x] Système de stockage/restauration de groupes de clips
- [x] Personnalisation complète des couleurs et de l'apparence
- [x] Support des images comme icônes
- [x] Navigation complète au clavier (flèches + Entrée)
- [ ] Historique avec recherche
- [ ] Snippets de code avec coloration syntaxique
- [ ] Synchronisation cloud (Dropbox, Google Drive)
- [ ] Raccourcis clavier individuels par clip
- [ ] Mode sombre/clair configurable
- [ ] Support multi-langues
- [ ] Import/export de collections au format JSON

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 👤 Auteur

**Sébastien Dethyre**

Développeur Full-Stack & Ingénieur Test Automation

- 💼 LinkedIn : [Sébastien Dethyre](https://linkedin.com/in/votre-profil)
- 📧 Email : dethyres@hotmail.fr
- 🐙 GitHub : [@SebDethyre](https://github.com/SebDethyre)
- 🌐 Site : [sebastiendethyre.github.io/site](https://sebastiendethyre.github.io/site)

**Compétences démontrées dans ce projet :**
- Architecture d'application PyQt6 avancée
- Animations et interfaces graphiques modernes
- Gestion de fichiers et persistence de données (JSON)
- Traitement d'images (PIL/Pillow)
- Automatisation système (subprocess, shell)
- Conception UX/UI intuitive (souris + clavier)
- Event filtering et gestion des événements clavier globaux
- Gestion d'état complexe
- Documentation technique complète

---

## 🙏 Remerciements

- PyQt6 pour le framework graphique puissant et moderne
- La communauté Python pour les excellentes bibliothèques
- Les contributeurs open-source

---

<p align="center">
  Fait avec ❤️ et beaucoup de ☕
</p>

<p align="center">
  ⭐ Si ClipNotes vous est utile, n'oubliez pas de lui donner une étoile !
</p>
