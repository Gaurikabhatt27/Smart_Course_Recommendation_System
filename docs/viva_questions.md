# Comprehensive Viva Questions and Answers
## Course: CSE494 – Intelligent NoSQL Databases
**Project:** Smart Course Recommendation System Using MongoDB  

---

### Q1: What is a NoSQL database, and how does MongoDB differ from a traditional Relational Database Management System (RDBMS)?
**Answer:** A NoSQL (Not Only SQL) database is a non-relational database designed to handle unstructured or semi-structured data, high velocity, and horizontal scalability. MongoDB is a document-oriented NoSQL database that stores data as JSON-like documents (BSON) with dynamic schemas, whereas traditional RDBMS (like MySQL or Oracle) store data in rigid tabular rows and columns enforced by static relational schemas and foreign keys.

---

### Q2: What is BSON, and why does MongoDB use BSON instead of plain text JSON?
**Answer:** BSON stands for Binary JSON. While JSON only natively supports strings, numbers, booleans, arrays, and objects, BSON extends JSON with additional rich data types critical for databases—including `ObjectId` (12-byte unique identifier), `Date` (64-bit UTC integer timestamp), `Decimal128` (high-precision floating-point), and binary data. BSON is also designed to be faster to scan and serialize/deserialize in binary format.

---

### Q3: Explain the internal structure and generation of a MongoDB `ObjectId`.
**Answer:** An `ObjectId` is a 12-byte BSON value consisting of:
1. **4 bytes:** A 4-byte Unix epoch timestamp in seconds (providing natural chronological sorting).
2. **5 bytes:** A random 5-byte value unique to the machine process.
3. **3 bytes:** An incrementing counter starting with a random value.
This design guarantees global uniqueness without needing a centralized sequence generator.

---

### Q4: When should you choose Document Embedding versus Referencing (Normalized) in MongoDB schema design?
**Answer:**
- **Embedding:** Choose embedding when data represents a "1-to-few" relationship, data has high cohesion and is almost always queried together (e.g., student skills and interests inside the student document), and the array is bounded in size.
- **Referencing:** Choose referencing when data represents a "Many-to-Many" relationship (e.g., student enrollments in courses) or "1-to-squillions", when documents would grow unbounded and risk exceeding the 16MB document limit, or when entities have independent update lifecycles.

---

### Q5: What is the maximum BSON document size in MongoDB, and why does this limit exist?
**Answer:** The maximum document size in MongoDB is **16 megabytes (MB)**. This limit ensures that a single document cannot consume excessive amounts of RAM or monopolize network bandwidth during retrieval. For storing large files exceeding 16MB (like videos or PDFs), MongoDB provides GridFS.

---

### Q6: How does MongoDB enforce schema validation, and how is it implemented in this project?
**Answer:** MongoDB enforces schema validation server-side using `$jsonSchema` validators configured via `create_collection` or the `collMod` admin command. In this project:
- `students` requires `name`, `email` (matching regex pattern), `skills`, `interests`, and `level` (restricted to enum `['Beginner', 'Intermediate', 'Advanced']`).
- `courses` requires positive `duration_hours` (minimum 0.5) and bounded `rating` (0.0 to 5.0).
- `enrollments` restricts `progress` (0 to 100) and `status` to `['Not Started', 'In Progress', 'Completed']`.
When an invalid insert or update is attempted, MongoDB rejects the write and throws a `WriteError (DocumentValidationFailure, error code 121)`.

---

### Q7: Does MongoDB automatically enforce foreign key constraints like SQL databases? How does this application handle referential integrity?
**Answer:** No, MongoDB does not natively enforce relational foreign key constraints or cascading deletes. In this application, referential integrity is enforced at the **application level** in `operations.py`:
Before creating an enrollment or review, the code queries `students` and `courses` using `find_one({"_id": oid})`. If either document is missing, the operation is blocked with a clear `Referential Integrity Error`.

---

### Q8: What PyMongo methods were used to implement CRUD operations in this project?
**Answer:**
- **Create:** `insert_one()` for single records, `insert_many()` for bulk operations.
- **Read:** `find()` returning an iterable cursor, `find_one()` returning a single document or `None`, and `count_documents()`.
- **Update:** `update_one()` with atomic update operators such as `$set` and `$setOnInsert` (supporting idempotent upserts).
- **Delete:** `delete_one()` and `delete_many()` with cascade options.

---

### Q9: What is an index in MongoDB, and what data structure does MongoDB use to build indexes?
**Answer:** An index is an auxiliary data structure that holds a small, sorted portion of the collection's data set. MongoDB builds indexes using a **B-Tree** (Balanced Tree) structure in the WiredTiger storage engine. This allows MongoDB to search and locate matching documents in $O(\log N)$ time rather than scanning every document in $O(N)$ time.

---

### Q10: What is the difference between a Single-Field Index and a Compound Index?
**Answer:**
- **Single-Field Index:** Indexes a single field (e.g., `db.courses.create_index([("category", 1)])`).
- **Compound Index:** Indexes multiple fields together in a specific sequence (e.g., `db.courses.create_index([("category", 1), ("level", 1)])`). A compound index can support queries that filter on both fields, or queries that filter on the index prefix (`category`).

---

### Q11: Explain the Index Prefix Rule in MongoDB compound indexes.
**Answer:** Index prefixes are the beginning subsets of indexed fields. For example, for compound index `{"category": 1, "level": 1}`, the prefix is `{"category": 1}`.
MongoDB can use this compound index to satisfy queries on:
1. `category` and `level`
2. `category` alone
However, it **cannot** efficiently use this index for queries filtering *only* on `level`, because the B-Tree is ordered primarily by the first key (`category`).

---

### Q12: How do you prevent duplicate enrollments for the same student in the same course?
**Answer:** By creating a **Unique Compound Index** on `enrollments`:
```python
db.enrollments.create_index(
    [("student_id", 1), ("course_id", 1)],
    unique=True,
    name="idx_enrollments_student_course_unique"
)
```
If an insert is attempted with an existing `(student_id, course_id)` pair, MongoDB raises a `DuplicateKeyError (code 11000)`.

---

### Q13: What is a Text Index in MongoDB, and how is it used here?
**Answer:** A text index allows full-text search capability over string content. In our project:
```python
db.courses.create_index([("title", "text"), ("description", "text")])
```
This enables tokenization and keyword search across both the course title and syllabus description without needing an external search engine.

---

### Q14: What is a Covered Query in MongoDB?
**Answer:** A covered query is a query that can be satisfied entirely using index keys without having to examine any documents in the collection (`totalDocsExamined == 0`). This occurs when all the query filter fields and all the projected return fields are included in the index, and `_id` is explicitly excluded (`_id: 0`).

---

### Q15: What is the purpose of the MongoDB `explain()` command, and what are its verbosity modes?
**Answer:** The `explain()` command provides query planner details and execution statistics for analyzing query efficiency. Its three verbosity modes are:
1. `queryPlanner`: Shows the winning plan chosen by MongoDB's query optimizer without executing the query.
2. `executionStats`: Executes the query and returns operational metrics such as execution time, documents examined, and keys scanned.
3. `allPlansExecution`: Evaluates and returns stats for all candidate plans evaluated during plan selection.

---

### Q16: In the `explain()` executionStats output, what is the critical difference between `COLLSCAN` and `IXSCAN`?
**Answer:**
- **`COLLSCAN` (Collection Scan):** MongoDB inspects every single document in the collection sequentially. For a collection of $N$ documents, `totalDocsExamined == N`.
- **`IXSCAN` (Index Scan):** MongoDB traverses the B-Tree index to locate matching keys directly. Only matching documents are fetched (`FETCH` stage), resulting in `totalKeysExamined` and `totalDocsExamined` proportional only to the result set size.

---

### Q17: What are `totalDocsExamined`, `totalKeysExamined`, and `nReturned` in `explain()` output?
**Answer:**
- `nReturned`: The exact number of documents that matched the query criteria and were returned to the client.
- `totalDocsExamined`: The number of collection documents MongoDB opened and inspected from disk/cache.
- `totalKeysExamined`: The number of index entries scanned in the B-Tree.
In an optimal indexed query, `totalKeysExamined` and `totalDocsExamined` are very close or equal to `nReturned`.

---

### Q18: What is index selectivity, and why does it matter?
**Answer:** Index selectivity refers to the proportion of documents an index can filter out. A field with high selectivity (like unique emails) returns very few documents per key, making the index extremely fast. A field with low selectivity (like a boolean flag) returns large portions of the collection, where an index scan plus fetch might offer little to no advantage over a direct collection scan.

---

### Q19: What are the trade-offs and performance costs of creating indexes?
**Answer:**
1. **Write Overhead:** Every write operation (`insert`, `update`, `delete`) must update every affected B-Tree index, which slows down write throughput.
2. **Memory (RAM) Overhead:** Indexes must reside in the WiredTiger RAM cache for optimal speed. Having too many unused indexes causes cache eviction of frequently used documents and keys.
3. **Storage Overhead:** Indexes consume disk space.

---

### Q20: What is the MongoDB Aggregation Pipeline?
**Answer:** The Aggregation Pipeline is a multi-stage framework for data transformation and analytics modeled on the concept of data processing pipelines. Documents enter the pipeline, pass through stages sequentially (such as filtering, grouping, projecting, unwinding, and sorting), and output transformed summary documents.

---

### Q21: Explain the `$group` stage and its common accumulator operators.
**Answer:** The `$group` stage groups input documents by a specified identifier expression (`_id`) and applies accumulator expressions to compute summary metrics:
- `{"$sum": 1}`: Counts documents in each group.
- `{"$avg": "$rating"}`: Calculates the numerical average of a field.
- `{"$min" / "$max"}`: Finds minimum or maximum values.
- `{"$push"}`: Collects field values into an array.

---

### Q22: How does the `$lookup` stage work in MongoDB?
**Answer:** `$lookup` performs a left outer join to an unsharded collection in the same database. It matches a local field in the pipeline document to a foreign field in the target collection and outputs the matched documents as an array field:
```json
{
  "$lookup": {
    "from": "courses",
    "localField": "course_id",
    "foreignField": "_id",
    "as": "course"
  }
}
```

---

### Q23: Why is `$unwind` commonly used after `$lookup`?
**Answer:** `$lookup` always outputs matching foreign documents inside an **array**, even if there is only a 1-to-1 match. The `$unwind` stage deconstructs the array field to produce an individual document for each element in the array, allowing downstream stages (like `$project` or `$group`) to access child fields directly (e.g., `$course.title`).

---

### Q24: What is the RAM limit for aggregation pipeline stages, and how is it overcome?
**Answer:** By default, pipeline stages have a memory limit of **100 MB of RAM**. If a stage (like `$sort` or `$group` on large collections) exceeds 100 MB, the query will fail with an error unless `allowDiskUse=True` is passed to the aggregation command, which allows MongoDB to write temporary spill files to disk.

---

### Q25: Why is early filtering with `$match` an important aggregation optimization best practice?
**Answer:** Placing `$match` as early as possible in the pipeline reduces the total volume of documents entering subsequent CPU-intensive stages like `$group` and `$lookup`. Furthermore, an early `$match` stage can leverage collection indexes, whereas stages following a `$group` or `$project` cannot use original collection indexes.

---

### Q26: Explain the rule-based course recommendation formula implemented in this project.
**Answer:**
```
Final Score = (0.50 × Skill Match Score) + (0.30 × Interest Match Score) + (0.20 × Course Rating Score)
```
- **Skill Match Score (0–100):** `(Matching Course Skills / Total Course Skills) * 100`. Measures how well the student's existing skills match course prerequisites.
- **Interest Match Score (0–100):** `(Overlapping Interests / Total Student Interests) * 100`, matching student interests against the course category and topics.
- **Course Rating Score (0–100):** `(Course Rating / 5.0) * 100`.
- All candidate courses already enrolled by the student are excluded before ranking. The top 5 scored courses are returned with an explainable justification.

---

### Q27: Why did we choose a rule-based algorithm over Machine Learning for this recommendation engine?
**Answer:**
1. **Explainability & Transparency:** Academic and educational recommendations require clear, explainable justification (e.g., "Builds upon your skills: Python; Aligns with interest: Data Science").
2. **Cold-Start Resilience:** New students and courses with zero historical interaction data can be recommended immediately based on content metadata.
3. **Course Focus:** The primary course requirement is mastering intelligent NoSQL databases, PyMongo CRUD, validation, and aggregation pipelines, rather than black-box machine learning APIs.

---

### Q28: How is database seeding made idempotent in `setup_db.py`?
**Answer:** Idempotency means running the script once or ten times produces the exact same valid database state without creating duplicate records. This is achieved using **upserts (`update_one(..., upsert=True)`)** with natural keys:
- Students are upserted using their unique `email`.
- Courses are upserted using their unique `title`.
- Enrollments are upserted using their compound key `(student_id, course_id)`.
- Reviews are upserted using `(student_id, course_id)`.

---

### Q29: What is the difference between PyMongo's `find()` and `find_one()`?
**Answer:**
- `find_one()` returns a single matching document as a Python dictionary, or `None` if no document matches.
- `find()` returns a `Cursor` object—an iterable pointer to the query result set on the MongoDB server that fetches documents in batches (typically 101 documents initially) to save network memory.

---

### Q30: How does Streamlit handle state and updates?
**Answer:** Streamlit uses a reactive script execution model: whenever a user interacts with a widget (clicks a button, selects a dropdown, enters text), the entire Python script runs from top to bottom. State that needs to persist across reruns is managed using `st.session_state` or retrieved directly from the MongoDB database.

---

### Q31: What happens if MongoDB becomes temporarily unavailable while the application is running?
**Answer:** The `database.py` module configures `MongoClient` with a 3000ms `serverSelectionTimeoutMS`. If the connection is broken, PyMongo raises `ServerSelectionTimeoutError`. The application intercepts this, masks connection strings to prevent exposing credentials, and renders a clean, informative error banner in the UI with troubleshooting steps rather than crashing with an unhandled stack trace.

---

### Q32: What are the main benefits of MongoDB's flexible document model over traditional relational schemas?
**Answer:**
1. **Dynamic Schema Evolution:** Fields can be added or updated without executing costly `ALTER TABLE` locks across millions of records.
2. **Natural Data Representation:** Objects, nested structures, and arrays in code directly map to BSON documents without requiring Object-Relational Mappers (ORMs).
3. **Horizontal Scalability:** MongoDB supports native sharding and replica sets for distributed scale and high availability.
