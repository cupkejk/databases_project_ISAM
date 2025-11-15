from random import random
N_DIMENSIONAL_VECTOR = 4
FILES = {1:'data.txt', 2:'runs.txt', 3:'out.txt'}
RECORDS = 20000
VECTOR_DIMENSION_STR_LEN = 22

def cmp(a, b):
    vec_a = Vector()
    vec_a.from_str(a)
    vec_b = Vector()
    vec_b.from_str(b)
    a_mag = vec_a.mag()
    b_mag = vec_b.mag()
    if a_mag > b_mag: return 1
    elif a_mag < b_mag: return -1
    else: return 0

def my_key(a):
    vec_a = Vector()
    vec_a.from_str(a)
    return vec_a.mag()

def str_to_vec(text):
    vec = Vector()
    vec.from_str(text)
    return vec

def random_vec():
    vec = Vector()
    vec.random()
    return vec

def file_index(page_id, b):
    start = page_id*b*(N_DIMENSIONAL_VECTOR*VECTOR_DIMENSION_STR_LEN+N_DIMENSIONAL_VECTOR)
    reading = b*8
    return start, reading

class Vector:
    def __init__(self):
        self.vec = [None for _ in range(N_DIMENSIONAL_VECTOR)]
    
    def random(self):
        self.vec = [(random()-0.5)*100 for _ in range(N_DIMENSIONAL_VECTOR)]

    def __str__(self):
        if self.vec[0] == None:
            return (((('-'*VECTOR_DIMENSION_STR_LEN) + ' ')) * (N_DIMENSIONAL_VECTOR - 1)) + '-'*VECTOR_DIMENSION_STR_LEN
        vec_str = ''
        for i in range(N_DIMENSIONAL_VECTOR):
            vec_str += f'{float(self.vec[i]):{VECTOR_DIMENSION_STR_LEN}.{VECTOR_DIMENSION_STR_LEN//2}f}' + ' ' 
        return vec_str[0:-1]

    def from_str(self, text):
        if not text or text == '\n' or text == (((('-'*VECTOR_DIMENSION_STR_LEN) + ' ')) * (N_DIMENSIONAL_VECTOR - 1)) + '-'*VECTOR_DIMENSION_STR_LEN+'\n':
            self.vec = [None for _ in range(N_DIMENSIONAL_VECTOR)]
            return
        for i in range(N_DIMENSIONAL_VECTOR):
            self.vec = [float(str) for str in text.strip().split()]
    
    def empty(self):
        self.vec = [None for _ in range(N_DIMENSIONAL_VECTOR)]
    
    def mag(self):
        if self.vec[0] == None:
            return float('inf')
        sum = 0
        for num in self.vec:
            sum += num**2
        sum = sum**(1/2)
        return sum



class Page:
    def __init__(self, b = 10):
        self.b = b
        self.records = [Vector() for _ in range(self.b)]
        self.n_records = 0
        self.is_empty = True
        self.index = 0

    def read(self):
        if str(self.records[self.index]) == '': return ''
        ret = str(self.records[self.index]) + '\n'
        self.index += 1
        if(self.index >= self.b):
            self.is_empty = True
            self.index = 0
        return ret
    
    def get(self):
        return str(self.records[self.index]) + '\n'
    
    def write(self, record):
        self.records[self.n_records].from_str(record)
        self.n_records+=1
    
    def isFull(self):
        if self.n_records >= self.b: return True
        return False
    
    def isEmpty(self):
        return self.is_empty
    
    def empty(self):
        self.n_records = 0
        self.is_empty = True
        self.index = 0
        for i in range(len(self.records)):
            self.records[i].empty()

    def data_to_page(self, data):
        record = data[0]
        i = 0
        while i < self.b and record:
            record = data[i]
            self.records[i].from_str(record)
            i+=1
        while i < self.b:
            self.records[i].from_str('')
            i+=1
        self.is_empty = False
        self.index = 0
    
    def page_to_data(self):
        data = []
        for i in range(len(self.records)):
            record = str(self.records[i]) + '\n'
            data.append(record)
        return data

class FileManager:
    def __init__(self, b = 10, n = 10):
        self.b = b
        self.n = n
        self.buffers = []
        self.disk_reads = 0
        self.disk_writes = 0
        self.read_buffer = Page()
        self.write_buffer = Page()
        self.read_page = 0
        self.write_page = 0
        self.last_read_file = None
        self.last_write_file = None
        self.run_pages = []

    def read(self, file, page_id = None):
        if self.last_read_file == None:
            self.last_read_file = file
        if self.last_read_file != file:
            self.last_read_file = file
            self.read_page = 0
        if self.read_buffer.isEmpty() == False:
            return self.read_buffer.read()
        self.read_file(file, page_id)
        return self.read_buffer.read()

    def read_file(self, file, page_id = None):
        self.disk_reads += 1
        if page_id == None:
            index, reading = file_index(self.read_page, self.b)
        else:
            index, reading = file_index(page_id, self.b)
        file.seek(index)
        data = []
        for i in range(10):
            line = file.readline()
            data.append(line)
        self.read_buffer.data_to_page(data)
        self.read_page += 1
    
    def write(self, file, record):
        if self.last_write_file == None:
            self.last_write_file = file
        if self.last_write_file != file:
            self.last_write_file = file
            self.write_page = 0
        
        self.write_buffer.write(record)
        if self.write_buffer.isFull():
            self.write_file(file)
            self.write_buffer.empty()
        
        return self.write_page
    
    def write_file(self, file = None):
        data = self.write_buffer.page_to_data()
        if file == None:
            return data
        self.disk_writes += 1
        self.write_page += 1
        for record in data:
            file.write(record)
    
    def dump(self, file = None):
        if self.write_buffer.records[0].vec[0] != None:
            self.write_file(file)
        else: return self.write_file()
        self.write_buffer.empty()

    def setup_buffers(self):
        self.buffers = [Page() for _ in range(self.n)]
    
    def load_buffers(self, runs_file):
        self.read_buffer.empty()
        for i in range(len(self.buffers)):
            buffer = self.buffers[i]
            if buffer.isEmpty():
                if len(self.run_pages[i]):
                    page_id = self.run_pages[i][0]
                else:
                    continue
                self.run_pages[i].remove(page_id)
                data = []
                for j in range(self.b):
                    record = self.read(runs_file, page_id)
                    data.append(record)
                buffer.data_to_page(data)
    
    def get_smallest(self):
        smallest_index = -1
        smallest_mag = float('inf')
        for i in range(len(self.buffers)):
            if self.buffers[i].isEmpty():
                continue
            num = self.buffers[i].get()
            num = my_key(num)
            if num < smallest_mag:
                smallest_mag = num
                smallest_index = i
        if smallest_index == -1: return -1
        record = self.buffers[smallest_index].read()
        return record





            
def create_file():
    vec = Vector()
    with open('data.txt', 'w') as f:
        for i in range(RECORDS):
            vec.random()
            f.write(str(vec) + '\n')

fm = FileManager()

def make_runs(fm):
    data_file = open(FILES[1], 'r')
    runs_file = open(FILES[2], 'w')
    runs = fm.n
    records_per_run = fm.b*fm.n
    runs = RECORDS/records_per_run
    if runs != int(runs):
        runs = int(runs) + 1
    runs = int(runs)
    buffer = [None for _ in range(records_per_run)]


    for run_num in range(runs):
        fm.run_pages.append([])

        i = 0
        while i < records_per_run:
            record = fm.read(data_file)
            buffer[i] = record
            i += 1
        buffer = sorted(buffer, key = my_key)
        for item in buffer:
            page_id = fm.write(runs_file, item)
            if page_id not in fm.run_pages[run_num]:
                fm.run_pages[run_num].append(page_id)
        fm.dump(runs_file)
        buffer = [None for _ in range(records_per_run)]

def merge_runs(fm, merging):
    fm.setup_buffers()
    runs_file = open(FILES[2], 'r')
    out_file = open(FILES[3], 'a')
    fm.load_buffers(runs_file, merging)



def merge_all_runs(fm):
    run_pages = []
    merge_list = []
    for i in range(len(fm.run_pages)):
        if i % fm.n == 0:
            merge_list.append([i])
        else:
            merge_list[i//fm.n].append(i)
    print(fm.run_pages)
    print(merge_list)
    
def sort_runs(fm):
    fm.setup_buffers()
    runs_file = open(FILES[2], 'r')
    out_file = open(FILES[3], 'w')
    fm.load_buffers(runs_file)
    num = fm.get_smallest()
    print(num)
    while num != -1:
        print(num)
        fm.write(out_file, num)
        fm.load_buffers(runs_file)
        num = fm.get_smallest()
    fm.dump(out_file)
    

def test():
    data = []
    with open('out.txt', 'r') as f:
        line = f.readline()
        while line:    
            data.append(my_key(line))
            line = f.readline()
    last = data[0]
    for dat in data:
        if dat < last:
            print("WRONGGGGGGG!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        last = dat
        

# test()
create_file()
make_runs(fm)
merge_all_runs(fm)
# sort_runs(fm)
    


