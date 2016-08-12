
# Play noise based on the return code of the last command.
# Intended to follow things like make commands in order to avoid AND/OR shenanigans.
build-status-noise(){
  if [ "$?" -gt 0 ]; then
    sound-klaxon-submarine
  else
    sound-work-complete
  fi
}
