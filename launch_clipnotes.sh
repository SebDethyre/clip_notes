#!/bin/bash
source ~/command_builder_venv/bin/activate
cd ~/repo_seb_dethyre/clip_notes

LOCK_FILE="/tmp/clipnotes.lock"
PID_FILE="/tmp/clipnotes.pid"

# Vérifie si une instance tourne via flock (non-bloquant)
# is_instance_running() {
#     exec 200>"$LOCK_FILE"
#     if ! flock -n 200; then
#         return 0  # Lock pris = instance en cours
#     fi
#     flock -u 200  # Libère immédiatement (on veut juste tester)
#     return 1      # Pas de lock = pas d'instance
# }

# # Si une instance existe, envoyer SIGUSR1 pour fermeture propre
# if is_instance_running; then
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$OLD_PID" ]; then
            # Envoyer signal de fermeture propre
            kill -SIGUSR1 "$OLD_PID" 2>/dev/null
            # Attendre un peu que le process se ferme
            # sleep 0.1
        fi
    fi
# fi

# Lancer ClipNotesWindow
python3 ClipNotesWindow.py &