
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

fi # end audioToolsDir check
