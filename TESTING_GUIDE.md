# Testing Guide: Interactive HTML Courses & Progress Tracking

## Pre-Testing Checklist

- [ ] Backend server running (main.py)
- [ ] Frontend development server running
- [ ] User logged in with valid JWT token
- [ ] Network DevTools accessible for debugging
- [ ] Database tools for viewing SQLite (optional: `sqlite3` CLI or DB Browser)

---

## Test 1: Course Generation Creates HTML

### Steps
1. Open Admin Dashboard → "Course Generator" tab
2. Select a department (e.g., "Sales")
3. Optionally add custom queries
4. Click **"Generate Course"** button
5. Wait for generation to complete

### Expected Results
- ✅ Course appears in the card showing all details
- ✅ **"View HTML Preview"** button appears and is clickable
- ✅ Both PDF and HTML files created in `Backend/generated_courses/`

### Verification (Terminal)
```bash
# Check generated files
ls -lah Backend/generated_courses/
# Should see: sales-index-*.pdf, sales-mod-*.html, sales-spa-*.html
```

---

## Test 2: HTML Module File Serving

### Steps
1. From Admin Dashboard course card, click **"View HTML Preview"**
2. A new browser tab opens with the interactive HTML

### Expected Results
- ✅ Beautiful, responsive HTML page loads
- ✅ NamanDarshan branding visible (saffron colors, fonts)
- ✅ Course title and modules displayed
- ✅ Quiz section shows all questions
- ✅ No 404 errors in network tab

### Network Debugging
```
GET /api/generated-courses/file/sales-spa-*.html
→ Status 200
→ Content-Type: text/html
```

---

## Test 3: Module Completion Progress Tracking

### Steps
1. Open generated module HTML in browser
2. Navigate through lesson content
3. Scroll to bottom → click **"Complete Module"** button
4. Observe console and network activity

### Expected Results
- ✅ Button changes to "Recording..." then disappears
- ✅ Success message appears: "✓ Module completion recorded!"
- ✅ No errors in browser console

### Network Request Inspection
```
POST /api/update-progress
Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  Content-Type: application/json

Body:
{
  "module_id": "mod_1",
  "module_title": "Module Title",
  "course_title": "Sales Course",
  "score": 100,
  "source": "html_booklet"
}

Response (200):
{
  "employee_id": "emp001",
  "stats": {"total_attempts": 1, "modules_passed": 1, ...},
  "badges": [...]
}
```

---

## Test 4: Quiz Submission with Score Tracking

### Steps
1. Open full course HTML SPA from Admin Dashboard
2. Navigate to a module with quiz
3. Answer all quiz questions
4. Click **"Submit Quiz"** button
5. Observe score display

### Expected Results
- ✅ Quiz options highlight when selected
- ✅ Submit button enables only when all questions answered
- ✅ After submission:
  - Correct answers turn green ✓
  - Wrong answers turn red ✗
  - Score percentage displays prominently
  - Explanations appear below each question
- ✅ Progress bar updates globally

### Network Request
```
POST /api/update-progress
Body:
{
  "module_id": "mod_1",
  "score": 85,  // Quiz score percentage
  ...
}

Response includes:
- updated_at: latest timestamp
- stats.total_attempts: incremented
- badges: possibly new badges earned
```

---

## Test 5: Progress Appears on Employee Dashboard

### Steps
1. Employee completes module/quiz in HTML
2. Employee returns to Main Dashboard
3. Navigate to **Dashboard** page
4. Check "Course Status" or Progress section

### Expected Results
- ✅ Completed course shows "Completed" status
- ✅ Progress bar is 100% filled
- ✅ Latest score displayed
- ✅ Takes less than 5 seconds to refresh

### Verification (API Direct)
```bash
# Get employee progress report
curl -s http://localhost:8000/api/progress-report \
  -H "Authorization: Bearer <token>" | jq .

# Expected response:
{
  "completedCourseIds": [1, 2, 3],
  "overallScore": 87.5,
  "coursesDone": 3,
  "completedCourses": [
    {
      "title": "Sales Course",
      "score": 85,
      "status": "Completed",
      "completed_at": "2026-04-08T..."
    }
  ]
}
```

---

## Test 6: Manager/Admin Progress Overview

### Steps
1. Manager/Admin logs in
2. Open Admin Dashboard → **"Progress Reports"** tab
3. Look for employee who completed module

### Expected Results
- ✅ Employee appears in table
- ✅ Correct completion count showing
- ✅ Average score calculated correctly
- ✅ Latest completed course shown
- ✅ Streak/badges displaying

### Database Verification
```bash
# Query SQLite directly (optional)
sqlite3 Backend/agents/growth_tracker.db

# Check employee progress
SELECT * FROM employee_course_progress 
WHERE employee_id = 'emp001';

# Should see row with:
- score: 85
- status: 'Completed'
- completed_at: recent timestamp
```

---

## Test 7: Growth Analytics & Badges

### Steps
1. Complete multiple modules (aim for 3-5)
2. Vary scores: 60%, 90%, 100%, 75%, 88%
3. Check profile/growth sections

### Expected Results
- ✅ Level updates: Beginner → Associate → Intermediate (on completions)
- ✅ Badges earned:
  - 🌱 First Step (on 1st completion)
  - 📚 Knowledge Builder (on 5th completion)
  - 💯 Perfect Score (if any quiz = 100%)
  - ⭐ High Achiever (if avg score ≥ 90%)
- ✅ Streak tracking active (if same-day completions)

---

## Test 8: Authentication & Authorization

### Test 8a: Missing Token
```bash
curl -X POST http://localhost:8000/api/update-progress \
  -H "Content-Type: application/json" \
  -d '{"module_id": "mod_1", "score": 85}'

# Expected: 401 Unauthorized
# {"detail": "Unauthorized"}
```

### Test 8b: Expired/Invalid Token
```bash
curl -X POST http://localhost:8000/api/update-progress \
  -H "Authorization: Bearer invalid_token_here" \
  -H "Content-Type: application/json" \
  -d '{"module_id": "mod_1", "score": 85}'

# Expected: 401 Unauthorized
```

### Test 8c: Valid Token
```bash
curl -X POST http://localhost:8000/api/update-progress \
  -H "Authorization: Bearer $(echo $JWT_TOKEN)" \
  -H "Content-Type: application/json" \
  -d '{"module_id": "mod_1", "score": 85}'

# Expected: 200 OK with progress response
```

---

## Test 9: Validation & Error Handling

### Test 9a: Missing Required Fields
```bash
# Missing module_id
curl -X POST .../api/update-progress \
  -H "Authorization: Bearer ..." \
  -H "Content-Type: application/json" \
  -d '{"score": 85}'

# Expected: 400 Bad Request
# {"detail": "module_id is required"}
```

### Test 9b: Invalid Score Range
```bash
curl -X POST .../api/update-progress \
  -H "Authorization: Bearer ..." \
  -H "Content-Type: application/json" \
  -d '{"module_id": "mod_1", "score": 150}'

# Expected: 400 Bad Request
# {"detail": "score must be between 0 and 100"}
```

### Test 9c: Invalid Score Type
```bash
curl -X POST .../api/update-progress \
  -H "Authorization: Bearer ..." \
  -H "Content-Type: application/json" \
  -d '{"module_id": "mod_1", "score": "not_a_number"}'

# Expected: 400 Bad Request
# {"detail": "score must be a number between 0 and 100"}
```

---

## Test 10: Dual-Write Consistency (JSON + SQLite)

### Steps
1. Complete one module/quiz
2. Check both `growth_data.json` and SQLite simultaneously

### Verification
```bash
# Check growth_data.json
cat Backend/generated_courses/growth_data.json | jq '.employees.emp001.completions[0]'

# Output should show:
{
  "module_id": "mod_1",
  "score": 85,
  "passed": true,
  "completed_at": "2026-04-08T..."
}
```

```bash
# Check SQLite
sqlite3 Backend/agents/growth_tracker.db \
  "SELECT score, completed_at, status FROM employee_course_progress WHERE employee_id='emp001';"

# Output should match JSON data (at least score and timestamp)
```

### Expected Results
- ✅ JSON has entry in completions array
- ✅ SQLite has matching row
- ✅ Timestamps within 1 second of each other
- ✅ Scores identical
- ✅ Status = "Completed" in both

---

## Test 11: End-to-End Workflow

### Complete Flow
```
1. Admin generates course        → HTML files created ✅
2. Admin publishes course        → Database entry created ✅
3. Employee logs in              → Can see course ✅
4. Employee launches module      → HTML opens in new tab ✅
5. Employee completes module     → Progress POSTed to API ✅
6. Progress syncs to DB          → JSON + SQLite updated ✅
7. Dashboard refreshes           → Status shows "Completed" ✅
8. Manager views overview        → Employee appears in progress table ✅
9. User earns badges             → Visible in profile ✅
10. Analytics built              → Can run reports ✅
```

### Verification Checklist
- [ ] All 10 steps execute without errors
- [ ] No 401/403/500 errors in console
- [ ] Network tab shows successful POSTs
- [ ] Both JSON and SQLite in sync
- [ ] UI updates reflect changes
- [ ] Timestamps are recent

---

## Browser DevTools Debugging Tips

### Network Tab
- **Filter**: Type `update-progress` to see all progress POST requests
- **Headers**: Verify `Authorization: Bearer ...` is present
- **Response**: Should be JSON with employee_id, stats, badges
- **Status**: All should be 200 OK

### Console Tab
- **Network Errors**: Look for 401, 403, 500, or timeout messages
- **Module Logger**: Module completion script logs to console
- **localStorage**: Check that token is set: `localStorage.getItem('token')`

### Storage Tab
- **localStorage**: Verify JWT token under key `token`
- **Cookies**: Check for session cookie (if used)

### Sample Console Check
```javascript
console.log(localStorage.getItem('token')); // Should print JWT token
```

---

## Performance Baselines

- HTML file load: < 2 seconds
- Quiz submission POST: < 1 second response
- Dashboard refresh: < 3 seconds
- Database query (SQLite): < 100ms
- Progress bar animation: smooth (60fps)

---

## Common Issues & Fixes

### Issue: 401 Unauthorized on Progress POST
**Cause**: Token missing or expired
**Fix**: 
```javascript
// In browser console
console.log(localStorage.getItem('token'));
// If empty, log out and log back in
```

### Issue: Module HTML doesn't load
**Cause**: File not found or wrong filename
**Fix**:
```bash
# Check file exists
ls -l Backend/generated_courses/ | grep spa
# Verify filename matches API response
```

### Issue: Progress not showing on dashboard
**Cause**: Employee ID mismatch or API failure
**Fix**:
```bash
# Check server logs for API errors
grep "Update progress" Backend/logs/*.log
# Verify employee_id in JWT
```

### Issue: Quiz score not triggering modules as "passed"
**Cause**: Score < 70 (default threshold)
**Fix**:
- Score must be ≥ 70 to mark as "passed"
- Check env var `LMS_PASS_THRESHOLD`

---

## Success Criteria

| Test | Pass Criteria | Status |
|------|---------------|--------|
| HTML Generation | Both PDF and HTML created | ☐ |
| File Serving | 200 response, proper MIME type | ☐ |
| Module Completion | Progress POSTed successfully | ☐ |
| Quiz Submission | Score recorded, feedback shown | ☐ |
| Dashboard Sync | Status updates within 5s | ☐ |
| Manager View | Employee visible with correct data | ☐ |
| Badge Earning | Badges awarded on thresholds | ☐ |
| Authentication | 401 on missing token | ☐ |
| Validation | 400 on invalid inputs | ☐ |
| Dual-Write Sync | JSON and SQLite match | ☐ |

---

## Final Verification

Once all tests pass, consider running:
```bash
# Full course generation test
python Backend/agents/Course_generator.py

# Growth tracker seed (optional)
python Backend/agents/Growth_tracker.py seed

# Database check
sqlite3 Backend/agents/growth_tracker.db ".tables"
# Should show: published_courses, employee_course_progress
```

**All tests passing? 🎉 Interactive HTML courses are ready for production!**
