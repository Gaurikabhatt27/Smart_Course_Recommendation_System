# MongoDB Aggregation Pipelines Documentation
## Course: CSE494 – Intelligent NoSQL Databases
**Project:** Smart Course Recommendation System Using MongoDB  

---

## 1. Overview of the Aggregation Framework

The MongoDB Aggregation Framework processes documents through multi-stage data transformation pipelines. Rather than executing multiple queries and combining data in Python, aggregation pipelines perform server-side grouping, joining, filtering, reshaping, and statistical computing within MongoDB's high-performance C++ execution engine.

---

## 2. Aggregation Pipelines Implemented

### Analytics A: Most Popular Courses
**Objective:** Calculate the top courses ranked by student enrollment volume and enrich them with course metadata.

**Pipeline Stages:**
1. `$group`: Groups by `$course_id` and counts documents using accumulator `{"$sum": 1}`.
2. `$sort`: Orders groups descending by `enrollment_count: -1`.
3. `$lookup`: Left outer join with the `courses` collection matching `_id` to retrieve course title, category, and catalog rating.
4. `$unwind`: Deconstructs the joined single-element array `$course`.
5. `$project`: Reshapes output fields and formats `_id` into a string.

**PyMongo Aggregation Definition:**
```python
POPULAR_COURSES_PIPELINE = [
    {"$group": {"_id": "$course_id", "enrollment_count": {"$sum": 1}}},
    {"$sort": {"enrollment_count": -1}},
    {
        "$lookup": {
            "from": "courses",
            "localField": "_id",
            "foreignField": "_id",
            "as": "course"
        }
    },
    {"$unwind": "$course"},
    {
        "$project": {
            "_id": 0,
            "course_id": {"$toString": "$_id"},
            "title": "$course.title",
            "category": "$course.category",
            "rating": "$course.rating",
            "enrollment_count": 1
        }
    }
]
```

**Sample Output Document:**
```json
{
  "course_id": "664b3a1a9e8f4d1e2c8a1201",
  "title": "Mastering Data Science with Python & Pandas",
  "category": "Data Science",
  "rating": 4.8,
  "enrollment_count": 4
}
```

---

### Analytics B: Average Rating per Course
**Objective:** Compute real-time average review scores and total review volume from the `reviews` collection.

**Pipeline Stages:**
1. `$group`: Groups by `$course_id`, calculates `$avg: "$rating"`, and counts total reviews with `$sum: 1`.
2. `$lookup`: Joins course document to retrieve the course title.
3. `$unwind`: Flattens the joined course array.
4. `$sort`: Orders courses by `avg_rating: -1`.
5. `$project`: Formats fields and rounds average rating to 2 decimal places using `{"$round": ["$avg_rating", 2]}`.

**PyMongo Pipeline:**
```python
COURSE_RATINGS_PIPELINE = [
    {
        "$group": {
            "_id": "$course_id",
            "avg_rating": {"$avg": "$rating"},
            "review_count": {"$sum": 1}
        }
    },
    {
        "$lookup": {
            "from": "courses",
            "localField": "_id",
            "foreignField": "_id",
            "as": "course"
        }
    },
    {"$unwind": "$course"},
    {"$sort": {"avg_rating": -1}},
    {
        "$project": {
            "_id": 0,
            "course_id": {"$toString": "$_id"},
            "title": "$course.title",
            "category": "$course.category",
            "avg_rating": {"$round": ["$avg_rating", 2]},
            "review_count": 1
        }
    }
]
```

---

### Analytics C: Category-wise Enrollments
**Objective:** Determine enrollment demand across academic disciplines (Data Science, Cloud, Web Dev, etc.).

**Pipeline Stages:**
1. `$lookup`: Joins each enrollment with its course record in `courses`.
2. `$unwind`: Flattens the joined `$course` object.
3. `$group`: Groups by `$course.category` and tallies enrollments with `{"$sum": 1}`.
4. `$sort`: Sorts categories descending by `enrollment_count: -1`.
5. `$project`: Renames `_id` to `category`.

**PyMongo Pipeline:**
```python
CATEGORY_ENROLLMENTS_PIPELINE = [
    {
        "$lookup": {
            "from": "courses",
            "localField": "course_id",
            "foreignField": "_id",
            "as": "course"
        }
    },
    {"$unwind": "$course"},
    {
        "$group": {
            "_id": "$course.category",
            "enrollment_count": {"$sum": 1}
        }
    },
    {"$sort": {"enrollment_count": -1}},
    {
        "$project": {
            "_id": 0,
            "category": "$_id",
            "enrollment_count": 1
        }
    }
]
```

---

### Analytics D: Student Learning Progress per Course
**Objective:** Track syllabus completion and learner retention per course module using conditional aggregation.

**Pipeline Stages:**
1. `$group`: Groups by `$course_id`, calculates `$avg: "$progress"`, and uses `$cond` operators inside `$sum` to compute counts for `"Completed"`, `"In Progress"`, and `"Not Started"`.
2. `$lookup`: Fetches course metadata.
3. `$unwind`: Flattens course array.
4. `$sort`: Orders by total enrolled students.
5. `$project`: Computes percentage completion rate:
   `{"$round": [{"$multiply": [{"$divide": ["$completed_count", "$total_students"]}, 100]}, 1]}`.

**Conditional Sum Accumulator Pattern:**
```json
{
  "completed_count": {
    "$sum": {
      "$cond": [{"$eq": ["$status", "Completed"]}, 1, 0]
    }
  }
}
```

---

### Analytics E: Global Database KPIs
**Objective:** Generate high-level summary KPIs for the executive dashboard:
- `total_students = db.students.count_documents({})`
- `total_courses = db.courses.count_documents({})`
- `total_enrollments = db.enrollments.count_documents({})`
- `total_reviews = db.reviews.count_documents({})`
- `avg_review_rating`: Global average computed via:
  ```python
  db["reviews"].aggregate([{"$group": {"_id": None, "global_avg": {"$avg": "$rating"}}}])
  ```
- `completion_rate`: Computed as `(completed_enrollments / total_enrollments) * 100`.
