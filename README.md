# 📋 ClipNotes

> Un presse-papier intelligent et ergonomique à portée de curseur

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![ClipNotes Demo](docs/demo.gif)

## ✨ Qu'est-ce que ClipNotes ?

**ClipNotes** est un gestionnaire de presse-papier nouvelle génération qui apparaît instantanément autour de votre curseur. Fini les allers-retours fastidieux pour copier vos liens, commandes, snippets de code ou templates favoris !

### 🎯 Pourquoi ClipNotes ?

- **⚡ Instantané** : Apparaît là où se trouve votre curseur
- **🎨 Élégant** : Interface radiale moderne avec animations fluides
- **😀 Organisé** : Étiquetez vos clips avec des emojis pour une reconnaissance visuelle immédiate
- **🔒 Discret** : Fenêtre légère et transparente qui disparaît quand vous n'en avez pas besoin
- **⌨️ Productif** : Accès par raccourci clavier, pas besoin de la souris

**Cas d'usage typiques :**
- Développeurs : commandes git, snippets de code, URLs de repos
- Designers : codes couleur, liens Figma/Adobe, textes récurrents
- Rédacteurs : templates d'emails, phrases types, liens de références
- DevOps : commandes SSH, chemins serveurs, configurations
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
sudo apt install python3-pip python3-venv xdotool

# Pour Wayland (optionnel, améliore la compatibilité)
sudo apt install python3-pyqt5 python3-pyqt5.qtsvg
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
   PyQt5>=5.15.0
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
3. Cliquez sur un clip pour le copier dans le presse-papier
4. Collez où vous voulez avec `Ctrl+V`

### Interface

```
          📝 (Modifier)
              ↑
    🌿 ←   [CENTRE]   → 🎩
              ↓
          ➕ (Ajouter)
              ↓
          🗑️ (Supprimer)
```

Le menu est organisé en **cercle** avec :
- **Centre** : Indicateur de mode (vide par défaut)
- **Périphérie** : Vos clips étiquetés avec des emojis
- **Boutons de contrôle** : ➕ Ajouter, 📝 Modifier, 🗑️ Supprimer

---

### ➕ Ajouter un nouveau clip

1. **Appuyez sur le raccourci** pour ouvrir ClipNotes
2. **Cliquez sur ➕** (bouton "Ajouter")
3. Une fenêtre contextuelle s'ouvre :
   - **Nom du clip** : Choisissez un emoji + nom descriptif (ex: `🐍 Python venv`)
   - **Bouton "😀 Emojis"** : Ouvre un sélecteur d'emojis pour faciliter le choix
   - **Contenu** : Le texte que vous voulez copier (commande, lien, texte...)
   - **Bouton "Ajouter"** : Valide et enregistre

4. Votre nouveau clip apparaît immédiatement dans le menu !

**💡 Astuce** : Utilisez des emojis pour catégoriser visuellement :
- 🔗 pour les liens
- 🐍 pour Python
- 🐳 pour Docker
- 💾 pour les commandes système
- 📧 pour les emails
- etc.

---

### 📝 Modifier un clip existant

**Activer le mode modification :**
1. **Appuyez sur le raccourci** pour ouvrir ClipNotes
2. **Cliquez sur 📝** (bouton "Modifier")
3. Le centre du menu s'illumine en **orange** 🟠 avec l'icône 📝
4. **Cliquez sur le clip** que vous voulez modifier

**Fenêtre d'édition :**
- Les champs sont **pré-remplis** avec les valeurs actuelles
- Modifiez le nom et/ou le contenu
- Cliquez sur **"Modifier"** pour sauvegarder

**Quitter le mode modification :**
- **Cliquez à nouveau sur 📝** pour désactiver le mode
- Ou cliquez ailleurs pour fermer le menu

---

### 🗑️ Supprimer un clip

**Activer le mode suppression :**
1. **Appuyez sur le raccourci** pour ouvrir ClipNotes
2. **Cliquez sur 🗑️** (bouton "Supprimer")
3. Le centre du menu s'illumine en **rouge** 🔴 avec l'icône 🗑️
4. **Cliquez sur le clip** à supprimer

**Confirmation :**
- Une boîte de dialogue apparaît : *"Supprimer le clip '[nom]' ?"*
- **Yes** : Le clip est définitivement supprimé
- **No** : Annulation, le clip est conservé

**Quitter le mode suppression :**
- **Cliquez à nouveau sur 🗑️** pour désactiver le mode
- Ou cliquez ailleurs pour fermer le menu

---

### 📋 Utiliser un clip

**Simple !**
1. Ouvrez ClipNotes avec votre raccourci
2. Cliquez sur le clip voulu
3. Le contenu est **automatiquement copié** dans le presse-papier
4. Le menu se ferme
5. Collez avec `Ctrl+V` où vous voulez !

**Note :** Les sauts de ligne dans vos clips sont préservés. Parfait pour les commandes multi-lignes !

---

## 🎨 Fonctionnalités avancées

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

### Persistance des données

- Tous vos clips sont sauvegardés dans **`clip_notes.txt`**
- Format simple et lisible : `emoji_nom:contenu`
- Éditable manuellement si besoin (attention à la syntaxe)
- Rechargement automatique à chaque ouverture

---

## 🛠️ Architecture technique

### Structure du projet

```
clipnotes/
├── ClipNotesWindow.py      # Application principale
├── utils.py                 # Fonctions utilitaires (couleurs, fichiers, emojis)
├── ui/
│   ├── __init__.py
│   └── EmojiSelector.py     # Sélecteur d'emojis avec pagination
├── launch_clipnotes.sh      # Script de lancement avec gestion d'instances
├── clip_notes.txt           # Fichier de données (vos clips)
├── emojis.txt               # Liste des emojis disponibles
├── seguiemj.ttf             # Police pour le rendu des emojis
├── requirements.txt         # Dépendances Python
└── README.md                # Ce fichier
```

### Technologies utilisées

- **PyQt5** : Interface graphique et animations
- **Pyperclip** : Gestion du presse-papier système
- **Pillow (PIL)** : Rendu des emojis en images
- **xdotool** : Récupération de la position du curseur (X11)

### Concepts clés

1. **Menu radial** : Fenêtre `FramelessWindowHint` + `WindowStaysOnTopHint` avec positionnement dynamique
2. **Animations Qt** : `QPropertyAnimation` pour les effets visuels fluides
3. **Gestion d'état** : Modes (normal/modification/suppression) avec indicateurs visuels
4. **Lock file** : Fichier `.clipnotes.lock` contenant le PID pour éviter les instances multiples
5. **Auto-détection** : Utilisation de `__file__` pour les chemins (portabilité)

---

## 🐛 Troubleshooting

### Le menu n'apparaît pas au bon endroit (Wayland)

**Symptôme :** Sur le bureau vide, le menu apparaît au centre de l'écran au lieu du curseur.

**Cause :** Restriction de sécurité Wayland qui empêche la récupération de la position du curseur global.

**Solutions :**
1. **Forcer X11** (recommandé) :
   ```bash
   # Déconnectez-vous
   # Sur l'écran de connexion, cliquez sur l'icône ⚙️
   # Sélectionnez "Ubuntu sur Xorg" (ou session X11)
   # Reconnectez-vous
   ```

2. **Accepter la limitation** : Le menu fonctionne correctement quand le curseur est sur une fenêtre d'application (VSCode, navigateur, etc.)

3. **Variable d'environnement** (déjà dans le script) :
   ```bash
   export QT_QPA_PLATFORM=xcb
   ```

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

### Erreur "ModuleNotFoundError: No module named 'PyQt5'"

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
- Vérifier que `xdotool` est installé (plus rapide que le fallback Qt)
- Sur Wayland, forcer X11 améliore les performances

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

### Erreur "Permission denied" sur clip_notes.txt

**Solution :**
```bash
chmod 644 clip_notes.txt
```

---

### Le contenu copié a des `\n` au lieu de sauts de ligne

**Normal !** Les `\n` sont affichés dans le fichier mais correctement convertis lors de la copie.

**Si problème :**
- Vérifier que `paperclip_copy()` dans `utils.py` contient bien :
  ```python
  formatted_string = string.replace(r'\n', '\n')
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
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Signaler des bugs via les Issues
- Proposer des améliorations
- Soumettre des Pull Requests

### Idées d'évolution

- [ ] Support de catégories/dossiers pour organiser les clips
- [ ] Import/export de collections de clips
- [ ] Historique avec recherche
- [ ] Snippets de code avec coloration syntaxique
- [ ] Synchronisation cloud (Dropbox, Google Drive)
- [ ] Raccourcis clavier par clip
- [ ] Mode sombre/clair configurable
- [ ] Support multi-langues

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 👤 Auteur

**Sébastien Dethyre**

- 💼 LinkedIn : [Sébastien Dethyre](https://linkedin.com/in/votre-profil)
- 📧 Email : votre.email@example.com
- 🐙 GitHub : [@votre-username](https://github.com/votre-username)

---

## 🙏 Remerciements

- PyQt5 pour le framework graphique
- La communauté Python pour les excellentes bibliothèques
- Les contributeurs open-source

---

<p align="center">
  Fait avec ❤️ et beaucoup de ☕
</p>

<p align="center">
  ⭐ Si ClipNotes vous est utile, n'oubliez pas de lui donner une étoile !
</p>
