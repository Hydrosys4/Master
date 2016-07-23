import re
import itertools
import os

import subprocess
from pbkdf2 import PBKDF2




def ensure_file_exists(filename):
    """
    http://stackoverflow.com/a/12654798/1013960
    """
    if not os.path.exists(filename):
        open(filename, 'a').close()




def configuration(cell, passkey , staticIPoptions):
    """
    Returns a dictionary of configuration options for cell

    Asks for a password if necessary
    """
    if not cell.encrypted:
        di1 = {
            'wireless-essid': cell.ssid,
            'wireless-channel': 'auto',
        }
    else:
        if cell.encryption_type.startswith('wpa'):
            if len(passkey) != 64:
                passkey = PBKDF2(passkey, cell.ssid, 4096).hexread(32)

            di1 = {
                'wpa-ssid': cell.ssid,
                'wpa-psk': passkey,
                'wireless-channel': 'auto',
            }
        elif cell.encryption_type == 'wep':
            # Pass key lengths in bytes for WEP depend on type of key and key length:
            #
            #       64bit   128bit   152bit   256bit
            # hex     10      26       32       58
            # ASCII    5      13       16       29
            #
            # (source: https://en.wikipedia.org/wiki/Wired_Equivalent_Privacy)
            #
            # ASCII keys need to be prefixed with an s: in the interfaces file in order to work with linux' wireless
            # tools

            ascii_lengths = (5, 13, 16, 29)
            if len(passkey) in ascii_lengths:
                # we got an ASCII passkey here (otherwise the key length wouldn't match), we'll need to prefix that
                # with s: in our config for the wireless tools to pick it up properly
                passkey = "s:" + passkey

            di1 = {
                'wireless-essid': cell.ssid,
                'wireless-key': passkey,
            }
        else:
            raise NotImplementedError
    z = di1.copy()
    z.update(staticIPoptions)
    return z      


bound_ip_re = re.compile(r'^bound to (?P<ip_address>\S+)', flags=re.MULTILINE)



class Scheme(object):
    """
    Saved configuration for connecting to a wireless network.  This
    class provides a Python interface to the /etc/network/interfaces
    file.
    """

    interfaces = '/etc/network/interfaces'
    #interfaces = 'interfacesprova'

    @classmethod
    def for_file(cls, interfaces):
        """
        A class factory for providing a nice way to specify the interfaces file
        that you want to use.  Use this instead of directly overwriting the
        interfaces Class attribute if you care about thread safety.
        """
        return type(cls)(cls.__name__, (cls,), {
            'interfaces': interfaces,
        })

    def __init__(self, interface, name , mode , options=None):
        self.interface = interface
        self.name = name
        self.mode = mode
        self.options = options or {}

    def __str__(self):
        """
        Returns the representation of a scheme that you would need
        in the /etc/network/interfaces file.
        """
        iface = "iface {interface}-{name} inet {mode}".format(**vars(self))
        options = ''.join("\n    {k} {v}".format(k=k, v=v) for k, v in self.options.items())
        return iface + options + '\n'

    def __repr__(self):
        return 'Scheme(interface={interface!r}, name={name!r}, options={options!r}'.format(**vars(self))

    @classmethod
    def all(cls):
        """
        Returns an generator of saved schemes.
        """
        ensure_file_exists(cls.interfaces)
        with open(cls.interfaces, 'r') as f:
            return extract_schemes(f.read(), scheme_class=cls)

    @classmethod
    def where(cls, fn):
        return list(filter(fn, cls.all()))

    @classmethod
    def find(cls, interface, name):
        """
        Returns a :class:`Scheme` or `None` based on interface and
        name.
        """
        try:
            return cls.where(lambda s: s.interface == interface and s.name == name)[0]
        except IndexError:
            return None

    @classmethod
    def for_cell(cls, interface, name, mode , cell, passkey , staticIPoptions):
        """
        Intuits the configuration needed for a specific
        :class:`Cell` and creates a :class:`Scheme` for it.
        """
        return cls(interface, name, mode , configuration(cell, passkey, staticIPoptions))

    def save(self):
        """
        Writes the configuration to the :attr:`interfaces` file.
        """
        assert not self.find(self.interface, self.name), "This scheme already exists"

        with open(self.interfaces, 'a') as f:
            f.write('\n')
            f.write(str(self))

    def savestr(self,strlist):
        """
        Writes the configuration to the :attr:`interfaces` file.
        """
        assert not self.find(self.interface, self.name), "This scheme already exists"

        with open(self.interfaces, 'a') as f:
            for line in strlist:
				f.write('\n')
				f.write(line)


    def delete(self):
        """
        Deletes the configuration from the :attr:`interfaces` file.
        """
        iface = "iface %s-%s inet" % (self.interface, self.name)
        content = ''
        with open(self.interfaces, 'r') as f:
            skip = False
            for line in f:
                if not line.strip():
                    skip = False
                elif line.strip().find(iface)>-1:
                    skip = True
                if not skip:
                    content += line
        with open(self.interfaces, 'w') as f:
            f.write(content)

    @property
    def iface(self):
        return '{0}-{1}'.format(self.interface, self.name)

    def as_args(self):
        args = list(itertools.chain.from_iterable(
            ('-o', '{k}={v}'.format(k=k, v=v)) for k, v in self.options.items()))

        return [self.interface + '=' + self.iface] + args

    def activate(self):
        """
        Connects to the network as configured in this scheme.
        """

        subprocess.check_output(['/sbin/ifdown', self.interface], stderr=subprocess.STDOUT)
        ifup_output = subprocess.check_output(['/sbin/ifup'] + self.as_args(), stderr=subprocess.STDOUT)
        ifup_output = ifup_output.decode('utf-8')
        print ifup_output

        return self.parse_ifup_output(ifup_output)

    def parse_ifup_output(self, output):
        matches = bound_ip_re.search(output)
        if matches:
            return Connection(scheme=self, ip_address=matches.group('ip_address'))
        else:
            print "Failed to connect to " , self
            return False


class Connection(object):
    """
    The connection object returned when connecting to a Scheme.
    """
    def __init__(self, scheme, ip_address):
        self.scheme = scheme
        self.ip_address = ip_address


# TODO: support other interfaces
scheme_re = re.compile(r'iface\s+(?P<interface>wlan\d?)(?:-(?P<name>\w+))?')


def extract_schemes(interfaces, scheme_class=Scheme):
    lines = interfaces.splitlines()
    while lines:
        line = lines.pop(0)

        if line.startswith('#') or not line:
            continue

        match = scheme_re.match(line)
        if match:
            options = {}
            interface, scheme = match.groups()

            if not scheme or not interface:
                continue

            while lines and lines[0].startswith(' '):
                key, value = re.sub(r'\s{2,}', ' ', lines.pop(0).strip()).split(' ', 1)
                options[key] = value

            scheme = scheme_class(interface, scheme, "static" , options)

            yield scheme
