#record 8-key space 9.9+space*4-vec space 8-overflow
import random
import os
import time

b = 4
NORMAL = 'normal'
OVERFLOW = 'overflow'

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
        
        if self.overflow == None:
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
        if not data or data[0] == '': return
        for line in data:
            if line == '' or line[0] == '-': 
                continue
            rec = Record(0)
            rec.str_to_rec(line)
            self.recs.append(rec)
    
    def page_to_data(self):
        data = [str(rec) for rec in self.recs]
        for i in range(len(data)):
            if data[i] == 'None':
                data[i] = '-'*97 + '\n'
        while len(data) < b:
            data.append('-'*97 + '\n')
        return data
    
    def random(self):
        for i in range(b):
            rec = Record(0)
            rec.random(0, 0)
            self.recs.append(rec)
    
    def add(self, rec, type):
        if self.len() >= b: return -1
        if type == NORMAL:
            if self.len() > 0:
                if self.recs[-1].key > rec.key: return -1
        self.recs.append(rec)
        return self.len() - 1
    
    def len(self):
        size = 0
        for rec in self.recs:
            if rec != None:
                size+=1
        return size

class IndexPage:
    def __init__(self):
        self.recs = []
    
    def data_to_page(self, data):
        self.recs = []
        if not data or data[0] == '': return 
        for line in data:
            if line == '' or line[0] == '-': continue
            rec = IndexRecord(None, None)
            rec.str_to_rec(line)
            self.recs.append(rec)
    
    def page_to_data(self):
        data = [str(rec) for rec in self.recs]
        for i in range(len(data)):
            if data[i] == 'None':
                data[i] = '-'*17+'\n'
            while len(data) < b:
                data.append('-'*17+'\n')
        return data
    
    def between(self, key):
        if self.len() == 0: return 0, False
        for rec in self.recs:
            if rec.key > key:
                returning = rec.page - 1
                exists = False
                if self.len() > returning + 1: exists = True
                return returning, exists
        if self.len() < b: return self.len() - 1, False
        return -1, False
    
    def random(self):
        for i in range(b):
            rec = Record(0)
            rec.random(0, 0)
            self.recs.append(rec)
    
    def add(self, rec):
        if self.len() >= b: return -1

        self.recs.append(rec)
        return 0
    
    def len(self):
        size = 0
        for rec in self.recs:
            if rec != None:
                size+=1
        return size

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
        self.adding_to_overflow = 0
        self.add(0)

    def for_seek(self, page):
        return 98*b*page

    def for_seek_index(self, page):
        return 18*b*page
    
    # -----------------------------------------------------------
    # NOWE METODY DO WYŚWIETLANIA PLIKÓW
    # -----------------------------------------------------------
    def print_structure(self):
        print("\n" + "#"*50)
        print("DATABASE STRUCTURE DUMP")
        print("#"*50)
        self.print_index_file()
        self.print_data_file()
        self.print_overflow_file()
        print("#"*50 + "\n")

    def _print_file_by_pages(self, filename, title):
        self.push() # Zapisujemy stan pamięci na dysk przed odczytem
        print(f"\n--- {title} ({filename}) ---")
        if not os.path.exists(filename):
            print("[File does not exist]")
            return

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
                for line in lines:
                    print(line, end='')
                page_idx += 1

    def print_index_file(self):
        self._print_file_by_pages('index.txt', 'INDEX FILE')

    def print_data_file(self):
        self._print_file_by_pages('data.txt', 'DATA FILE')

    def print_overflow_file(self):
        self._print_file_by_pages('overflow.txt', 'OVERFLOW FILE')
    # -----------------------------------------------------------

    def search(self, key):
        temp_rec = Record(key)
        page_num, _ = self.page_to_append(temp_rec)
        
        if self.adding_page_num != page_num:
             self.save_page(self.adding_page_num)
             self.adding_page_num = page_num
             self.get_page(self.adding_page_num)
        
        if self.adding_page.len() == 0:
            return None

        for rec in self.adding_page.recs:
            if rec.key == key:
                return rec
        
        _, predecessor = self.get_overflow_from_rec(temp_rec)
        curr_overflow_ptr = predecessor.overflow
        
        while curr_overflow_ptr is not None:
             ov_ptr, ov_rec = self.get_overflow_from_rec_from_overflow(curr_overflow_ptr, False)
             if ov_rec.key == key:
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
        
        if self.adding_page.len() == 0:
            return False

        for rec in self.adding_page.recs:
            if rec.key == key:
                rec.vec = new_vec
                self.save_page(self.adding_page_num)
                return True
        
        _, predecessor = self.get_overflow_from_rec(temp_rec)
        curr_overflow_ptr = predecessor.overflow
        
        while curr_overflow_ptr is not None:
             ov_ptr, ov_rec = self.get_overflow_from_rec_from_overflow(curr_overflow_ptr, False)
             if ov_rec.key == key:
                 ov_rec.vec = new_vec
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

        if self.adding_page.len() == 0:
            print(f"Key {key} not found for deletion.")
            return False
             
        found_in_main = -1
        for i, rec in enumerate(self.adding_page.recs):
            if rec.key == key:
                found_in_main = i
                break
        
        if found_in_main != -1:
            rec = self.adding_page.recs[found_in_main]
            if rec.overflow is None:
                del self.adding_page.recs[found_in_main]
                self.save_page(self.adding_page_num)
            else:
                first_ov_ptr = rec.overflow
                next_ov_ptr, first_ov_rec = self.get_overflow_from_rec_from_overflow(first_ov_ptr, False)
                rec.key = first_ov_rec.key
                rec.vec = first_ov_rec.vec
                rec.overflow = first_ov_rec.overflow 
                self.save_page(self.adding_page_num)
            return True
            
        _, predecessor = self.get_overflow_from_rec(temp_rec)
        prev_info = {
            'location': 'main', 
            'page': self.adding_page_num, 
            'index_in_page': self.adding_page.recs.index(predecessor)
        }
        
        curr_ptr = predecessor.overflow
        
        while curr_ptr is not None:
            curr_page_idx = curr_ptr // b
            curr_rec_idx = curr_ptr % b
            
            self.save_overflow_page(self.overflow_page_num)
            self.overflow_page_num = curr_page_idx
            self.get_overflow_page(self.overflow_page_num)
            
            rec = self.overflow_page.recs[curr_rec_idx]
            
            if rec.key == key:
                next_link = rec.overflow
                if prev_info['location'] == 'main':
                    if self.adding_page_num != prev_info['page']:
                        self.get_page(prev_info['page'])
                    self.adding_page.recs[prev_info['index_in_page']].overflow = next_link
                    self.save_page(prev_info['page'])
                else:
                    prev_page = prev_info['page']
                    self.get_overflow_page(prev_page)
                    self.overflow_page.recs[prev_info['index_in_page']].overflow = next_link
                    self.save_overflow_page(prev_page)
                return True
            
            prev_info = {
                'location': 'overflow',
                'page': curr_page_idx,
                'index_in_page': curr_rec_idx
            }
            curr_ptr = rec.overflow

        print(f"Key {key} not found for deletion.")
        return False

    def add(self, rec_or_key, limit=b, check_exists=True):
        if isinstance(rec_or_key, Record):
            rec = rec_or_key
            rec.overflow = None
        else:
            rec = Record(rec_or_key)
            rec.random(rec_or_key, None)
        
        if check_exists:
            if self.update(rec.key, rec.vec):
                return
            
        page, does_next_exist = self.page_to_append(rec)
        if page != self.adding_page_num:
            self.save_page(self.adding_page_num)
            self.adding_page_num = page
            self.get_page(self.adding_page_num)
        
        if self.adding_page.len() >= limit:
            if does_next_exist:
                self.add_overflow(rec)
                return
            else:
                if self.adding_page.recs[-1].key > rec.key:
                    self.add_overflow(rec)
                    return
                self.save_page(self.adding_page_num)
                self.adding_page_num = page + 1
                self.get_page(self.adding_page_num)
                self.adding_pages += 1
        
        if self.adding_page.len() == 0:
            self.add_index(rec.key, self.adding_page_num)
        
        if self.adding_page.add(rec, NORMAL) == -1:
            self.add_overflow(rec)
        
        if self.overflow_pages >= 4: self.reorganize()
    
    def add_overflow(self, rec):
        overflow, overflow_rec = self.get_overflow_from_rec(rec)
        if overflow == None:
            adding = self.overflow_page.add(rec, OVERFLOW)
            while adding == -1:
                self.save_overflow_page(self.overflow_page_num)
                self.overflow_page_num = self.overflow_pages - 1
                self.get_overflow_page(self.overflow_page_num)
                adding = self.overflow_page.add(rec, OVERFLOW)
                if adding == -1:
                    self.overflow_pages += 1
            overflow_rec.overflow = adding + self.overflow_page_num * b
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
            if new_overflow_rec.overflow != None:
                rec.overflow = new_overflow_rec.overflow
            new_overflow_rec.overflow = self.adding_to_overflow
            adding = self.overflow_page.add(rec, OVERFLOW)
            while adding == -1:
                self.save_overflow_page(self.overflow_page_num)
                self.overflow_page_num = self.overflow_pages - 1
                self.get_overflow_page(self.overflow_page_num)
                adding = self.overflow_page.add(rec, OVERFLOW)
                if adding == -1:
                    self.overflow_pages += 1
        self.adding_to_overflow += 1

    def get_page_from_overflow(self, overflow):
        return overflow//b
            
    def get_overflow_from_rec_from_overflow(self, overflow, reorganizing):
        overflow_page = overflow//b
        overflow_index = overflow%b
        if not reorganizing:
            self.save_overflow_page(self.overflow_page_num)
        self.overflow_page_num = overflow_page
        self.get_overflow_page(self.overflow_page_num)
        return self.overflow_page.recs[overflow_index].overflow, self.overflow_page.recs[overflow_index]

    def get_overflow_from_rec(self, rec):
        last_rec = None
        for data_rec in self.adding_page.recs:
            if data_rec.key > rec.key:
                if last_rec == None:
                    pass
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

        returning = None
        index_rec = self.get_next_index_rec()
        while index_rec != None:
            
            if index_rec.key > rec.key:
                returning = last_page, True
                break
            last_page = index_rec.page

            index_rec = self.get_next_index_rec()
        
        self.get_index_page(self.index_page_num)

        if returning:
            return returning

        if last_page == None:
            return 0, False

        return last_page, False
    
    def get_next_index_rec(self):
        if self.temp_index_num == 0:
            self.get_index_page(self.temp_index_page_num)
        if self.temp_index_num == 0:
            pass
        if self.index_page.len() > self.temp_index_num:
            rec = self.index_page.recs[self.temp_index_num]
        else:
            return None
        self.temp_index_num += 1
        if self.temp_index_num == b:
            self.temp_index_num = 0
            self.temp_index_page_num += 1
        return rec
        
    def get_index_page(self, page):
        i = self.for_seek_index(page)
        self.index_file.seek(i)
        data = []
        for i in range(b):
            data.append(self.index_file.readline())
        self.index_page.data_to_page(data)
    
    def get_page(self, page):
        i = self.for_seek(page)
        self.data_file.seek(i)
        data = []
        for i in range(b):
            data.append(self.data_file.readline())
        self.adding_page.data_to_page(data)
    
    def get_page_from_file(self, page_num, file, page):
        i = self.for_seek(page_num)
        file.seek(i)
        data = []
        for i in range(b):
            line = file.readline()
            if not line: break
            data.append(line)
        while len(data) < b:
            data.append('')
        page.data_to_page(data)
    
    def get_old_overflow_rec(self, overflow_ptr, file_handle):
        page = overflow_ptr // b
        idx = overflow_ptr % b
        
        seek_pos = self.for_seek(page)
        file_handle.seek(seek_pos)
        
        lines = []
        for _ in range(b):
            lines.append(file_handle.readline())
        
        temp_page = Page()
        temp_page.data_to_page(lines)
        if idx < len(temp_page.recs):
            return temp_page.recs[idx]
        return None

    def get_overflow_page(self, page):
        i = self.for_seek(page)
        self.overflow_file.seek(i)
        data = []
        for i in range(b):
            data.append(self.overflow_file.readline())
        self.overflow_page.data_to_page(data)
    
    def save_overflow_page(self, page):
        data = self.overflow_page.page_to_data()
        i = self.for_seek(page)
        self.overflow_file.seek(i)
        for line in data:
            self.overflow_file.write(line)
    
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
    
    def push(self):
        self.push_data()
        self.push_index()
        self.push_overflow()

    def push_data(self):
        self.save_page(self.adding_page_num)
    
    def push_index(self):
        self.save_index_page(self.index_page_num)
    
    def push_overflow(self):
        self.save_overflow_page(self.overflow_page_num)

    def reorganize(self):
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
            
            if temp_adding_page.len() == 0:
                break
                
            for rec in temp_adding_page.recs:
                next_overflow_ptr = rec.overflow 
                self.add(rec, limit=b-2, check_exists=False) 
                
                curr_ptr = next_overflow_ptr
                while curr_ptr is not None:
                    overflow_rec = self.get_old_overflow_rec(curr_ptr, old_overflow_handle)
                    if overflow_rec:
                        next_overflow_ptr = overflow_rec.overflow 
                        self.add(overflow_rec, limit=b-2, check_exists=False) 
                        curr_ptr = next_overflow_ptr
                    else:
                        break 
            
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
    
    def experiment(self, n_recs, plus = 0):
        arr = [i for i in range(1+plus, n_recs+1+plus)]
        random.shuffle(arr)
        for i in arr:
            self.add(i)

# ... (All previous class definitions: Record, IndexRecord, Page, IndexPage, Manager) ...

# === MAIN PROGRAM LOOP ===

if __name__ == "__main__":
    m = Manager()
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
        print("6. Show Database Structure")
        print("0. Exit")
        print("="*30)

        choice = input("Choose an option: ").strip()

        if choice == '1':
            try:
                key = int(input("Enter key (int): "))
                m.add(key)
                print(f"Record with key {key} added/processed.")
                m.push()
            except ValueError:
                print("Invalid input. Key must be an integer.")

        elif choice == '2':
            try:
                key = int(input("Enter key to search: "))
                result = m.search(key)
                if result:
                    print(f"\n[FOUND]: {result}")
                else:
                    print(f"\n[NOT FOUND]: Key {key} does not exist.")
            except ValueError:
                print("Invalid input.")

        elif choice == '3':
            try:
                key = int(input("Enter key to update: "))
                vec_str = input("Enter 4 vector numbers separated by space: ")
                vec = [float(x) for x in vec_str.split()]
                if len(vec) != 4:
                    print("Error: Vector must have exactly 4 numbers.")
                    continue
                
                success = m.update(key, vec)
                if success:
                    print("Update successful.")
                else:
                    print("Update failed (Key not found).")
                    m.push()
            except ValueError:
                print("Invalid input. Ensure key is int and vector contains floats.")

        elif choice == '4':
            try:
                key = int(input("Enter key to delete: "))
                success = m.delete(key)
                if success:
                    print("Delete successful.")
                else:
                    print("Delete failed (Key not found).")
                    m.push()
            except ValueError:
                print("Invalid input.")

        elif choice == '5':
            print("Reorganizing...")
            start_time = time.time()
            m.reorganize()
            print(f"Reorganization complete in {time.time() - start_time:.4f}s.")

        elif choice == '6':
            m.print_structure()

        elif choice == '0':
            print("Saving and Exiting...")
            m.push() # Ensure final state is saved
            break

        else:
            print("Invalid option. Please try again.")