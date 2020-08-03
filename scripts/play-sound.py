#!/usr/bin/env python

import os, re, socket, subprocess, sys, time
try:
    import pychromecast
    CHROMECAST_IMPORT = True
except ImportError:
    CHROMECAST_IMPORT = False

def _print_message(header_colour, header_text, message, stderr=False):
    f=sys.stdout
    if stderr:
        f=sys.stderr
    print("%s[%s]: %s" % (colour_text(header_text, header_colour), colour_text(os.path.basename(sys.argv[0]), COLOUR_GREEN), message), file=f)

def colour_text(text, colour = None):
    if not colour:
        colour = COLOUR_BOLD
    # A useful shorthand for applying a colour to a string.
    return "%s%s%s" % (colour, text, COLOUR_OFF)

def convert_s2b(msg):
    if sys.version_info.major == 3:
        return bytes(str(msg), 'utf-8')
    return str(msg)
def convert_b2s(msg):
    if sys.version_info.major == 3:
        return str(msg, 'utf-8')
    return str(msg)

def enable_colours(force = False):
    global COLOUR_PURPLE
    global COLOUR_RED
    global COLOUR_GREEN
    global COLOUR_YELLOW
    global COLOUR_BLUE
    global COLOUR_BOLD
    global COLOUR_OFF
    if force or sys.stdout.isatty():
        # Colours for standard output.
        COLOUR_PURPLE = '\033[1;35m'
        COLOUR_RED = '\033[1;91m'
        COLOUR_GREEN = '\033[1;92m'
        COLOUR_YELLOW = '\033[1;93m'
        COLOUR_BLUE = '\033[1;94m'
        COLOUR_BOLD = '\033[1m'
        COLOUR_OFF = '\033[0m'
    else:
        # Set to blank values if not to standard output.
        COLOUR_PURPLE = ''
        COLOUR_RED = ''
        COLOUR_GREEN = ''
        COLOUR_YELLOW = ''
        COLOUR_BLUE = ''
        COLOUR_BOLD = ''
        COLOUR_OFF = ''
enable_colours()

error_count = 0
def print_error(message):
    global error_count
    error_count += 1
    _print_message(COLOUR_RED, "Error", message)

def print_exception(e, msg=None):
    # Shorthand wrapper to handle an exception.
    # msg: Used to provide more context.
    sub_msg = ""
    if msg:
        sub_msg = " (%s)" % msg
    print_error("Unexpected %s%s: %s" % (colour_text(type(e).__name__, COLOUR_RED), sub_msg, str(e)))

def print_notice(message):
    _print_message(COLOUR_BLUE, "Notice", message)

def print_warning(message):
    _print_message(COLOUR_YELLOW, "Warning", message)

class BaseHandler:
    def __init__(self, runner):
        self.runner = runner

class HandlerAudioServer (BaseHandler):

    DEFAULT_PORT = 4321

    def __get_port(self):

        if self.port_raw:
            try:
                port = int(self.port_raw)
            except ValueError:
                return None

        return self.DEFAULT_PORT

    def __get_port_raw(self):
        return os.environ.get('AUDIO_PORT')

    def __init__(self, runner):
        self.runner = runner

    def __is_udp(self):
        u = os.environ.get('AUDIO_UDP')
        if u and not re.search(r'^0+$', u):
            return True
        return False

    is_udp = property(__is_udp)

    def play(self, sound, count):

        if self.port is None:
            print_error('Invalid network port: %s', self.port_raw)
            return

        for i in range(count):
            if not self.play_sound(sound):
                break

    def play_sound(self, sound):

        port = self.port
        server = self.runner.audio_server

        msg = convert_s2b(sound)
        addr = (server, port)
        server_tag = '%s:%s' % (colour_text(server, COLOUR_BLUE), colour_text(port))

        if self.is_udp:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                try:
                    s.sendto(msg, addr)
                    return True
                except Exception as e:
                    print_error('Error sending datagram to %s: %s' % (server_tag, str(e)))
        else:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

                s.settimeout(3)

                try:
                    s.connect(addr)
                    s.send(msg)
                except ConnectionRefusedError:
                    print_error('Connection to %s refused.' % server_tag)
                    return False
                except socket.timeout:
                    print_error('Connection to %s timed out.' % server_tag)
                    return False

                try:
                    reply = convert_b2s(s.recv(1024)).strip()
                except socket.timeout:
                    print_error('Timed out waiting for a reply from  %s.' % server_tag)
                    return False

                if reply == 'played':
                    return True
                else:
                    reply_error_tag = '%s: %s' % (server_tag, colour_text(sound))
                    if reply == 'not-found':
                        print_error('Sound not found on server %s' % reply_error_tag)
                    elif not reply:
                        print_error('Empty response attempting to play sound at %s' % reply_error_tag)
                    return False

    port = property(__get_port)
    port_raw = property(__get_port_raw)

class HandlerGoogleHome(BaseHandler):

    ENV_BASE_HTTP = 'AUDIO_SERVER_BASE_HTTP'
    ENV_BASE_LOCAL = 'AUDIO_SERVER_BASE_LOCAL'

    '''
    Get the base of the URL that the Google Home device will access.
    '''
    def __get_base_http(self):
        return re.sub(r'/$', '', os.environ.get(self.ENV_BASE_HTTP) or '')

    '''
    Get directory that a copy of the available sound files is expected to be in.
    This needs to match, because it is used to construct the URL that the Google
    Home device will access.
    '''
    def __get_base_local(self):
        return os.environ.get(self.ENV_BASE_LOCAL) or ''

    base_http = property(__get_base_http)
    base_local = property(__get_base_local)

    def floor_volume(self, dev):
        vol_prec = dev.status.volume_level
        dev.set_volume(0.0) # Set volum 0 to not hear the 'bloop' sound.
        return vol_prec

    def play(self, sound, count):

        '''
        Original Python approach of using a Python Chromecast library to interact with Google home by 'Giovanni'
        Source: https://www.gioexperience.com/google-home-hack-send-voice-programmaticaly-with-python/

        A hiccup in my original approach at this is that it requires an external source to share the file over HTTP.
        This isn't the end of the world, given things like the network-soundboard script, my core-tools
        module's http-quick-share script, or the stock SimpleHttpServer module. However, it still
        adds a few steps that I'd rather skip if possible.
        '''

        if not self.setup(sound):
            return

        # ToDo: Improve on error handling

        '''
          The original version of the Chromecast script temporarily muted
            the Google device in order to avoid a 'BEEP'. However, I found the
            high and brief 'bip' caused by setting the volume back to be much
            more unpleasant than the longer but lower 'bloop' that came from my device.
          Leaving this in for the moment. Will make it more configurable later.
          # vol_prec=self.floor_volume(dev)
        '''

        mc = self.dev.media_controller # Shorthand
        mc.play_media(self.path_http, "audio/mp3")
        mc.block_until_active()
        mc.pause() # Prepare audio
        time.sleep(1) # Necessary sleep while audio prepares.

        # Reset the volume that was previous set.
        # Currently commented, see above comment.
        #self.dev.set_volume(vol_prec) #setting volume to precedent value

        mc.play() #play the mp3

        # Wait for the item to be done.
        while not mc.status.player_is_idle:
           time.sleep(0.25)
        mc.stop()

    def setup(self, sound):

        global error_count
        old_count = error_count

        if not CHROMECAST_IMPORT:
            mod = 'pychromecast'
            print_error('Could not import %s module. With %s: pip install --user %s' % (coloud_text(mod), colour_text('pip', COLOUR_BLUE), mod))

        if not self.base_http:
            print_error('No base HTTP path set for Google Home (%s environment variable)' % colour_text(self.ENV_BASE_HTTP))
        elif not re.match(r'^https?://', self.base_http, re.IGNORECASE):
            print_error('Invalid base HTTP path (%s environment variable): %s' % (colour_text(self.ENV_BASE_HTTP), colour_text(self.base_http)))

        if not self.base_local:
            print_error('No local audio directory set for Google Home (%s environment variable)' % colour_text(self.ENV_BASE_LOCAL))
        elif not os.path.isdir(self.base_local):
            print_error('No such local directory (%s environment variable): %s' % (colour_text(self.ENV_BASE_LOCAL), colour_text(self.base_local, COLOUR_GREEN)))

        path_file = self.runner.get_sound_file(sound)
        if not path_file:
            # If we cannot find the sound file, then we do not have enough info to make a full URL.
            print_error('Unable to find file for sound: %s' % colour_text(sound))

        self.path_http = '%s/%s' % (self.base_http, re.sub(r'%s/*' % self.base_local, '', path_file))
        '''
            Idea: Could have the client making the request validate the URL
                    by making a request of our own before we ask anything
                    of the Google Home device. If it doesn't give a 200 status code,
                    then it's not worth passing along.

                    Could even go a step further and validate the content as an MP3.
        '''

        try:
            self.dev = pychromecast.Chromecast(self.runner.audio_server)
            self.dev.wait()
        except pychromecast.error.ChromecastConnectionError as e:
            print_error('Google Home Error: %s' % str(e))

        # If there was an uptick in errors since we invoked this function,
        #   then our status is not good.
        return error_count == old_count


class HandlerLocal(BaseHandler):

    CMD = 'mpg123'

    def play(self, sound, count):
        if self.which(self.CMD) is None:
            print_error('Unable to find %s command in any directory in %s' % colour_text(self.CMD, COLOUR_BLUE), colour_text('PATH', COLOUR_PURPLE))
            return

        file_path = self.runner.get_sound_file(sound)
        if not file_path:
            print_error('Unable to find file for sound: %s' % colour_text(sound))
            return

        p = subprocess.Popen([self.CMD, "--loop", str(count), file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.communicate()

    def which(self, program):
        # Credit: "Jay": https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file
        return None

class Runner:

    REPLAY_MAX = 5

    def __get_audio_server(self):
        return os.environ.get('AUDIO_SERVER')

    def __get_replay_count(self):
        count = 1
        if len(sys.argv) > 1:
            try:

                count = int(self.__get_replay_count_raw())
            except ValueError:
                return None
        return max(1, min(self.REPLAY_MAX, count))

    def __get_replay_count_raw(self):
        return sys.argv[-1]

    def __get_sound_name(self):
        # ToDo: Add a way to alternately specify in CLI args.
        return re.sub(r'^sound\-', '', os.path.basename(sys.argv[0]))

    def __init__(self):

        self.sound_dir = os.path.join(os.environ.get('audioToolsDir', os.path.join(os.path.realpath(sys.argv[0]), '..')), 'files')

    audio_server = property(__get_audio_server)

    def get_sound_file(self, sound_name):
        items = {}

        for root, dirs, files in os.walk(self.sound_dir):
            for f in files:
                if re.sub(r'\.mp3', '', f) == sound_name:
                    return os.path.join(root, f)

    def get_handler(self):
        if self.audio_server:
            if os.environ.get('AUDIO_SERVER_TYPE') == 'google-home':
                return HandlerGoogleHome(self)
            return HandlerAudioServer(self)
        return HandlerLocal(self)

    replay_count = property(__get_replay_count)

    def run(self, handler = None):
        sound_name = self.sound_name

        if handler is None:
            handler = self.get_handler()

        if self.replay_count is None:
            print_error('Invalid replay count: %s' % colour_text(self.__get_replay_count_raw()))
            return

        handler.play(sound_name, self.replay_count)

    sound_name = property(__get_sound_name)

if __name__ == '__main__':
    runner = Runner()
    runner.run()
    exit_code = 1
    if error_count == 0:
        exit_code = 0
    exit(exit_code)
