
if qtype mpg123; then

  random-sound(){
    # Notes:
    #   An alias cannot be run as a stored value in a variable.
    #   The name of a function cannot be defined using a variable
    #   Because of the above two notes, we must do the sound search all over again.
    local soundFile="$(find "$soundToolsDir/files" -type f -name '*mp3' 2> /dev/null | shuf | head -n1)"
    if [ -n "$soundFile" ]; then
      mpg123 -q "$soundFile"
    else
      error "$(printf "No sound files found in ${Colour_FilePath}%s${Colour_Off}" "$soundToolsDir/files")"
    fi
  }
fi
