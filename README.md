
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

## Network Sounds

The script at `scripts/audio-server.py` can be used to get sound requests from remote machines.

Setting targetting environment variables on the client side causes the sound-playing script to send requests via `nc` rather than invoke `mpg123` itself.

### Client Environment Variables

The sound playing script responds to the following variables:

| Variable       | Description                                                                                                                                                                                                                     |
|----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `AUDIO_SERVER` | Server to target for remote sound playing.                                                                                                                                                                                      |
| `AUDIO_PORT`   | Port to use for playing sounds on the remote server. Default: 4321                                                                                                                                                              |
| `AUDIO_UDP`    | Set to a non-zero value to relay sound requests via UDP instead of the default of TCP. Using this mode, the sound script is unable to verify if a sound played successfully unless there was a fundamental error in targetting. |

### Manual Sending

If for some reason you do not want to use environment variables, commands can easily be made manually with `nc`.
  To request a sound, enter the sound name, with or without the `sound-` prefix.

Example:

    echo sound-jobs-done | nc remote-server 4321

You are also able to enter 'list' to list all available sounds.

    echo list | nc remote-server 4321
