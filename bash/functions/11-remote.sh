
audio-remote(){
  if [ -z "${3}" ]; then
    error "Usage: audio-remote server port command"
    return 1
  fi
  nc "${1}" "${2}" <<< "${3}"
}
