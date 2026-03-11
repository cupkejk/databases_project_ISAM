# ISAM Database Manager

A Python implementation of the Indexed Sequential Access Method (ISAM). This project simulates a file-based database system that manages records using primary data pages, a sparse index, and a linked-list overflow area.



## Overview

This project demonstrates how traditional database engines manage physical storage. It handles data in fixed-size blocks (pages) to minimize disk I/O and uses a multi-layered storage approach to balance search speed with insertion flexibility.

### Storage Components
* Primary Area (data.txt): Stores records in sorted pages.
* Index (index.txt): A sparse index containing the first key of each primary page for fast page lookups.
* Overflow Area (overflow.txt): Handles records that cannot fit into their designated primary page, using pointers to maintain logical order.

---

## How It Works

### Record Structure
Each record is precisely 100 bytes, ensuring predictable offsets for "disk" seeking:

Field | Size | Description
--- | --- | ---
Key | 8 bytes | Unique integer identifier
Vector | 80 bytes | Four floating-point numbers
Overflow | 8 bytes | Pointer to the next record in the overflow chain
Deleted | 1 byte | Flag for "soft" deletion (0 = Active, 1 = Deleted)
Spaces | 2 bytes | Spaces inbetween different data
New Line | 1 byte | New line at the end of each record for readability

### Key Algorithms
* Alpha: Controls how full a page is during reorganization. For example, 0.5 leaves 50% free space for future inserts.
* Reorganization: When the overflow area grows beyond the reorg_threshold, the system automatically merges all records back into a fresh primary area and rebuilds the index.
* Disk Simulation: Every operation tracks "Reads" and "Writes" to measure performance efficiency.

---

## Getting Started

### Prerequisites
* Python 3.x
* Matplotlib (only required for running experiments)

### Usage
Run the main script to enter the interactive CLI via the command: python main.py

### CLI Options
1. Add/Search/Update/Delete: Standard CRUD operations.
2. Physical Dump: View the raw contents of the .txt files page-by-page.
3. Logical View: Traverse the database in sorted order (following overflow pointers).
4. Batch Processing: Provide a text file with commands (e.g., A 10, S 10, D 10).
5. Experiments: Generate Matplotlib graphs to see how different alpha values affect disk I/O.

---

## Performance Testing

The system includes a built-in experiment module to visualize the trade-offs of the ISAM structure. By running Option 10, you can compare how different Fill Factors (Alpha) and Reorganization Thresholds impact the number of disk operations.



---

## 🛠 Project Structure
* Record / IndexRecord: Defines the data serialization and deserialization.
* Page / IndexPage: Manages blocks of records and "dirty" states for writing.
* Manager: The core engine handling file I/O, search logic, and reorganization.
