#!/usr/bin/python

'''
    This is a super-silly server made to play sounds on a remote server.
    The intent was to easily play a sound using only netcat as a client.
'''

import getopt, os, random, re, socket, struct, subprocess, sys, thread

DEFAULT_AUDIO_PORT = 4321
SOUNDS = [{},{}]

if sys.stdout.isatty():
    # Colours for standard output.
    COLOUR_RED= '\033[1;91m'
    COLOUR_GREEN = '\033[1;92m'
    COLOUR_YELLOW = '\033[1;93m'
    COLOUR_BLUE = '\033[1;94m'
    COLOUR_PURPLE = '\033[1;95m'
    COLOUR_BOLD = '\033[1m'
    COLOUR_OFF = '\033[0m'
else:
    # Set to blank values if not to standard output.
    COLOUR_RED= ''
    COLOUR_GREEN = ''
    COLOUR_YELLOW = ''
    COLOUR_BLUE = ''
    COLOUR_PURPLE = ''
    COLOUR_BOLD = ''
    COLOUR_OFF = ''

class NetAccess:
    # Basic IPv4 CIDR syntax check
    REGEX_INET4_CIDR='^(([0-9]){1,3}\.){3}([0-9]{1,3})\/[0-9]{1,2}$'

    def __init__(self):
        self.errors = []
        self.allowed_addresses = []
        self.allowed_networks = []
        self.denied_addresses = []
        self.denied_networks = []

    def add_access(self, addr_list, net_list, candidate):
        error = False
        if re.match(self.REGEX_INET4_CIDR, candidate):
            e, n = self.ip_validate_cidr(candidate)
            error = e
            if not e:
                # No error
                net_list.append((n, candidate))
        else:
            e, a, astr = self.ip_validate_address(candidate)
            error = e
            if not e:
                # No error
                addr_list.append((a, candidate, astr))
        return error

    def add_blacklist(self, candidate):
        return self.add_access(self.denied_addresses, self.denied_networks, candidate)

    def add_whitelist(self, candidate):
        return self.add_access(self.allowed_addresses, self.allowed_networks, candidate)

    def announce_filter_actions(self):
        for action, address_list, network_list in [("Allowing", self.allowed_addresses, self.allowed_networks), ("Denying", self.denied_addresses, self.denied_networks)]:
            l = []
            l.extend([("address", s, i) for n, s, i in address_list])
            l.extend([("network", s, s) for n, s in network_list])

            for title, ip, address in l:
                if ip == address:
                    print "%s %s: %s%s%s" % (action, title, COLOUR_GREEN, address, COLOUR_OFF)
                else:
                    print "%s %s: %s%s%s (%s%s%s)" % (action, title, COLOUR_GREEN, address, COLOUR_OFF, COLOUR_GREEN, ip, COLOUR_OFF)

    # Credit for initial IP functions: http://code.activestate.com/recipes/66517/

    def ip_make_mask(self, n):
        # Return a mask of n bits as a long integer
        return (2L<<n-1)-1

    def ip_strton(self, ip):
        # Convert decimal dotted quad string to long integer
        return struct.unpack('<L',socket.inet_aton(ip))[0]

    def ip_network_mask(self, ip, bits):
        # Convert a network address to a long integer
        return self.ip_strton(ip) & self.ip_make_mask(int(bits))

    def ip_addrn_in_network(self, ip, net):
        # Is a numeric address in a network?
        return ip & net == net

    def ip_validate_address(self, candidate):
        try:
            ip = socket.gethostbyname(candidate)
            return (False, self.ip_strton(ip), ip)
        except socket.gaierror:
            self.errors.append("Unable to resolve: %s%s%s" % (COLOUR_GREEN, candidate, COLOUR_OFF))
            return (True, None, None)

    def ip_validate_cidr(self, candidate):
        a = candidate.split("/")[0]
        m = candidate.split("/")[1]
        try:
            if socket.gethostbyname(a) and int(m) <= 32:
                return (False, self.ip_network_mask(a, m))
        except socket.gaierror:
            pass
        self.errors.append("Invalid CIDR address: %s%s%s" % (COLOUR_GREEN, candidate, COLOUR_OFF))
        return (True, None)

    def is_allowed(self, address):
        # Blacklist/Whitelist filtering
        allowed = True

        if len(self.allowed_addresses) or len(self.allowed_networks):
            # Whitelist processing, address is not allowed until it is cleared.
            allowed = False

            if address in [a[2] for a in self.allowed_addresses]:
                allowed = True
            else:
                # Try checking allowed networks
                cn = self.ip_strton(address)
                for n in [n[0] for n in self.allowed_networks]:
                    if self.ip_addrn_in_network(cn, n):
                        allowed = True
                        break

        if len(self.denied_addresses) or len(self.denied_networks):
            # Blacklist processing. A blacklist argument one-ups a whitelist argument in the event of a conflict

            if address in [a[2] for a in self.denied_addresses]:
                allowed = False
            else:
                # Try checking denied networks
                cn = self.ip_strton(address)
                for n in [n[0] for n in self.denied_networks]:
                    if self.ip_addrn_in_network(cn, n):
                        allowed = False
                        break
        return allowed

# Function for multi-threaded handling of connections
def clientthread(conn, addr):

    global SOUNDS

    # Read message from client
    # Assuming a single message per connection.
    # 1024 bytes is expected to be extreme overkill
    conn.settimeout(5)
    try:
        data = conn.recv(1024)
        if not data:
            conn.close()
            return

        # Lop off trailing '.mp3' extension, and everything after the first newline.
        command = re.sub(r"(\.mp3)?\n.{0,}", "", data, flags=re.IGNORECASE)
        reply = ""
        if command == "list":
            l = SOUNDS[0].keys()
            l.sort()
            for i in l:
                reply += "%s\n" % i
            print "Client %s%s:%d%s requested a listing." % (COLOUR_GREEN, addr[0], addr[1], COLOUR_OFF)
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
                printout = "Client %s%s:%d%s requested a random sound. Choice: %s%s%s " % (COLOUR_GREEN, addr[0], addr[1], COLOUR_OFF, COLOUR_BOLD, key, COLOUR_OFF)
            else:
                printout = "Client %s%s:%d%s requested %s%s%s sound " % (COLOUR_GREEN, addr[0], addr[1], COLOUR_OFF, COLOUR_BOLD, command, COLOUR_OFF)
            found = False
            if path:
                found = True
                reply = "played\n"
                printout += "(%s%s%s)" % (COLOUR_GREEN, path, COLOUR_OFF)
            else:
                reply = "not-found\n"
                printout += "(%s%s%s)" % (COLOUR_RED, "Not found", COLOUR_OFF)
            print printout

            if found:
                p = subprocess.Popen(["mpg123", "-q", path])
                p.communicate()
    except OSError:
        reply = "play-error\n"
    except socket.timeout:
        reply = "timeout\n"

    conn.sendall(reply)
    conn.close()

def find_mp3_files(path):
    global SOUNDS
    for root, dirs, files in os.walk(path):
        for name in files:
            if name.endswith(".mp3"):
                s = name.split(".")
                SOUNDS[0][".".join(s[0:len(s)-1])] = os.path.join(root, name)
                SOUNDS[1]["sound-" + ".".join(s[0:len(s)-1])] = os.path.join(root, name) # Super-lazy double-index for "sound-" prefix.

def hexit(exit_code):
    print "%s [-a allow-address/range] [-b bind-address] [-d deny-address/range] [-h] [-p port]" % os.path.basename(sys.argv[0])
    exit(exit_code)

def main():

    err, args = process_arguments()
    if err:
        exit(1)

    directory = os.path.realpath(args.get("dir", os.environ.get("audioToolsDir") + "/files"))

    global SOUNDS
    find_mp3_files(directory)
    if not len(SOUNDS[0]):
        print "No MP3 files found in %s%s%s..." % (COLOUR_GREEN, directory, COLOUR_OFF)
        exit(1)

    # Print a summary of directory/bind options.
    print "Serving %s%d%s sounds from %s%s%s on %s%s:%d%s" % (COLOUR_BOLD, len(SOUNDS[0]), COLOUR_OFF, COLOUR_GREEN, directory, COLOUR_OFF, COLOUR_GREEN, args.get("bind", "0.0.0.0"), args.get("port", DEFAULT_AUDIO_PORT), COLOUR_OFF)

    sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind socket to local host and port
    try:
        sockobj.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sockobj.bind((args.get("bind", "0.0.0.0"), args.get("port", DEFAULT_AUDIO_PORT)))
    except socket.error as msg:
        print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        exit(1)

    sockobj.listen(10)

    # Keep accepting new connections
    while True:
        try:
            conn, addr = sockobj.accept()
        except KeyboardInterrupt:
            break
        print 'Connected with %s%s:%d%s' % (COLOUR_GREEN, addr[0], addr[1], COLOUR_OFF),

        # Blacklist/Whitelist filtering
        allowed = True

        if len(args["allowed_addresses"]) or len(args["allowed_networks"]):
            # Whitelist processing, address is not allowed until it is cleared.
            allowed = False

            if addr[0] in [a[2] for a in args["allowed_addresses"]]:
                allowed = True
            else:
                # Try checking allowed networks
                cn = ip_strton(addr[0])
                for n in [n[0] for n in args["allowed_networks"]]:
                    if ip_addrn_in_network(cn, n):
                        allowed = True
                        break

        if len(args["denied_addresses"]) or len(args["denied_networks"]):
            # Blacklist processing. A blacklist argument one-ups a whitelist argument in the event of a conflict

            if addr[0] in [a[2] for a in args["denied_addresses"]]:
                allowed = False
            else:
                # Try checking denied networks
                cn = ip_strton(addr[0])
                for n in [n[0] for n in args["denied_networks"]]:
                    if ip_addrn_in_network(cn, n):
                        allowed = False
                        break

        if not allowed:
            print "(Denied)"
            conn.close()
            continue
        else:
            print "" # Finish connection announcement line


        # Spawn new thread and pass it the new socket object
        thread.start_new_thread(clientthread ,(conn,addr))

    sockobj.close()

def process_arguments():
    args = {"denied_addresses":[], "denied_networks":[],"allowed_addresses":[], "allowed_networks":[]}
    error = False
    errors = []
    global access
    access = NetAccess()

    try:
        opts, flat_args = getopt.gnu_getopt(sys.argv[1:],"a:b:d:hp:")
    except getopt.GetoptError as e:
        print "GetoptError: %s" % e
        hexit(1)
    for opt, arg in opts:
        if opt in ("-a"):
            error = access.add_whitelist(arg) or error
        elif opt in ("-b"):
            args["bind"] = arg
        elif opt in ("-d"):
            error = access.add_blacklist(arg) or error
        elif opt in ("-h"):
            hexit(0)
        elif opt in ("-p"):
            args["port"] = int(arg)
    switch_arg = False
    if len(flat_args):
        args["dir"] = flat_args[len(flat_args)-1]

    if len(access.errors):
        error = True
        errors.extend(access.errors)

    if not error:
        access.announce_filter_actions()
    else:
        for e in errors:
            print "Error: %s" % e
    return error, args

if __name__ == "__main__":
    main()
