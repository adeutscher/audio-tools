#!/bin/bash

# This script was made to regenerate
#   the bin/ directory for the sound tools.

# My original system was to make an alias for each sound file.
# This was very time-consuming (~300ms to the 1ms times of other files).

soundsDir="$audioToolsDir/files"
binDir="$audioToolsDir/bin"

if [ -z "$audioToolsDir" ]; then
    printf "Sound tools not defined (audioToolsDir variable).\n" >&2
    exit 1
elif [ ! -d "$soundsDir" ]; then
    printf "Sound directory not found: %s\n" "$soundsDir" >&2
    exit 1
fi

mkdir -p "$binDir"

count=0
while read __file; do
    [ -z "$__file" ] && continue
    # Create a symbolic link to play script.
    # The script will deduce the filename from the $0 variable.
    if ln -s "../scripts/play-sound.py" "$binDir/sound-$(basename "${__file%.*}")" 2> /dev/null; then
        printf 'Created symbolic link for %s\n' "$(basename "$__file")"
        count="$(($count+1))"
    fi
done <<< "$(find "$soundsDir" -type f -name '*mp3' -o -type l -name '*mp3'  2> /dev/null)"

removedCount=0
# Read dead symbolic links
while read __file; do
    [ -z "$__file" ] && continue
    rm "$__file"
    removedCount="$(($removedCount+1))"
done <<< "$(find "$audioToolsDir" -xtype l)"

removedSoundCount=0
# Read links to no-longer-present sounds.
while read __file; do
    [ -z "$__file" ] && continue
    __filename="$(sed 's/sound-//' <<< "$(basename "$__file")").mp3"
    __filepath="$(find "$soundsDir" -name "$__filename" | head -n1)"
    if [ -z "$__filepath" ]; then
        printf "Removing link to missing sound: %s\n" "$__file"
	rm "$__file"
        removedSoundCount="$(($removedSoundCount+1))"
    fi
done <<< "$(find "$binDir" -type l -name 'sound-*')"

printf 'Created %d new symbolic links.\n' "$count"
if (( "$removedCount" )); then
    printf 'Removed %d dead symbolic links.\n' "$removedCount"
fi
if (( "$removedSoundCount" )); then
    printf 'Removed %d missing sound links.\n' "$removedSoundCount"
fi
