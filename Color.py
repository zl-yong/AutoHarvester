from enum import Enum
import colorama as color

color.init()

class Color(Enum):
    DEFAULT  = color.Style.RESET_ALL
    BRIGHT   = color.Style.BRIGHT
    RED      = color.Fore.RED
    GREEN    = color.Fore.GREEN
    BLUE     = color.Fore.BLUE
    BLACK    = color.Fore.BLACK
    MAGENTA  = color.Fore.MAGENTA
    BG_WHITE = color.Back.WHITE
    

class ColorText:
    def __init__(self, text, *options):
        self.text    = text.text if isinstance(text, ColorText) else text
        self.options = text.options + options if isinstance(text, ColorText) else options

    def __str__(self):
        return ''.join([i.value if isinstance(i, Color) else i for i in self.options]) + self.text + Color.DEFAULT.value

    def __format__(self, format_spec):
        return ''.join([i.value if isinstance(i, Color) else i for i in self.options]) + format(str(self.text), format_spec) + Color.DEFAULT.value

    def __len__(self):
        return len(self.text)

def bright(text):
    return ColorText(text, Color.BRIGHT)

def red(text):
    return ColorText(text, Color.RED)

def blue(text):
    return ColorText(text, Color.BLUE)

def green(text):
    return ColorText(text, Color.GREEN)

def magenta(text):
    return ColorText(text, Color.MAGENTA)

def invert(text):
    return ColorText(text, Color.BLACK, Color.BG_WHITE)

def stripColors(string):
    for i in Color:
        string = string.replace(i.value, '')
    return string
