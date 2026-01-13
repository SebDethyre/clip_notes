import pyperclip
import subprocess
import io

import json
import os

from PIL import Image, ImageDraw, ImageFont

from PyQt6.QtGui import QColor, QPixmap, QImage
import re

def is_emoji(s):
    """
    Détecte si une chaîne est un emoji ou un symbole Unicode graphique.
    Version ultra-permissive qui accepte TOUS les emojis.
    """
    if not s:
        return False
    
    # Liste de caractères spéciaux souvent utilisés comme emojis
    # special_chars = {
    #     '⭕', '➕', '➖', '✖', '✔', '✓', '❌', '⚠', '⚡', '★', '☆',
    #     '♥', '♦', '♣', '♠', '◆', '◇', '○', '●', '◎', '◉', '□', '■',
    #     '▲', '▼', '◀', '▶', '△', '▽', '◁', '▷', '☐', '☑', '☒',
    #     '+', '-', '×', '÷', '=', '≠', '≈', '~', '*', '#', '@', '&',
    #     '!', '?', '$', '%', '^', '<', '>', '|', '\\'
    # }
    
    # if s in special_chars:
    #     return True
    
    # Approche ultra-permissive : toutes les plages Unicode possibles d'emojis et symboles
    for char in s:
        code_point = ord(char)
        
        # Ignorer les variation selectors et zero-width joiners
        if code_point in (0xFE0E, 0xFE0F, 0x200D):
            continue
        
        # Toutes les plages possibles d'emojis et symboles graphiques
        if (
            (0x1F000 <= code_point <= 0x1FFFF) or  # Toute la plage Supplementary Multilingual Plane des emojis
            (0x2190 <= code_point <= 0x27BF) or    # Flèches, symboles mathématiques, Dingbats
            (0x2900 <= code_point <= 0x2BFF) or    # Flèches supplémentaires, symboles
            (0x1F300 <= code_point <= 0x1F9FF) or  # Emojis principaux
            (0x1FA00 <= code_point <= 0x1FAFF) or  # Symboles étendus
            (0x2600 <= code_point <= 0x26FF) or    # Symboles divers
            (0x2700 <= code_point <= 0x27BF) or    # Dingbats
            (0x2B00 <= code_point <= 0x2BFF) or    # Symboles divers
            (0x3000 <= code_point <= 0x303F) or    # Symboles CJK
            (0x3200 <= code_point <= 0x32FF) or    # Lettres CJK entre parenthèses
            (0x3300 <= code_point <= 0x33FF)       # Compatibilité CJK
        ):
            return True
    
    return False

def has_rich_formatting(html_content):
    """
    Détecte si un contenu HTML contient du vrai formatting riche 
    (coloration syntaxique, styles, etc.) et pas juste du texte basique.
    
    Returns:
        bool: True si le HTML contient du formatting riche, False sinon
    """
    if not html_content:
        return False
    
    # Patterns indiquant du formatting riche (coloration de code, etc.)
    rich_patterns = [
        'color:',           # Couleur de texte
        'background-color:', # Couleur de fond
        'font-weight:',     # Gras
        'font-style:',      # Italique
        'text-decoration:', # Souligné, etc.
        '<span style=',     # Spans avec styles
        '<font color=',     # Ancienne syntaxe de couleur
        r'rgb\(',           # Couleurs RGB
        r'rgba\(',          # Couleurs RGBA
        r'#[0-9a-fA-F]{3,6}', # Couleurs hex
    ]
    
    # Le HTML basique de QTextEdit ressemble à :
    # <!DOCTYPE ...><html><head>...</head><body style="..."><p style="...">texte</p></body></html>
    # On cherche des styles AU-DELÀ de ce wrapper basique
    
    import re
    for pattern in rich_patterns:
        # Chercher le pattern dans le body (pas dans les meta du head)
        body_match = re.search(r'<body[^>]*>(.*)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            body_content = body_match.group(1)
            if re.search(pattern, body_content, re.IGNORECASE):
                return True
    
    return False

colors = {
    "blanc": (255, 255, 255),
    "noir": (0, 0, 0),
    "rouge": (255, 0, 0),
    "vert": (0, 255, 0),
    "bleu": (0, 0, 255),
    "jaune": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "gris": (128, 128, 128),
    "orange": (255, 165, 0),
    "rose": (255, 192, 203)
}

def couleur_avec_opacite(couleur, opacite):
    """Accepte soit un nom de couleur (str) soit un tuple RGB (r, g, b)"""
    if isinstance(couleur, str):
        # Ancien format : nom de couleur
        r, g, b = colors[couleur]
    else:
        # Nouveau format : tuple RGB
        r, g, b = couleur
    return QColor(r, g, b, opacite)

def emoji_pixmap(emoji_char, size=32):
    
    font = ImageFont.truetype("seguiemj.ttf", size=int(size / 1.5))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((size/2, size/2), emoji_char, font=font, embedded_color=True, anchor="mm")
    
    # Convert PIL Image to QPixmap
    data = io.BytesIO()
    img.save(data, format='PNG')
    qt_img = QImage.fromData(data.getvalue(), "PNG")
    return QPixmap.fromImage(qt_img)

def image_pixmap(path, size=32):
    img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
    data = io.BytesIO()
    img.save(data, format="PNG")
    qt_img = QImage.fromData(data.getvalue(), "PNG")
    return QPixmap.fromImage(qt_img)

def text_pixmap(text, size=32):
    """
    Crée un pixmap avec du texte dont la taille s'adapte à la longueur.
    Plus le texte est long, plus la police est petite.
    """
    text_length = len(text)
    
    # Calcul de la taille de police en fonction de la longueur
    # Formule : plus c'est long, plus c'est petit
    if text_length <= 2:
        font_size = int(size * 0.6)  # ~19px pour size=32
    elif text_length <= 4:
        font_size = int(size * 0.45)  # ~14px
    elif text_length <= 6:
        font_size = int(size * 0.35)  # ~11px
    elif text_length <= 10:
        font_size = int(size * 0.28)  # ~9px
    else:
        font_size = int(size * 0.22)  # ~7px pour les très longs textes
    
    # Utiliser une police système standard
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Dessiner le texte centré
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Centrer le texte
    x = (size - text_width) / 2 - bbox[0]
    y = (size - text_height) / 2 - bbox[1]
    
    # Dessiner le texte en blanc
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    # Convert PIL Image to QPixmap
    data = io.BytesIO()
    img.save(data, format='PNG')
    qt_img = QImage.fromData(data.getvalue(), "PNG")
    return QPixmap.fromImage(qt_img)

def sort_actions_map(actions_map, json_order=None):
    """
    Trie le dictionnaire d'actions selon :
    1. L'action (None d'abord, puis copy, term, exec)
    2. L'ordre du JSON si fourni, sinon alphabétiquement par alias
    
    Retourne une liste d'items triés : [(alias, (action_data, value, action)), ...]
    
    Args:
        actions_map: Le dictionnaire d'actions
        json_order: Dictionnaire optionnel {alias: index} pour l'ordre personnalisé
    """
    # Définir l'ordre de priorité des actions
    action_order = {
        None: 0,    # Boutons d'action (➕, 📝, 🗑️) en premier
        "copy": 1,
        "term": 2,
        "exec": 3
    }
    
    # Convertir le dictionnaire en liste d'items
    items = list(actions_map.items())
    
    # Fonction de tri personnalisée
    def sort_key(item):
        alias, (action_data, value, action) = item
        # Première clé : priorité de l'action
        action_priority = action_order.get(action, 999)
        # Deuxième clé : ordre du JSON si disponible, sinon alphabétique
        if json_order and alias in json_order:
            order_key = json_order[alias]
        else:
            order_key = alias.lower()
        return (action_priority, order_key)
    
    # Trier
    sorted_items = sorted(items, key=sort_key)
    return sorted_items


def get_json_order(file_path):
    """
    Retourne un dictionnaire {alias: index} basé sur l'ordre des entrées dans le JSON.
    """
    if not os.path.exists(file_path):
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {item.get('alias'): i for i, item in enumerate(data) if item.get('alias')}
    except:
        return {}


def reorder_json_clips(file_path, action, new_order):
    """
    Réordonne les clips d'une action spécifique dans le fichier JSON.
    
    Args:
        file_path: Chemin du fichier JSON
        action: L'action concernée ("copy", "term", "exec")
        new_order: Liste des alias dans le nouvel ordre
    """
    if not os.path.exists(file_path):
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return
    
    # Séparer les clips par action
    clips_by_action = {"copy": [], "term": [], "exec": []}
    for item in data:
        item_action = item.get('action', 'copy')
        if item_action in clips_by_action:
            clips_by_action[item_action].append(item)
    
    # Réordonner les clips de l'action concernée selon new_order
    reordered = []
    alias_to_clip = {clip.get('alias'): clip for clip in clips_by_action[action]}
    for alias in new_order:
        if alias in alias_to_clip:
            reordered.append(alias_to_clip[alias])
    
    # Remplacer les clips de cette action par les réordonnés
    clips_by_action[action] = reordered
    
    # Reconstruire la liste complète (copy, term, exec)
    new_data = clips_by_action["copy"] + clips_by_action["term"] + clips_by_action["exec"]
    
    # Sauvegarder
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)

def populate_actions_map_from_file(file_path, actions_map_sub, callback):
    # Déterminer le chemin du fichier JSON
    json_path = file_path.replace('.txt', '.json')
    
    # Lire uniquement depuis le JSON
    if not os.path.exists(json_path):
        print(f"[Info] Fichier JSON introuvable: {json_path}")
        return
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            
        for item in json_data:
            alias = item.get('alias')
            string = item.get('string')
            action = item.get('action', 'copy')
            
            if not alias or not string:
                continue
            
            # Déterminer quelle fonction utiliser selon l'action
            if action == 'copy':
                func = paperclip_copy
            elif action == 'term':
                func = execute_terminal
            elif action == 'exec':
                func = execute_command
            else:
                func = callback  # Fallback
            
            # Format: [(func, [string], {}), string, action]
            actions_map_sub[alias] = [(func, [string], {}), string, action]
            
    except Exception as e:
        print(f"[Erreur lecture JSON] {e}")

def append_to_actions_file(file_path, key, value):
    # Vérifier si la clé existe déjà dans le fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # Vérifier si la clé existe déjà
    for line in lines:
        if line.startswith(f"{key}:"):
            print(f"[Info] La clé '{key}' existe déjà.")
            return
    # Vérifier si la valeur est non vide avant d'ajouter
    if not value.strip():  # Ignore si la valeur est vide ou contient seulement des espaces
        # print("[Info] La valeur est vide. Aucune action effectuée.")
        return
    # Nettoyer les lignes vides existantes dans le fichier
    lines = [line for line in lines if line.strip()]

    # Ajouter la nouvelle ligne si la clé n'existe pas et si la valeur est valide
    with open(file_path, 'w', encoding='utf-8') as f:
        # Réécrire les lignes sans les lignes vides
        f.writelines(lines)
        # Ajouter la nouvelle ligne
        f.write(f"{key}:{value}\n")
        # print(f"[Info] La clé '{key}' a été ajoutée au fichier.")

def append_to_actions_file_json(file_path, alias, string, action="copy", html_string=None):
    """
    Ajoute une entrée dans le fichier JSON d'actions.
    
    Args:
        file_path: Chemin du fichier JSON
        alias: L'alias/clé de l'action
        string: La commande ou chaîne à associer
        action: Type d'action ("copy", "term", "exec"), par défaut "copy"
        html_string: Le contenu HTML formaté (optionnel, pour conserver la coloration)
    """
    # Vérifier si la valeur est non vide
    if not string.strip():
        return
    
    # Charger le fichier JSON existant ou créer une liste vide
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    
    # Vérifier si l'alias existe déjà
    for item in data:
        if item.get("alias") == alias:
            print(f"[Info] L'alias '{alias}' existe déjà.")
            return
    
    # Ajouter la nouvelle entrée
    new_entry = {
        "alias": alias,
        "action": action,
        "string": string
    }
    # Ajouter le HTML seulement s'il est fourni
    if html_string:
        new_entry["html_string"] = html_string
    
    data.append(new_entry)
    
    # Sauvegarder dans le fichier JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    # print(f"[Info] L'alias '{alias}' a été ajouté au fichier.")

def replace_or_append_in_actions_file(file_path, key, value):
    # Vérifie si la valeur est vide ou ne contient que des espaces
    if not value.strip():
        print("[Info] La valeur est vide. Aucune action effectuée.")
        return
    # Préparer la ligne à écrire (en gérant les éventuels sauts de ligne)
    formatted_value = value.replace('\n', '\\n')
    new_line = f"{key}:{formatted_value}\n"
    # Lire les lignes existantes
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # Nettoyer les lignes vides
    lines = [line for line in lines if line.strip()]

    key_found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            lines[i] = new_line
            key_found = True
            # print(f"[Info] La clé '{key}' existait déjà et sa valeur a été remplacée.")
            break
    if not key_found:
        lines.append(new_line)
        # print(f"[Info] La clé '{key}' n'existait pas. Elle a été ajoutée.")

    # Réécriture du fichier
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def replace_or_append_at_lineno(chemin_fichier, clef, valeur, numero_ligne):
    with open(chemin_fichier, 'r', encoding='utf-8') as f:
        # enlève les \n
        lignes = f.read().splitlines()

    # Vérification que le numéro de ligne est valide
    if numero_ligne < 1 or numero_ligne > len(lignes):
        raise ValueError("Le numéro de ligne est en dehors des limites du fichier.")

    # Remplacement de la ligne sans ajouter de \n parasite
    lignes[numero_ligne - 1] = f"{clef}:{valeur}"

    # Réécriture du fichier avec des sauts de ligne explicites
    with open(chemin_fichier, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lignes) + '\n')  # ajoute un \n final propre

def replace_or_append_json(file_path, alias, string, action="copy", html_string=None):
    """
    Remplace une entrée existante ou l'ajoute si elle n'existe pas.
    
    Args:
        file_path: Chemin du fichier JSON
        alias: L'alias/clé de l'action
        string: La commande ou chaîne à associer
        action: Type d'action ("copy", "term", "exec"), par défaut "copy"
        html_string: Le contenu HTML formaté (optionnel, pour conserver la coloration)
    """
    # Vérifier si la valeur est non vide
    if not string.strip():
        return
    
    # Charger le fichier JSON existant ou créer une liste vide
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    
    # Chercher si l'alias existe déjà
    found = False
    for item in data:
        if item.get("alias") == alias:
            # Remplacer les valeurs
            item["string"] = string
            item["action"] = action
            # Gérer le HTML : l'ajouter, le mettre à jour, ou le supprimer
            if html_string:
                item["html_string"] = html_string
            elif "html_string" in item:
                del item["html_string"]  # Supprimer si plus de HTML
            found = True
            print(f"[Info] L'alias '{alias}' a été mis à jour.")
            break
    
    # Si l'alias n'existe pas, l'ajouter
    if not found:
        new_entry = {
            "alias": alias,
            "action": action,
            "string": string
        }
        if html_string:
            new_entry["html_string"] = html_string
        data.append(new_entry)
        print(f"[Info] L'alias '{alias}' a été ajouté.")
    
    # Sauvegarder dans le fichier JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def delete_from_json(file_path, alias):
    """
    Supprime une entrée du fichier JSON.
    
    Args:
        file_path: Chemin du fichier JSON
        alias: L'alias à supprimer
    """
    if not os.path.exists(file_path):
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        data = []
    
    # Filtrer pour retirer l'alias
    data = [item for item in data if item.get('alias') != alias]
    
    # Sauvegarder
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"[Info] L'alias '{alias}' a été supprimé.")

def delete_line_in_file(path, lineno):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if 1 <= lineno <= len(lines):
        del lines[lineno - 1]
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

def remove_from_actions_file(path, name_to_remove):
    with open(path, "r") as f:
        lines = f.readlines()
    with open(path, "w") as f:
        for line in lines:
            if not line.strip().startswith(f"{name_to_remove}:"):
                f.write(line)

def paperclip_copy(string):
    # Remplacer '\\n' par des sauts de ligne réels
    formatted_string = string.replace(r'\n', '\n')
    pyperclip.copy(formatted_string)

def execute_terminal(string):
    # Remplacer '\\n' par des sauts de ligne réels
    formatted_string = string.replace(r'\n', '\n')
    
    # Détecter et ouvrir un nouveau terminal selon l'environnement
    terminals = [
        ['gnome-terminal', '--', 'bash', '-c', formatted_string + '; exec bash'],
        ['konsole', '-e', 'bash', '-c', formatted_string + '; exec bash'],
        ['xterm', '-e', 'bash', '-c', formatted_string + '; exec bash'],
        ['x-terminal-emulator', '-e', 'bash', '-c', formatted_string + '; exec bash'],
    ]
    
    for terminal in terminals:
        try:
            subprocess.Popen(terminal)
            return
        except FileNotFoundError:
            continue
    
    # Si aucun terminal n'est trouvé
    print("Aucun terminal trouvé. Exécution dans le shell actuel...")
    subprocess.run(formatted_string, shell=True)

def execute_command(string):
    formatted_string = string.replace(r'\n', '\n')
    subprocess.Popen(formatted_string, shell=True, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True)  # Détache complètement du processus parent