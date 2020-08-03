#!/bin/bash

play_local_sound(){
  SOUND_DIR="${audioToolsDir:-"$(readlink -f "$(dirname "$0")/..")"}/files"
  SOUND_FILE="$(find "${SOUND_DIR}" -type f -name '*mp3' 2> /dev/null | shuf | head -n1)"
  if [ -n "${SOUND_FILE}" ]; then
    mpg123 -q "${SOUND_FILE}"
  else
    printf "Count not find a local random sound in directory: %s\n" "${SOUND_FILE}"
  fi
}

play_remote_sound(){
  # Play sound on remote server using audio-server.py.
  output="$(nc "${AUDIO_SERVER}" "${AUDIO_PORT:-4321}" <<< "random")"
  if [[ "${output}" != "played" ]]; then
    if [ -n "${output}" ]; then
      # Print non-played error message if present.
      # If output is empty, then assuming that there is an error that nc has already complained about
      printf "Server error: %s\n" "${output}" >&2
    fi
    exit 1
  fi
}

if [ -z "${AUDIO_SERVER}" ]; then
  play_local_sound
elif [[ "${AUDIO_SERVER_TYPE}" == "google-home" ]]; then
  echo "Random sounds current not supported for Google Home." >&2
  exit 1
else
  play_remote_sound
fi


