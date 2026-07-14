const { createApp } = Vue;

function badgeClass(status) {
  const map = {
    pending: "badge bg-secondary",
    approved: "badge bg-success",
    rejected: "badge bg-danger",
    closed: "badge bg-dark",
    applied: "badge bg-info text-dark",
    shortlisted: "badge bg-warning text-dark",
    selected: "badge bg-success",
  };
  return map[status] || "badge bg-secondary";
}

// ─────────────────────────────────────────────
// Login
// ─────────────────────────────────────────────
const LoginView = {
  template: "#tpl-login",
  props: ["prefillEmail", "flash"],
  data() {
    return { email: this.prefillEmail || "", password: "", error: "", loading: false };
  },
  methods: {
    async submit() {
      this.error = "";
      this.loading = true;
      try {
        const { user } = await api.post("/api/auth/login", { email: this.email, password: this.password });
        this.$emit("login-success", user);
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
  },
};

// ─────────────────────────────────────────────
// Register
// ─────────────────────────────────────────────
const RegisterView = {
  template: "#tpl-register",
  data() {
    return { role: "student", name: "", email: "", password: "", error: "", loading: false };
  },
  methods: {
    async submit() {
      this.error = "";
      this.loading = true;
      try {
        await api.post("/api/auth/register", {
          role: this.role, name: this.name, email: this.email, password: this.password,
        });
        this.$emit("registered", this.email);
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
  },
};

// ─────────────────────────────────────────────
// Admin Dashboard
// ─────────────────────────────────────────────
const AdminDashboard = {
  template: "#tpl-admin-dashboard",
  data() {
    return {
      badgeClass,
      adminTab: "overview",
      stats: {},
      companies: [],
      drives: [],
      // Applications tab
      allApplications: [],
      appFilter: "",
      // Students tab
      allStudents: [],
      // Search tab
      searchQuery: "",
      searchResults: null,
      // Charts
      _charts: {},
    };
  },
  async mounted() {
    this.stats     = await api.get("/api/admin/dashboard");
    this.companies = await api.get("/api/admin/companies?status=pending");
    this.drives    = await api.get("/api/admin/drives?status=pending");
    // Load charts after next tick so canvas elements are rendered
    this.$nextTick(() => this.loadCharts());
  },
  methods: {
    async setCompanyStatus(id, status) {
      await api.patch(`/api/admin/companies/${id}/status`, { status });
      this.companies = this.companies.filter(c => c.id !== id);
      this.stats = await api.get("/api/admin/dashboard");
    },
    async setDriveStatus(id, status) {
      await api.patch(`/api/admin/drives/${id}/status`, { status });
      this.drives = this.drives.filter(d => d.id !== id);
    },
    async loadAllApplications() {
      this.adminTab = "applications";
      const url = this.appFilter
        ? `/api/admin/applications?status=${this.appFilter}`
        : "/api/admin/applications";
      this.allApplications = await api.get(url);
    },
    async loadStudents() {
      this.adminTab = "students";
      this.allStudents = await api.get("/api/admin/students");
    },
    async blacklistUser(userId) {
      await api.patch(`/api/admin/users/${userId}/blacklist`, {});
      this.allStudents = await api.get("/api/admin/students");
    },
    async runSearch() {
      this.searchResults = await api.get(`/api/admin/search?q=${encodeURIComponent(this.searchQuery)}`);
    },
    async loadCharts() {
      let chartData;
      try {
        chartData = await api.get("/api/admin/stats/charts");
      } catch { return; }

      const COLORS = ["#0d6efd","#ffc107","#198754","#dc3545","#6f42c1","#0dcaf0","#fd7e14","#6c757d","#20c997","#d63384"];

      const destroyAndCreate = (id, config) => {
        if (this._charts[id]) this._charts[id].destroy();
        const el = document.getElementById(id);
        if (!el) return;
        this._charts[id] = new Chart(el, config);
      };

      // Doughnut — application status breakdown
      destroyAndCreate("statusChart", {
        type: "doughnut",
        data: {
          labels: chartData.status_breakdown.labels,
          datasets: [{ data: chartData.status_breakdown.data, backgroundColor: COLORS }],
        },
        options: { plugins: { legend: { position: "bottom" } }, responsive: true },
      });

      // Doughnut — company approval status
      destroyAndCreate("companyChart", {
        type: "doughnut",
        data: {
          labels: chartData.company_breakdown.labels,
          datasets: [{ data: chartData.company_breakdown.data, backgroundColor: ["#ffc107","#198754","#dc3545"] }],
        },
        options: { plugins: { legend: { position: "bottom" } }, responsive: true },
      });

      // Horizontal bar — applications per drive
      destroyAndCreate("driveChart", {
        type: "bar",
        data: {
          labels: chartData.per_drive.labels,
          datasets: [{
            label: "Applicants",
            data: chartData.per_drive.data,
            backgroundColor: "#0d6efd",
          }],
        },
        options: {
          indexAxis: "y",
          plugins: { legend: { display: false } },
          responsive: true,
          scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } },
        },
      });
    },
  },
};

// ─────────────────────────────────────────────
// Company Dashboard
// ─────────────────────────────────────────────
const CompanyDashboard = {
  template: "#tpl-company-dashboard",
  data() {
    return {
      badgeClass,
      companyTab: "drives",
      profile: {},
      editProfile: { name: "", hr_contact: "", website: "" },
      profileError: "",
      profileMsg: "",
      drives: [],
      applicants: [],
      applicantsFor: null,
      interviewDates: {},   // { [application_id]: "YYYY-MM-DD" }
      driveError: "",
      newDrive: {
        job_title: "",
        eligibility_branch: "",
        eligibility_cgpa: null,
        eligibility_year: null,
        application_deadline: "",
      },
    };
  },
  async mounted() {
    this.profile = await api.get("/api/company/profile");
    this.drives  = await api.get("/api/company/drives");
    this.editProfile = { name: this.profile.name, hr_contact: this.profile.hr_contact || "", website: this.profile.website || "" };
  },
  methods: {
    async createDrive() {
      this.driveError = "";
      try {
        const created = await api.post("/api/company/drives", this.newDrive);
        this.drives.push(created);
        this.newDrive = { job_title: "", eligibility_branch: "", eligibility_cgpa: null, eligibility_year: null, application_deadline: "" };
      } catch (e) {
        this.driveError = e.message;
      }
    },
    async viewApplicants(driveId) {
      this.applicantsFor = driveId;
      this.applicants = await api.get(`/api/company/drives/${driveId}/applications`);
      // init interviewDates map
      this.applicants.forEach(a => {
        if (!this.interviewDates[a.id]) this.interviewDates[a.id] = "";
      });
    },
    async updateApplication(appId, status) {
      if (!status) return;
      const updated = await api.patch(`/api/company/applications/${appId}/status`, { status });
      const idx = this.applicants.findIndex(a => a.id === appId);
      if (idx !== -1) this.applicants[idx] = updated;
    },
    async scheduleInterview(appId) {
      const date = this.interviewDates[appId];
      if (!date) { alert("Please pick a date first."); return; }
      const updated = await api.patch(`/api/company/applications/${appId}/interview`, { interview_date: date });
      const idx = this.applicants.findIndex(a => a.id === appId);
      if (idx !== -1) this.applicants[idx] = updated;
    },
    async saveProfile() {
      this.profileError = "";
      this.profileMsg = "";
      try {
        const updated = await api.put("/api/company/profile", {
          name: this.editProfile.name,
          hr_contact: this.editProfile.hr_contact,
          website: this.editProfile.website,
        });
        this.profile = updated;
        this.profileMsg = "Profile updated successfully!";
      } catch (e) {
        this.profileError = e.message;
      }
    },
  },
};

// ─────────────────────────────────────────────
// Student Dashboard
// ─────────────────────────────────────────────
const StudentDashboard = {
  template: "#tpl-student-dashboard",
  data() {
    return {
      badgeClass,
      studentTab: "drives",
      drives: [],
      applications: [],
      branchFilter: "",
      applyError: "",
      // Profile tab
      profileForm: { name: "", branch: "", cgpa: null, year: null, resume_path: "" },
      profileError: "",
      profileMsg: "",
      resumeError: "",
      resumeMsg: "",
      // Export
      exportLoading: false,
      exportMsg: "",
      exportPollTimer: null,
    };
  },
  computed: {
    appliedDriveIds() {
      return new Set(this.applications.map(a => a.drive_id));
    },
    activeApplications() {
      return this.applications.filter(a => ["applied", "shortlisted"].includes(a.status));
    },
    placementHistory() {
      return this.applications.filter(a => ["selected", "rejected"].includes(a.status));
    },
  },
  async mounted() {
    this.drives       = await api.get("/api/student/drives");
    this.applications = await api.get("/api/student/applications");
  },
  methods: {
    async filterDrives() {
      const url = this.branchFilter
        ? `/api/student/drives?branch=${encodeURIComponent(this.branchFilter)}`
        : "/api/student/drives";
      this.drives = await api.get(url);
    },
    async apply(driveId) {
      this.applyError = "";
      try {
        await api.post(`/api/student/drives/${driveId}/apply`, {});
        this.applications = await api.get("/api/student/applications");
      } catch (e) {
        this.applyError = e.message;
      }
    },
    async loadProfile() {
      this.studentTab = "profile";
      const data = await api.get("/api/student/profile");
      this.profileForm = { ...data };
    },
    async saveProfile() {
      this.profileError = "";
      this.profileMsg = "";
      try {
        const updated = await api.put("/api/student/profile", {
          name: this.profileForm.name,
          branch: this.profileForm.branch,
          cgpa: this.profileForm.cgpa,
          year: this.profileForm.year,
        });
        this.profileForm = { ...updated };
        this.profileMsg = "Profile saved successfully!";
      } catch (e) {
        this.profileError = e.message;
      }
    },
    async uploadResume() {
      this.resumeError = "";
      this.resumeMsg = "";
      const file = this.$refs.resumeFile.files[0];
      if (!file) { this.resumeError = "Please select a file."; return; }
      const formData = new FormData();
      formData.append("resume", file);
      try {
        const res = await fetch("/api/student/resume", {
          method: "POST",
          credentials: "include",
          body: formData,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Upload failed");
        this.profileForm.resume_path = data.resume_path;
        this.resumeMsg = "Resume uploaded successfully!";
      } catch (e) {
        this.resumeError = e.message;
      }
    },
    async exportCsv() {
      this.exportLoading = true;
      this.exportMsg = "";
      try {
        const { task_id } = await api.post("/api/student/applications/export", {});
        this.exportMsg = "Export started — checking status...";
        this._pollExport(task_id);
      } catch (e) {
        this.exportMsg = "Export failed: " + e.message;
        this.exportLoading = false;
      }
    },
    _pollExport(taskId) {
      this.exportPollTimer = setInterval(async () => {
        try {
          const result = await api.get(`/api/student/tasks/${taskId}`);
          if (result.ready) {
            clearInterval(this.exportPollTimer);
            this.exportLoading = false;
            this.exportMsg = `Export ready! File: ${result.result?.file || 'done'}. Check your email for the download link.`;
          }
        } catch {
          clearInterval(this.exportPollTimer);
          this.exportLoading = false;
          this.exportMsg = "Could not check export status.";
        }
      }, 2000);
    },
  },
  beforeUnmount() {
    if (this.exportPollTimer) clearInterval(this.exportPollTimer);
  },
};

// ─────────────────────────────────────────────
// Root App
// ─────────────────────────────────────────────
createApp({
  components: {
    "login-view":        LoginView,
    "register-view":     RegisterView,
    "admin-dashboard":   AdminDashboard,
    "company-dashboard": CompanyDashboard,
    "student-dashboard": StudentDashboard,
  },
  data() {
    return { user: null, currentView: "login-view", prefillEmail: "", flashMessage: "" };
  },
  async created() {
    const { user } = await api.get("/api/auth/me");
    if (user) this.onLogin(user);
  },
  methods: {
    onLogin(user) {
      this.user = user;
      this.currentView = `${user.role}-dashboard`;
    },
    onRegistered(email) {
      this.prefillEmail = email;
      this.flashMessage = "Account created! Please log in.";
      this.currentView = "login-view";
    },
    async logout() {
      await api.post("/api/auth/logout", {});
      this.user = null;
      this.prefillEmail = "";
      this.flashMessage = "";
      this.currentView = "login-view";
    },
  },
}).mount("#app");
