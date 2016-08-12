if qtype battery-short; then

    battery-watch(){
        local threshold=${1:-15}

        if ! __pgrep "^\d*$" <<< "$threshold" || [ "$threshold" -lt 1 ] || [ "$threshold" -gt 100 ]; then
            error "Threshold must be an integer between 1 and 100 inclusive."
        fi

        if ! qtype sound-alarm-metal-gear sound-pokemon-pikachu sound-stargate-alert; then
            error "$(printf "Some necessary commands for the battery alert were not found! Please debug the $Colour_BIBlue%s$Colour_Off function!" "battery-watch")"
        fi

        notice "$(printf "Alarm will sound if the battery goes below %d%%." "$threshold")"

        # Do a sleep-loop until the battery is low enough.
        # Reminder: Ctrl-C'ing will successfully abort the entire function and skip the alerm.
        while [ "$(battery-short)" -gt "$threshold" ]; do sleep 20; done

        local message="$(printf "Battery power lower than %d%%!" "$threshold")"

        # Also try to send a desktop message via notify-send for good measure,
        #     but none of the printouts are as important as the sound itself.
        timeout 0.5 notify-send --icon=esd "$message" 2> /dev/null >&2
        notice "$message"

        sound-alarm-metal-gear; sound-pokemon-pikachu; sound-stargate-alert; sound-stargate-alert; sound-stargate-alert; sound-pokemon-pikachu

    }

fi
