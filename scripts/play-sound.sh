#!/bin/bash

# Deduce filename in $soundToolsDir/files
#   out of $0 and play sound with mpg123

if ! type mpg123 2> /dev/null >&2; then
    printf 'Cannot find mpg123 in PATH variable!\n' >&2
    exit 1
elif [ ! -L "$0" ]; then
    printf 'Do not run this script directly.\n' >&2
    printf 'Should be run through symbolic link created by regenerate.sh script.\n' >&2
    exit 1
fi

soundDir="$soundToolsDir/files"
__filename="$(sed 's/sound-//' <<< "$(basename "$0")").mp3"
__file="$(find "$soundDir" -name "$__filename")"

if [ -z "$__file" ]; then
    printf 'Unable to find %s in %s\n' "$__filename" "$soundDir"
    exit 1
elif [ ! -f "$__file" ]; then
    printf 'Error with locating %s\n' "$__file"
    exit 1
fi

mpg123 -q "$__file"