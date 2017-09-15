
# audio-tools

This is a module for desktop systems dedicated to playing funny sounds
  and other sound-related functions.

It is useful for either scripted or ad-hoc alerts, especially when
  you need to be away from your machine or if you are working with
  long-running jobs.

## Adding Sound Clips

Sound clips are played with the `mpg123` command.

To add a sound clip, place it anywhere you please in `files/`.
I have created subdirectories here for organization.

After adding the file, you must regenerate the `bin/` directory
  using the `regenerate.sh` script:

```bash
./regenerate.sh
```

The regeneration script is necessary to make the sound files available
  without the relatively time-consuming task of making individual aliases.

Once regenerated, a sound will be available as a `sound-` command. For example,
  `noise.mp3` will be usable as `sound-noise`.
