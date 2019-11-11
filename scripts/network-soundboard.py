#!/usr/bin/env python

# Host an ad-hoc soundboard with audio files stored in a directory.

# Based off of (via StackExchange):
#   * https://pymotw.com/2/BaseHTTPServer/index.html#module-BaseHTTPServer
#   * https://docs.python.org/2/library/simplehttpserver.html

import getopt, os, re, socket, sys

if sys.version_info[0] == 2:
    from urlparse import unquote
else:
    from urllib.parse import unquote

tools_dir = os.environ.get("toolsDir")
if tools_dir:
    sys.path.append(tools_dir + "/scripts/networking/http-servers")
import CoreHttpServer as common
common.local_files.append(os.path.realpath(__file__))

# Remove unused arguments
del common.args.opts[common.OPT_TYPE_FLAG]["-P"]
common.args.add_validator(common.validate_common_directory) # Validate directory.

# Specific to browser sharer

import cgi

# Script Content

audio_dir = os.environ.get("audioToolsDir")
if audio_dir:
    # If possible (and I'm not sure why it wouldn't be),
    #   go to the audio tools directory and serve out of the files.
    common.DEFAULT_TARGET = "%s/files" % audio_dir

class SimpleHTTPVerboseReqeustHandler(common.CoreHttpServer):

    server_version = "CoreHttpServer (Soundboard Serving)"

    """
    Expected file extensions for HTML5-compatible formats.

    Note that some browsers may not support all of the
    below formats.
    """
    audio_extensions = [ "mp3", "ogg", "wav" ]

    def draw_soundboard(self):
        """Helper to produce a directory listing (absent index.html).
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """

        target_dir = common.get_target()

        try:
            raw_contents = os.walk(target_dir)
        except:
            return self.send_error(500, "Error accessing directory.")

        content = ""

        contents = []

        for dirname, subdirList, fileList in raw_contents:
            # Move from the object returned by walk() to a list.
            contents.append((dirname, fileList))

        for dirname, fileList in sorted(contents, key=lambda entry: entry[0]):
            # Cycle through our list of items, sorted by directory name.
            items = []

            if dirname.startswith(target_dir):
                display_name = str.replace(dirname, target_dir, "", 1)
            else:
                display_name = dirname

            if not display_name or display_name == ".":
                display_name = "/"

            attribute_path = re.sub("^\/", "", display_name)

            display_name = re.sub("\/", " / ", display_name)

            for fname in sorted(fileList):
                if not self.is_audio_file(fname):
                    continue
                items.append("""
                <li class="sound-item"><span audio-path=\"%s/%s\" onClick=\"playSound(this)\">%s</span></li>
                """ % (attribute_path, fname, self.quote_html(re.sub("\.+(%s)$" % "|".join(self.audio_extensions), "", fname))))

            if not items:
                continue # Do not bother to report on categories without any audio files.

            content += """<div class="sound-section"><h2>%s</h2><ul class="sound-list">%s</ul>\n""" % (self.quote_html(display_name), "\n".join(items))

        displaypath = cgi.escape(unquote(common.get_target()))

        if not content:
            content = "No audio files found in directory: %s" % displaypath

        htmlContent = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n
<html>
    <head>
        <title>Soundboard: %s</title>
        %s
        %s
    </head>
    <body>
        <audio id="audio" autoplay="">This browser does not support HTML5, which is required to use this soundboard.</audio>\n
        %s
    </body>
</html>""" % (displaypath, self.get_soundboard_css(), self.get_soundboard_javascript(), content)
        return self.serve_content(htmlContent);

    def get_soundboard_css(self):
        return """
        <style>

        ul.sound-list li.sound-item {
            display: block;
        }
        </style>"""

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
        </script>"""

    def is_audio_file(self, path):
        """
        Check to see if the file path appears to be an audio file.

        At the moment and for the foreseeable future,
        this is just a file extension check. This isn't a serious
        enough situation to need to do anything deeper.

        Additional note: Some browsers may not support the playing of
                         all extensions through <audio> tags.
        """

        # Get our extension, and flatten it to lowercase.
        ext = path.split(".")[-1].lower()

        return (ext in self.audio_extensions)

    def send_head(self):
        """
        Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """

        # Search pattern indicating a file request.
        search_pattern = "^/audio/+"

        path = getattr(self, common.ATTR_PATH, "/")

        if path == "/":
            # Main directory. Display soundboard.
            return self.draw_soundboard()
        elif path.lower() == "/favicon.ico":
            return self.send_error(404, "File not found.")
        elif re.match(search_pattern, path):
            # Request for audio file.

            # Strip out "/audio" from the path, and attempt to reach the path as a file relative to our target directory.
            audio_path = os.path.realpath("%s/%s" % (common.get_target(), self.translate_path(re.sub(search_pattern, "", path), False)))

            # If the requested file path does appear to be a sound file, then immediately 404 out.
            # This script should not be used as an arbitrary file-sharing server.
            # That's exactly what the verbose share script was made for.
            # The file should be an existing audio file.
            if not self.is_audio_file(audio_path) or not (os.path.exists(audio_path) and os.path.isfile(audio_path)):
                return self.send_error(404, "File not found")

            return self.serve_file(audio_path)

        else:
            # For any other path than '/audio', redirect back to '/'.
            return self.send_redirect("/")

if __name__ == '__main__':
    common.args.process(sys.argv)

    bind_address, bind_port, directory = common.get_target_information()

    common.announce_common_arguments("Serving audio")

    common.serve(SimpleHTTPVerboseReqeustHandler, directory)
