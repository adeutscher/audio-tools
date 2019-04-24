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
sm.set_default_port(DEFAULT_AUDIO_PORT)
SOUNDS = [{},{}]

class AudioServerHandler:
    def __init__(self, session):
        self.session = session
        self.reply = not session.udp

    def handle(self, header, data):
        return play_sound(data, self.session.addr)

def find_mp3_files(path):
    global SOUNDS
    for root, dirs, files in os.walk(path):
        for name in files:
            if name.endswith(".mp3"):
                s = name.split(".")
                SOUNDS[0][".".join(s[0:len(s)-1])] = os.path.join(root, name)
                SOUNDS[1]["sound-" + ".".join(s[0:len(s)-1])] = os.path.join(root, name) # Super-lazy double-index for "sound-" prefix.

def play_sound(data, addr):
    try:
        # Lop off trailing '.mp3' extension, and everything after the first newline.
        command = re.sub(r"(\.mp3)?\n.{0,}", "", data, flags=re.IGNORECASE)
        reply = ""
        if command == "list":
            l = SOUNDS[0].keys()
            l.sort()
            for i in l:
                reply += "%s\n" % i
            print "Client %s:%s requested a listing." % (colour_path(addr[0]), colour_path(addr[1]))
        else:
            path = ""
            if command == "random":
                key = random.choice(SOUNDS[0].keys())
                path = SOUNDS[0][key]
            if command in SOUNDS[0]:
                path = SOUNDS[0][command]
            elif command in SOUNDS[1]:
                path = SOUNDS[1][command]

            if command == "random":
                printout = "Client %s:%s requested a random sound. Choice: %s" % (colour_path(addr[0]), colour_path(addr[1]), colour_text(key))
            else:
                printout = "Client %s:%s requested %s sound " % (colour_path(addr[0]), colour_text(addr[1]), colour_text(command))
            found = False
            if path:
                found = True
                reply = "played\n"
                printout += "(%s)" % colour_path(re.sub('^%s/' % os.environ.get("HOME"), '~/', path))
            else:
                reply = "not-found\n"
                printout += "(%s)" % colour_text("Not found", sm.COLOUR_RED)
            print printout

            if found:
                p = subprocess.Popen(["mpg123", "-q", path])
                p.communicate()
    except OSError:
        reply = "play-error\n"
    return reply

if __name__ == "__main__":
    sm.set_mode_tcp_default()
    args.process(sys.argv)
    directory = args.last_operand(os.environ.get("audioToolsDir") + "/files")
    find_mp3_files(directory)
    sm.announce_common_arguments("Playing %s sounds in %s" % (colour_text(len(SOUNDS[0])), colour_path(directory)))
    sm.serve(AudioServerHandler)
