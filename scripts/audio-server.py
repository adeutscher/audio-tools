#!/usr/bin/python

'''
This is a super-silly server made to play sounds on a remote server.
The intent was to easily play a sound using only netcat as a client.
'''

from __future__ import print_function
import json,os,random,re,subprocess,sys,time

tools_dir = os.environ.get("toolsDir")
if tools_dir:
    sys.path.append(tools_dir + '/scripts/networking/simple-message-servers')
import SimpleMessages as sm
from SimpleMessages import args, colour_path, colour_text
sm.local_files.append(os.path.realpath(__file__))

try:
    if sys.version_info.major == 3:
        # Chromecast module seems to only work for Python3.
        # With Python2 being EoL, that probably won't change in the future.
        import pychromecast
        CHROMECAST_IMPORT = True
except ImportError:
    CHROMECAST_IMPORT = False

DEFAULT_AUDIO_PORT = 4321
DEFAULT_VOLUME = 100
TITLE_VOLUME = "volume"
TITLE_GOOGLE_HOME_IP = 'google-home-ip'
TITLE_GOOGLE_HOME_BASE_URL = 'google-home-base-url'

args.add_opt(sm.OPT_TYPE_LONG, "volume", TITLE_VOLUME, "Set volume as a percentage of system volume.", converter=int, default=DEFAULT_VOLUME, default_announce = True)
args.add_opt(sm.OPT_TYPE_SHORT, 'g', TITLE_GOOGLE_HOME_IP, 'Set IP of Google Home device.', environment = 'AUDIO_SERVER_GOOGLE_HOME_IP')
args.add_opt(sm.OPT_TYPE_LONG, 'base-url', TITLE_GOOGLE_HOME_BASE_URL, 'Set base of URL that Google Home device will use to retrieve files.', environment = 'AUDIO_SERVER_BASE_URL')

sm.set_default_port(DEFAULT_AUDIO_PORT)
SOUNDS = [{},{}]

def print_client_message(client, message):
    print('[%s]  %s  %s' % (time.strftime('%Y-%m-%d %I:%M:%S'), colour_text(client, sm.COLOUR_BLUE), message))

def validate_google_home(self):
    
    errors = []
    
    if not CHROMECAST_IMPORT:
        mod = 'pychromecast'
        if sys.version_info.major == 2:
            # In Python2, the failed import is because we haven't tried to import it.
            #   The import in Python2 failed on my Pi with a syntax error.
            errors.append('The %s module does not work in Python2. Use Python3 instead.' % colour_text(mod))
        else:            
            errors.append('Could not import %s module. With %s: pip install --user %s' % (colour_text(mod), colour_text('pip', sm.COLOUR_BLUE), mod))
    
    if self[TITLE_GOOGLE_HOME_BASE_URL]:
        if not re.match(r'^https?://', self[TITLE_GOOGLE_HOME_BASE_URL], re.IGNORECASE):
            errors.append('Invalid base URL: %s' % colour_text(self[TITLE_GOOGLE_HOME_BASE_URL]))
        if not self[TITLE_GOOGLE_HOME_IP]:
            errors.append('Base URL provided, but Google Home IP was not provided.')
    elif self[TITLE_GOOGLE_HOME_IP]:
        # Implies no base url
        errors.append('Google Home IP was provided, but no base URL was provided.')
        
    return errors
    
args.add_validator(validate_google_home)
    
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
            if args[TITLE_GOOGLE_HOME_IP]:
                self.play_sound_google_home(path, count)
            else:
                self.play_sound_local(path, count)
        return reply
    
    def play_sound_google_home(self, path_file, count):
        
        base_http = re.sub(r'/*$', '', args[TITLE_GOOGLE_HOME_BASE_URL])
        global BASE

        path_http = '%s/%s' % (base_http, re.sub(r'%s/*' % BASE, '', path_file))
        
        try:
            if CHROMECAST_IMPORT:
                dev = pychromecast.Chromecast(args[TITLE_GOOGLE_HOME_IP])
                dev.wait()
        except pychromecast.error.ChromecastConnectionError as e:
            sm.print_error('Google Home Error: %s' % str(e))
            return False
            
        # ToDo: Improve on error handling

        '''
          The original version of the Chromecast script temporarily muted
            the Google device in order to avoid a 'BEEP'. However, I found the
            high and brief 'bip' caused by setting the volume back to be much
            more unpleasant than the longer but lower 'bloop' that came from my device.
        '''

        mc = dev.media_controller # Shorthand
        mc.play_media(path_http, "audio/mp3")
        mc.block_until_active()
        mc.pause() # Prepare audio
        time.sleep(1) # Necessary sleep while audio prepares.

        mc.play() #play the mp3

        # Wait for the item to be done.
        while not mc.status.player_is_idle:
           time.sleep(0.25)
        mc.stop()
            
        return True
        
    def play_sound_local(self, path, count):
        magic_value = 32768 # mpg123 default filter level
        filter_value = int(args[TITLE_VOLUME] / 100.0 * magic_value)

        # Note: 'filter' phrasing is an artifact of older audio terms.
        for i in range(count):
            p = subprocess.Popen(["mpg123", "-f", str(filter_value),"-q", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            p.communicate()

def find_mp3_files(path):
    global BASE
    BASE = path
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
    phrasing = 'Playing sounds'
    if args[TITLE_GOOGLE_HOME_IP]:
        phrasing = 'Tasking Google Home node @ %s' % colour_text(args[TITLE_GOOGLE_HOME_IP], sm.COLOUR_BLUE)
    sm.announce_common_arguments(phrasing)
    sm.serve(AudioServerHandler)
