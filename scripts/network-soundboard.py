#!/usr/bin/env python

# Host an ad-hoc soundboard with audio files stored in a directory.

# Based off of (via StackExchange):
#   * https://pymotw.com/2/BaseHTTPServer/index.html#module-BaseHTTPServer
#   * https://docs.python.org/2/library/simplehttpserver.html

import getopt, os, re, socket, sys, urllib

tools_dir = os.environ.get("toolsDir")
if tools_dir:
    sys.path.append(tools_dir + "/scripts/networking/http-servers")
import CoreHttpServer as common

# Specific to browser sharer

import cgi

# Script Content

DEFAULT_DIR = os.getcwd()
audio_dir = os.environ.get("audioToolsDir")
if audio_dir:
    # If possible (and I'm not sure why it wouldn't be),
    #   go to the audio tools directory and serve out of the files.
    DEFAULT_DIR = "%s/files" % audio_dir

def hexit(exit_code):
    print "%s [-a allow-address/range] [-A allow-list-file] [-b bind-address] [-d deny-address/range] [-D deny-list-file] [-h] [-l] [-n] [-p port] [-P] [-r] [-t] [-v]" % os.path.basename(sys.argv[0])
    exit(exit_code)

def process_arguments():

    # Verbose Sharing Arguments

    good = True
    errors = []

    short_opts = common.common_short_opts + "h"
    long_opts = common.common_long_opts

    try:
        opts, flat_args = getopt.gnu_getopt(sys.argv[1:], short_opts, long_opts)
    except getopt.GetoptError as e:
        print "GetoptError: %s" % str(e)
        hexit(1)
    for opt, arg in opts:
        common_good, processed = common.handle_common_argument(opt, arg)
        good = common_good and good

        if processed:
            continue

        if opt in ("-h"):
            hexit(0)

    switch_arg = False

    common.args[common.TITLE_DIR] = DEFAULT_DIR # Default to current directory or audio tools directory.
    if flat_args:
        common.args[common.TITLE_DIR] = flat_args[len(flat_args)-1]

    if len(common.access.errors):
        good = False
        errors.extend(common.access.errors)

    if good:
        common.access.announce_filter_actions()
    else:
        for e in errors:
            common.print_error(e)

    return good

class SimpleHTTPVerboseReqeustHandler(common.CoreHttpServer):

    server_version = "CoreHttpServer (Soundboard Serving)"

    def draw_soundboard(self):
        """Helper to produce a directory listing (absent index.html).
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """

        target_dir = common.args.get(common.TITLE_DIR, DEFAULT_DIR)

        try:
            contents = os.walk(target_dir)
        except:
            return self.send_error(500, "Error accessing directory.")

        content = ""
        for dirname, subdirList, fileList in contents:

            items = []

            if dirname.startswith(target_dir):
                display_name = str.replace(dirname, target_dir, "", 1)
            else:
                display_name = dirname

            if not display_name or display_name == ".":
                display_name = "/"

            attribute_path = re.sub("^\/", "", display_name)

            display_name = re.sub("\/", " / ", display_name)

            for fname in fileList:
                if not fname.endswith(".mp3"):
                    continue
                items.append("\t\t<h3 audio-path=\"%s/%s\" onClick=\"playSound(this)\">%s</h3>\n" % (attribute_path, fname, self.quote_html(re.sub("\.+mp3$", "", fname))))

            if not items:
                continue # Do not bother to report on categories without any audio files.

            content += "\t<h2>%s</h2>\n" % self.quote_html(display_name)
            for item in items:
                content += item

        displaypath = cgi.escape(urllib.unquote(common.args.get(common.TITLE_DIR, DEFAULT_DIR)))

        if not content:
            content = "No audio files found in directory: %s" % displaypath

        htmlContent = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n
<html>
    <head>
        <title>Soundboard: %s</title>
        %s
    </head>
    <body>
        <audio id="audio" autoplay="">This browser does not support HTML5, which is required to use this soundboard.</audio>\n
        %s
    </body>
</html>""" % (displaypath, self.get_soundboard_javascript(), content)
        return self.serve_content(htmlContent);

    def get_soundboard_javascript(self):
        return """
        <script>
        // Declare audio element.
        // Intentionally null for the moment because we have not yet
        // declared the element in HTML. Searching would be pointless.
        var audioElement = null;

        function playSound(el){
            var path = el.getAttribute("audio-path")

            // Mistaken invocation?
            if (path == null)
                return;

            if(audioElement == null)
                // Initialize audio element
                audioElement = document.getElementById("audio");

            audioElement.setAttribute("src", "audio/" + path);
        }
        </script>
"""

    def send_head(self):
        """
        Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """

        search_pattern = "^/audio/+"
        target_dir = common.args.get(common.TITLE_DIR, os.getcwd())

        if self.path == "/":
            # Main directory. Display soundboard.
            return self.draw_soundboard()
        elif re.match(search_pattern, self.path):
            # Request for audio file.
            # Strip out "/audio" from the path, and attempt to reach the path as a file relative to our target directory.
            audio_path = os.path.realpath("%s/%s" % (target_dir, re.sub(search_pattern, "", self.path)))

            # If the requested file path does not end in '.mp3', then then assume that it won't be an audio file.
            # This should not be used as an arbitrary file-sharing server. Immediately 404 out.
            # The file should be an existing audio file.
            if not audio_path.endswith(".mp3") or not (os.path.exists(audio_path) and os.path.isfile(audio_path)):
                return self.send_error(404, "File not found")

            return self.serve_file(audio_path)

        else:
            # For any other path than '/audio', redirect back to '/'.
            return self.send_redirect("/")

if __name__ == '__main__':
    if not process_arguments():
        exit(1)

    bind_address, bind_port, directory = common.get_target_information()

    if not os.path.isdir(directory):
        common.print_error("Path %s does not seem to exist." % common.colour_text(common.COLOUR_GREEN, os.path.realpath(directory)))
        exit(1)

    common.announce_common_arguments("Serving audio")

    common.serve(SimpleHTTPVerboseReqeustHandler, directory)
