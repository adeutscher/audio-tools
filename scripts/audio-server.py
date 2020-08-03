#!/usr/bin/python

'''
This is a super-silly server made to play sounds on a remote server.
The intent was to easily play a sound using only netcat as a client.
'''

from __future__ import print_function
import json,os,random,re,subprocess,sys,time

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

def print_client_message(client, message):
    print('[%s]  %s  %s' % (time.strftime('%Y-%m-%d %I:%M:%S'), colour_text(client, sm.COLOUR_BLUE), message))

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

    def parse_data(self, data):
        
        count = 1
        try:
            cmd_obj = json.loads(data)
            cmd_raw = str(cmd_obj.get('cmd') or '')
            
            try:
                count = int(cmd_obj.get('loop'))
            except (TypeError, ValueError):
                pass
        except json.decoder.JSONDecodeError:
            '''
                JSON decode failed.
                
                If this is legitimate, then it could be:
                    * A old client script that hasn't been updated to the Python version.
                    * A manual request via nc (maybe the system doesn't support Python?)
            '''
            cmd_raw = data
            
        cmd = re.sub(r"(\.mp3)?\n.{0,}", "", cmd_raw, flags=re.IGNORECASE)
        # Cap count per-request at 3
        count = max(1, min(3, count))
        
        return (cmd, count)

    def play_sound(self, header, data):
        # Lop off trailing '.mp3' extension, and everything after the first newline.
        
        
        command, count = self.parse_data(data)
        
        reply = ""

        client = self.session.addr[0]

        if command == "list":
            l = SOUNDS[0].keys()
            l.sort()
            for i in l:
                reply += "%s\n" % i

            print_client_message(client, "Listing requested.")
            return reply

        path = ""
        if command == "random":
            key = random.choice(list(SOUNDS[0].keys()))
            path = SOUNDS[0][key]
        if command in SOUNDS[0]:
            path = SOUNDS[0][command]
        elif command in SOUNDS[1]:
            path = SOUNDS[1][command]

        if command == "random":
            printout = "Random: %s" % colour_path(self.session.addr[0])
        else:
            printout = colour_text(command)
            
        if count > 1:
            printout += ' x%s' % colour_text(count)

        found = False
        if path:
            found = True
            reply = "played\n"
            printout += " (%s)" % colour_path(re.sub('^%s/' % os.environ.get("HOME"), '~/', path))
        else:
            reply = "not-found\n"
            printout += " (%s)" % colour_text("Not found", sm.COLOUR_RED)
        print_client_message(client, printout)

        if found:
            magic_value = 32768 # mpg123 default filter level
            filter_value = int(args[TITLE_VOLUME] / 100.0 * magic_value)

            # Note: 'filter' phrasing is an artifact of older audio terms.
            for i in range(count):
                p = subprocess.Popen(["mpg123", "-f", str(filter_value),"-q", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                p.communicate()
        return reply

def find_mp3_files(path):
    global SOUNDS
    for root, dirs, files in os.walk(path):
        for name in [n for n in files if n.endswith('.mp3')]:
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
