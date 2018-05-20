#!/bin/bash

# Watch for opening/closing connections on the specified TCP port.
# When an open/close is detected, play a sound.

# Common message functions.

set_colours(){
  # Define colours
  BLUE='\033[1;34m'
  GREEN='\033[1;32m'
  RED='\033[1;31m'
  YELLOW='\033[1;93m'
  PURPLE='\033[1;95m'
  BOLD='\033[1m'
  NC='\033[0m' # No Color
}
[ -t 1 ] && set_colours

error(){
  printf "${RED}"'Error'"${NC}"'['"${GREEN}"'%s'"${NC}"']: %s\n' "$(basename "${0}")" "${@}"
  __error_count=$((${__error_count:-0}+1))
}

notice(){
  printf "${BLUE}"'Notice'"${NC}"'['"${GREEN}"'%s'"${NC}"']: %s\n' "$(basename "${0}")" "${@}"
}

notice_closed(){
  printf "${RED}"'Closed'"${NC}"'['"${GREEN}"'%s'"${NC}"']: %s\n' "$(basename "${0}")" "${@}"
}

notice_new(){
  printf "${GREEN}"'New'"${NC}"'['"${GREEN}"'%s'"${NC}"']: %s\n' "$(basename "${0}")" "${@}"
}

# Script Functions
##

set_new_connections(){
  local new_connections_raw="$(netstat -tn 2> /dev/null \
    | grep -P "^tcp\s" \
    | grep ESTABLISHED \
    | sed 's/:/ /g' \
    | awk -F' ' '
    {
      if($7 > $5 && $5=='${target_port}' && substr($4,0,3)!=127){
        print $1" "$4" "$6" "$5" "$7;
      }
    }')"
  new_connections_count=0
  unset new_sources
  unset new_ports
  unset new_checksums
  # Set new connections into an array.
  while read new_connection; do
    [ -n "${new_connection}" ] || continue

    new_sources[${new_connections_count}]="$(cut -d' ' -f3 <<< "${new_connection}")"
    new_ports[${new_connections_count}]="$(cut -d' ' -f4 <<< "${new_connection}")"
    new_checksums[${new_connections_count}]="$(cksum <<< "${new_connection}")"

    new_connections_count="$((${new_connections_count}+1))"
  done <<< "${new_connections_raw}"
}

# Transfer new connections to old connections
set_old_connections(){
  old_connections_count=0
  unset old_sources
  unset old_ports
  unset old_checksums
  while [ "${old_connections_count}" -lt "${new_connections_count}" ]; do
    old_sources[${old_connections_count}]="${new_sources[${old_connections_count}]}"
    old_ports[${old_connections_count}]="${new_ports[${old_connections_count}]}"
    old_checksums[${old_connections_count}]="${new_checksums[${old_connections_count}]}"

    old_connections_count="$((${old_connections_count}+1))"
  done
}

# Keep an eye on our tally of incoming connections.
# Play a sound if there are new/closed connections since the last check.
watch_connections_alert(){

  # Port to watch for.
  target_port=$1

  if [ -z "$target_port" ]; then
    error "No port number specified."
  elif ! grep -Pq "^\d+$" <<< "$target_port" || [ "$target_port" -ge 65536 ] || [ "$target_port" -le 0 ]; then
    error "$(printf "Invalid port: ${BOLD}%s${NC}" "$target_port")"
  fi

  # Assign arguments to variables or fall back to defaults.
  command_new_connections="${2:-sound-sombra-boop}"
  command_closed_connections="${3:-sound-meep-meep}"

  if ! type "${command_new_connections}" 2> /dev/null >&2; then
    error "$(printf "New connection sound command not found: ${BLUE}%s${NC}" "${command_new_connections}")"
  elif ! grep -Pq "^sound-" <<< "${command_new_connections}"; then
    error "$(printf "New connection command is not an audio-tools sound: ${BLUE}%s${NC}" "${command_new_connections}")"
  fi

  if ! type "${command_closed_connections}" 2> /dev/null >&2; then
    error "$(printf "Closed connection sound command not found: ${BLUE}%s${NC}" "${command_old_connections}")"
  elif ! grep -Pq "^sound-" <<< "${command_new_connections}"; then
    error "$(printf "Closed connection command is not an audio-tools sound: ${BLUE}%s${NC}" "${command_old_connections}")"
  fi

  # Exit if any errors were raised.
  (( "${__error_count:-0}" )) && exit 1

  notice "$(printf "Playing alerts for remote connections on ${BOLD}tcp/%d${NC}" "${target_port}")"
  notice "$(printf "Sound on new connections: ${BLUE}%s${NC}" "${command_new_connections}")"
  notice "$(printf "Sound on closed connections: ${BLUE}%s${NC}" "${command_closed_connections}")"

  # Set initial values so that the status quo at invocation time does not trigger a sound.
  set_new_connections
  set_old_connections

  # Loop forever.
  while (( 1 )); do

    set_new_connections

    i=0
    have_new=0
    # If a connection is in the new array but not the old one, then it is new since the last interval.
    while [ "${i}" -lt "${new_connections_count:-0}" ]; do
      ii=0
      present=0
      while ! (( "${present}" )) && [ "${ii}" -lt "${old_connections_count:-0}" ]; do
        [[ "${new_checksums[${i}]}" == "${old_checksums[${ii}]}" ]] && present=1
        ii="$((${ii}+1))"
      done

      if ! (( "${present}" )); then
        notice_new "$(printf "${GREEN}New${NC} connection: ${GREEN}%s${NC} on ${BOLD}tcp/%s${NC}" "${new_sources[${i}]}" "${new_ports[${i}]}")"
        have_new=1
      fi
      i="$((${i}+1))"
    done
    # Only play new-sound once, despite how many new connections might have opened.
    (( "${have_new}" )) && "${command_new_connections}"

    i=0
    have_closed=0
    # If a connection is in the old array but not the new one, then it has closed since the last interval.
    while [ "${i}" -lt "${old_connections_count:-0}" ]; do
      ii=0
      present=0
      while ! (( "${present}" )) && [ "${ii}" -lt "${new_connections_count:-0}" ]; do
        [[ "${old_checksums[${i}]}" == "${new_checksums[${ii}]}" ]] && present=1
        ii="$((${ii}+1))"
      done

      if ! (( "${present}" )); then
        notice_closed "$(printf "${RED}Closed${NC} connection: ${GREEN}%s${NC} on ${BOLD}tcp/%s${NC}" "${old_sources[${i}]}" "${old_ports[${i}]}")"
        have_closed=1
      fi
      i="$((${i}+1))"
    done
    # Only play closed-sound once, despite how many connections might have closed.
    (( "${have_closed}" )) && "${command_closed_connections}"

    # Transfer new connections to old connections;
    set_old_connections

    sleep 1
  done
}

watch_connections_alert $@
