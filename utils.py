import pyperclip
import subprocess
import io
from PIL import Image, ImageDraw, ImageFont

from PyQt6.QtGui import QColor, QPixmap, QImage
import re

def is_emoji(s):
    # emojis usuels
    return bool(re.match(r"[\U0001F300-\U0001FAFF]", s))

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

def couleur_avec_opacite(nom_couleur, opacite):
    r, g, b = colors[nom_couleur]
    return QColor(r, g, b, opacite)

def emoji_pixmap(emoji_char, size=32):
    
    font = ImageFont.truetype("/home/simon/Téléchargements/sandbox/radial_menu/seguiemj.ttf", size=int(size / 1.5))
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

def populate_actions_map_from_file(file_path, actions_map_sub, callback):
    with open(file_path, 'r', encoding='utf-8') as f:
        for lineno, line in enumerate(f, start=1):
            # Supprime les espaces superflus avant et après la ligne
            line = line.strip()
            # Ignore les lignes vides ou celles commentées
            if not line or line.startswith("#"):
                continue
            try:
                key, value = line.split(":", 1)
                actions_map_sub[key] = [(callback, [value], {}), value, lineno]
            except ValueError as e:
                print(f"[Erreur de parsing] Ligne: {line}\n → {e}")

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