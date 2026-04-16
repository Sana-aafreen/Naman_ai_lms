# API Reference: Course Progress Tracking

## Endpoints Overview

### Course Generation & Publishing
- `POST /api/course-generator` — Generate course with PDF & HTML
- `POST /api/generated-courses/publish` — Publish to LMS
- `GET /api/courses` — List published courses by department

### Progress Tracking
- `POST /api/update-progress` — Record module/quiz completion
- `GET /api/progress-report` — Get employee progress
- `GET /api/progress-overview` — Manager/Admin team progress

### Course Assignments
- `GET /api/course-assignments/{course_id}` — Get course details
- `POST /api/course-assignments/{course_id}/submit` — Submit quiz

---

## POST /api/update-progress

Records a module or quiz completion to both GrowthTracker (JSON analytics) and SQLite (LMS database).

### Authentication
```
Authorization: Bearer <JWT_TOKEN>
```

### Request Body
```json
{
  "module_id": "string",           // REQUIRED: unique module identifier
  "score": "number",               // REQUIRED: 0-100 percentage
  "module_title": "string",        // OPTIONAL: human-readable module name
  "course_title": "string",        // OPTIONAL: parent course name
  "source": "string"               // OPTIONAL: "html" | "html_booklet" (default)
}
```

### Request Examples

#### Module Booklet Completion
```bash
curl -X POST http://localhost:8000/api/update-progress \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "module_id": "mod_002",
    "module_title": "Sales Foundations",
    "course_title": "Sales Department Course",
    "score": 100,
    "source": "html_booklet"
  }'
```

#### Quiz Submission
```bash
curl -X POST http://localhost:8000/api/update-progress \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "module_id": "mod_001_quiz",
    "module_title": "Module 1 Final Assessment",
    "course_title": "Sales Department Course",
    "score": 87,
    "source": "html"
  }'
```

### Response (200 OK)
```json
{
  "employee_id": "emp_abc123",
  "employee_name": "Ananya Sharma",
  "department": "Sales",
  "role": "Employee",
  "level": "Intermediate",
  "joined_at": "2025-11-01T12:30:45Z",
  "updated_at": "2026-04-08T14:22:33Z",
  "stats": {
    "total_attempts": 5,
    "modules_passed": 4,
    "average_score": 86,
    "highest_score": 100,
    "current_streak": 2,
    "longest_streak": 5
  },
  "badges": [
    "🌱 First Step",
    "📚 Knowledge Builder",
    "⭐ High Achiever"
  ],
  "recent_completions": [
    {
      "module_id": "mod_001",
      "module_title": "Sales Foundations",
      "score": 87,
      "passed": true,
      "completed_at": "2026-04-08T14:22:33Z"
    }
  ]
}
```

### Response Status Codes

| Code | Meaning | Possible Causes |
|------|---------|-----------------|
| 200 | Success | Progress recorded to both JSON and SQLite |
| 400 | Bad Request | Missing/invalid module_id or score |
| 401 | Unauthorized | Missing or invalid Bearer token |
| 500 | Server Error | Database connection or serialization error |

### Error Response Examples

#### Missing Required Field
```json
{
  "detail": "module_id is required"
}
```

#### Invalid Score Range
```json
{
  "detail": "score must be between 0 and 100"
}
```

#### Unauthorized
```json
{
  "detail": "Unauthorized"
}
```

---

## GET /api/progress-report

Retrieves a single employee's progress across all completed courses.

### Authentication
```
Authorization: Bearer <JWT_TOKEN>
```

### Request
```bash
curl http://localhost:8000/api/progress-report \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Response (200 OK)
```json
{
  "overallScore": 85.5,
  "coursesDone": 3,
  "learningHours": 4.5,
  "departmentRank": "#3",
  "completedCourseIds": [1, 2, 3],
  "skills": [
    {
      "name": "Course Knowledge",
      "score": 85,
      "color": "bg-saffron"
    },
    {
      "name": "Assessment Accuracy",
      "score": 85,
      "color": "bg-gold"
    },
    {
      "name": "Learning Consistency",
      "score": 60,
      "color": "bg-nd-blue"
    }
  ],
  "badges": [
    {
      "icon": "📘",
      "title": "Course Starter",
      "desc": "Completed your first published course"
    },
    {
      "icon": "🎯",
      "title": "Quiz Ace",
      "desc": "Maintained an 80%+ average score"
    }
  ],
  "completedCourses": [
    {
      "course_id": 1,
      "title": "Sales Fundamentals",
      "department": "Sales",
      "score": 92,
      "completed_at": "2026-04-01T10:15:00Z",
      "status": "Completed",
      "correct_answers": 23,
      "total_questions": 25
    },
    {
      "course_id": 2,
      "title": "Customer Service Excellence",
      "department": "Sales",
      "score": 78,
      "completed_at": "2026-04-03T14:30:00Z",
      "status": "Completed",
      "correct_answers": 19,
      "total_questions": 25
    }
  ],
  "growthStats": {
    "total_completions": 3,
    "average_score": 85.5,
    "pass_rate": 100,
    "department_avg": 82,
    "platform_avg": 80
  },
  "growthBadges": ["⭐ High Achiever"],
  "level": "Intermediate",
  "recentCompletions": [
    {
      "module_id": "mod_003",
      "module_title": "Final Assessment",
      "score": 78,
      "passed": true,
      "completed_at": "2026-04-06T16:45:00Z"
    }
  ],
  "currentStreak": 2
}
```

---

## GET /api/progress-overview

Retrieves team/organization progress for managers and administrators.

### Authentication
```
Authorization: Bearer <JWT_TOKEN>
Role: "Manager" or "Admin"
```

### Request
```bash
curl http://localhost:8000/api/progress-overview \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Response (200 OK) — Manager View
```json
{
  "title": "Sales Employee Progress",
  "subtitle": "Employee course completion and quiz scores in your department",
  "rows": [
    {
      "employeeId": "emp_abc",
      "employeeName": "Ananya Sharma",
      "department": "Sales",
      "role": "Employee",
      "coursesCompleted": 3,
      "averageScore": 85.5,
      "latestScore": 92,
      "latestCompletedAt": "2026-04-08T14:22:33Z",
      "streak": 2,
      "growthBadges": ["⭐ High Achiever", "🎓 Course Graduate"],
      "level": "Intermediate",
      "completedCourses": [
        {
          "title": "Sales Fundamentals",
          "department": "Sales",
          "score": 92,
          "completedAt": "2026-04-08T14:22:33Z",
          "status": "Completed"
        }
      ]
    },
    {
      "employeeId": "emp_def",
      "employeeName": "Rohit Verma",
      "department": "Sales",
      "role": "Employee",
      "coursesCompleted": 1,
      "averageScore": 78,
      "latestScore": 78,
      "latestCompletedAt": "2026-04-07T09:15:00Z",
      "streak": 0,
      "growthBadges": ["🌱 First Step"],
      "level": "Beginner",
      "completedCourses": [
        {
          "title": "Sales Fundamentals",
          "department": "Sales",
          "score": 78,
          "completedAt": "2026-04-07T09:15:00Z",
          "status": "Completed"
        }
      ]
    }
  ]
}
```

### Response (200 OK) — Admin View
```json
{
  "title": "Organization Progress Overview",
  "subtitle": "Employee and manager course completion with quiz scores",
  "rows": [
    // All employees across all departments
  ]
}
```

---

## POST /api/course-generator

Generates a complete course package with PDF booklets and interactive HTML modules/SPA.

### Authentication
```
Authorization: Bearer <JWT_TOKEN>
Role: "Manager" or "Admin"
```

### Request Body
```json
{
  "department": "string",           // REQUIRED: department name
  "relatedQueries": ["string"]      // OPTIONAL: custom queries for content
}
```

### Request Example
```bash
curl -X POST http://localhost:8000/api/course-generator \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "department": "Sales",
    "relatedQueries": [
      "How do we handle VIP darshan requests?",
      "What is the process for yatra bookings?"
    ]
  }'
```

### Response (200 OK)
```json
{
  "success": true,
  "format": "pdf",
  "department": "Sales",
  "title": "Sales Department Training Course",
  "summary": "Comprehensive training on NamanDarshan sales processes, VIP darshan, and customer service.",
  "audience": "Sales team members",
  "generated_at": "2026-04-08T10:00:00Z",
  "pdf_path": "/path/to/sales-index-20260408100000.pdf",
  "pdf_filename": "sales-index-20260408100000.pdf",
  "index_html_path": "/path/to/sales-spa-sales-course-20260408100000.html",
  "index_html_filename": "sales-spa-sales-course-20260408100000.html",
  "prerequisites": ["Basic familiarity with darshan services"],
  "learning_objectives": [
    "Understand VIP darshan booking process",
    "Learn yatra package offerings",
    "Master customer communication",
    "Know escalation procedures"
  ],
  "module_booklets": [
    {
      "module_index": 1,
      "module_id": "mod_001",
      "module_title": "Sales Foundations",
      "pdf_path": "/path/to/sales-mod-01-sales-foundations-*.pdf",
      "pdf_filename": "sales-mod-01-sales-foundations-*.pdf",
      "pdf_url": "/api/generated-courses/file/sales-mod-01-sales-foundations-*.pdf",
      "html_path": "/path/to/sales-mod-01-sales-foundations-*.html",
      "html_filename": "sales-mod-01-sales-foundations-*.html",
      "html_url": "/api/generated-courses/file/sales-mod-01-sales-foundations-*.html",
      "duration": "45 minutes",
      "introduction": "Welcome to Sales Foundations...",
      "why_it_matters": "Understanding fundamentals...",
      "goals": ["Understanding core concepts", "Learning best practices"],
      "lesson_explanations": [...],
      "practice_activities": [...],
      "sop_checkpoints": [...],
      "module_recap": "In this module, we covered..."
    }
  ],
  "module_mcqs": [
    {
      "module_index": 1,
      "module_title": "Sales Foundations",
      "generated_by": "groq_key2",
      "questions": [
        {
          "id": "q_1_1",
          "question": "What is the first step in handling a VIP darshan request?",
          "options": [
            "Immediate booking",
            "Verify customer details and availability",
            "Quote pricing",
            "Assign pandit"
          ],
          "correctOptionIndex": 1,
          "explanation": "Customer verification is essential for accurate service..."
        }
      ]
    }
  ],
  "modules": [...],
  "quiz_questions": [...],
  "source_notes": [...]
}
```

---

## POST /api/generated-courses/publish

Publishes a generated course to the LMS database, making it available to employees.

### Authentication
```
Authorization: Bearer <JWT_TOKEN>
Role: "Manager" or "Admin"
```

### Request Body
```json
{
  "department": "string",
  "title": "string",
  "summary": "string",
  "audience": "string",
  "pdf_path": "string",              // REQUIRED
  "pdf_filename": "string",          // OPTIONAL
  "index_html_path": "string",       // OPTIONAL
  "index_html_filename": "string",   // OPTIONAL
  "generated_at": "string",
  "source_notes": ["string"],
  "modules": [{}],
  "modules_html": [{}],
  "quiz_questions": [{}]
}
```

### Response (200 OK)
```json
{
  "id": 5,
  "department": "Sales",
  "title": "Sales Department Training Course",
  "summary": "...",
  "audience": "Sales team members",
  "generated_at": "2026-04-08T10:00:00Z",
  "published_at": "2026-04-08T14:45:00Z",
  "pdf_path": "/path/to/sales-index-20260408100000.pdf",
  "pdf_filename": "sales-index-20260408100000.pdf",
  "pdf_url": "/api/generated-courses/file/sales-index-20260408100000.pdf",
  "index_html_path": "/path/to/sales-spa-*.html",
  "index_html_filename": "sales-spa-*.html",
  "index_html_url": "/api/generated-courses/file/sales-spa-*.html",
  "source_notes": [...],
  "modules": [...],
  "modules_html": [...],
  "quiz_questions": [...],
  "created_by": "admin_user"
}
```

---

## GET /api/courses

Lists all published courses filtered by department.

### Query Parameters
- `department` (required): Department name

### Request
```bash
curl "http://localhost:8000/api/courses?department=Sales" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Response (200 OK)
```json
[
  {
    "id": "generated-5",
    "title": "Sales Department Training Course",
    "dept": "Sales",
    "dur": "1.5 hrs",
    "level": "Generated",
    "progress": 0,
    "status": "Assigned",
    "icon": "📄",
    "bg": "linear-gradient(135deg, hsl(22 85% 42%), hsl(34 83% 52%))",
    "source": "generated",
    "publishedCourseId": 5,
    "pdf_url": "/api/generated-courses/file/sales-index-*.pdf",
    "index_html_url": "/api/generated-courses/file/sales-spa-*.html",
    "modules_html": [],
    "summary": "Comprehensive training on NamanDarshan sales processes...",
    "hasQuiz": true
  }
]
```

---

## Database Schema Reference

### employee_course_progress (SQLite)
```sql
CREATE TABLE employee_course_progress (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  course_id INTEGER NOT NULL,
  employee_id TEXT NOT NULL,
  employee_name TEXT,
  department TEXT,
  score REAL NOT NULL,
  total_questions INTEGER NOT NULL,
  correct_answers INTEGER NOT NULL,
  answers_json TEXT DEFAULT '[]',
  completed_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'Completed',
  UNIQUE(course_id, employee_id)
);
```

### Growth Data Structure (JSON)
```json
{
  "employees": {
    "emp_abc": {
      "employee_id": "emp_abc",
      "employee_name": "Ananya Sharma",
      "department": "Sales",
      "role": "Employee",
      "joined_at": "2025-11-01T12:30:45Z",
      "completions": [
        {
          "completion_id": "emp_abc-mod_001-1-20260408142233",
          "module_id": "mod_001",
          "module_title": "Sales Foundations",
          "course_title": "Sales Department Course",
          "department": "Sales",
          "score": 87,
          "passed": true,
          "attempt": 1,
          "completed_at": "2026-04-08T14:22:33Z",
          "source": "html"
        }
      ],
      "streaks": {
        "current": 2,
        "longest": 5,
        "last_date": "2026-04-08"
      },
      "badges": ["🌱 First Step", "📚 Knowledge Builder"],
      "updated_at": "2026-04-08T14:22:33Z"
    }
  },
  "meta": {
    "last_updated": "2026-04-08T14:22:33Z",
    "total_completions": 42
  }
}
```

---

## Implementation Notes

### Token Management
HTML modules retrieve token from:
1. `localStorage.getItem('token')`
2. `sessionStorage.getItem('token')`

Embed in Authorization header:
```javascript
const token = localStorage.getItem('token');
fetch('/api/update-progress', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### Score Validation
- **Input**: Percentage 0-100
- **Storage (JSON)**: Stored as integer percentage
- **Storage (SQLite)**: Stored as REAL (float) for averaging
- **Display**: Shown as percentage with % symbol

### Dual-Write Guarantee
- JSON write always succeeds or throws
- SQLite write is best-effort (silent fail won't block response)
- Both databases should stay in sync within 1 second

### Error Handling
```javascript
// In HTML module
fetch('/api/update-progress', {...})
  .then(res => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  })
  .catch(err => {
    console.error('Progress update failed:', err);
    // Show user-friendly error message
  });
```
