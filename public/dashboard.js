const state = {
  token: localStorage.getItem("token") || "",
  user: null,
  jobs: [],
  network: {
    suggestions: [],
    connections: [],
  },
};

const redirectToLogin = () => {
  window.location.href = "/login";
};

const api = async (path, options = {}) => {
  const headers = options.headers ? { ...options.headers } : {};
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));

  if (response.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    redirectToLogin();
    throw new Error("Your session expired. Please log in again.");
  }

  if (!response.ok) {
    throw new Error(data.message || "Request failed");
  }

  return data;
};

document.addEventListener("DOMContentLoaded", () => {
  const elements = {
    logoutBtn: document.getElementById("logoutBtn"),
    navTabs: Array.from(document.querySelectorAll(".nav-tab")),
    filtersForm: document.getElementById("filtersForm"),
    jobsList: document.getElementById("jobsList"),
    recruiterPanel: document.getElementById("recruiterPanel"),
    seekerPanel: document.getElementById("seekerPanel"),
    jobForm: document.getElementById("jobForm"),
    importForm: document.getElementById("importForm"),
    recruiterJobs: document.getElementById("recruiterJobs"),
    applicationsList: document.getElementById("applicationsList"),
    recommendedJobs: document.getElementById("recommendedJobs"),
    resumeForm: document.getElementById("resumeForm"),
    profileSummary: document.getElementById("profileSummary"),
    profileStats: document.getElementById("profileStats"),
    profilePageAvatar: document.getElementById("profilePageAvatar"),
    profilePageSummary: document.getElementById("profilePageSummary"),
    profileDetailList: document.getElementById("profileDetailList"),
    sessionBadge: document.getElementById("sessionBadge"),
    profileAvatar: document.getElementById("profileAvatar"),
    composerAvatar: document.getElementById("composerAvatar"),
    jobsCount: document.getElementById("jobsCount"),
    networkCount: document.getElementById("networkCount"),
    networkSuggestions: document.getElementById("networkSuggestions"),
    networkConnections: document.getElementById("networkConnections"),
    toast: document.getElementById("toast"),
  };

  const showToast = (message, isError = false) => {
    elements.toast.textContent = message;
    elements.toast.classList.remove("hidden");
    elements.toast.style.background = isError ? "#7f1d1d" : "#1f2933";
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      elements.toast.classList.add("hidden");
    }, 2500);
  };

  const persistSession = () => {
    if (state.token) {
      localStorage.setItem("token", state.token);
    }
    localStorage.setItem("user", JSON.stringify(state.user));
  };

  const loadCurrentUser = async () => {
    const data = await api("/api/auth/me");
    state.user = data.user;
    persistSession();
  };

  const renderProfile = () => {
    elements.sessionBadge.textContent = state.user.role === "recruiter" ? "Recruiter" : "Job seeker";
    const initials = state.user.name
      .split(" ")
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();

    if (elements.profileAvatar) {
      elements.profileAvatar.textContent = initials || "CN";
    }

    if (elements.composerAvatar) {
      elements.composerAvatar.textContent = initials || "CN";
    }

    if (elements.profilePageAvatar) {
      elements.profilePageAvatar.textContent = initials || "CN";
    }

    elements.profileSummary.innerHTML = `
      <h3>${state.user.name}</h3>
      <p class="muted">${state.user.headline}</p>
      <p class="muted">${state.user.email}</p>
    `;

    elements.profileStats.innerHTML = `
      <div class="stat-row"><span>Skills</span><strong>${state.user.skills ? state.user.skills.split(",").filter(Boolean).length : 0}</strong></div>
      <div class="stat-row"><span>Resume</span><strong>${state.user.resumeFilename ? "Uploaded" : "Missing"}</strong></div>
      <div class="stat-row"><span>Connections</span><strong>${state.network.connections.length}</strong></div>
    `;

    if (elements.profilePageSummary) {
      elements.profilePageSummary.innerHTML = `
        <h3>${state.user.name}</h3>
        <p class="muted">${state.user.headline}</p>
        <p class="muted">${state.user.email}</p>
      `;
    }

    if (elements.profileDetailList) {
      elements.profileDetailList.innerHTML = `
        <div class="stat-row"><span>Role</span><strong>${state.user.role === "recruiter" ? "Recruiter" : "Job seeker"}</strong></div>
        <div class="stat-row"><span>Skills</span><strong>${state.user.skills || "Not added yet"}</strong></div>
        <div class="stat-row"><span>Resume</span><strong>${state.user.resumeFilename || "No file uploaded"}</strong></div>
        <div class="stat-row"><span>Connections</span><strong>${state.network.connections.length}</strong></div>
      `;
    }

    elements.recruiterPanel.classList.toggle("hidden", state.user.role !== "recruiter");
    elements.seekerPanel.classList.toggle("hidden", state.user.role !== "job_seeker");
  };

  const showSection = (sectionId) => {
    document.querySelectorAll(".dashboard-section").forEach((section) => {
      section.classList.toggle("hidden", section.id !== sectionId);
    });

    document.body.classList.toggle("jobs-view", sectionId === "jobsSection");
    document.body.classList.toggle("profile-view", sectionId === "profileSection");

    elements.navTabs.forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.section === sectionId);
    });
  };

  const renderJobs = (jobs, container, allowApply = true) => {
    if (!jobs.length) {
      container.innerHTML = "<p class='muted'>No jobs found yet.</p>";
      return;
    }

    container.innerHTML = jobs
      .map(
        (job) => `
          <article class="job-card">
            <div class="job-actions">
              <div>
                <h3>${job.title}</h3>
                <p>${job.company}</p>
              </div>
              ${job.matchScore ? `<span class="match">${job.matchScore}% match</span>` : ""}
            </div>
            <div class="job-meta">
              <span>${job.location}</span>
              <span>${job.jobType}</span>
              <span>${job.salaryRange || "Compensation shared later"}</span>
            </div>
            <p>${job.description}</p>
            <p class="muted"><strong>Skills:</strong> ${job.skillsRequired}</p>
            <div class="job-actions">
              <small class="muted">Posted by ${job.recruiterName}</small>
              ${
                allowApply && state.user.role === "job_seeker"
                  ? `<button class="small-btn" data-apply="${job.id}">Apply now</button>`
                  : ""
              }
            </div>
          </article>
        `
      )
      .join("");
  };

  const renderApplications = (items) => {
    if (!items.length) {
      elements.applicationsList.innerHTML =
        "<p class='muted'>You have not applied to any jobs yet.</p>";
      return;
    }

    elements.applicationsList.innerHTML = items
      .map(
        (application) => `
          <article class="application-card">
            <h3>${application.title}</h3>
            <div class="application-meta">
              <span>${application.company}</span>
              <span>${application.location}</span>
              <span>Status: <strong>${application.status}</strong></span>
            </div>
            <p class="muted">Applied on ${new Date(application.appliedAt).toLocaleDateString()}</p>
          </article>
        `
      )
      .join("");
  };

  const formatRole = (role) => (role === "recruiter" ? "Recruiter" : "Job seeker");

  const renderNetworkCards = (items, container, mode) => {
    if (!container) {
      return;
    }

    if (!items.length) {
      container.innerHTML = `
        <div class="network-empty">
          <strong>${mode === "suggestions" ? "No suggestions right now" : "No connections yet"}</strong>
          <p class="muted">
            ${
              mode === "suggestions"
                ? "More people will appear here as new members join CareerNest."
                : "Start connecting with recruiters and peers to build your network."
            }
          </p>
        </div>
      `;
      return;
    }

    container.innerHTML = items
      .map((person) => {
        const initials = person.name
          .split(" ")
          .map((part) => part[0])
          .join("")
          .slice(0, 2)
          .toUpperCase();

        const meta =
          mode === "suggestions"
            ? `${person.matchScore}% match${person.sharedSkills?.length ? ` · ${person.sharedSkills.slice(0, 3).join(", ")}` : ""}`
            : `Connected ${new Date(person.connectedAt).toLocaleDateString()}`;

        return `
          <article class="network-card">
            <div class="network-card-head">
              <div class="avatar-circle small">${initials || "CN"}</div>
              <div class="network-copy">
                <h3>${person.name}</h3>
                <p class="muted">${person.headline}</p>
                <p class="muted">${formatRole(person.role)}</p>
              </div>
            </div>
            <p class="network-meta">${meta}</p>
            ${
              mode === "suggestions"
                ? `<button class="small-btn" data-connect="${person.id}">Connect</button>`
                : `<p class="muted">${person.email}</p>`
            }
          </article>
        `;
      })
      .join("");
  };

  const renderNetwork = () => {
    if (elements.networkCount) {
      elements.networkCount.textContent = `${state.network.connections.length} connection${
        state.network.connections.length === 1 ? "" : "s"
      }`;
    }

    renderNetworkCards(state.network.suggestions, elements.networkSuggestions, "suggestions");
    renderNetworkCards(state.network.connections, elements.networkConnections, "connections");
  };

  const loadJobs = async (query = "") => {
    const data = await api(`/api/jobs${query}`);
    state.jobs = data.jobs;
    if (elements.jobsCount) {
      elements.jobsCount.textContent = `${data.jobs.length} role${data.jobs.length === 1 ? "" : "s"}`;
    }
    renderJobs(data.jobs, elements.jobsList, true);
  };

  const loadRecruiterJobs = async () => {
    if (state.user.role !== "recruiter") {
      return;
    }
    const data = await api("/api/recruiter/jobs");
    renderJobs(data.jobs, elements.recruiterJobs, false);
  };

  const loadApplications = async () => {
    if (state.user.role !== "job_seeker") {
      return;
    }
    const [applications, recommended] = await Promise.all([
      api("/api/applications"),
      api("/api/jobs/recommended"),
    ]);
    renderApplications(applications.applications);
    renderJobs(recommended.jobs, elements.recommendedJobs, true);
  };

  const loadNetwork = async () => {
    const data = await api("/api/network");
    state.network = {
      suggestions: data.suggestions || [],
      connections: data.connections || [],
    };
    renderNetwork();
  };

  const refreshDashboard = async () => {
    await loadCurrentUser();
    await loadNetwork();
    renderProfile();
    await loadJobs();
    await loadRecruiterJobs();
    await loadApplications();
  };

  document.addEventListener("click", async (event) => {
    const applyButton = event.target.closest("[data-apply]");
    if (applyButton) {
      try {
        await api("/api/applications", {
          method: "POST",
          body: JSON.stringify({ jobId: Number(applyButton.dataset.apply) }),
        });
        showToast("Application submitted");
        await loadJobs();
        await loadApplications();
      } catch (error) {
        showToast(error.message, true);
      }
      return;
    }

    const connectButton = event.target.closest("[data-connect]");
    if (!connectButton) {
      return;
    }

    try {
      const data = await api("/api/network/connect", {
        method: "POST",
        body: JSON.stringify({ userId: Number(connectButton.dataset.connect) }),
      });
      showToast(data.message || "Connection added");
      await loadNetwork();
      renderProfile();
    } catch (error) {
      showToast(error.message, true);
    }
  });

  elements.logoutBtn.addEventListener("click", () => {
    fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    redirectToLogin();
  });

  elements.navTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      showSection(tab.dataset.section);
    });
  });

  elements.filtersForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const params = new URLSearchParams();
    const values = Object.fromEntries(new FormData(event.currentTarget).entries());
    Object.entries(values).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      }
    });
    try {
      await loadJobs(params.toString() ? `?${params.toString()}` : "");
    } catch (error) {
      showToast(error.message, true);
    }
  });

  elements.jobForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/jobs", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget).entries())),
      });
      showToast("Job posted");
      event.currentTarget.reset();
      await loadRecruiterJobs();
      await loadJobs();
    } catch (error) {
      showToast(error.message, true);
    }
  });

  elements.importForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const data = await api("/api/jobs/import", {
        method: "POST",
        body: new FormData(event.currentTarget),
      });
      showToast(
        data.skippedCount
          ? `${data.message}. Skipped ${data.skippedCount} incomplete row(s)`
          : data.message
      );
      event.currentTarget.reset();
      await loadRecruiterJobs();
      await loadJobs();
    } catch (error) {
      showToast(error.message, true);
    }
  });

  elements.resumeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const data = await api("/api/resume", {
        method: "POST",
        body: new FormData(event.currentTarget),
      });
      state.user = data.user;
      persistSession();
      renderProfile();
      showToast("Resume uploaded");
      event.currentTarget.reset();
      await loadApplications();
    } catch (error) {
      showToast(error.message, true);
    }
  });

  refreshDashboard().catch((error) => {
    showToast(error.message, true);
  });

  showSection("homeSection");
});
