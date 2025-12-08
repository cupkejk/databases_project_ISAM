#record 8-key space 9.9+space*4-vec space 8-overflow
import random

PAGE_LIMIT = 10

class Record:
    def __init__(self, key):
        self.vec = []
        self.key = key
        self.overflow = None
    
    def random(self, key, overflow):
        self.vec = []
        for i in range(4):
            self.vec.append(random.random()*100)
        self.key = key
        self.overflow = overflow
        
    def str_to_rec(self, data):
        self.key = int(data[0:8])
        self.vec = []
        for i in range(9, 89, 20):
            num = data[i:i+19]
            self.vec.append(float(num))
        overflow = data[89:97]
        if overflow[0] == 'x': self.overflow = None
        else: self.overflow = int(overflow)
    
    def __str__(self):
        key_str = str(self.key)
        rec_str = key_str
        for i in range(9 - len(key_str)):
            rec_str = rec_str + ' '
        for i in range(4):
            rec_str = rec_str + f'{self.vec[i]:19.9f}' + ' '
        
        if not self.overflow:
            rec_str = rec_str + 'x       '
            return rec_str
        
        overflow_str = str(self.overflow)
        rec_str = rec_str + overflow_str
        for i in range(8-len(overflow_str)):
            rec_str = rec_str + ' '
        
        return rec_str + '\n'

class IndexRecord:
    def __init__(self, key, page):
        self.key = key
        self.page = page

    def str_to_rec(self, data):
        if len(data) != 17:
            raise ValueError("Input string must be exactly 17 characters long.")
            
        key_str = data[0:8]
        page_str = data[9:17]

        self.key = int(key_str)
        self.page = int(page_str)
    
    def __str__(self):
        key_str = str(self.key)
        page_str = str(self.page)
        
        if len(key_str) < 8: key_str = key_str + (' ' * (8 - len(key_str)))
        if len(page_str) < 8: page_str = page_str + (' ' * (8 - len(page_str)))

        return key_str + ' ' + page_str + '\n'

class Page:
    def __init__(self):
        self.recs = []
    
    def data_to_page(self, data):
        self.recs = []
        for line in data:
            rec = Record(0)
            rec.str_to_rec(line)
            self.recs.append(rec)
        
        for i in range(10-len(self.recs)):
            self.recs.append(None)
    
    def page_to_data(self):
        data = [str(rec) for rec in self.recs]
        for i in range(len(data)):
            if data[i] == 'None':
                data[i] = '-'*98 + '\n'
        return data
    
    def random(self):
        for i in range(10):
            rec = Record(0)
            rec.random(0, 0)
            self.recs.append(rec)
    
    def add(self, rec):
        if len(self.recs) >= 10: return 1

        self.recs.append(rec)
        return 0

class IndexPage:
    def __init__(self):
        self.recs = []
    
    def data_to_page(self, data):
        self.recs = []
        for line in data:
            rec = Record(0)
            rec.str_to_rec(line)
            self.recs.append(rec)
        
        for i in range(10-len(self.recs)):
            self.recs.append(None)
    
    def page_to_data(self):
        data = [str(rec) for rec in self.recs]
        for i in range(len(data)):
            if data[i] == 'None':
                data[i] = '-'*17+'\n'
        return data
    
    def between(self, key):
        if len(self.recs) == 0: return 0
        if self.recs[-1].key > key: return -1
        if self.recs[0].key < key: return -1
        i = 0
        while self.recs[i] != None and self.recs[i].key < key:
            i += 1
        return i - 1
    
    def random(self):
        for i in range(10):
            rec = Record(0)
            rec.random(0, 0)
            self.recs.append(rec)
    
    def add(self, rec):
        if len(self.recs) >= 10: return 1

        self.recs.append(rec)
        return 0

class Manager:
    def __init__(self):
        self.data_file = open('data.txt', 'w+')
        self.index_file = open('index.txt', 'w+')
        self.overflow_file = open('overflow.txt', 'w+')
        self.adding_page_num = 0
        self.adding_pages = 1
        self.adding_page = Page()
        self.index_page_num = 0
        self.index_pages = 1
        self.index_page = IndexPage()
        self.overflow_page_num = 0
        self.overflow_pages = 1
        self.overflow_page = Page()

    def for_seek(self, page):
        return 98*10*page

    def for_seek_index(self, page):
        return 18*10*page
    
    def add(self, rec):
        if len(self.adding_page.recs) == 10:
            self.next_page()
        page = self.page_to_append(rec)
        if page == self.adding_page_num:
            if self.adding_page.add(rec):
                self.overflow_page.add(rec)
    
    def next_page(self):
        data = self.adding_page.page_to_data()
        for line in data:
            self.data_file.write(line)
        
        max = float('-inf')
        for rec in self.adding_page.recs:
            if rec.key > max:
                max = rec.key
        index_rec = IndexRecord(max, self.adding_page_num)
        self.index_page.add(index_rec)
        self.adding_page_num += 1
        self.adding_page = Page()

    def page_to_append(self, rec):
        key = rec.key
        if self.index_pages == 1:
            i = self.index_page.between(key)
            return i
        
    def get_index_page(self, page):
        i = self.for_seek_index(page)
        self.index_file.seek(i)
        data = []
        for i in range(10):
            data.append(self.index_file.readline())
        self.index_page.data_to_page(data)
    
    def save_index_page(self, page):
        data = self.index_page.page_to_data()
        i = self.for_seek_index(page)
        self.index_file.seek(i)
        for line in data:
            self.index_file.write(line)

m = Manager()
for i in range(100):
    rec = Record(i+1)
    rec.random(i+1, None)
    m.add(rec)
    for rec in m.adding_page.recs:
        print(rec)
    for rec in m.index_page.recs:
        print(rec)
    print()
