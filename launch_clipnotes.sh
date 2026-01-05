#!/bin/bash
source ~/clip_notes_venv/bin/activate
cd ~/repo_seb_dethyre/clip_notes

LOCK_FILE=".clipnotes.lock"

# Si un lock existe, tuer l'ancien process
if [ -f "$LOCK_FILE" ]; then
    OLD_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ]; then
        kill -9 "$OLD_PID" 2>/dev/null
    fi
    rm -f "$LOCK_FILE"
fi

# Lancer le nouveau en arrière-plan
python3 ClipNotesWindow.py >/dev/null 2>&1 &
