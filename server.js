const express = require("express");
const cors = require("cors");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const multer = require("multer");
const fs = require("fs");
const path = require("path");
const sqlite3 = require("sqlite3").verbose();

const app = express();
const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || "mini-linkedin-secret";
const databaseDir = path.join(__dirname, "data");
const uploadsDir = path.join(__dirname, "uploads");
const databasePath = path.join(databaseDir, "job_portal.db");

fs.mkdirSync(databaseDir, { recursive: true });
fs.mkdirSync(uploadsDir, { recursive: true });

const db = new sqlite3.Database(databasePath);

const run = (sql, params = []) =>
  new Promise((resolve, reject) => {
    db.run(sql, params, function onRun(error) {
      if (error) {
        reject(error);
        return;
      }
      resolve({ id: this.lastID, changes: this.changes });
    });
  });

const get = (sql, params = []) =>
  new Promise((resolve, reject) => {
    db.get(sql, params, (error, row) => {
      if (error) {
        reject(error);
        return;
      }
      resolve(row);
    });
  });

const all = (sql, params = []) =>
  new Promise((resolve, reject) => {
    db.all(sql, params, (error, rows) => {
      if (error) {
        reject(error);
        return;
      }
      resolve(rows);
    });
  });

const initializeDatabase = async () => {
  await run("PRAGMA foreign_keys = ON");
  await run(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('job_seeker', 'recruiter')),
      headline TEXT NOT NULL,
      skills TEXT DEFAULT '',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
  `);

  await run(`
    CREATE TABLE IF NOT EXISTS resumes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL UNIQUE,
      original_name TEXT NOT NULL,
      stored_name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
  `);

  await run(`
    CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      recruiter_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      company TEXT NOT NULL,
      location TEXT NOT NULL,
      job_type TEXT NOT NULL,
      salary_range TEXT DEFAULT '',
      description TEXT NOT NULL,
      skills_required TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (recruiter_id) REFERENCES users(id) ON DELETE CASCADE
    )
  `);

  await run(`
    CREATE TABLE IF NOT EXISTS applications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id INTEGER NOT NULL,
      seeker_id INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'Applied',
      applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(job_id, seeker_id),
      FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
      FOREIGN KEY (seeker_id) REFERENCES users(id) ON DELETE CASCADE
    )
  `);

  await run(`
    CREATE TABLE IF NOT EXISTS connections (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_one_id INTEGER NOT NULL,
      user_two_id INTEGER NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      CHECK(user_one_id < user_two_id),
      UNIQUE(user_one_id, user_two_id),
      FOREIGN KEY (user_one_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (user_two_id) REFERENCES users(id) ON DELETE CASCADE
    )
  `);
};

const storage = multer.diskStorage({
  destination: (_req, _file, callback) => callback(null, uploadsDir),
  filename: (_req, file, callback) => {
    const safeName = file.originalname.replace(/[^a-zA-Z0-9.-]/g, "_");
    callback(null, `${Date.now()}-${safeName}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 3 * 1024 * 1024 },
});

const importUpload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 2 * 1024 * 1024 },
});

app.use(cors());
app.use(express.json());
app.use((req, res, next) => {
  if (
    req.path === "/" ||
    req.path === "/login" ||
    req.path === "/register" ||
    req.path === "/dashboard" ||
    req.path.endsWith(".html")
  ) {
    res.setHeader("Cache-Control", "no-store");
  }
  next();
});
app.use("/uploads", express.static(uploadsDir));
app.use(express.static(path.join(__dirname, "public")));

const createToken = (user) =>
  jwt.sign({ id: user.id, role: user.role, email: user.email }, JWT_SECRET, {
    expiresIn: "7d",
  });

const setAuthCookie = (res, token) => {
  res.setHeader(
    "Set-Cookie",
    `auth_token=${token}; HttpOnly; Path=/; Max-Age=${7 * 24 * 60 * 60}; SameSite=Lax`
  );
};

const clearAuthCookie = (res) => {
  res.setHeader("Set-Cookie", "auth_token=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax");
};

const serializeUser = async (userId) => {
  const user = await get(
    `
      SELECT u.id, u.name, u.email, u.role, u.headline, u.skills, r.original_name AS resumeFilename
      FROM users u
      LEFT JOIN resumes r ON r.user_id = u.id
      WHERE u.id = ?
    `,
    [userId]
  );
  return user;
};

const authRequired = async (req, res, next) => {
  const header = req.headers.authorization || "";
  const cookieHeader = req.headers.cookie || "";
  const cookieToken = cookieHeader
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("auth_token="));
  const token = header.startsWith("Bearer ")
    ? header.slice(7)
    : cookieToken
      ? decodeURIComponent(cookieToken.slice("auth_token=".length))
      : "";

  if (!token) {
    res.status(401).json({ message: "Authentication required" });
    return;
  }

  try {
    const payload = jwt.verify(token, JWT_SECRET);
    const user = await serializeUser(payload.id);
    if (!user) {
      res.status(401).json({ message: "Invalid session" });
      return;
    }
    req.user = user;
    next();
  } catch (_error) {
    res.status(401).json({ message: "Invalid or expired token" });
  }
};

const requireRole = (role) => (req, res, next) => {
  if (req.user.role !== role) {
    res.status(403).json({ message: `Only ${role} accounts can perform this action` });
    return;
  }
  next();
};

const buildJobFilters = (query) => {
  const clauses = [];
  const params = [];

  if (query.q) {
    clauses.push("(j.title LIKE ? OR j.company LIKE ? OR j.skills_required LIKE ?)");
    params.push(`%${query.q}%`, `%${query.q}%`, `%${query.q}%`);
  }

  if (query.location) {
    clauses.push("j.location LIKE ?");
    params.push(`%${query.location}%`);
  }

  if (query.jobType) {
    clauses.push("j.job_type = ?");
    params.push(query.jobType);
  }

  return {
    where: clauses.length ? `WHERE ${clauses.join(" AND ")}` : "",
    params,
  };
};

const calculateMatchScore = (jobSkills, userSkills, hasResume) => {
  const normalize = (value) =>
    (value || "")
      .split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean);

  const required = normalize(jobSkills);
  const available = new Set(normalize(userSkills));

  if (!required.length) {
    return hasResume ? 75 : 60;
  }

  const matches = required.filter((skill) => available.has(skill)).length;
  const rawScore = Math.round((matches / required.length) * 100);
  return Math.min(100, hasResume ? rawScore + 10 : rawScore);
};

const calculateConnectionScore = (candidate, currentUser) => {
  const normalize = (value) =>
    (value || "")
      .split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean);

  const currentSkills = new Set(normalize(currentUser.skills));
  const candidateSkills = normalize(candidate.skills);
  const sharedSkills = candidateSkills.filter((skill) => currentSkills.has(skill));
  let score = sharedSkills.length * 18;

  if (candidate.role === currentUser.role) {
    score += 12;
  } else {
    score += 20;
  }

  if (candidate.headline && currentUser.headline) {
    const candidateHeadline = candidate.headline.toLowerCase();
    const currentHeadline = currentUser.headline.toLowerCase();
    if (candidateHeadline.includes("react") && currentHeadline.includes("react")) {
      score += 8;
    }
    if (candidateHeadline.includes("recruit") && currentHeadline.includes("recruit")) {
      score += 8;
    }
  }

  return {
    score: Math.min(99, Math.max(35, score)),
    sharedSkills,
  };
};

const normalizeJobRecord = (record) => {
  const pick = (...keys) => {
    for (const key of keys) {
      if (record[key] !== undefined && record[key] !== null && String(record[key]).trim()) {
        return String(record[key]).trim();
      }
    }
    return "";
  };

  const normalized = {
    title: pick("title", "jobTitle", "job_title"),
    company: pick("company", "companyName", "company_name"),
    location: pick("location", "jobLocation", "job_location"),
    jobType: pick("jobType", "job_type", "employmentType", "employment_type") || "Full-time",
    salaryRange: pick("salaryRange", "salary_range", "salary"),
    description: pick("description", "jobDescription", "job_description"),
    skillsRequired: pick("skillsRequired", "skills_required", "skills", "requiredSkills"),
  };

  return normalized;
};

const validateImportedJob = (job) =>
  job.title &&
  job.company &&
  job.location &&
  job.jobType &&
  job.description &&
  job.skillsRequired;

const parseCsvLine = (line) => {
  const values = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        current += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      values.push(current.trim());
      current = "";
      continue;
    }

    current += char;
  }

  values.push(current.trim());
  return values;
};

const parseCsvJobs = (content) => {
  const lines = content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    return [];
  }

  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const values = parseCsvLine(line);
    return headers.reduce((record, header, index) => {
      record[header] = values[index] || "";
      return record;
    }, {});
  });
};

app.post("/api/auth/register", async (req, res) => {
  try {
    const { name, email, password, role, headline, skills = "" } = req.body;

    if (!name || !email || !password || !role || !headline) {
      res.status(400).json({ message: "All required fields must be provided" });
      return;
    }

    const existingUser = await get("SELECT id FROM users WHERE email = ?", [email]);
    if (existingUser) {
      res.status(409).json({ message: "An account with this email already exists" });
      return;
    }

    const passwordHash = await bcrypt.hash(password, 10);
    const result = await run(
      `
        INSERT INTO users (name, email, password_hash, role, headline, skills)
        VALUES (?, ?, ?, ?, ?, ?)
      `,
      [name, email, passwordHash, role, headline, skills]
    );

    const user = await serializeUser(result.id);
    const token = createToken(user);
    setAuthCookie(res, token);
    res.status(201).json({ token, user });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

app.post("/api/auth/login", async (req, res) => {
  try {
    const { email, password } = req.body;
    const account = await get("SELECT * FROM users WHERE email = ?", [email]);

    if (!account) {
      res.status(401).json({ message: "Invalid email or password" });
      return;
    }

    const valid = await bcrypt.compare(password, account.password_hash);
    if (!valid) {
      res.status(401).json({ message: "Invalid email or password" });
      return;
    }

    const user = await serializeUser(account.id);
    const token = createToken(user);
    setAuthCookie(res, token);
    res.json({ token, user });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

app.get("/api/auth/me", authRequired, async (req, res) => {
  res.json({ user: req.user });
});

app.post("/api/auth/logout", (_req, res) => {
  clearAuthCookie(res);
  res.json({ message: "Logged out" });
});

app.get("/api/jobs", async (req, res) => {
  try {
    const filters = buildJobFilters(req.query);
    const jobs = await all(
      `
        SELECT
          j.id,
          j.title,
          j.company,
          j.location,
          j.job_type AS jobType,
          j.salary_range AS salaryRange,
          j.description,
          j.skills_required AS skillsRequired,
          j.created_at AS createdAt,
          u.name AS recruiterName
        FROM jobs j
        INNER JOIN users u ON u.id = j.recruiter_id
        ${filters.where}
        ORDER BY j.created_at DESC
      `,
      filters.params
    );

    res.json({ jobs });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

app.post("/api/jobs", authRequired, requireRole("recruiter"), async (req, res) => {
  try {
    const {
      title,
      company,
      location,
      jobType,
      salaryRange = "",
      description,
      skillsRequired,
    } = req.body;

    if (!title || !company || !location || !jobType || !description || !skillsRequired) {
      res.status(400).json({ message: "Please provide all required job details" });
      return;
    }

    const result = await run(
      `
        INSERT INTO jobs (
          recruiter_id, title, company, location, job_type, salary_range, description, skills_required
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `,
      [req.user.id, title, company, location, jobType, salaryRange, description, skillsRequired]
    );

    const job = await get(
      `
        SELECT
          j.id,
          j.title,
          j.company,
          j.location,
          j.job_type AS jobType,
          j.salary_range AS salaryRange,
          j.description,
          j.skills_required AS skillsRequired,
          u.name AS recruiterName
        FROM jobs j
        INNER JOIN users u ON u.id = j.recruiter_id
        WHERE j.id = ?
      `,
      [result.id]
    );

    res.status(201).json({ job });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

app.get("/api/recruiter/jobs", authRequired, requireRole("recruiter"), async (req, res) => {
  try {
    const jobs = await all(
      `
        SELECT
          j.id,
          j.title,
          j.company,
          j.location,
          j.job_type AS jobType,
          j.salary_range AS salaryRange,
          j.description,
          j.skills_required AS skillsRequired,
          j.created_at AS createdAt,
          u.name AS recruiterName
        FROM jobs j
        INNER JOIN users u ON u.id = j.recruiter_id
        WHERE j.recruiter_id = ?
        ORDER BY j.created_at DESC
      `,
      [req.user.id]
    );
    res.json({ jobs });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

app.post("/api/applications", authRequired, requireRole("job_seeker"), async (req, res) => {
  try {
    const { jobId } = req.body;

    const job = await get("SELECT id FROM jobs WHERE id = ?", [jobId]);
    if (!job) {
      res.status(404).json({ message: "Job not found" });
      return;
    }

    await run("INSERT INTO applications (job_id, seeker_id) VALUES (?, ?)", [jobId, req.user.id]);
    res.status(201).json({ message: "Application submitted" });
  } catch (error) {
    if (String(error.message).includes("UNIQUE")) {
      res.status(409).json({ message: "You have already applied to this job" });
      return;
    }
    res.status(500).json({ message: error.message });
  }
});

app.get("/api/applications", authRequired, requireRole("job_seeker"), async (req, res) => {
  try {
    const applications = await all(
      `
        SELECT
          a.id,
          a.status,
          a.applied_at AS appliedAt,
          j.title,
          j.company,
          j.location
        FROM applications a
        INNER JOIN jobs j ON j.id = a.job_id
        WHERE a.seeker_id = ?
        ORDER BY a.applied_at DESC
      `,
      [req.user.id]
    );
    res.json({ applications });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

app.get("/api/jobs/recommended", authRequired, requireRole("job_seeker"), async (req, res) => {
  try {
    const jobs = await all(
      `
        SELECT
          j.id,
          j.title,
          j.company,
          j.location,
          j.job_type AS jobType,
          j.salary_range AS salaryRange,
          j.description,
          j.skills_required AS skillsRequired,
          u.name AS recruiterName
        FROM jobs j
        INNER JOIN users u ON u.id = j.recruiter_id
        ORDER BY j.created_at DESC
      `
    );

    const recommended = jobs
      .map((job) => ({
        ...job,
        matchScore: calculateMatchScore(job.skillsRequired, req.user.skills, Boolean(req.user.resumeFilename)),
      }))
      .sort((a, b) => b.matchScore - a.matchScore)
      .slice(0, 6);

    res.json({ jobs: recommended });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

app.get("/api/network", authRequired, async (req, res) => {
  try {
    const connections = await all(
      `
        SELECT
          u.id,
          u.name,
          u.email,
          u.role,
          u.headline,
          u.skills,
          c.created_at AS connectedAt
        FROM connections c
        INNER JOIN users u
          ON u.id = CASE
            WHEN c.user_one_id = ? THEN c.user_two_id
            ELSE c.user_one_id
          END
        WHERE c.user_one_id = ? OR c.user_two_id = ?
        ORDER BY c.created_at DESC, u.name ASC
      `,
      [req.user.id, req.user.id, req.user.id]
    );

    const suggestionsRaw = await all(
      `
        SELECT u.id, u.name, u.email, u.role, u.headline, u.skills
        FROM users u
        WHERE u.id != ?
          AND NOT EXISTS (
            SELECT 1
            FROM connections c
            WHERE
              (c.user_one_id = ? AND c.user_two_id = u.id)
              OR (c.user_two_id = ? AND c.user_one_id = u.id)
          )
        ORDER BY u.created_at DESC, u.name ASC
      `,
      [req.user.id, req.user.id, req.user.id]
    );

    const suggestions = suggestionsRaw
      .map((candidate) => {
        const { score, sharedSkills } = calculateConnectionScore(candidate, req.user);
        return {
          ...candidate,
          sharedSkills,
          matchScore: score,
        };
      })
      .sort((a, b) => b.matchScore - a.matchScore || a.name.localeCompare(b.name))
      .slice(0, 8);

    res.json({ connections, suggestions });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

app.post("/api/network/connect", authRequired, async (req, res) => {
  try {
    const targetUserId = Number(req.body.userId);

    if (!Number.isInteger(targetUserId) || targetUserId <= 0) {
      res.status(400).json({ message: "A valid user is required" });
      return;
    }

    if (targetUserId === req.user.id) {
      res.status(400).json({ message: "You cannot connect with yourself" });
      return;
    }

    const targetUser = await get(
      "SELECT id, name, email, role, headline, skills FROM users WHERE id = ?",
      [targetUserId]
    );
    if (!targetUser) {
      res.status(404).json({ message: "User not found" });
      return;
    }

    const [userOneId, userTwoId] =
      req.user.id < targetUserId ? [req.user.id, targetUserId] : [targetUserId, req.user.id];

    await run("INSERT INTO connections (user_one_id, user_two_id) VALUES (?, ?)", [
      userOneId,
      userTwoId,
    ]);

    res.status(201).json({
      message: `You are now connected with ${targetUser.name}`,
    });
  } catch (error) {
    if (String(error.message).includes("UNIQUE")) {
      res.status(409).json({ message: "You are already connected with this person" });
      return;
    }
    res.status(500).json({ message: error.message });
  }
});

app.post(
  "/api/resume",
  authRequired,
  requireRole("job_seeker"),
  upload.single("resume"),
  async (req, res) => {
    try {
      if (!req.file) {
        res.status(400).json({ message: "Resume file is required" });
        return;
      }

      await run(
        `
          INSERT INTO resumes (user_id, original_name, stored_name, file_path)
          VALUES (?, ?, ?, ?)
          ON CONFLICT(user_id)
          DO UPDATE SET
            original_name = excluded.original_name,
            stored_name = excluded.stored_name,
            file_path = excluded.file_path,
            uploaded_at = CURRENT_TIMESTAMP
        `,
        [req.user.id, req.file.originalname, req.file.filename, req.file.path]
      );

      const user = await serializeUser(req.user.id);
      res.status(201).json({ message: "Resume uploaded", user });
    } catch (error) {
      res.status(500).json({ message: error.message });
    }
  }
);

app.post(
  "/api/jobs/import",
  authRequired,
  requireRole("recruiter"),
  importUpload.single("jobsFile"),
  async (req, res) => {
    try {
      if (!req.file) {
        res.status(400).json({ message: "Import file is required" });
        return;
      }

      const extension = path.extname(req.file.originalname).toLowerCase();
      const rawContent = req.file.buffer.toString("utf8").trim();

      if (!rawContent) {
        res.status(400).json({ message: "The uploaded file is empty" });
        return;
      }

      let records;
      if (extension === ".json") {
        const parsed = JSON.parse(rawContent);
        records = Array.isArray(parsed) ? parsed : parsed.jobs;
      } else if (extension === ".csv") {
        records = parseCsvJobs(rawContent);
      } else {
        res.status(400).json({ message: "Only CSV and JSON files are supported" });
        return;
      }

      if (!Array.isArray(records) || !records.length) {
        res.status(400).json({ message: "No job records were found in the uploaded file" });
        return;
      }

      const normalizedJobs = records.map(normalizeJobRecord);
      const validJobs = normalizedJobs.filter(validateImportedJob);

      if (!validJobs.length) {
        res.status(400).json({
          message:
            "No valid jobs found. Required fields: title, company, location, jobType, description, skillsRequired",
        });
        return;
      }

      for (const job of validJobs) {
        await run(
          `
            INSERT INTO jobs (
              recruiter_id, title, company, location, job_type, salary_range, description, skills_required
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          `,
          [
            req.user.id,
            job.title,
            job.company,
            job.location,
            job.jobType,
            job.salaryRange,
            job.description,
            job.skillsRequired,
          ]
        );
      }

      res.status(201).json({
        message: `Imported ${validJobs.length} job${validJobs.length === 1 ? "" : "s"}`,
        importedCount: validJobs.length,
        skippedCount: normalizedJobs.length - validJobs.length,
      });
    } catch (error) {
      if (error instanceof SyntaxError) {
        res.status(400).json({ message: "Invalid JSON file format" });
        return;
      }
      res.status(500).json({ message: error.message });
    }
  }
);

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, service: "mini-linkedin-job-portal" });
});

app.get("/", (_req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.get("/login", (_req, res) => {
  res.sendFile(path.join(__dirname, "public", "login.html"));
});

app.get("/register", (_req, res) => {
  res.sendFile(path.join(__dirname, "public", "register.html"));
});

app.get("/dashboard", (_req, res) => {
  res.sendFile(path.join(__dirname, "public", "dashboard.html"));
});

app.get("*", (_req, res) => {
  res.redirect("/login");
});

initializeDatabase()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`Server running on http://localhost:${PORT}`);
    });
  })
  .catch((error) => {
    console.error("Failed to initialize database", error);
    process.exit(1);
  });
