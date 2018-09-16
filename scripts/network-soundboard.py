#!/usr/bin/env python

# Based off of (via StackExchange):
#   * https://pymotw.com/2/BaseHTTPServer/index.html#module-BaseHTTPServer
#   * https://docs.python.org/2/library/simplehttpserver.html

import getopt, os, re, socket, sys, urllib

tools_dir = os.environ.get("toolsDir")
if tools_dir:
    sys.path.append(tools_dir + "/scripts/networking/http-servers")
import CoreHttpServer as common

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# Specific to browser sharer

import cgi

# Script Content

DEFAULT_DIR = os.getcwd()
audio_dir = os.environ.get("audioToolsDir")
if audio_dir:
    # If possible (and I'm not sure why it wouldn't be),
    #   go to the audio tools directory and serve out of the files.
    DEFAULT_DIR = "%s/files"

TITLE_LOCAL_LINKS = "locallinks"

def hexit(exit_code):
    print "%s [-a allow-address/range] [-A allow-list-file] [-b bind-address] [-d deny-address/range] [-D deny-list-file] [-h] [-l] [-n] [-p port] [-P] [-r] [-t] [-v]" % os.path.basename(sys.argv[0])
    exit(exit_code)

def process_arguments():

    # Verbose Sharing Arguments

    good = True
    errors = []

    short_opts = common.common_short_opts + "hlnrt"
    long_opts = common.common_long_opts + [ "--local-links", "--no-links" ]

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
        elif opt in ("-l", "--local-links"):
            common.args[TITLE_LOCAL_LINKS] = True
        elif opt in ("-n", "--no-links"):
            common.args[TITLE_NO_LINKS] = True
        elif opt in ("-r"):
            common.args[TITLE_REVERSE] = True
        elif opt in ("-t"):
            common.args[TITLE_TIMESORT] = True

    switch_arg = False

    common.args[common.TITLE_DIR] = os.getcwd() # Default to current directory.
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

    server_version = "CoreHttpServer (Content Serving)"

    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

    def humansize(self, nbytes):
        if nbytes == 0: return '0B'
        i = 0
        while nbytes >= 1024 and i < len(self.suffixes)-1:
            nbytes /= 1024.
            i += 1
        f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
        return '%s%s' % (f, self.suffixes[i])

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
            display_name = re.sub("\/", " / ", display_name)

            for fname in fileList:
                if not fname.endswith(".mp3"):
                    continue
                items.append("\t\t<h3>%s</h3>\n" % self.quote_html(re.sub("\.+mp3$", "", fname)))

            if not items:
                continue

            content += "\t<h2>%s</h2>\n" % self.quote_html(display_name)
            for item in items:
                content += item

        f = StringIO()
        displaypath = cgi.escape(urllib.unquote(common.args.get(common.TITLE_DIR, DEFAULT_DIR)))
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n')
        f.write("<html>\n<title>Soundboard: %s</title>\n" % displaypath)
        f.write("<body>\n")
        f.write(content)
        f.write("</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f


        if common.args.get(TITLE_TIMESORT, DEFAULT_TIMESORT):
            itemlist.sort(key=lambda a: os.path.getmtime(os.path.join(path, a)), reverse = reverse_order)
        else:
            itemlist.sort(key=lambda a: a.lower(), reverse = reverse_order)



        if not self.path == "/":
            f.write('        <li><a href="..">%s</a></li>\n' % cgi.escape("<UP ONE LEVEL>"))
        for name in itemlist:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            extrainfo = ""
            reachable = True

            if os.path.islink(fullname):
                # Note: a link to a directory displays with @ and links with /
                displayname = name + "@"
                reachable = not (common.args.get(TITLE_NO_LINKS, False) or (common.args.get(TITLE_LOCAL_LINKS, False) and not os.path.realpath(fullname).startswith(os.getcwd() + "/")))

                if not reachable:
                    # Symbolic link is inaccessible. Override extra info to plainly say 'symlink'.
                    if common.args.get(TITLE_NO_LINKS, False):
                        extrainfo = "(Symlink)"
                    else:
                        # Implies local links only, meaning an unreachable link is external.
                        extrainfo = "(External Symlink)"
                elif os.path.isdir(os.path.realpath(fullname)):
                    # Directory via Symlink
                    # Append / for directories or @ for symbolic links
                    displayname = name + "/@"
                    linkname = name + "/"

                    extrainfo = "(Symlink to directory <strong>%s</strong>)" % cgi.escape(os.path.realpath(fullname))
                elif os.path.isfile(os.path.realpath(fullname)):
                    # File via Symlink
                    extrainfo = "(Symlink to %s file <strong>%s</strong>)" % (self.humansize(os.stat(fullname).st_size), cgi.escape(os.path.realpath(fullname)))
                else:
                    # Dead symlink
                    linkname = None
                    extrainfo = "(Dead symlink to <strong>%s</strong>)" % os.readlink(fullname)

            elif os.path.isdir(fullname):
                # Directory
                displayname = name + "/"
                linkname = name + "/"
                extrainfo = "(Directory)"
            else:
                # File
                extrainfo = "(%s File)" % self.humansize(os.stat(fullname).st_size)

            if linkname and reachable:
                f.write('        <li><a href="%s">%s</a> %s</li>\n'
                        % (urllib.quote(linkname), cgi.escape(displayname), extrainfo))
            else:
                f.write('        <li><strong>%s</strong> %s</li>\n'
                        % (cgi.escape(displayname), extrainfo))
        f.write("      </ul>\n      <hr>\n  </body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

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
