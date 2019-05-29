#!/usr/bin/python

'''
This is a super-silly server made to play sounds on a remote server.
The intent was to easily play a sound using only netcat as a client.
'''

import os,random,re,subprocess,sys

tools_dir = os.environ.get("toolsDir")
if tools_dir:
    sys.path.append(tools_dir + "/scripts/networking/simple-message-servers")
import SimpleMessages as sm
from SimpleMessages import args, colour_path, colour_text
sm.local_files.append(os.path.realpath(__file__))

DEFAULT_AUDIO_PORT = 4321
DEFAULT_VOLUME = 100
TITLE_VOLUME = "volume"

args.add_opt(sm.OPT_TYPE_LONG, "volume", TITLE_VOLUME, "Set volume as a percentage of system volume.", converter=int, default=DEFAULT_VOLUME, default_announce = True)

sm.set_default_port(DEFAULT_AUDIO_PORT)
SOUNDS = [{},{}]

def validate_volume(self):
    if self[TITLE_VOLUME] < 0:
        return "Volume value is too low: %s%%" % colour_text(args[TITLE_VOLUME])
    if self[TITLE_VOLUME] > 200:
        return "Volume value is too high: %s%%" % colour_text(args[TITLE_VOLUME])
args.add_validator(validate_volume)

class AudioServerHandler:
    def __init__(self, session):
        self.session = session
        self.session.reply = not session.udp

    def handle(self, header, data):
        try:
            return self.play_sound(header, data)
        except OSError:
            return "play-error\n"

    def play_sound(self, header, data):
        # Lop off trailing '.mp3' extension, and everything after the first newline.
        command = re.sub(r"(\.mp3)?\n.{0,}", "", data, flags=re.IGNORECASE)
        reply = ""
        if command == "list":
            l = SOUNDS[0].keys()
            l.sort()
            for i in l:
                reply += "%s\n" % i
            print "Client %s:%s requested a listing." % (colour_path(self.session.addr[0]), colour_path(self.session.addr[1]))
            return reply

        path = ""
        if command == "random":
            key = random.choice(SOUNDS[0].keys())
            path = SOUNDS[0][key]
        if command in SOUNDS[0]:
            path = SOUNDS[0][command]
        elif command in SOUNDS[1]:
            path = SOUNDS[1][command]

        if command == "random":
            printout = "Client %s:%s requested a random sound. Choice: %s" % (colour_path(self.session.addr[0]), colour_path(self.session.addr[1]), colour_text(key))
        else:
            printout = "Client %s:%s requested %s sound " % (colour_path(self.session.addr[0]), colour_path(self.session.addr[1]), colour_text(command))
        found = False
        if path:
            found = True
            reply = "played\n"
            printout += " (%s)" % colour_path(re.sub('^%s/' % os.environ.get("HOME"), '~/', path))
        else:
            reply = "not-found\n"
            printout += " (%s)" % colour_text("Not found", sm.COLOUR_RED)
        print printout

        if found:
            magic_value = 32768 # mpg123 default filter level
            filter_value = int(args[TITLE_VOLUME] / 100.0 * magic_value)

            # Note: 'filter' phrasing is an artifact of older audio terms.
            p = subprocess.Popen(["mpg123", "-f", str(filter_value),"-q", path])
            p.communicate()
        return reply

def find_mp3_files(path):
    global SOUNDS
    for root, dirs, files in os.walk(path):
        for name in files:
            if name.endswith(".mp3"):
                s = name.split(".")
                SOUNDS[0][".".join(s[0:len(s)-1])] = os.path.join(root, name)
                SOUNDS[1]["sound-" + ".".join(s[0:len(s)-1])] = os.path.join(root, name) # Super-lazy double-index for "sound-" prefix.

if __name__ == "__main__":
    sm.set_mode_tcp_default()
    args.process(sys.argv)
    directory = find_mp3_files(args.last_operand(os.environ.get("audioToolsDir") + "/files"))
    if args[TITLE_VOLUME] != DEFAULT_VOLUME:
        sm.print_notice("Volume: %s%%" % colour_text(args[TITLE_VOLUME]))
    sm.announce_common_arguments("Playing sounds")
    sm.serve(AudioServerHandler)
