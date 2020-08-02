#!/usr/bin/env python

import os, re, socket, subprocess, sys

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

class HandlerAudioServer:

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

class HandlerLocal:

    CMD = 'mpg123'

    def __init__(self, runner):
        self.runner = runner

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
