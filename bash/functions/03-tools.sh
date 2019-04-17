
if [ -n "$audioToolsDir" ]; then

    update-tools-audio(){

        # Make sure that some joker didn't go and unset the audioToolsDir 
        #     variable after this function was defined.
        if [ -z "$audioToolsDir" ]; then
            error 'Audio tools directory is unknown! It should be recorded in the $audioToolsDir variable.'
            return 1
        fi

        update-repo "$audioToolsDir" "sound tools"

        # Confirm the permissions on the module directory
        #     Do this whether or not the SVN update actually succeeded.
        chmod 700 "$audioToolsDir"
    }

  audio-server-set(){
    # Lazy macro function for setting audio server.
    # Tab-completing our way to 'audio-server-set ___' is more convenient
    #   to type than 'export AUDIO_SERVER=___'

    local addr="$(cut -d':' -f1 <<< "${1}" | awk -F' ' '{print $1}')"
    local port="$(cut -d':' -f2 <<< "${2}")"

    if [ -z "${addr}" ]; then
      notice "Clearing out audio server variabls."
      unset AUDIO_SERVER AUDIO_PORT
      return 0
    elif [ -n "${port}" ]; then
      if ! grep -Pq "^\d+$" <<< "${port}" || [ "${port}" -gt 65535 ]; then
        error "$(printf "Invalid port: ${Colour_Bold}%s${Colour_Off}" "${port}")"
        return 1
      fi
    fi

    if grep -Pq "^(([0-9]){1,3}\.){3}([0-9]{1,3})$" <<< "${addr}"; then
      local host="${addr}"
    else
      local host="$(host "${addr}" 2> /dev/null | grep -m1 "has address" | awk '{ print $NF }')"
    fi

    if [ -z "${host}" ]; then
      error "$(printf "Invalid server address: ${Colour_NetworkAddress}%s${Colour_Off}" "${addr}")"
      return 1
    fi

    export AUDIO_SERVER="${host}"
    export AUDIO_PORT="${port:-4321}"

    notice "$(printf "Setting audio server address: ${Colour_NetworkAddress}%s${Colour_Off}:${Colour_NetworkAddress}%d${Colour_Off}" "${host}" "${port:-1234}")"
  }

fi # end audioToolsDir check
