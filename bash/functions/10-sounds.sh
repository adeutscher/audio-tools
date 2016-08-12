
if qtype mpg123; then

   for soundFile in $(find "$soundToolsDir/files" -type f -name '*mp3' 2> /dev/null); do
       alias sound-$(basename "${soundFile%.*}")="mpg123 -q '$soundFile'"
   done

fi
