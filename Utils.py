from datetime import datetime
from time import sleep, time

class Delay:
    def __init__(self, refreshRate=1):
        self.refreshRate = refreshRate
        self.delayUntil  = 0

    def delay(self, seconds):
        self.delayUntil = time() + seconds
        while time() < self.delayUntil:
            sleep(self.refreshRate)

    def stop(self):
        self.delayUntil = 0

    def __str__(self):
        return f'Delay: refreshRate={self.refreshRate}, delayUntil={self.delayUntil}'

    def __format__(self, format_spec):
        return format(str(self), format_spec)

class Timer:
    def __init__(self):
        self.restart()

    def end(self, printElapsed=False):
        self.spent = time() - self.start
        if printElapsed: print(f'Elapsed: {self.spent:.2f}s')
        return self.spent

    def restart(self):
        self.start = time()
        self.spent = 0

def getTime(timestamp=None, withMicroSeconds=False) -> str:
    """Converts a given timestamp (if provided) or the current time to a easily readable string

    params:
        [Optional] timestamp -> Timestamp to convert to string. If None, the current time will be used.
        withMicroSeconds     -> If True, resulting string will have microseconds

    returns:
        str -> easily readable string representing the timestamp"""
    return (datetime.fromtimestamp(timestamp) if timestamp else datetime.now()).strftime('%Y-%m-%d %H:%M:%S' + ('.%f' if withMicroSeconds else ''))

def log(string):
    with open('Log.log', 'a') as f:
        f.write(f'{getTime()} {string}\n')
        
def progressBar(current, end, string=None, additional=None, precision=2, init=False):
    string     = string or "Loading"
    additional = additional or ""
    if "string" not in progressBar.__dict__ or string != progressBar.string:
        progressBar.timer      = Timer()
        progressBar.lastEta    = "?"
        progressBar.lastSeen   = current
        progressBar.string     = string
        progressBar.lastChange = time()
    # No progress since last iteration, and less than 1 seconds ago
    if progressBar.lastSeen == current and time() - progressBar.lastChange < 1:
        eta = progressBar.lastEta
    # Current != 0
    elif current:
        progressBar.lastChange = time()
        eta = f'{(end / current - 1) * progressBar.timer.end():.2f}'
    else:
        eta = '?'
    print(f'{string} [{current / end * 100:{precision + 4}.{precision}f}%] ({current:{len(str(end))}} of {end}) ETA: {getTime(time() + float(eta)) if eta != "?" else "?"} ({eta}s) {additional}'.ljust(119), end="\r" if current != end else "\n")
    progressBar.lastSeen = current
    progressBar.lastEta  = eta

def group(items, groups):
    minimum = len(items) // groups
    extra = len(items) % groups
    result = []
    current = 0
    for i in range(groups):
        count = minimum + (1 if i < extra else 0)
        result.append(items[current : current + count])
        current += count
    return result

def doNothing(*args, **kwargs):
    pass

def extract(string, pattern, delim=None, trim=False):
    def extractUntil(stop, string):
        assert stop in string, f'Base::extract.extractUntil: (error) stop ({stop}) not in string ({string})'
        return (string[:string.find(stop)], string[string.find(stop) + len(stop):])
    delim     = delim or ('{', '}')
    extracted = dict()
    assert f'{delim[1]}{delim[0]}' not in pattern, f'Base::extract: (error) cannot extract keywords back-to-back ({pattern})'
    assert delim[0] not in string, f'Base::extract: (error) opening delimiter ({delim[0]}) found in string ({string})'
    assert delim[1] not in string, f'Base::extract: (error) closing delimiter ({delim[1]}) found in string ({string})'
    initialWord, pattern = extractUntil("{", pattern)
    assert initialWord in string, f'Base::extract: (error) initial word ({initialWord}) not in string ({string})'
    string = string[len(initialWord):]
    while pattern.find(delim[1]) != -1:
        key, pattern  = extractUntil('}', pattern)
        word, pattern = extractUntil('{', pattern) if '{' in pattern else (pattern, '')
        assert word in string, f'Base::extract: (error) word ({word}) not in string ({string})'        
        extracted[key], string = extractUntil(word, string) if len(word) else (string, "")
    if '_' in extracted: del extracted['_']
    if trim            : extracted = {i: extracted[i].strip() for i in extracted}
    return extracted
