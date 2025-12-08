import os
import random
import math

# --- CONFIGURATION ---
BLOCK_FACTOR = 4       # Records per page (b=4)
RECORD_SIZE = 98       # Fixed byte size per record line (including \n)
INDEX_REC_SIZE = 19    # Fixed byte size per index record

FILE_DATA = 'data.txt'
FILE_INDEX = 'index.txt'
FILE_OVERFLOW = 'overflow.txt'

# --- CLASS DEFINITIONS ---

class Record:
    def __init__(self, key=0):
        self.vec = [0.0] * 4
        self.key = key
        self.overflow = None  # Integer pointer (Global Record Index in Overflow File)

    def random_gen(self, key):
        self.vec = [random.random() * 100 for _ in range(4)]
        self.key = key
        self.overflow = None

    def str_to_rec(self, data):
        """Parses a fixed-width string into a Record object."""
        if not data or len(data) < 10: return
        try:
            # Parse Key (0-9)
            self.key = int(data[0:9].strip())
            
            # Parse Vector (9-89)
            self.vec = []
            start = 9
            for i in range(4):
                num_str = data[start:start+20]
                self.vec.append(float(num_str))
                start += 20
            
            # Parse Overflow Pointer (89-97)
            overflow_str = data[89:97].strip()
            if overflow_str == 'x' or overflow_str == '':
                self.overflow = None
            else:
                self.overflow = int(overflow_str)
        except ValueError:
            pass 

    def __str__(self):
        """Formats record to exactly 98 bytes."""
        # Key: 9 chars
        rec_str = f"{self.key:<9}"
        # Vector: 80 chars
        for i in range(4):
            rec_str += f"{self.vec[i]:19.9f} "
        
        # Pointer: 8 chars
        if self.overflow is None:
            rec_str += f"{'x':<8}"
        else:
            rec_str += f"{self.overflow:<8}"
        
        # Newline: 1 char
        return rec_str + '\n'

class IndexRecord:
    """Helper for Index File records."""
    def __init__(self, key=0, page_id=0):
        self.key = key
        self.page_id = page_id

    def __str__(self):
        # 9 chars Key + 9 chars ID + 1 newline = 19 bytes
        return f"{self.key:<9} {self.page_id:<9}\n"

    def parse(self, line):
        parts = line.split()
        if len(parts) >= 2:
            self.key = int(parts[0])
            self.page_id = int(parts[1])

class Page:
    """Generic Page used for Data and Overflow files."""
    def __init__(self):
        self.recs = [] # List of Record objects

    def data_to_page(self, lines):
        self.recs = []
        for line in lines:
            if len(line.strip()) > 5 and not line.startswith('-'):
                rec = Record(0)
                rec.str_to_rec(line)
                self.recs.append(rec)
    
    def page_to_data(self):
        data = []
        for rec in self.recs:
            data.append(str(rec))
        # Fill empty slots with dashes
        while len(data) < BLOCK_FACTOR:
            data.append('-' * (RECORD_SIZE - 1) + '\n')
        return data

    def is_full(self):
        return len(self.recs) >= BLOCK_FACTOR

    def insert_sorted(self, new_rec):
        """
        Inserts and sorts. 
        Returns the POPPED record (largest) if the page was full.
        """
        self.recs.append(new_rec)
        self.recs.sort(key=lambda x: x.key)
        
        if len(self.recs) > BLOCK_FACTOR:
            return self.recs.pop()
        return None
    
    def append(self, new_rec):
        """Used for Overflow pages (No sorting, just fill)."""
        if len(self.recs) < BLOCK_FACTOR:
            self.recs.append(new_rec)
            return True
        return False

class IndexPage:
    """Specific Page for Index File."""
    def __init__(self):
        self.records = [] 

    def data_to_page(self, lines):
        self.records = []
        for line in lines:
            if len(line.strip()) > 1:
                irec = IndexRecord()
                irec.parse(line)
                self.records.append(irec)

    def page_to_data(self):
        data = []
        for irec in self.records:
            data.append(str(irec))
        # Fill empty slots
        while len(data) < BLOCK_FACTOR:
            data.append(' ' * (INDEX_REC_SIZE - 1) + '\n')
        return data

class Manager:
    def __init__(self):
        self.disk_reads = 0
        self.disk_writes = 0
        self.index = [] 
        
        # Init files if not exist
        for f in [FILE_DATA, FILE_INDEX, FILE_OVERFLOW]:
            open(f, 'w').close()
        
        self.load_index()

    # --- LOW LEVEL DISK IO ---

    def _read_page_generic(self, filename, page_id, page_class, rec_size):
        """Reads a specific page (block) from disk."""
        self.disk_reads += 1
        lines = []
        offset = page_id * BLOCK_FACTOR * rec_size
        
        if os.path.getsize(filename) <= offset:
            return page_class()

        with open(filename, 'r') as f:
            f.seek(offset)
            for _ in range(BLOCK_FACTOR):
                line = f.readline()
                if not line: break
                lines.append(line)
        
        p = page_class()
        p.data_to_page(lines)
        return p

    def _write_page_generic(self, filename, page_id, page_obj, rec_size):
        """Writes a specific page (block) to disk."""
        self.disk_writes += 1
        new_lines = page_obj.page_to_data()
        offset = page_id * BLOCK_FACTOR * rec_size
        
        # If writing past end of file, append mode handles it better conceptually, 
        # but for simulation we assume random access capability r+
        curr_size = os.path.getsize(filename)
        
        if offset >= curr_size:
             with open(filename, 'a') as f:
                 f.writelines(new_lines)
        else:
            with open(filename, 'r+') as f:
                f.seek(offset)
                f.writelines(new_lines)

    # --- FILE SPECIFIC IO WRAPPERS ---

    def get_data_page(self, page_id):
        return self._read_page_generic(FILE_DATA, page_id, Page, RECORD_SIZE)

    def write_data_page(self, page_id, page):
        self._write_page_generic(FILE_DATA, page_id, page, RECORD_SIZE)

    def append_new_data_page(self, page):
        """Calculates new ID and appends page."""
        size = os.path.getsize(FILE_DATA)
        page_bytes = BLOCK_FACTOR * RECORD_SIZE
        new_id = size // page_bytes
        self.write_data_page(new_id, page)
        return new_id

    # --- INDEX MANAGEMENT ---

    def load_index(self):
        """Loads entire index via paging."""
        self.index = []
        size = os.path.getsize(FILE_INDEX)
        if size == 0: return

        pg_bytes = BLOCK_FACTOR * INDEX_REC_SIZE
        num_pages = (size + pg_bytes - 1) // pg_bytes

        for i in range(num_pages):
            pg = self._read_page_generic(FILE_INDEX, i, IndexPage, INDEX_REC_SIZE)
            for r in pg.records:
                self.index.append((r.key, r.page_id))

    def save_index(self):
        """Saves entire index via paging."""
        open(FILE_INDEX, 'w').close() # Wipe
        curr = IndexPage()
        pid = 0
        
        for k, p in self.index:
            curr.records.append(IndexRecord(k, p))
            if len(curr.records) == BLOCK_FACTOR:
                self._write_page_generic(FILE_INDEX, pid, curr, INDEX_REC_SIZE)
                pid += 1
                curr = IndexPage()
        
        if curr.records:
            self._write_page_generic(FILE_INDEX, pid, curr, INDEX_REC_SIZE)

    # --- OVERFLOW MANAGEMENT (SMART BUFFERING) ---

    def write_overflow(self, record):
        """
        Adds record to Overflow file. 
        Algorithm:
        1. Check the LAST page of the file.
        2. If it has space, Append to it and Update in place.
        3. If full, Create NEW page and Append to file.
        Returns: Global Record Index.
        """
        size = os.path.getsize(FILE_OVERFLOW)
        pg_bytes = BLOCK_FACTOR * RECORD_SIZE
        
        # Calculate ID of the last page
        if size == 0:
            last_page_id = 0
            page = Page() # New empty page
        else:
            last_page_id = (size - 1) // pg_bytes
            page = self._read_page_generic(FILE_OVERFLOW, last_page_id, Page, RECORD_SIZE)

        # Try to add to this page
        if page.append(record):
            # Success, it fit in the existing last page (or the new one 0)
            self._write_page_generic(FILE_OVERFLOW, last_page_id, page, RECORD_SIZE)
            # Return Global Index: (PageID * B) + (IndexInPage)
            return (last_page_id * BLOCK_FACTOR) + (len(page.recs) - 1)
        else:
            # Page was full, need a brand new page
            new_page_id = last_page_id + 1
            new_page = Page()
            new_page.append(record)
            self._write_page_generic(FILE_OVERFLOW, new_page_id, new_page, RECORD_SIZE)
            return (new_page_id * BLOCK_FACTOR) + 0

    def read_overflow(self, ptr_index):
        """Reads record given Global Index."""
        pid = ptr_index // BLOCK_FACTOR
        offset = ptr_index % BLOCK_FACTOR
        page = self._read_page_generic(FILE_OVERFLOW, pid, Page, RECORD_SIZE)
        if offset < len(page.recs):
            return page.recs[offset]
        return None

    def update_overflow_line(self, ptr_index, new_rec):
        """Updates record in overflow given Global Index."""
        pid = ptr_index // BLOCK_FACTOR
        offset = ptr_index % BLOCK_FACTOR
        page = self._read_page_generic(FILE_OVERFLOW, pid, Page, RECORD_SIZE)
        if offset < len(page.recs):
            page.recs[offset] = new_rec
            self._write_page_generic(FILE_OVERFLOW, pid, page, RECORD_SIZE)

    # --- CORE OPERATIONS ---

    def find_page_for_key(self, key):
        for max_k, pid in self.index:
            if key <= max_k: return pid
        if self.index: return self.index[-1][1]
        return 0

    def get_global_max(self):
        return self.index[-1][0] if self.index else -1

    def insert(self, key):
        rec = Record(key)
        rec.random_gen(key)
        
        # Optimization: Append if Key > All
        if self.index and key > self.get_global_max():
            last_pid = self.index[-1][1]
            last_page = self.get_data_page(last_pid)
            
            if not last_page.is_full():
                last_page.insert_sorted(rec)
                self.write_data_page(last_pid, last_page)
                self.index[-1] = (key, last_pid)
                self.save_index()
                print(f"Inserted {key} (Append Last Page).")
                return
            else:
                # Create NEW Primary Page
                new_p = Page()
                new_p.insert_sorted(rec)
                new_pid = self.append_new_data_page(new_p)
                self.index.append((key, new_pid))
                self.save_index()
                print(f"Inserted {key} (New Page {new_pid}).")
                return

        # Standard Insert
        pid = self.find_page_for_key(key)
        page = self.get_data_page(pid)
        
        popped = page.insert_sorted(rec)
        
        if popped:
            # Page full: Move largest to Overflow
            ov_ptr = self.write_overflow(popped)
            # Link current last record to this overflow
            page.recs[-1].overflow = ov_ptr
        
        self.write_data_page(pid, page)
        
        # Update Index Memory
        if len(page.recs) > 0:
            cmax = page.recs[-1].key
            if not self.index: self.index.append((cmax, 0))
            elif pid < len(self.index):
                old, pg = self.index[pid]
                self.index[pid] = (max(old, cmax), pg)
            self.save_index()
        
        print(f"Inserted {key}.")

    def get_record(self, key):
        pid = self.find_page_for_key(key)
        page = self.get_data_page(pid)
        
        # Check Primary
        for r in page.recs:
            if r.key == key: return r
        
        # Check Overflow Chain
        if len(page.recs) > 0:
            curr = page.recs[-1].overflow
            while curr is not None:
                r = self.read_overflow(curr)
                if not r: break
                if r.key == key: return r
                curr = r.overflow
        return None

    def delete_record(self, key):
        # Tombstone strategy (Key = -1)
        pid = self.find_page_for_key(key)
        page = self.get_data_page(pid)
        
        for r in page.recs:
            if r.key == key:
                r.key = -1
                self.write_data_page(pid, page)
                print(f"Deleted {key} (Primary).")
                return True

        if len(page.recs) > 0:
            curr = page.recs[-1].overflow
            while curr is not None:
                r = self.read_overflow(curr)
                if not r: break
                if r.key == key:
                    r.key = -1
                    self.update_overflow_line(curr, r)
                    print(f"Deleted {key} (Overflow).")
                    return True
                curr = r.overflow
        
        print("Record not found.")
        return False

    def update_record(self, key, new_vec):
        pid = self.find_page_for_key(key)
        page = self.get_data_page(pid)
        
        for r in page.recs:
            if r.key == key:
                r.vec = new_vec
                self.write_data_page(pid, page)
                print(f"Updated {key}.")
                return True
        
        if len(page.recs) > 0:
            curr = page.recs[-1].overflow
            while curr is not None:
                r = self.read_overflow(curr)
                if not r: break
                if r.key == key:
                    r.vec = new_vec
                    self.update_overflow_line(curr, r)
                    print(f"Updated {key}.")
                    return True
                curr = r.overflow
        return False

    def reorganize(self):
        print("\n--- REORGANIZATION STARTED ---")
        all_recs = []
        
        # 1. Collect Valid Records
        if self.index:
            for _, pid in self.index:
                page = self.get_data_page(pid)
                for r in page.recs:
                    # Logic Fix: We must capture the overflow chain even if 'r' is deleted!
                    
                    # 1. Save 'r' if it is valid
                    if r.key != -1: 
                        all_recs.append(r)
                    
                    # 2. FOLLOW THE CHAIN (Regardless of r.key) 
                    if r.overflow is not None:
                        curr = r.overflow
                        while curr is not None:
                            ovr = self.read_overflow(curr)
                            if ovr:
                                # Save overflow record if valid
                                if ovr.key != -1: 
                                    all_recs.append(ovr)
                                curr = ovr.overflow
                            else: 
                                curr = None
        
        # 2. Sort all collected records
        all_recs.sort(key=lambda x: x.key)
        
        print(f"Collected {len(all_recs)} valid records.")

        # 3. Wipe Files Clean
        open(FILE_DATA, 'w').close()
        open(FILE_INDEX, 'w').close()
        open(FILE_OVERFLOW, 'w').close()
        self.index = []
        self.disk_reads = 0
        self.disk_writes = 0
        
        # 4. Rewrite Packed Pages
        curr_page = Page()
        pid = 0
        
        for r in all_recs:
            r.overflow = None # Reset pointers (they are now contiguous)
            curr_page.recs.append(r)
            
            # If page full, write to disk
            if curr_page.is_full():
                self.write_data_page(pid, curr_page)
                self.index.append((r.key, pid))
                pid += 1
                curr_page = Page()
        
        # Write remaining partial page
        if curr_page.recs:
            self.write_data_page(pid, curr_page)
            self.index.append((curr_page.recs[-1].key, pid))
            
        self.save_index()
        print("--- REORGANIZATION COMPLETE ---")

    def print_structure(self):
        print("\n=== FILE STRUCTURE ===")
        print("INDEX:", self.index)
        
        print("\n--- PRIMARY DATA ---")
        if self.index:
            last = self.index[-1][1]
            for i in range(last + 1):
                p = self.get_data_page(i)
                content = []
                for r in p.recs:
                    s = str(r.key)
                    if r.key == -1: s = "[DEL]"
                    if r.overflow is not None: s += f"->{r.overflow}"
                    content.append(s)
                print(f"Page {i}: {content}")
        
        print("\n--- OVERFLOW (Paged) ---")
        if os.path.exists(FILE_OVERFLOW):
            sz = os.path.getsize(FILE_OVERFLOW)
            pg_bytes = BLOCK_FACTOR * RECORD_SIZE
            if sz > 0:
                n_pages = (sz + pg_bytes - 1) // pg_bytes
                for i in range(n_pages):
                    p = self._read_page_generic(FILE_OVERFLOW, i, Page, RECORD_SIZE)
                    content = []
                    for r in p.recs:
                        s = str(r.key)
                        if r.key == -1: s = "[DEL]"
                        if r.overflow is not None: s += f"->{r.overflow}"
                        content.append(s)
                    print(f"OvPage {i}: {content}")

    def run_experiments(self):
        print("\n=== EXPERIMENTS ===")
        print(f"{'N':<8} | {'Reads':<8} | {'Writes':<8} | {'Total':<8} | {'Avg':<8}")
        
        for n in [50, 100, 200, 500]:
            # Reset
            open(FILE_DATA, 'w').close()
            open(FILE_INDEX, 'w').close()
            open(FILE_OVERFLOW, 'w').close()
            self.index = []
            self.disk_reads = 0
            self.disk_writes = 0
            
            keys = list(range(1, n+1))
            random.shuffle(keys)
            
            for k in keys:
                self.insert(k)
            
            tot = self.disk_reads + self.disk_writes
            print(f"{n:<8} | {self.disk_reads:<8} | {self.disk_writes:<8} | {tot:<8} | {tot/n:.2f}")

if __name__ == "__main__":
    mgr = Manager()
    while True:
        print("\n1. Insert  2. Read  3. Update  4. Delete  5. Reorg  6. Show  7. Exp  8. Quit")
        c = input("> ")
        if c == '1':
            try: mgr.insert(int(input("Key: ")))
            except: pass
        elif c == '2':
            try: 
                r = mgr.get_record(int(input("Key: ")))
                if r and r.key != -1: print(r)
                else: print("Not found.")
            except: pass
        elif c == '3':
            try: mgr.update_record(int(input("Key: ")), [random.random() for _ in range(4)])
            except: pass
        elif c == '4':
            try: mgr.delete_record(int(input("Key: ")))
            except: pass
        elif c == '5': mgr.reorganize()
        elif c == '6': mgr.print_structure()
        elif c == '7': mgr.run_experiments()
        elif c == '8': break