from Color import ColorText
from Utils import *
import json

class ReadonlyDict(dict):
    __setitem__ = lambda self, key, value: None

def strictReadonly(dictionary):
    return ReadonlyDict({k: strictReadonly(v) if type(v) is dict else v for k, v in dictionary.items()})

#TODO: table() with inverted keys as headers, data as rows
class Data:
    __len__ = lambda self: len(self.__data)
    # Added 11 Nov 2021 - significant perfomance improvements over "if key in self.keys"
    __contains__ = lambda self, key: key in self.__data
    # Added 21 Nov 2021 - allows iteration
    __iter__ = lambda self: self.__data.__iter__()

    def __init__(self, initialData=None, readonly=False, default=None):
        initialData  = initialData or {}
        self.__data  = initialData if not readonly else strictReadonly(initialData)
        self.default = default

    def setAll(self, col, function):
        for k in self:
            self.set(k, col, function(k, self.get(k)))

    def set(self, *args):
        self.get(*args[:-2])[args[-2]] = args[-1]
        return self

    def get(self, *args):
        target = self.__data
        for a in args:
            try:
                target = target[a]
            except (KeyError, IndexError):
                return self.default
        return target

    # Faster than existence check if Exception rate is low, else slower (except is more expensive than if)
    def delete(self, key):
        try:
            self.__data.pop(key)
        except:
            pass

    def batchDelete(self, function=lambda k, v: False):
        for key in self.keys:
            if function(key, self.get(key)):
                self.delete(key)

    def setReadonly(self):
        self.__data = strictReadonly(self.__data)

    @property
    def keys(self):
        return list(self.__data)

    @property
    def length(self):
        return len(self.__data)

    # Added 30 June 2021
    def filterColumns(self, *columnNames, readonly=True):
        return Data({i: {j: self.get(i, j) for j in columnNames} for i in self.keys}, readonly)

    def removeColumns(self, columnNames, readonly=True):
        return Data({i: {j: self.get(i, j) for j in self.get(i) if j not in columnNames} for i in self.keys}, readonly)

    def filter(self, function=lambda k, v: True, readonly=True, **kwargs):
        return Data({i: self.get(i) for i in self.keys if all([self.get(i, j) in kwargs[j] if type(kwargs[j]) == list else self.get(i, j) == kwargs[j] for j in kwargs]) and function(i, self.get(i))}, readonly)

    def proportion(self, function = lambda k, v: True, **kwargs):
        return f'{len(self.filter(function, **kwargs)) / len(self) * 100:.2f}%'

    def sort(self, sortBy, sortFunction=str, reverse=False):
        return Data({i: self.get(i) for i in sorted(self.keys, key=lambda x: sortFunction(self.get(x, sortBy)), reverse=reverse)}, True)

    def group(self, groupFunction=lambda k, v: k, mergeProperty=lambda k, v: k, mergeFunction=list):
        grouping = {}
        for i in self.keys:
            a = mergeProperty(i, self.get(i))
            if (b := groupFunction(i, self.get(i))) in grouping:
                grouping[b].append(a)
            else:
                grouping[b] = [a]
        return Data({i: mergeFunction(grouping[i]) for i in grouping})

    def table(self, title=None, columns=None, alignments=None, indexLabel=None, note=None):
        title = title or 'Data'
        if len(self) == 0:
            return f'{title}: No data :(\n{note if note else ""}'
        if not isinstance(self.get(self.keys[0]), dict):
            return Data({i: {'value': self.get(i)} for i in self.keys}).table(title, columns, alignments, indexLabel, note)
        indexLabel = indexLabel or 'index'
        assert indexLabel not in self.get(self.keys[0]), 'Data.table: (error) index label should not be a property'        
        table   = ''
        cols    = [indexLabel] + list(map(str, (columns or list(self.get(self.keys[0])))))
        aligns  = ['>' if a == 'right' else '<' if a == 'left' else '^' for a in alignments] if alignments else ['^'] * (len(cols) - 1)
        longest = [max([len(str(k) if c == indexLabel else str(self.get(k, c)) if not isinstance(self.get(k, c), ColorText) else self.get(k, c)) for k in self.keys] + [len(c)]) for c in cols]
        # Header
        length = (len(cols) - 1) * 3 + 4 + sum(longest)
        table += '-' * length + '\n|' + title.center(length - 2) + '|\n' + '-' * length + '\n| ' + ' | '.join([c.center(longest[cols.index(c)]) for c in cols]) + ' |' + '\n' + '-' * length + '\n| '

        # Data
        table += ' |\n| '.join([' | '.join([str(k).ljust(longest[0])] + [f'{str(self.get(k, c)) if not isinstance(self.get(k, c), ColorText) else self.get(k, c):{aligns[cols.index(c) - 1]}{longest[cols.index(c)]}}' for c in cols[1:]]) for k in self.keys])

        # Footer
        table += ' |\n' + '-' * length

        # Note
        table += f'\n{note}' if note else ''
        return table

    def select(self, count):
        data = {}
        l    = 0
        for k, v in self.__data.items():
            if l == count:
                break
            data[k] = v
            l += 1
        return Data(data)

    def selectUnique(self, column):
        return list(set([self.get(i, column) for i in self.keys]))

    def selectAsList(self, column):
        return [self.get(i, column) for i in self.keys]

    def exportTable(self, title=None, columns=None, alignments=None, indexLabel=None, note=None, filepath=None):
        with open(filepath or 'Table-' + getTime().replace(':','') + '.txt', 'w') as f:
            f.write(self.table(title, columns, alignments, indexLabel, note))

    # Updated 30 July 2021
    def exportCSV(self, filepath=None):
        with open(filepath or 'CSV-' + getTime().replace(':','') + '.csv', 'w') as f:
            # Heading
            f.write(','.join(['"index"'] + [f'"{str(c)}"' for c in list(self.get(self.keys[0]))]) + '\n')
                
            # Content
            f.write('\n'.join([','.join([f'"{str(k)}"'] + [f'"{str(self.get(k, v))}"' for v in self.get(k)]) for k in self.keys]))

    # Updated 13 Nov 2021
    def fromCSV(filepath):
        with open(filepath) as f:
            texts = [l for l in f]
            cols  = texts[0][1:-2].split('","')[1:]
            return Data({(data := line[1:-2].split('","'))[0]: {cols[col]: data[col + 1] for col in range(len(cols))} for line in texts[1:]})

    def show(self, title=None, columns=None, alignments=None, indexLabel=None, note=None):
        print(self.table(title, columns, alignments, indexLabel, note))

    def selfSort(self):
        self.__data = {i: {j: self.get(i, j) for j in sorted(self.get(i))} if type(self.get(i)) is dict else self.get(i) for i in sorted(self.keys)}
        return self

    def reverseIndex(self):
        return Data({i: self.get(i) for i in self.keys[::-1]})

    def store(self, filepath=None, sortBeforeStore=True):
        if sortBeforeStore:
            self.selfSort()
        with open(filepath or getTime().replace(':','') + '.json', 'w') as f:
            json.dump(self.get(), f, indent=4)
        return self

    def update(self, data, conflictResolution=lambda old, new: new):
        for key in data.keys:
            self.set(key, conflictResolution(self.get(key), data.get(key)) if key in self.keys else data.get(key))

class FileData(Data):
    def __init__(self, filepath):
        self.filepath = filepath
        self.load()

    def load(self):
        try:
            with open(self.filepath, 'r') as f:
                super().__init__(json.load(f))
        except FileNotFoundError:
            super().__init__()
        return self

    def store(self, sortBeforeStore=True):
        super().store(self.filepath, sortBeforeStore)
        return self

    def archive(self, amount):
        with FileData(f'ARCHIVE_{self.filepath}') as f:
            s = self.select(amount)
            f.update(s)
            for key in s.keys: self.delete(key)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, exc_tb):
        self.store()

CONFIG = FileData('Config.json')
STRATEGIES = FileData('Strategies.json')
