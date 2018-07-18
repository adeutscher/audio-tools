#!/bin/bash

# Deduce filename in $audioToolsDir/files
#   out of $0 and play sound.

# Set AUDIO_SERVER (and optionally AUDIO_PORT) to play on remote server instead of local machine.

play_local_sound(){
  # Play sound on local machine using mpg123.

  if ! type mpg123 2> /dev/null >&2; then
    printf 'Cannot find mpg123 in PATH variable!\n' >&2
    exit 1
  elif [ ! -L "${0}" ]; then
    printf 'Do not run this script directly.\n' >&2
    printf 'Should be run through symbolic link created by regenerate.sh script.\n' >&2
    exit 1
  fi

  SOUND_PATH="$(find "${SOUND_DIR}" -name "${SOUND_NAME}" 2> /dev/null | head -n1)"
  if [ -z "$SOUND_PATH" ]; then
    printf 'Unable to find %s in %s\n' "${SOUND_NAME}" "${SOUND_DIR}"
    exit 1
  elif [ ! -f "${SOUND_PATH}" ]; then
    printf 'Error with locating %s\n' "${SOUND_PATH}"
    exit 1
  fi

  mpg123 -q "${SOUND_PATH}"
}

play_remote_sound(){
  # Play sound on remote server using audio-server.py.

  port=${AUDIO_PORT:-4321}
  output="$(nc "${AUDIO_SERVER}" "${port}" <<< "${SOUND_NAME}")"
  if [[ "${output}" != "played" ]]; then
    if [ -n "${output}" ]; then
      # Print non-played error message if present.
      printf "Server error (%s:%s): %s\n" "${AUDIO_SERVER}" "${port}" "${output}" >&2
    else
      # If output is empty, then assuming that there is an error that nc has already complained about
      # However, what nc (without a -v switch) does NOT cover
      #   is a reminder of which server/port that we are trying
      #   to connect to.
      printf "No response from server: %s:%s\n" "${AUDIO_SERVER}" "${port}" >&2
    fi
    exit 1
  fi
}

SOUND_DIR="${audioToolsDir:-"$(readlink -f "$(dirname "$0")/..")"}/files"
SOUND_NAME="$(sed 's/sound-//' <<< "$(basename "$0")").mp3"

if [ -n "${AUDIO_SERVER}" ]; then
  play_remote_sound
else
  play_local_sound
fi
