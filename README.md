# Mini LinkedIn Job Portal

A compact full-stack job portal where users can register either as `job_seeker` or `recruiter`, post jobs, apply, track applications, upload resumes, and filter opportunities.

## Features

- Role-based registration and login using JWT authentication
- SQLite relational schema for users, resumes, jobs, and applications
- REST APIs for auth, jobs, recruiter dashboards, applications, and resume upload
- Search and filter jobs by keyword, location, and job type
- Recommended jobs for seekers based on skills and uploaded resume presence
- Responsive frontend with separate recruiter and job seeker flows

## Tech Stack

- Node.js
- Express
- SQLite
- Vanilla HTML, CSS, and JavaScript

## Setup

1. Install dependencies:

   ```bash
   npm install
   ```

2. Start the app:

   ```bash
   npm start
   ```

3. Open `http://localhost:3000`

## Core Database Relations

- `users` stores both recruiters and job seekers with a `role`
- `resumes.user_id -> users.id` creates a one-to-one resume relation
- `jobs.recruiter_id -> users.id` links each job to the recruiter who posted it
- `applications.job_id -> jobs.id` and `applications.seeker_id -> users.id` form the many-to-many application relationship

## REST API Overview

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/jobs`
- `POST /api/jobs`
- `POST /api/jobs/import`
- `GET /api/recruiter/jobs`
- `POST /api/applications`
- `GET /api/applications`
- `GET /api/jobs/recommended`
- `POST /api/resume`
- `GET /api/health`

## Notes

- Resume files are stored in the local `uploads/` folder.
- The SQLite database is created automatically inside `data/job_portal.db`.
- You can override the default JWT secret with the `JWT_SECRET` environment variable.

## Import External Jobs

Recruiters can import job listings from the dashboard using `.csv` or `.json` files.

Supported fields:

- `title`
- `company`
- `location`
- `jobType`
- `salaryRange`
- `description`
- `skillsRequired`

Example files are included at:

- [sample-jobs.csv](</abs/path/c:/Users/CEC47/Desktop/Online job portal(mini linkedIn)/sample-jobs.csv>)
- [sample-jobs.json](</abs/path/c:/Users/CEC47/Desktop/Online job portal(mini linkedIn)/sample-jobs.json>)
