const toast = document.getElementById("toast");
const form = document.getElementById("registerForm");

const showToast = (message, isError = false) => {
  toast.textContent = message;
  toast.style.background = isError ? "#7f1d1d" : "#1f2933";
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 2500);
};

const saveSession = (payload) => {
  localStorage.setItem("token", payload.token);
  localStorage.setItem("user", JSON.stringify(payload.user));
};

const clearSession = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
};

clearSession();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(form).entries());

  try {
    const response = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.message || "Registration failed");
    }
    saveSession(data);
    window.location.replace("/dashboard");
  } catch (error) {
    showToast(error.message, true);
  }
});
