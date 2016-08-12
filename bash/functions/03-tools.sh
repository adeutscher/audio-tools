
if [ -n "$soundToolsDir" ]; then

    update-tools-sound(){

        # Make sure that some joker didn't go and unset the soundToolsDir 
        #     variable after this function was defined.
        if [ -z "$soundToolsDir" ]; then
            error 'Sound tools directory is unknown! It should be recorded in the $soundToolsDir variable.'
            return 1
        fi

        update-repo "$soundToolsDir" "sound tools"

        # Confirm the permissions on the module directory
        #     Do this whether or not the SVN update actually succeeded.
        chmod 700 "$soundToolsDir"

    }

fi # end soundToolsDir check
