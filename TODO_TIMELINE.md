# HRMS Backend (Django) – TODO & Timeline

**Generated:** 2026-05-25

This file is a living checklist to track what is *done*, what is *pending*, and what needs *frontend integration*.

---

## 1) Current backend APIs present (apis/v1)
Based on `hrms/urls.py` + `apis/urls.py`, the currently routed endpoints are:

### Auth
- `POST apis/v1/auth/google/`
- `POST apis/v1/auth/user/` (login)
- `POST apis/v1/auth/update-password/`
- `POST apis/v1/auth/reset/password/` (send OTP)
- `POST apis/v1/auth/reset/otp/` (confirm OTP)

### Company / Organization
- `POST/PATCH apis/v1/company/details/`

### Policy
- `POST/PATCH/GET apis/v1/company/policy/`

### Department
- `POST/GET/PATCH apis/v1/department/`

### Employees
- `POST/GET/PATCH apis/v1/employees/`

### Attendance
- `POST apis/v1/attendance/` (check-in/out)
- `GET apis/v1/attendance/` (attendance listing/status)

---

## 2) Items that look unfinished / risky / need verification
These are not necessarily “broken”, but they are the first things to review before integration:

1. **Response format consistency**
   - There is a `BaseResponseMixin` with `success_response()` / `error_response()`.
   - Confirm every endpoint returns the same envelope and status codes.

2. **Permissions / roles coverage**
   - Some views clearly check `user_type` (e.g., admin-only employee creation, employee-only attendance).
   - Verify all endpoints have correct access rules (company admins vs employees).

3. **Pagination + filtering**
   - `PageNumberPagination` is imported; confirm where it is used (employees, attendance, etc.) and ensure consistent query params.

4. **Location / reverse geocoding**
   - Attendance uses `geopy` reverse geocoding.
   - Validate rate limits/timeouts and whether you want this to be optional or async.

5. **Email workflows**
   - Password reset uses SMTP settings; verify env vars exist in deployment.

---

## 3) Missing backend APIs (based on current Flutter screens)
Flutter currently has UI screens for (at least):
- Announcements
- Leave requests
- Notifications

There are **no routed endpoints** yet for those features in `apis/urls.py`.

### Recommended endpoints to add next
(Names can change, but keep consistent patterns and JWT auth.)

#### Leave management
- `POST /leaves/` (apply)
- `GET /leaves/` (list; admin can see all, employee sees own)
- `PATCH /leaves/<id>/` (approve/reject/cancel)

#### Announcements
- `POST /announcements/` (admin)
- `GET /announcements/` (admin + employee)
- `DELETE /announcements/<id>/` (admin)

#### Notifications
- `GET /notifications/`
- `PATCH /notifications/<id>/read/`

---

## 4) Suggested timeline (upcoming days)
Assuming today is **2026-05-25**.

### Day 1 (2026-05-25 to 2026-05-26)
- Freeze & document existing API contracts (request/response examples)
- Add Postman/Insomnia collection OR Swagger (drf-spectacular recommended)

### Day 2 (2026-05-27)
- Implement Leave module (models + serializers + endpoints + permissions)

### Day 3 (2026-05-28)
- Implement Announcements module + basic Notifications

### Day 4 (2026-05-29)
- Integration support: align all endpoints to frontend needs, add filtering/pagination

### Day 5 (2026-05-30)
- QA + bug fixes + seed data for staging

---

## 5) Integration checklist for frontend
When Flutter integrates:
- Confirm base URL + version prefix: `/apis/v1/`
- Ensure JWT access token is attached for all protected calls
- Confirm error handling: `{"success": false, "error": ...}`

---

## 6) Notes
- This repo snapshot was inspected via code search, which may not find everything (results can be incomplete). Re-check by browsing the repo locally as well.
