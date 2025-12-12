#record 8-key space 9.9+space*4-vec space 8-overflow space 1-deleted
import random
import os
import time
import matplotlib.pyplot as plt

b = 4
NORMAL = 'normal'
OVERFLOW = 'overflow'

REC_LEN_WITHOUT_NL = 99
REC_LEN_WITH_NL = 100 

class Record:
    def __init__(self, key):
        self.vec = []
        self.key = key
        self.overflow = None
        self.deleted = 0
    
    def random(self, key, overflow):
        self.vec = []
        for i in range(4):
            self.vec.append(random.random()*100)
        self.key = key
        self.overflow = overflow
        self.deleted = 0
        
    def str_to_rec(self, data):
        try:
            self.key = int(data[0:8])
            self.vec = []
            for i in range(9, 89, 20):
                num = data[i:i+19]
                self.vec.append(float(num))
            overflow = data[89:97]
            if overflow[0] == 'x': self.overflow = None
            else: self.overflow = int(overflow)
            if len(data) > 98: self.deleted = int(data[98])
            else: self.deleted = 0
        except ValueError:
            self.key = 0
            self.deleted = 1

    def __str__(self):
        key_str = str(self.key)
        rec_str = key_str
        for i in range(9 - len(key_str)): rec_str = rec_str + ' '
        for i in range(4): rec_str = rec_str + f'{self.vec[i]:19.9f}' + ' '
        
        if self.overflow == None: rec_str = rec_str + 'x       '
        else:
            overflow_str = str(self.overflow)
            rec_str = rec_str + overflow_str
            for i in range(8-len(overflow_str)): rec_str = rec_str + ' '
        
        rec_str = rec_str + ' ' + str(self.deleted)
        return rec_str + '\n'

class IndexRecord:
    def __init__(self, key, page):
        self.key = key
        self.page = page

    def str_to_rec(self, data):
        if len(data) < 18: return
        try:
            self.key = int(data[0:8])
            self.page = int(data[9:17])
        except: pass
    
    def __str__(self):
        key_str = str(self.key)
        page_str = str(self.page)
        if len(key_str) < 8: key_str = key_str + (' ' * (8 - len(key_str)))
        if len(page_str) < 8: page_str = page_str + (' ' * (8 - len(page_str)))
        return key_str + ' ' + page_str + '\n'

class Page:
    def __init__(self):
        self.recs = []
        self.dirty = False
    
    def data_to_page(self, data):
        self.recs = []
        self.dirty = False
        if not data: return
        for line in data:
            if not line or line[0] == '-': continue
            rec = Record(0)
            rec.str_to_rec(line)
            self.recs.append(rec)
    
    def page_to_data(self):
        data = [str(rec) for rec in self.recs]
        pad_line = '-' * REC_LEN_WITHOUT_NL + '\n'
        for i in range(len(data)):
            if data[i] == 'None': data[i] = pad_line
        while len(data) < b: data.append(pad_line)
        return data
    
    def add(self, rec, type):
        if self.len() >= b: return -1
        if type == NORMAL:
            insert_idx = len(self.recs)
            for i in range(len(self.recs)):
                if self.recs[i].key > rec.key:
                    insert_idx = i
                    break
            self.recs.insert(insert_idx, rec)
        else:
            self.recs.append(rec)
        self.dirty = True
        return self.len() - 1
    
    def len(self):
        return sum(1 for rec in self.recs if rec is not None)

class IndexPage:
    def __init__(self):
        self.recs = []
        self.dirty = False
    
    def data_to_page(self, data):
        self.recs = []
        self.dirty = False
        if not data: return 
        for line in data:
            if not line or line[0] == '-': continue
            rec = IndexRecord(None, None)
            rec.str_to_rec(line)
            self.recs.append(rec)
    
    def page_to_data(self):
        data = [str(rec) for rec in self.recs]
        pad = '-'*17+'\n'
        while len(data) < b: data.append(pad)
        return data
    
    def add(self, rec):
        if self.len() >= b: return -1
        self.recs.append(rec)
        self.dirty = True
        return 0
    
    def len(self):
        return sum(1 for rec in self.recs if rec is not None)

class Manager:
    def __init__(self, alpha=0.5, reorg_threshold=0.4):
        self.alpha = alpha
        self.reorg_threshold = reorg_threshold
        
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
        self.adding_to_overflow = 0
        
        self.reads = 0
        self.writes = 0
        
        self.add(0)
        self.reset_counters()

    def reset_counters(self):
        self.reads = 0
        self.writes = 0

    def for_seek(self, page): return REC_LEN_WITH_NL * b * page
    def for_seek_index(self, page): return 18 * b * page
    
    def print_structure(self):
        print("\n" + "#"*50)
        print(" PHYSICAL STRUCTURE DUMP (Internal Representation)")
        print(f" Primary Pages: {self.adding_pages}, Overflow Pages: {self.overflow_pages}")
        print(f" Alpha: {self.alpha}, Reorg Threshold: {self.reorg_threshold}")
        print("#"*50)
        self.print_index_file()
        self.print_data_file()
        self.print_overflow_file()
        print("#"*50 + "\n")

    def browse_sorted(self):
        print("\n" + "="*50)
        print(" LOGICAL SEQUENCE (Sorted by Key)")
        print("="*50)

        self.push()
        
        data_handle = open('data.txt', 'r')
        overflow_handle = open('overflow.txt', 'r')
        
        for p_idx in range(self.adding_pages):
            page = Page()
            self.get_page_from_file(p_idx, data_handle, page)
            
            for rec in page.recs:
                if rec.deleted == 0:
                    print(f"Main:     {rec.key} | {rec.vec[0]:.2f}...")
                
                curr_ptr = rec.overflow
                while curr_ptr is not None:
                    ov_rec = self.get_old_overflow_rec(curr_ptr, overflow_handle)
                    if ov_rec:
                        if ov_rec.deleted == 0:
                            print(f"  -> Ov:  {ov_rec.key} | {ov_rec.vec[0]:.2f}...")
                        curr_ptr = ov_rec.overflow
                    else:
                        break
        
        data_handle.close()
        overflow_handle.close()
        print("="*50 + "\n")

    def _print_file_by_pages(self, filename, title):
        self.push() 
        print(f"\n--- {title} ({filename}) ---")
        if not os.path.exists(filename): return

        with open(filename, 'r') as f:
            page_idx = 0
            while True:
                lines = []
                for _ in range(b):
                    line = f.readline()
                    if not line: break
                    lines.append(line)
                if not lines: break
                print(f"[Page {page_idx}]")
                for line in lines: print(line, end='')
                page_idx += 1

    def print_index_file(self): self._print_file_by_pages('index.txt', 'INDEX FILE')
    def print_data_file(self): self._print_file_by_pages('data.txt', 'DATA FILE')
    def print_overflow_file(self): self._print_file_by_pages('overflow.txt', 'OVERFLOW FILE')

    def search(self, key):
        temp_rec = Record(key)
        page_num, _ = self.page_to_append(temp_rec)
        
        if self.adding_page_num != page_num:
             self.save_page(self.adding_page_num)
             self.adding_page_num = page_num
             self.get_page(self.adding_page_num)
        
        if self.adding_page.len() == 0: return None

        for rec in self.adding_page.recs:
            if rec.key == key:
                if rec.deleted == 1: return None
                return rec
        
        _, predecessor = self.get_overflow_from_rec(temp_rec)
        curr_overflow_ptr = predecessor.overflow
        
        while curr_overflow_ptr is not None:
             ov_ptr, ov_rec = self.get_overflow_from_rec_from_overflow(curr_overflow_ptr, False)
             if ov_rec.key == key:
                 if ov_rec.deleted == 1: return None
                 return ov_rec
             curr_overflow_ptr = ov_rec.overflow
        return None

    def update(self, key, new_vec):
        temp_rec = Record(key)
        page_num, _ = self.page_to_append(temp_rec)
        
        if self.adding_page_num != page_num:
             self.save_page(self.adding_page_num)
             self.adding_page_num = page_num
             self.get_page(self.adding_page_num)
        
        if self.adding_page.len() == 0: return False

        for rec in self.adding_page.recs:
            if rec.key == key:
                if rec.deleted == 1: return False
                rec.vec = new_vec
                self.adding_page.dirty = True 
                self.save_page(self.adding_page_num)
                return True
        
        _, predecessor = self.get_overflow_from_rec(temp_rec)
        curr_overflow_ptr = predecessor.overflow
        
        while curr_overflow_ptr is not None:
             ov_ptr, ov_rec = self.get_overflow_from_rec_from_overflow(curr_overflow_ptr, False)
             if ov_rec.key == key:
                 if ov_rec.deleted == 1: return False
                 ov_rec.vec = new_vec
                 self.overflow_page.dirty = True
                 self.save_overflow_page(self.overflow_page_num)
                 return True
             curr_overflow_ptr = ov_rec.overflow
        return False

    def delete(self, key):
        temp_rec = Record(key)
        page_num, _ = self.page_to_append(temp_rec)
        
        if self.adding_page_num != page_num:
             self.save_page(self.adding_page_num)
             self.adding_page_num = page_num
             self.get_page(self.adding_page_num)

        if self.adding_page.len() == 0: return False
             
        for rec in self.adding_page.recs:
            if rec.key == key:
                if rec.deleted == 1: return False
                rec.deleted = 1
                self.adding_page.dirty = True
                self.save_page(self.adding_page_num)
                return True
            
        _, predecessor = self.get_overflow_from_rec(temp_rec)
        curr_ptr = predecessor.overflow
        
        while curr_ptr is not None:
            curr_page_idx = curr_ptr // b
            curr_rec_idx = curr_ptr % b
            self.save_overflow_page(self.overflow_page_num)
            self.overflow_page_num = curr_page_idx
            self.get_overflow_page(self.overflow_page_num)
            
            rec = self.overflow_page.recs[curr_rec_idx]
            if rec.key == key:
                if rec.deleted == 1: return False
                rec.deleted = 1
                self.overflow_page.dirty = True
                self.save_overflow_page(self.overflow_page_num)
                return True
            curr_ptr = rec.overflow
        return False

    def add(self, rec_or_key, limit=None, check_exists=True, reorganizing=False):
        if limit is None:
            if reorganizing:
                limit = max(1, int(b * self.alpha))
            else:
                limit = b

        if isinstance(rec_or_key, Record):
            rec = rec_or_key
            rec.overflow = None
        else:
            rec = Record(rec_or_key)
            rec.random(rec_or_key, None)
        
        if not reorganizing: rec.deleted = 0

        if check_exists and not reorganizing:
            if self.search(rec.key): 
                print(f"Key {rec.key} already exists.")
                return

        page, does_next_exist = self.page_to_append(rec)
        if page != self.adding_page_num:
            self.save_page(self.adding_page_num)
            self.adding_page_num = page
            self.get_page(self.adding_page_num)
        
        if self.adding_page.len() >= limit:
            if reorganizing:
                self.save_page(self.adding_page_num)
                self.adding_page_num = page + 1
                self.get_page(self.adding_page_num)
                self.adding_pages += 1
                
                if self.adding_page.len() == 0:
                    self.add_index(rec.key, self.adding_page_num)
                
                self.adding_page.add(rec, NORMAL)
                return
            else:
                self.add_overflow(rec)
                
                dynamic_limit = max(2, int(self.adding_pages * self.reorg_threshold))
                if self.overflow_pages > dynamic_limit: 
                    print(f"[AUTO-REORG] Overflow ({self.overflow_pages}pg) > Limit ({dynamic_limit}pg).")
                    self.reorganize()
                return

        if self.adding_page.len() == 0:
            self.add_index(rec.key, self.adding_page_num)
        
        if self.adding_page.add(rec, NORMAL) == -1:
            self.add_overflow(rec)
        
        if not reorganizing:
            dynamic_limit = max(2, int(self.adding_pages * self.reorg_threshold))
            if self.overflow_pages > dynamic_limit: 
                print(f"[AUTO-REORG] Overflow limit reached.")
                self.reorganize()
    
    def add_overflow(self, rec):
        overflow, overflow_rec = self.get_overflow_from_rec(rec)
        if overflow == None:
            adding = self.overflow_page.add(rec, OVERFLOW)
            while adding == -1:
                self.save_overflow_page(self.overflow_page_num)
                self.overflow_page_num = self.overflow_pages - 1
                self.get_overflow_page(self.overflow_page_num)
                adding = self.overflow_page.add(rec, OVERFLOW)
                if adding == -1: self.overflow_pages += 1
            overflow_rec.overflow = adding + self.overflow_page_num * b
            self.adding_page.dirty = True 
        else:
            new_overflow, new_overflow_rec = self.get_overflow_from_rec_from_overflow(overflow, 0)
            last_overflow = overflow
            last_overflow_rec = overflow_rec
            i = 0
            if new_overflow_rec.key > rec.key: new_overflow = None
            while new_overflow != None:
                last_overflow = overflow
                overflow = new_overflow
                last_overflow_rec = overflow_rec
                overflow_rec = new_overflow_rec
                new_overflow, new_overflow_rec = self.get_overflow_from_rec_from_overflow(overflow, 0)
                i+=1
                if new_overflow_rec.key > rec.key: break
            if new_overflow_rec.key > rec.key:
                if self.get_page_from_overflow(last_overflow) != self.overflow_page_num:
                    self.save_overflow_page(self.overflow_page_num)
                    self.overflow_page_num = self.get_page_from_overflow(last_overflow)
                    self.get_overflow_page(self.overflow_page_num)
                new_overflow_rec = self.overflow_page.recs[last_overflow%b]
                if i == 0:
                    new_overflow_rec = last_overflow_rec
                    self.adding_page.dirty = True
                else:
                    self.overflow_page.dirty = True

            if new_overflow_rec.overflow != None:
                rec.overflow = new_overflow_rec.overflow
            new_overflow_rec.overflow = self.adding_to_overflow
            self.overflow_page.dirty = True

            adding = self.overflow_page.add(rec, OVERFLOW)
            while adding == -1:
                self.save_overflow_page(self.overflow_page_num)
                self.overflow_page_num = self.overflow_pages - 1
                self.get_overflow_page(self.overflow_page_num)
                adding = self.overflow_page.add(rec, OVERFLOW)
                if adding == -1: self.overflow_pages += 1
        self.adding_to_overflow += 1

    def get_page_from_overflow(self, overflow): return overflow//b
            
    def get_overflow_from_rec_from_overflow(self, overflow, reorganizing):
        overflow_page = overflow//b
        overflow_index = overflow%b
        if not reorganizing: self.save_overflow_page(self.overflow_page_num)
        self.overflow_page_num = overflow_page
        self.get_overflow_page(self.overflow_page_num)
        return self.overflow_page.recs[overflow_index].overflow, self.overflow_page.recs[overflow_index]

    def get_overflow_from_rec(self, rec):
        last_rec = None
        for data_rec in self.adding_page.recs:
            if data_rec.key > rec.key:
                if last_rec == None: pass
                return last_rec.overflow, last_rec
            last_rec = data_rec
        if last_rec == None:
            return self.adding_page.recs[-1].overflow, self.adding_page.recs[-1]
        return last_rec.overflow, last_rec

    def add_index(self, key, page):
        index_rec = IndexRecord(key, page)
        if self.index_page.add(index_rec) == -1:
            self.save_index_page(self.index_page_num)
            self.index_page_num += 1
            self.index_pages += 1
            self.index_page.recs = []
            self.index_page.add(index_rec)
    
    def page_to_append(self, rec):
        self.save_index_page(self.index_page_num)
        self.temp_index_page_num = 0
        self.temp_index_num = 0
        last_page = None
        returning = None
        index_rec = self.get_next_index_rec()
        while index_rec != None:
            if index_rec.key > rec.key:
                returning = last_page, True
                break
            last_page = index_rec.page
            index_rec = self.get_next_index_rec()
        self.get_index_page(self.index_page_num)
        if returning: return returning
        if last_page == None: return 0, False
        return last_page, False
    
    def get_next_index_rec(self):
        if self.temp_index_num == 0: self.get_index_page(self.temp_index_page_num)
        if self.index_page.len() > self.temp_index_num:
            rec = self.index_page.recs[self.temp_index_num]
        else: return None
        self.temp_index_num += 1
        if self.temp_index_num == b:
            self.temp_index_num = 0
            self.temp_index_page_num += 1
        return rec
        
    def get_index_page(self, page):
        i = self.for_seek_index(page)
        self.index_file.seek(i)
        data = []
        for i in range(b): data.append(self.index_file.readline())
        self.index_page.data_to_page(data)
    
    def get_page(self, page):
        i = self.for_seek(page)
        self.data_file.seek(i)
        data = []
        for i in range(b): data.append(self.data_file.readline())
        self.adding_page.data_to_page(data)
        self.reads += 1
    
    def get_page_from_file(self, page_num, file, page):
        i = self.for_seek(page_num)
        file.seek(i)
        data = []
        for i in range(b):
            line = file.readline()
            if not line: break
            data.append(line)
        while len(data) < b: data.append('')
        page.data_to_page(data)
        self.reads += 1
    
    def get_old_overflow_rec(self, overflow_ptr, file_handle):
        page = overflow_ptr // b
        idx = overflow_ptr % b
        seek_pos = self.for_seek(page)
        file_handle.seek(seek_pos)
        lines = []
        for _ in range(b): lines.append(file_handle.readline())
        temp_page = Page()
        temp_page.data_to_page(lines)
        if idx < len(temp_page.recs): return temp_page.recs[idx]
        return None

    def get_overflow_page(self, page):
        i = self.for_seek(page)
        self.overflow_file.seek(i)
        data = []
        for i in range(b): data.append(self.overflow_file.readline())
        self.overflow_page.data_to_page(data)
        self.reads += 1
    
    def save_overflow_page(self, page):
        if self.overflow_page.dirty == False: return
        data = self.overflow_page.page_to_data()
        i = self.for_seek(page)
        self.overflow_file.seek(i)
        for line in data: self.overflow_file.write(line)
        self.writes += 1
        self.overflow_page.dirty = False
    
    def save_index_page(self, page):
        if self.index_page.dirty == False: return
        data = self.index_page.page_to_data()
        i = self.for_seek_index(page)
        self.index_file.seek(i)
        for line in data: self.index_file.write(line)
        self.writes += 1
        self.index_page.dirty = False
    
    def save_page(self, page):
        if self.adding_page.dirty == False: return
        data = self.adding_page.page_to_data()
        i = self.for_seek(page)
        self.data_file.seek(i)
        for line in data: self.data_file.write(line)
        self.writes += 1
        self.adding_page.dirty = False
    
    def push(self):
        self.save_page(self.adding_page_num)
        self.save_index_page(self.index_page_num)
        self.save_overflow_page(self.overflow_page_num)

    def reorganize(self):
        print(f"\n*** REORGANIZATION STARTED (Alpha={self.alpha}) ***")
        self.push()
        old_data_file = self.data_file
        old_overflow_handle = open('overflow.txt', 'r')
        
        self.data_file = open('new_data.txt', 'w+')
        self.index_file = open('new_index.txt', 'w+')
        self.overflow_file = open('new_overflow.txt', 'w+')

        reading_page_num = 0
        
        self.adding_page.recs = []
        self.index_page.recs = []
        self.overflow_page.recs = []
        self.overflow_pages = 1
        self.index_pages = 1
        self.adding_pages = 1
        self.overflow_page_num = 0
        self.index_page_num = 0
        self.adding_page_num = 0
        self.adding_to_overflow = 0

        while True:
            temp_adding_page = Page()
            self.get_page_from_file(reading_page_num, old_data_file, temp_adding_page)
            if temp_adding_page.len() == 0: break
                
            for rec in temp_adding_page.recs:
                next_overflow_ptr = rec.overflow 
                if rec.deleted == 0:
                    rec.overflow = None 
                    self.add(rec, limit=None, check_exists=False, reorganizing=True) 
                
                curr_ptr = next_overflow_ptr
                while curr_ptr is not None:
                    overflow_rec = self.get_old_overflow_rec(curr_ptr, old_overflow_handle)
                    if overflow_rec:
                        next_overflow_ptr = overflow_rec.overflow 
                        if overflow_rec.deleted == 0:
                            overflow_rec.overflow = None
                            self.add(overflow_rec, limit=None, check_exists=False, reorganizing=True) 
                        curr_ptr = next_overflow_ptr
                    else: break 
            reading_page_num += 1

        self.push()
        self.data_file.close()
        self.index_file.close()
        self.overflow_file.close()
        old_data_file.close()
        old_overflow_handle.close()

        if os.path.exists('data.txt'): os.remove('data.txt')
        if os.path.exists('index.txt'): os.remove('index.txt')
        if os.path.exists('overflow.txt'): os.remove('overflow.txt')
        
        os.rename('new_data.txt', 'data.txt')
        os.rename('new_index.txt', 'index.txt')
        os.rename('new_overflow.txt', 'overflow.txt')

        self.data_file = open('data.txt', 'r+')
        self.index_file = open('index.txt', 'r+')
        self.overflow_file = open('overflow.txt', 'r+')
        print("*** REORGANIZATION COMPLETE ***\n")
    
    def run_test_file(self, filename):
        if not os.path.exists(filename):
            print("File not found.")
            return

        with open(filename, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if not parts: continue
                
                cmd = parts[0].upper()
                self.reset_counters()
                
                try:
                    if cmd == 'A': # Add: A 10
                        key = int(parts[1])
                        print(f"CMD: Add {key}")
                        self.add(key)
                    elif cmd == 'D': # Delete: D 10
                        key = int(parts[1])
                        print(f"CMD: Delete {key}")
                        if self.delete(key): print("Deleted.")
                        else: print("Not Found.")
                    elif cmd == 'U': # Update: U 10 1.1 2.2 3.3 4.4
                        key = int(parts[1])
                        vec = [float(x) for x in parts[2:]]
                        print(f"CMD: Update {key}")
                        if self.update(key, vec): print("Updated.")
                        else: print("Not Found.")
                    elif cmd == 'S': # Search: S 10
                        key = int(parts[1])
                        print(f"CMD: Search {key}")
                        res = self.search(key)
                        if res: print(f"Found: {res}")
                        else: print("Not Found.")
                except Exception as e:
                    print(f"Error executing line: {line} -> {e}")

                print(f"Disk Operations -> Reads: {self.reads}, Writes: {self.writes}")

    def experiment(self, n_recs):
        arr = [i for i in range(1, n_recs+1)]
        random.shuffle(arr)
        for i in arr: self.add(i)

if __name__ == "__main__":
    m = Manager(alpha=0.5, reorg_threshold=0.4)
    print("Database Manager Initialized.")

    while True:
        print("\n" + "="*30)
        print("       MAIN MENU")
        print("="*30)
        print("1. Add Record")
        print("2. Search Record")
        print("3. Update Record")
        print("4. Delete Record")
        print("5. Reorganize Database")
        print("6. Show Structure (Physical Dump)")
        print("7. Browse Sorted (Logical View)")
        print("8. Run Test File")
        print("9. Configure Experiment (Set Alpha)")
        print("10. Run an experiment")
        print("0. Exit")
        print("="*30)

        choice = input("Choose an option: ").strip()
        m.reset_counters()

        if choice == '1':
            try:
                key = int(input("Enter key (int): "))
                m.add(key)
                print(f"Result: Added/Processed.")
            except ValueError: print("Invalid input.")
        elif choice == '2':
            try:
                key = int(input("Enter key: "))
                res = m.search(key)
                if res: print(f"Result: {res}")
                else: print("Result: Not Found.")
            except ValueError: print("Invalid.")
        elif choice == '3':
            try:
                key = int(input("Enter key: "))
                vec = [float(x) for x in input("Enter 4 floats: ").split()]
                if m.update(key, vec): print("Result: Updated.")
                else: print("Result: Failed.")
            except ValueError: print("Invalid.")
        elif choice == '4':
            try:
                key = int(input("Enter key: "))
                if m.delete(key): print("Result: Deleted.")
                else: print("Result: Failed.")
            except ValueError: print("Invalid.")
        elif choice == '5':
            m.reorganize()
        elif choice == '6':
            m.print_structure()
        elif choice == '7':
            m.browse_sorted()
        elif choice == '8':
            fname = input("Enter filename: ")
            m.run_test_file(fname)
        elif choice == '9':
            try:
                a = float(input("Enter Alpha (0.1 - 1.0): "))
                t = float(input("Enter Reorg Threshold (e.g. 0.4 for 40%): "))
                m = Manager(alpha=a, reorg_threshold=t)
                print("Manager re-initialized with new parameters. DB cleared.")
            except ValueError: print("Invalid.")
        elif choice == '10':
            try:
                print("1. Add records")
                print("2. Full experiment")
                new_choice = input()
                if new_choice == '1':
                    n = int(input("Num records: "))
                    m.experiment(n)
                elif new_choice == '2':
                    alphas = [0.25, 0.5, 0.75]
                    thresholds = [0.2, 0.4, 0.6, 0.8]
                    operations = []
                    for threshold in thresholds:
                        for alpha in alphas:
                            reads = 0
                            writes = 0
                            n = 10
                            for i in range(n):
                                m = Manager(alpha=alpha, reorg_threshold=threshold)
                                m.experiment(200)
                                reads, writes = m.reads, m.writes
                            reads, writes = reads/n, writes/n
                            operations.append([reads, writes])
                    i = 0
                    alphas_g = []
                    thresholds_g = []
                    reads_g = []
                    writes_g = []
                    for threshold in thresholds:
                        for alpha in alphas:
                            print(f"Disk Operations for:\nAlpha = {alpha}\nReorganization Threshold = {threshold}\nReads: {operations[i][0]}, Writes: {operations[i][1]}\n")
                            alphas_g.append(alpha)
                            thresholds_g.append(threshold)
                            reads_g.append(operations[i][0])
                            writes_g.append(operations[i][1])
                            i += 1

                    unique_thresholds = sorted(list(set(thresholds_g)))
                    data_by_threshold = {t: {'alphas': [], 'reads': [], 'writes': []} for t in unique_thresholds}

                    for i in range(len(alphas_g)):
                        t = thresholds_g[i]
                        data_by_threshold[t]['alphas'].append(alphas_g[i])
                        data_by_threshold[t]['reads'].append(reads_g[i])
                        data_by_threshold[t]['writes'].append(writes_g[i])

                    for t in unique_thresholds:
                        zipped = sorted(zip(data_by_threshold[t]['alphas'], 
                                            data_by_threshold[t]['reads'], 
                                            data_by_threshold[t]['writes']))
                        if zipped:
                            data_by_threshold[t]['alphas'], data_by_threshold[t]['reads'], data_by_threshold[t]['writes'] = zip(*zipped)

                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

                    for t in unique_thresholds:
                        ax1.plot(data_by_threshold[t]['alphas'], data_by_threshold[t]['reads'], marker='o', label=f'Threshold: {t}')

                    ax1.set_title('Disk READ Operations vs Alpha')
                    ax1.set_xlabel('Alpha')
                    ax1.set_ylabel('Number of Reads')
                    ax1.grid(True)
                    ax1.legend()

                    for t in unique_thresholds:
                        ax2.plot(data_by_threshold[t]['alphas'], data_by_threshold[t]['writes'], marker='s', label=f'Threshold: {t}')

                    ax2.set_title('Disk WRITE Operations vs Alpha')
                    ax2.set_xlabel('Alpha')
                    ax2.set_ylabel('Number of Writes')
                    ax2.grid(True)
                    ax2.legend()

                    plt.tight_layout()
                    plt.show()
            except ValueError: print("Invalid.")
        elif choice == '0':
            m.push()
            break
        
        if choice in ['1','2','3','4','5','10']:
            print(f"Disk Operations -> Reads: {m.reads}, Writes: {m.writes}")