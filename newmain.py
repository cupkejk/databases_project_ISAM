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
            return rec_str + '\n'
        
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
        if len(data) != 18:
            print("Must be exactly 18 characters long")
            exit(0)
            
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
        if data[0] == '': return
        for line in data:
            if line == '': continue
            rec = Record(0)
            rec.str_to_rec(line)
            self.recs.append(rec)
    
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
        if data[0] == '': return 
        for line in data:
            if line == '': continue
            rec = IndexRecord(None, None)
            rec.str_to_rec(line)
            self.recs.append(rec)
    
    def page_to_data(self):
        data = [str(rec) for rec in self.recs]
        for i in range(len(data)):
            if data[i] == 'None':
                data[i] = '-'*17+'\n'
        return data
    
    def between(self, key):
        if len(self.recs) == 0: return 0, False
        for rec in self.recs:
            if rec.key > key:
                returning = rec.page - 1
                exists = False
                if len(self.recs) > returning + 1: exists = True
                return returning, exists
        if len(self.recs) < 10: return len(self.recs) - 1, False
        return -1, False
    
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
        self.temp_index_page_num = 0
        self.temp_index_num = 0

    def for_seek(self, page):
        return 98*10*page

    def for_seek_index(self, page):
        return 18*10*page
    
    def add(self, rec_key):
        rec = Record(rec_key)
        rec.random(rec_key, None)
        page, does_next_exist = self.page_to_append(rec)
        if page != self.adding_page_num:
            self.save_page(self.adding_page_num)
            self.adding_page_num = page
            self.get_page(self.adding_page_num)
        if len(self.adding_page.recs) == 10:
            if does_next_exist:
                self.add_overflow(rec)
                return
            else:
                self.save_page(self.adding_page_num)
                self.adding_page_num = page + 1
                self.get_page(self.adding_page_num)
                self.adding_pages += 1
        if len(self.adding_page.recs) == 0:
            self.add_index(rec.key, self.adding_page_num)
        self.adding_page.add(rec)
    
    def add_overflow(self, rec):
        overflow, overflow_rec = self.get_overflow_from_rec(rec)
        if overflow == None:
            adding = self.overflow_page.add(rec)
            while adding == -1:
                self.save_overflow_page(self.overflow_page_num)
                self.overflow_page_num = self.overflow_pages - 1
                self.load_overflow_page(self.overflow_page_num)
                adding = self.overflow_page.add(rec)
                if adding == -1:
                    self.overflow_pages += 1
    
    def get_overflow_from_rec(self, rec):
        last_rec = None
        for data_rec in self.adding_page.recs:
            if data_rec.key > rec.key:
                return last_rec.overflow, last_rec
            last_rec = data_rec
        if last_rec == None:
            return self.adding_page.recs[-1].overflow, self.adding_page.recs[-1]
        return last_rec.overflow, last_rec

    def add_index(self, key, page):
        index_rec = IndexRecord(key, page)
        if self.index_page.add(index_rec):
            self.save_index_page(self.index_page_num)
            self.index_page_num += 1
            self.index_pages += 1
            self.index_page.recs = []
            self.index_page.add(index_rec)
    
    def next_page(self):
        data = self.adding_page.page_to_data()
        for line in data:
            self.data_file.write(line)
        self.adding_page_num += 1
        self.adding_page = Page()

    def page_to_append(self, rec):
        self.save_index_page(self.index_page_num)
        self.temp_index_page_num = 0
        self.temp_index_num = 0
        last_page = None

        index_rec = self.get_next_index_rec()
        while index_rec != None:
            
            if index_rec.key > rec.key: return last_page, True
            last_page = index_rec.page

            index_rec = self.get_next_index_rec()
        
        self.get_index_page(self.index_page_num)

        if last_page == None:
            return 0, False

        return last_page, False
    
    def get_next_index_rec(self):
        if self.temp_index_num == 0:
            self.get_index_page(self.temp_index_page_num)
        if self.temp_index_num == 0:
            pass
        if len(self.index_page.recs) > self.temp_index_num:
            if len(self.index_page.recs) == 1:
                pass
            rec = self.index_page.recs[self.temp_index_num]
        else:
            return None
        self.temp_index_num += 1
        if self.temp_index_num == 10:
            self.temp_index_num = 0
            self.temp_index_page_num += 1
        return rec
        
    def get_index_page(self, page):
        i = self.for_seek_index(page)
        self.index_file.seek(i)
        data = []
        for i in range(10):
            data.append(self.index_file.readline())
        self.index_page.data_to_page(data)
    
    def get_page(self, page):
        i = self.for_seek(page)
        self.data_file.seek(i)
        data = []
        for i in range(10):
            data.append(self.data_file.readline())
        self.adding_page.data_to_page(data)
    
    def save_index_page(self, page):
        data = self.index_page.page_to_data()
        i = self.for_seek_index(page)
        self.index_file.seek(i)
        for line in data:
            self.index_file.write(line)
    
    def save_page(self, page):
        data = self.adding_page.page_to_data()
        i = self.for_seek(page)
        self.data_file.seek(i)
        for line in data:
            self.data_file.write(line)

m = Manager()
for i in range(10, 50, 2):
    m.add(i+1)
    for rec in m.adding_page.recs:
        print(rec)
    for rec in m.index_page.recs:
        print(rec)
    for rec in m.overflow_page.recs:
        print(rec)
    print("#######################################")
m.add(30)
for rec in m.adding_page.recs:
    print(rec)
for rec in m.index_page.recs:
    print(rec)
for rec in m.overflow_page.recs:
    print(rec)
