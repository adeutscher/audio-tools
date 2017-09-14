
# sound-tools

This is a module for desktop systems dedicated to playing funny sounds.

It is useful for either scripted or ad-hoc alerts, especially when
  you need to be away from your machine or if you are working with
  long-running jobs.

## Adding Sound Clips

To add a sound clip, place it anywhere you please in `files/`.
I have created subdirectories here for organization.

After adding the file, you must regenerate the `bin/` directory
  using the `regenerate.sh` script:

```
./regenerate.sh
```

The regeneration script is necessary to make the sound files available
  without the relatively time-consuming task of making individual aliases.
