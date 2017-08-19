
alias watch-ssh-connections="watch-connections-alert 22 sound-stargate-wormhole-open sound-stargate-wormhole-close"

# Keep an eye on our tally of incoming connections.
# Play a sound if there are new/closed connections since the last check.
watch-connections-alert(){

  # Port to watch for.
  local target_port=$1

  if [ -z "$target_port" ]; then
    error "No port number specified."
    return 1
  elif ! grep -Pq "^\d+$" <<< "$target_port" || [ "$target_port" -ge 65536 ] || [ "$target_port" -le 0 ]; then
    error "$(printf "Invalid port: ${Colour_Bold}%s${Colour_Off}" "$target_port")"
    return 1
  fi

  # Assign arguments to variables or fall back to defaults.
  more_connections=${2:-sound-sombra-boop}
  fewer_connections=${3:-sound-meep-meep}

  if ! qtype $more_connections $fewer_connections; then
    error "$(printf "Sound commands not found (More: ${Colour_Command}%s${Colour_Off}, Less: ${Colour_Command}%s${Colour_Off})" "$more_connections" "$fewer_connections")"
    return 1
  fi

  local ephemeral_lower=$(cat "/proc/sys/net/ipv4/ip_local_port_range" | awk '{ print $1 }')

  # At the moment, this function works by tracking the total number of incoming connections on the targetted port.
  # The flaw in this is that if a connection were terminated and a new one made in between loops no event would be triggered.
  # A more sophisticated way of going about this would be to also track source ports/addresses, but that is a bridge too far at the moment.

  # A note on playing: The which/awk/sed shenanigans are necessary because BASH will not play an alias from a variable.
  #                      It's super annoying.
  #                      A consequence of this is that this function in theory would not play nice with files that include single quotes in their paths.

  while (( 1 )); do
    local new_connections_count="$(netstat -Wtun | grep ESTABLISHED  | awk -F' ' '{ match($4,/[1-90]*$/,a); l[2]=a[0]; sub(/:[1-90]*$/,"",$4); l[1]=$4; match($5,/[1-90]*$/,a); r[2]=a[0]; sub(/:[1-90]*$/,"",$5); r[1]=$5; if(l[2] < '${ephemeral_lower}' && (r[2] > '${ephemeral_lower}' || $1 ~ /^tcp/) && ! (r[2] == 2049 && $1 ~ /^tcp/)){ print l[1] " " l[2] }; }' | grep --colour=never -Pvw '(127\.0\.0\.1|::1)' | cut -d' ' -f2 | grep -w "$target_port" | wc -l)"

    if [ "$new_connections_count" -gt "${connections_count:-0}" ]; then
      # One or more new connections since last loop.
      mpg123 -q $(which $more_connections | head -n1 | sed -e "s/^.*='//g" -e "s/\\\''//g" -e "s/'//g" | awk -F' ' '{$1=""; $2=""; print $0}')
    elif [ "$new_connections_count" -lt "${connections_count:-0}" ]; then
      # One or more connections has terminated since the last loop.
      mpg123 -q $(which $fewer_connections | head -n1 | sed -e "s/^.*='//g" -e "s/\\\''//g" -e "s/'//g" | awk -F' ' '{$1=""; $2=""; print $0}')
    fi
    local connections_count="$new_connections_count"
    sleep 1
  done


}
