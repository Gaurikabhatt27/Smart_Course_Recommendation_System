# Database Design & Architecture Document
## Course: CSE494 – Intelligent NoSQL Databases
**Project:** Smart Course Recommendation System Using MongoDB  
**Primary Database:** MongoDB 8.x  
**Driver:** PyMongo  

---

## 1. Document Model Overview

MongoDB stores semi-structured data as BSON (Binary JSON) documents. In this project, the data model balances read efficiency, write performance, and maintainability across four core collections:
1. `students`
2. `courses`
3. `enrollments`
4. `reviews`

An optional auxiliary collection `recommendation_logs` records recommendation events for auditing without impacting the primary domain entities.

---

## 2. Collections and Schema Definitions

### A. `students` Collection
Stores student personal profiles, academic proficiency level, technical skills, and domain interests.

| Field | BSON Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `_id` | ObjectId | Primary Key (Auto) | Unique 12-byte BSON identifier |
| `name` | string | Required, minLength: 2 | Full legal name of student |
| `email` | string | Required, Unique, Regex | RFC-compliant unique email address |
| `skills` | array of strings | Required | Current technical skill competencies |
| `interests`| array of strings | Required | Domain topics and career interests |
| `level` | string | Enum: `['Beginner', 'Intermediate', 'Advanced']` | Academic skill tier |
| `created_at`| date | Required | Timestamp of profile registration |

**Sample Document:**
```json
{
  "_id": {"$oid": "664b3a1a9e8f4d1e2c8a1101"},
  "name": "Aarav Sharma",
  "email": "aarav.sharma@example.com",
  "skills": ["Python", "SQL", "Pandas"],
  "interests": ["Data Science", "Artificial Intelligence"],
  "level": "Intermediate",
  "created_at": {"$date": "2026-10-18T18:00:00Z"}
}
```

---

### B. `courses` Collection
Stores the academic course catalog across specialized domains.

| Field | BSON Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `_id` | ObjectId | Primary Key (Auto) | Unique BSON identifier |
| `title` | string | Required, minLength: 3 | Official course name |
| `category` | string | Enum: 6 Domains | Category: Data Science, AI, Web Dev, Databases, Cloud, Cybersecurity |
| `skills` | array of strings | Required | Key technical skills covered |
| `level` | string | Enum: `['Beginner', 'Intermediate', 'Advanced']` | Prerequisites difficulty level |
| `duration_hours`| double/number | Required, min: 0.5 | Total lecture & lab hours |
| `rating` | double/number | Required, 0.0 - 5.0 | Baseline catalog quality rating |
| `description` | string | Required | Syllabus overview and outcomes |
| `created_at` | date | Required | Timestamp added to catalog |

**Sample Document:**
```json
{
  "_id": {"$oid": "664b3a1a9e8f4d1e2c8a1201"},
  "title": "Mastering Data Science with Python & Pandas",
  "category": "Data Science",
  "skills": ["Python", "Pandas", "NumPy", "Statistics", "Data Visualization"],
  "level": "Intermediate",
  "duration_hours": 36.0,
  "rating": 4.8,
  "description": "Comprehensive practical data science course covering exploratory data analysis.",
  "created_at": {"$date": "2026-10-18T18:00:00Z"}
}
```

---

### C. `enrollments` Collection
Represents the Many-to-Many association between Students and Courses, capturing learning progression and status.

| Field | BSON Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `_id` | ObjectId | Primary Key (Auto) | Unique enrollment record ID |
| `student_id` | ObjectId | Required, References `students._id` | Foreign reference to student |
| `course_id` | ObjectId | Required, References `courses._id` | Foreign reference to course |
| `progress` | double/number | Required, 0.0 - 100.0 | Syllabus completion percentage |
| `status` | string | Enum: `['Not Started', 'In Progress', 'Completed']` | Current academic status |
| `enrolled_at` | date | Required | Date when enrollment began |

**Compound Unique Index:** `(student_id, course_id)` ensures a student cannot enroll multiple times in the same course simultaneously.

---

### D. `reviews` Collection
Stores student ratings and feedback commentary for completed or ongoing courses.

| Field | BSON Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `_id` | ObjectId | Primary Key (Auto) | Unique review identifier |
| `student_id` | ObjectId | Required, References `students._id` | Reviewer identity reference |
| `course_id` | ObjectId | Required, References `courses._id` | Reviewed course reference |
| `rating` | integer | Required, 1 to 5 | Star score (1-5) |
| `comment` | string | Required, minLength: 3 | Written feedback commentary |
| `created_at` | date | Required | Review submission timestamp |

---

## 3. Embedding vs. Referencing Design Decisions

### Where Embedding is Used:
- **`students.skills` & `students.interests`:** Embedded as arrays of strings inside the student document.
- **`courses.skills`:** Embedded as an array of strings inside the course document.

**Justification:**
1. **High Cohesion & Locality:** A student's skills and interests are intrinsic attributes of their identity. They are always accessed when retrieving the student's profile or evaluating course recommendations.
2. **Atomic Reads & Zero Join Overhead:** Storing skills directly in the document avoids costly relational joins or `$lookup` stages for profile retrieval.
3. **Bounded Size:** A student's skills list typically contains 5–20 strings, well below MongoDB's 16MB document size limit.

### Where Referencing is Used:
- **`enrollments`:** References `student_id` and `course_id`.
- **`reviews`:** References `student_id` and `course_id`.

**Justification:**
1. **Unbounded Growth Prevention:** If enrollments were embedded inside a course document (e.g., `course.enrolled_students = [...]`), popular courses with tens of thousands of students would experience document growth, memory fragmentation, and eventual violation of the 16MB BSON document limit.
2. **Independent Lifecycle:** A student's enrollment status and progress changes frequently. Updating an enrollment document in an independent collection avoids locking or rewriting large student or course parent documents.
3. **Bi-directional Querying:** By referencing, we can easily answer both "Which courses is Student X enrolled in?" and "Which students are enrolled in Course Y?" without duplicating documents.

---

## 4. Referential Integrity Strategy

MongoDB does not automatically enforce foreign key constraints (unlike traditional RDBMS with `ON DELETE CASCADE`). Therefore, referential integrity is guaranteed through a hybrid pattern:

1. **Application-Level Pre-flight Checks:**
   In `operations.py`, before inserting an enrollment or review:
   ```python
   if not db["students"].find_one({"_id": s_oid}):
       return False, "Referential Integrity Error: Student does not exist."
   if not db["courses"].find_one({"_id": c_oid}):
       return False, "Referential Integrity Error: Course does not exist."
   ```
2. **Safe Deletion Cascades:**
   When deleting a student or course, the system can cascade deletion to avoid orphan records in `enrollments` and `reviews`:
   ```python
   db["enrollments"].delete_many({"student_id": s_oid})
   db["reviews"].delete_many({"student_id": s_oid})
   db["students"].delete_one({"_id": s_oid})
   ```

---

## 5. Indexing Architecture

| Collection | Index Name | Key(s) | Type | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `students` | `idx_students_email_unique` | `{"email": 1}` | Unique B-Tree | Prevents duplicate registrations & O(log N) lookup |
| `students` | `idx_students_level` | `{"level": 1}` | Single Field | Accelerates filtering by proficiency tier |
| `courses` | `idx_courses_category` | `{"category": 1}` | Single Field | Optimizes category browsing |
| `courses` | `idx_courses_category_level`| `{"category": 1, "level": 1}` | Compound | Supports combined category + difficulty filters |
| `courses` | `idx_courses_text_title_desc`| `{"title": "text", "description": "text"}` | Text Index | Enables natural language keyword search |
| `courses` | `idx_courses_rating` | `{"rating": -1}` | Single Field (Desc) | Speeds up highest-rated catalog queries |
| `enrollments` | `idx_enrollments_student_course_unique` | `{"student_id": 1, "course_id": 1}` | Unique Compound | Prevents duplicate student enrollments |
| `enrollments` | `idx_enrollments_student_id` | `{"student_id": 1}` | Single Field | Optimizes student dashboard lookups |
| `enrollments` | `idx_enrollments_course_id` | `{"course_id": 1}` | Single Field | Optimizes course popularity aggregations |
| `reviews` | `idx_reviews_course_id` | `{"course_id": 1}` | Single Field | Supports course rating aggregations |
