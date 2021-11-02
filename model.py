import json


class Model():
    def __init__(self, filenames):
        self.data = {}
        self.filenames = filenames
        self.read_config()
    
    def read_config(self):
        with \
            open(self.filenames['config']) as fh1, \
            open(self.filenames['pairs']) as fh2, \
            open(self.filenames['trades']) as fh3:
            self.data['config'] = json.load(fh1)
            self.data['pairs'] = json.load(fh2)
            self.data['trades'] = json.load(fh3)
    
    def write_config(self):
        with \
            open(self.filenames['config'], 'w') as fh1, \
            open(self.filenames['pairs'], 'w') as fh2, \
            open(self.filenames['trades'], 'w') as fh3:
            json.dump(self.data['config'], fh1)
            json.dump(self.data['pairs'], fh2)
            json.dump(self.data['trades'], fh3)
