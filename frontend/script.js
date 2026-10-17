(() => {
  "use strict";

  const ACTIVE_REPOSITORY_KEY = "skillpath-ai.active-repository";
  const REFRESH_INTERVAL_MS = 15_000;

  const state = {
    job: null,
    savedJobs: [],
    repository: null,
    snapshot: null,
    history: [],
    monitor: null,
    events: [],
    telegram: null,
    telegramPairing: null,
    serverTelegram: null,
    serverJobSearch: null,
    jobSearchResults: [],
    activeView: "setup",
    roleCategory: "all",
    skillFilterStatus: "all",
    skillFilterSearch: "",
    selectedSkillKey: null,
    selectedEvidenceIndex: 0,
    validatedRepoMeta: null,
    lastComparison: null,
    compareTableSearch: "",
    compareTableFilter: "all",
    refreshTimer: null,
    refreshBusy: false,
  };

  const byId = (id) => document.getElementById(id);
  const elements = {
    backendOfflineBanner: byId("backend-offline-banner"),
    connectionStatus: byId("connection-status"),
    brandHomeLink: byId("brand-home-link"),
    navTabSetup: byId("nav-tab-setup"),
    navTabResult: byId("nav-tab-result"),
    navTabCompare: byId("nav-tab-compare"),
    navResultBadge: byId("nav-result-badge"),
    navCompareBadge: byId("nav-compare-badge"),
    viewSetup: byId("view-setup"),
    viewResult: byId("view-result"),
    viewCompare: byId("view-compare"),
    stepperStep1: byId("stepper-step-1"),
    stepperStep2: byId("stepper-step-2"),
    stepperStep3: byId("stepper-step-3"),
    roleCategoryPills: byId("role-category-pills"),
    jobCardsList: byId("job-cards-list"),
    toggleCustomJobButton: byId("toggle-custom-job-button"),
    customJobDrawer: byId("custom-job-drawer"),
    closeCustomJobButton: byId("close-custom-job-button"),
    newJobModeButton: byId("new-job-mode-button"),
    fetchJobUrlButton: byId("fetch-job-url-button"),
    updateJobButton: byId("update-job-button"),
    setupJobBadge: byId("setup-job-badge"),
    setupJobTitle: byId("setup-job-title"),
    setupJobCompany: byId("setup-job-company"),
    setupJobTags: byId("setup-job-tags"),
    setupReqCount: byId("setup-req-count"),
    setupKeyReqsList: byId("setup-key-reqs-list"),
    setupRepoName: byId("setup-repo-name"),
    setupRepoDesc: byId("setup-repo-desc"),
    validateRepoButton: byId("validate-repo-button"),
    reviewSelectedJobTitle: byId("review-selected-job-title"),
    reviewSelectedJobMeta: byId("review-selected-job-meta"),
    reviewSelectedRepoName: byId("review-selected-repo-name"),
    reviewSelectedRepoMeta: byId("review-selected-repo-meta"),
    resultLastAnalyzedTime: byId("result-last-analyzed-time"),
    resultLastAnalyzedCommit: byId("result-last-analyzed-commit"),
    reanalyzeButton: byId("reanalyze-button"),
    fitGaugeCircle: byId("fit-gauge-circle"),
    kpiCardDemonstrated: byId("kpi-card-demonstrated"),
    kpiCardPartial: byId("kpi-card-partial"),
    kpiCardMissing: byId("kpi-card-missing"),
    kpiCardTotal: byId("kpi-card-total"),
    kpiDemonstratedCount: byId("kpi-demonstrated-count"),
    kpiPartialCount: byId("kpi-partial-count"),
    kpiMissingCount: byId("kpi-missing-count"),
    kpiTotalCount: byId("kpi-total-count"),
    skillFilterSearch: byId("skill-filter-search"),
    skillFilterStatus: byId("skill-filter-status"),
    inspectorSkillTitle: byId("inspector-skill-title"),
    inspectorSkillStatus: byId("inspector-skill-status"),
    inspectorFileTabs: byId("inspector-file-tabs"),
    inspectorFilePath: byId("inspector-file-path"),
    inspectorLineRange: byId("inspector-line-range"),
    inspectorCodeExcerpt: byId("inspector-code-excerpt"),
    inspectorWhyText: byId("inspector-why-text"),
    inspectorClaimBoundary: byId("inspector-claim-boundary"),
    inspectorLimitsList: byId("inspector-limits-list"),
    toggleMonitorButton: byId("toggle-monitor-button"),
    inspectedFilesSummary: byId("inspected-files-summary"),
    llmModeBadge: byId("llm-mode-badge"),
    toggleScopeDrawerButton: byId("toggle-scope-drawer-button"),
    scopeFilesDrawer: byId("scope-files-drawer"),
    scopeDrawerSummaryTitle: byId("scope-drawer-summary-title"),
    scopeInspectedList: byId("scope-inspected-list"),
    scopeSkippedList: byId("scope-skipped-list"),
    compareRepoName: byId("compare-repo-name"),
    compareRepoBadges: byId("compare-repo-badges"),
    compareDeltaBadge: byId("compare-delta-badge"),
    compareJobTitle: byId("compare-job-title"),
    compareJobCompany: byId("compare-job-company"),
    compareSnapshotSelect: byId("compare-snapshot-select"),
    compareBeforeSub: byId("compare-before-sub"),
    compareBeforeScore: byId("compare-before-score"),
    compareBeforeBars: byId("compare-before-bars"),
    compareAfterSub: byId("compare-after-sub"),
    compareAfterScore: byId("compare-after-score"),
    compareAfterBars: byId("compare-after-bars"),
    distSegDemo: byId("dist-seg-demo"),
    distSegPart: byId("dist-seg-part"),
    distSegMiss: byId("dist-seg-miss"),
    distLabelDemo: byId("dist-label-demo"),
    distLabelPart: byId("dist-label-part"),
    distLabelMiss: byId("dist-label-miss"),
    compareTopGaps: byId("compare-top-gaps"),
    compareStrengths: byId("compare-strengths"),
    compareTableSearch: byId("compare-table-search"),
    compareTableFilter: byId("compare-table-filter"),
    compareTableBody: byId("compare-table-body"),
    savedJobsSelect: byId("saved-jobs-select"),
    deleteJobButton: byId("delete-job-button"),
    jobForm: byId("job-form"),
    jobTitle: byId("job-title"),
    jobCompany: byId("job-company"),
    jobCity: byId("job-city"),
    jobSourceUrl: byId("job-source-url"),
    jobDescription: byId("job-description"),
    saveJobButton: byId("save-job-button"),
    jobFeedback: byId("job-form-feedback"),
    jobDiscovery: byId("job-discovery"),
    quickLiveJobsButton: byId("quick-live-jobs-button"),
    jobSearchForm: byId("job-search-form"),
    jobSearchQuery: byId("job-search-query"),
    jobSearchLocation: byId("job-search-location"),
    jobSearchCountry: byId("job-search-country"),
    searchJobsButton: byId("search-jobs-button"),
    jobSearchFeedback: byId("job-search-feedback"),
    jobSearchResults: byId("job-search-results"),
    savedReposBar: byId("saved-repos-bar"),
    savedReposSelect: byId("saved-repos-select"),
    deleteRepoButton: byId("delete-repo-button"),
    browseReposButton: byId("browse-repos-button"),
    repositoryForm: byId("repository-form"),
    repositoryUrl: byId("repository-url"),
    connectRepositoryButton: byId("connect-repository-button"),
    disconnectRepositoryButton: byId("disconnect-repository-button"),
    repositoryHelp: byId("repository-help"),
    repositoryFeedback: byId("repository-form-feedback"),
    userReposDrawer: byId("user-repos-drawer"),
    userReposTitle: byId("user-repos-title"),
    closeUserReposButton: byId("close-user-repos-button"),
    userReposList: byId("user-repos-list"),
    scopeNotice: byId("scope-notice"),
    contextLinks: byId("context-links"),
    fitScore: byId("fit-score"),
    fitTitle: byId("fit-title"),
    fitDescription: byId("fit-description"),
    fitFormula: byId("fit-formula"),
    assessmentState: byId("assessment-state"),
    repositoryState: byId("repository-state"),
    repositoryFacts: byId("repository-facts"),
    monitorState: byId("monitor-state"),
    monitorFacts: byId("monitor-facts"),
    checkMonitorButton: byId("check-monitor-button"),
    reassessmentHeading: byId("reassessment-heading"),
    reassessmentMessage: byId("reassessment-message"),
    reassessmentMeta: byId("reassessment-meta"),
    eventIcon: byId("event-icon"),
    viewComparisonButton: byId("view-comparison-button"),
    telegramState: byId("telegram-state"),
    telegramDescription: byId("telegram-description"),
    telegramPairing: byId("telegram-pairing"),
    telegramPairButton: byId("telegram-pair-button"),
    skillsGrid: byId("skills-grid"),
    skillsNote: byId("skills-note"),
    historyList: byId("history-list"),
    refreshHistoryButton: byId("refresh-history-button"),
    guidanceList: byId("guidance-list"),
    comparisonPanel: byId("comparison-panel"),
    comparisonMeta: byId("comparison-meta"),
    comparisonGrid: byId("comparison-grid"),
    closeComparisonButton: byId("close-comparison-button"),
    toastRegion: byId("toast-region"),
  };

  function text(value, fallback = "—") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value);
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function make(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined && value !== null) node.textContent = String(value);
    return node;
  }

  function safeHref(value) {
    try {
      const parsed = new URL(value, window.location.origin);
      return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : null;
    } catch (_) {
      return null;
    }
  }

  function externalLink(label, url, className = "repo-link") {
    const href = safeHref(url);
    if (!href) return make("span", className, label);
    const link = make("a", className, label);
    link.href = href;
    link.target = "_blank";
    link.rel = "noreferrer noopener";
    link.title = label;
    return link;
  }

  function shortSha(sha) {
    return typeof sha === "string" && sha ? sha.slice(0, 12) : "—";
  }

  function formatDate(value) {
    if (!value) return "Not reported";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  }

  function statusClass(statusCode, statusText) {
    const code = String(statusCode || statusText || "").toLowerCase();
    if (code.includes("awaiting")) return "awaiting";
    if (code.includes("partial")) return "partial";
    if (code.includes("not_demonstrated") || code.includes("not demonstrated")) return "not-demonstrated";
    if (code.includes("demonstrated")) return "demonstrated";
    return "unknown";
  }

  function setTone(element, tone, label) {
    element.dataset.tone = tone;
    element.textContent = label;
  }

  function setConnection(tone, label) {
    clear(elements.connectionStatus);
    const dot = make("span", `status-dot status-dot--${tone === "ready" ? "ready" : tone === "error" ? "error" : tone === "working" ? "working" : "idle"}`);
    dot.setAttribute("aria-hidden", "true");
    elements.connectionStatus.append(dot, make("span", "", label));
  }

  function setFeedback(element, message, type = "") {
    element.textContent = message || "";
    if (type) element.dataset.state = type;
    else delete element.dataset.state;
  }

  function setButtonLoading(button, loading, loadingText) {
    if (!button) return;
    const hasPrimaryLabel = button.classList.contains("button");
    const label = hasPrimaryLabel ? button.querySelector(":scope > span:first-child") : null;
    if (loading) {
      button.dataset.originalLabel = label?.textContent || button.textContent;
      button.disabled = true;
      button.classList.add("is-loading");
      if (label && loadingText) label.textContent = loadingText;
    } else {
      button.classList.remove("is-loading");
      if (label && button.dataset.originalLabel) label.textContent = button.dataset.originalLabel;
      button.disabled = false;
    }
  }

  function toast(message, type = "") {
    const item = make("div", `toast${type ? ` toast--${type}` : ""}`, message);
    elements.toastRegion.appendChild(item);
    window.setTimeout(() => item.remove(), 6000);
  }

  async function api(path, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    const requestOptions = { ...options, headers };
    if (options.body && typeof options.body !== "string") {
      headers["Content-Type"] = "application/json";
      requestOptions.body = JSON.stringify(options.body);
    }
    let response;
    try {
      response = await fetch(path, requestOptions);
    } catch (_) {
      const error = new Error("The local server could not be reached. Start the backend and try again.");
      error.code = "network_error";
      throw error;
    }
    let payload = null;
    try {
      payload = await response.json();
    } catch (_) {
      // A non-JSON error still becomes a safe, user-readable error below.
    }
    if (!response.ok) {
      const error = new Error(payload?.error?.message || `Request failed (${response.status}).`);
      error.code = payload?.error?.code || "request_failed";
      error.details = payload?.error?.details;
      throw error;
    }
    return payload;
  }

  function factRow(label, valueNode) {
    const row = document.createElement("div");
    row.append(make("dt", "", label));
    const detail = make("dd");
    if (valueNode instanceof Node) detail.append(valueNode);
    else detail.textContent = text(valueNode);
    row.append(detail);
    return row;
  }

  function renderContext() {
    clear(elements.contextLinks);
    if (!state.job || !state.repository) {
      elements.contextLinks.append(make("span", "context-empty", "No connected assessment yet"));
      return;
    }
    const isLocalBenchmark = !state.job.source_url || state.job.source_url.includes("skillpath.local");
    const jobLabel = state.job.company && state.job.company !== "Company not specified" ? `${state.job.company} benchmark` : `${state.job.title} benchmark`;
    const jobNode = isLocalBenchmark
      ? make("span", "context-link", jobLabel)
      : externalLink(`${state.job.company} job source`, state.job.source_url, "context-link");
    const repoLink = externalLink(`${state.repository.owner}/${state.repository.name}`, state.repository.repository_url, "context-link");
    elements.contextLinks.append(jobNode, repoLink);
  }

  function switchView(viewName) {
    const valid = ["setup", "result", "compare"].includes(viewName) ? viewName : "setup";
    state.activeView = valid;
    const views = [
      ["setup", elements.viewSetup, elements.navTabSetup],
      ["result", elements.viewResult, elements.navTabResult],
      ["compare", elements.viewCompare, elements.navTabCompare],
    ];
    views.forEach(([key, sec, tab]) => {
      if (sec) sec.classList.toggle("is-active", key === valid);
      if (tab) tab.classList.toggle("is-active", key === valid);
    });
    if (valid === "compare" && state.history.length >= 2 && !state.lastComparison) {
      showComparison(state.history[0].id, state.history[1].id, { stayInView: true });
    } else if (valid === "compare") {
      renderCompareDashboard();
    }
  }

  function matchesCategory(item, cat) {
    if (!cat || cat === "all") return true;
    const hay = `${item.title || ""} ${item.company || ""} ${item.description || ""} ${(item.skills || []).map((s) => s.name || s.skill || "").join(" ")}`.toLowerCase();
    if (cat === "internship") return hay.includes("intern") || (item.employment_type || "").toLowerCase().includes("intern");
    if (cat === "backend") return /backend|fastapi|flask|sql|api|python|server|java|c\+\+/.test(hay);
    if (cat === "frontend") return /frontend|react|html|css|ui|javascript|typescript|full-stack|full stack/.test(hay);
    if (cat === "ai") return /ai|ml|machine learning|rag|llm|generative|embeddings/.test(hay);
    if (cat === "data") return /data|sql|analytics|pipeline|ml|embeddings/.test(hay);
    if (cat === "software") return /software|engineer|developer|systems|full-stack|backend/.test(hay);
    return true;
  }

  function renderSetupWorkspace() {
    // 1. Update Stepper states
    const hasJob = Boolean(state.job?.id);
    const hasRepo = Boolean(state.repository?.id || state.validatedRepoMeta);
    if (elements.stepperStep1) {
      elements.stepperStep1.classList.toggle("is-done", hasJob);
      elements.stepperStep1.classList.toggle("is-active", !hasJob);
    }
    if (elements.stepperStep2) {
      elements.stepperStep2.classList.toggle("is-done", hasRepo);
      elements.stepperStep2.classList.toggle("is-active", hasJob && !hasRepo);
    }
    if (elements.stepperStep3) {
      elements.stepperStep3.classList.toggle("is-done", Boolean(state.snapshot));
      elements.stepperStep3.classList.toggle("is-active", hasJob && hasRepo);
    }

    // 2. Render Job Cards List (Saved jobs + live search results)
    if (elements.jobCardsList) {
      clear(elements.jobCardsList);
      const searchQ = (elements.jobSearchQuery?.value || "").trim().toLowerCase();
      const combined = [];
      (state.savedJobs || []).forEach((j) => {
        combined.push({ kind: "saved", data: j });
      });
      (state.jobSearchResults || []).forEach((r, idx) => {
        combined.push({ kind: "live", data: r, liveIndex: idx });
      });

      const filtered = combined.filter(({ data }) => {
        if (!matchesCategory(data, state.roleCategory)) return false;
        if (!searchQ) return true;
        const textBlob = `${data.title || ""} ${data.company || ""} ${data.description || ""}`.toLowerCase();
        return textBlob.includes(searchQ);
      });

      if (!filtered.length) {
        elements.jobCardsList.append(
          make("div", "history-empty", "No matching roles in this category. Try 'All Roles', click 'Search Live', or add a custom role.")
        );
      } else {
        filtered.forEach(({ kind, data, liveIndex }) => {
          const isSelected = kind === "saved" && state.job?.id && String(state.job.id) === String(data.id);
          const card = make("article", `job-card${isSelected ? " is-selected" : ""}`);
          const left = document.createElement("div");
          const top = make("div", "job-card__top");
          top.append(make("h3", "job-card__title", text(data.title, "Untitled Role")));
          const comp = data.company && data.company !== "Company not specified" ? data.company : "Benchmark Role";
          top.append(make("span", "job-card__company", comp));
          left.append(top);

          const meta = make("div", "job-card__meta");
          if (data.location || data.city) meta.append(make("span", "", `📍 ${data.location || data.city}`));
          const isLocal = !data.source_url || String(data.source_url).includes("skillpath.local");
          meta.append(make("span", "", kind === "live" ? `⚡ Live (${data.provider || "Search"})` : isLocal ? "📋 Role Benchmark" : "🔗 Verified URL"));
          left.append(meta);

          if (data.description) {
            left.append(make("p", "job-card__desc", data.description));
          }

          const tagsWrap = make("div", "job-card__tags");
          const skillsArr = Array.isArray(data.skills) ? data.skills : [];
          skillsArr.slice(0, 6).forEach((s) => {
            tagsWrap.append(make("span", "skill-tag-chip", text(s.name || s.skill, "Skill")));
          });
          if (skillsArr.length > 6) {
            tagsWrap.append(make("span", "skill-tag-chip", `+${skillsArr.length - 6} more`));
          }
          left.append(tagsWrap);
          card.append(left);

          const rightBtn = make(
            "button",
            `button ${isSelected ? "button--primary" : "button--quiet"} button--sm`,
            isSelected ? "Selected ✓" : kind === "live" ? "Use Posting" : "Select Role"
          );
          rightBtn.type = "button";
          card.addEventListener("click", async () => {
            if (kind === "live") {
              await useJobSearchResult(liveIndex, { autoSave: true });
            } else if (elements.savedJobsSelect) {
              elements.savedJobsSelect.value = String(data.id);
              await onSavedJobSelectChange();
            }
          });
          card.append(rightBtn);
          elements.jobCardsList.append(card);
        });
      }
    }

    // 3. Selected Job Details Panel & Key Requirements
    if (elements.setupJobTitle) {
      if (state.job) {
        setTone(elements.setupJobBadge, "ready", "Selected");
        elements.setupJobTitle.textContent = text(state.job.title, "Selected Role");
        const compText = state.job.company && state.job.company !== "Company not specified" ? state.job.company : "SkillPath Benchmark";
        elements.setupJobCompany.textContent = compText;
        if (elements.setupJobTags) {
          clear(elements.setupJobTags);
          const isSynthetic = !state.job.source_url || state.job.source_url.includes("skillpath.local");
          elements.setupJobTags.append(
            make("span", "meta-pill", isSynthetic ? "Synthetic Benchmark" : "Public Job URL")
          );
          if (!isSynthetic && state.job.source_url) {
            elements.setupJobTags.append(externalLink("Source Link ↗", state.job.source_url, "meta-pill"));
          }
        }
        const reqs = Array.isArray(state.job.skills) ? state.job.skills : [];
        if (elements.setupReqCount) elements.setupReqCount.textContent = String(reqs.length);
        if (elements.setupKeyReqsList) {
          clear(elements.setupKeyReqsList);
          if (!reqs.length) {
            elements.setupKeyReqsList.append(make("li", "reqs-empty", "No supported skills extracted yet."));
          } else {
            reqs.forEach((r) => {
              const li = document.createElement("li");
              li.append(make("span", "", text(r.name || r.skill, "Requirement")));
              li.append(make("span", "meta-pill", text(r.requirement_type, "required")));
              elements.setupKeyReqsList.append(li);
            });
          }
        }
      } else {
        setTone(elements.setupJobBadge, "", "Awaiting selection");
        elements.setupJobTitle.textContent = "Select a Job Opportunity";
        elements.setupJobCompany.textContent = "Choose a role from the cards or paste a real job posting.";
        if (elements.setupJobTags) clear(elements.setupJobTags);
        if (elements.setupReqCount) elements.setupReqCount.textContent = "0";
        if (elements.setupKeyReqsList) {
          clear(elements.setupKeyReqsList);
          elements.setupKeyReqsList.append(make("li", "reqs-empty", "Select a job card to preview extracted requirements."));
        }
      }
    }

    // 4. Review & Start Analysis Bar + Update Job button visibility
    if (elements.updateJobButton) {
      elements.updateJobButton.hidden = !state.job?.id;
    }
    if (elements.reviewSelectedJobTitle) {
      elements.reviewSelectedJobTitle.textContent = state.job ? state.job.title : "Auto-select latest / benchmark role";
      elements.reviewSelectedJobMeta.textContent = state.job
        ? `${state.job.company || "Company"} · ${(state.job.skills || []).length} requirements`
        : "Or select a specific job card above";
    }
    const repoMeta = state.repository || state.validatedRepoMeta;
    if (elements.reviewSelectedRepoName) {
      elements.reviewSelectedRepoName.textContent = repoMeta
        ? `${repoMeta.owner}/${repoMeta.name}`
        : elements.repositoryUrl?.value.trim() || "No repository linked";
      elements.reviewSelectedRepoMeta.textContent = repoMeta
        ? `Branch: ${repoMeta.default_branch || "main"} · ${shortSha(repoMeta.latest_known_sha || repoMeta.commit_sha)}`
        : "Enter a GitHub URL above";
    }
    if (elements.setupRepoName) {
      if (repoMeta) {
        elements.setupRepoName.textContent = `${repoMeta.owner}/${repoMeta.name}`;
        const insp = state.snapshot?.inspection || {};
        const descParts = [
          repoMeta.visibility || insp.visibility || "public",
          repoMeta.language || insp.language || "",
          typeof (repoMeta.stars ?? insp.stars) === "number" ? `★ ${repoMeta.stars ?? insp.stars}` : "",
        ].filter(Boolean);
        elements.setupRepoDesc.textContent = descParts.join(" · ") || "Validated GitHub repository";
      } else {
        elements.setupRepoName.textContent = "No repository validated";
        elements.setupRepoDesc.textContent = "Enter a GitHub URL and click 'Validate Repository' or 'Start Analysis'.";
      }
    }
  }

  function renderRepositoryFacts() {
    clear(elements.repositoryFacts);
    if (!state.repository) {
      elements.repositoryFacts.append(
        factRow("Repository", "—"),
        factRow("Branch", "—"),
        factRow("Commit", "—")
      );
      setTone(elements.repositoryState, "", "Not connected");
      return;
    }
    const repositoryName = `${state.repository.owner}/${state.repository.name}`;
    const commit = state.repository.latest_commit_url
      ? externalLink(shortSha(state.repository.latest_known_sha), state.repository.latest_commit_url, "evidence-file")
      : shortSha(state.repository.latest_known_sha);
    elements.repositoryFacts.append(
      factRow("Repository", externalLink(repositoryName, state.repository.repository_url, "evidence-file")),
      factRow("Branch", state.repository.default_branch),
      factRow("Commit", commit)
    );
    setTone(elements.repositoryState, "ready", "Connected");
  }

  function renderFit() {
    const assessment = state.snapshot?.assessment;
    const score = assessment?.fit_score;
    const summary = assessment?.summary || {};
    const circumference = 314.16;

    if (elements.reanalyzeButton) {
      elements.reanalyzeButton.disabled = !state.repository?.id;
    }
    if (elements.resultLastAnalyzedTime) {
      elements.resultLastAnalyzedTime.textContent = state.snapshot?.assessed_at
        ? formatDate(state.snapshot.assessed_at)
        : "Not yet analyzed";
    }
    if (elements.resultLastAnalyzedCommit) {
      elements.resultLastAnalyzedCommit.textContent = state.snapshot?.commit_sha
        ? `Commit: ${shortSha(state.snapshot.commit_sha)}`
        : "Commit: —";
    }

    if (!assessment) {
      elements.fitScore.textContent = "—";
      if (elements.fitGaugeCircle) {
        elements.fitGaugeCircle.style.strokeDashoffset = String(circumference);
      }
      if (elements.navResultBadge) elements.navResultBadge.hidden = true;
      const reqCount = state.job?.skills?.length || 0;
      if (elements.kpiDemonstratedCount) elements.kpiDemonstratedCount.textContent = "0";
      if (elements.kpiPartialCount) elements.kpiPartialCount.textContent = "0";
      if (elements.kpiMissingCount) elements.kpiMissingCount.textContent = "0";
      if (elements.kpiTotalCount) elements.kpiTotalCount.textContent = String(reqCount);

      if (reqCount) {
        elements.fitTitle.textContent = `${reqCount} requirements established`;
        elements.fitDescription.textContent = `Job benchmark ready. Connect or assess a repository to inspect code evidence and calculate your fit score.`;
        elements.fitFormula.textContent = "Score will calculate automatically as soon as repository code is inspected.";
        setTone(elements.assessmentState, "working", "Awaiting repository code");
      } else {
        elements.fitTitle.textContent = "No score received";
        elements.fitDescription.textContent = "A score is shown only when the assessment API returns its calculation or summary.";
        elements.fitFormula.textContent = "No calculation has been reported.";
        setTone(elements.assessmentState, "", "Awaiting assessment");
      }
      return;
    }

    const numericScore = Number.isFinite(score?.value) ? score.value : null;
    elements.fitScore.textContent = numericScore !== null ? `${numericScore}%` : "—";
    if (elements.fitGaugeCircle) {
      const pct = numericScore !== null ? Math.max(0, Math.min(100, numericScore)) : 0;
      elements.fitGaugeCircle.style.strokeDashoffset = String(circumference * (1 - pct / 100));
    }
    if (elements.navResultBadge) {
      elements.navResultBadge.hidden = numericScore === null;
      elements.navResultBadge.textContent = numericScore !== null ? `${numericScore}%` : "—";
    }
    const demoCount = summary.demonstrated || 0;
    const partCount = summary.partially_demonstrated || 0;
    const missCount = summary.not_demonstrated || 0;
    const totalCount = summary.all_supported_skills ?? (demoCount + partCount + missCount);
    if (elements.kpiDemonstratedCount) elements.kpiDemonstratedCount.textContent = String(demoCount);
    if (elements.kpiPartialCount) elements.kpiPartialCount.textContent = String(partCount);
    if (elements.kpiMissingCount) elements.kpiMissingCount.textContent = String(missCount);
    if (elements.kpiTotalCount) elements.kpiTotalCount.textContent = String(totalCount);

    elements.fitTitle.textContent = numericScore !== null ? "Traceable evidence fit" : "No supported score";
    elements.fitDescription.textContent = `${demoCount} demonstrated, ${partCount} partial, and ${missCount} not demonstrated in this inspected scope.`;
    elements.fitFormula.textContent = score?.formula || "The backend did not return a score calculation.";
    setTone(elements.assessmentState, "ready", "Evidence assessed");
  }

  function renderEvidenceInspector(item) {
    if (!elements.inspectorSkillTitle) return;
    if (!item) {
      elements.inspectorSkillTitle.textContent = "Select a skill card";
      elements.inspectorSkillStatus.className = "status-chip status-chip--unknown";
      elements.inspectorSkillStatus.textContent = "Awaiting selection";
      if (elements.inspectorFileTabs) clear(elements.inspectorFileTabs);
      if (elements.inspectorFilePath) elements.inspectorFilePath.textContent = "No file selected";
      if (elements.inspectorLineRange) elements.inspectorLineRange.textContent = "L—";
      if (elements.inspectorCodeExcerpt) {
        elements.inspectorCodeExcerpt.textContent =
          "Click any skill card on the left ('View Evidence') to inspect the exact repository file, 1-indexed line numbers, and source code excerpt.";
      }
      if (elements.inspectorWhyText) {
        elements.inspectorWhyText.textContent =
          "Every demonstrated or partial signal is verified against actual inspected repository lines. Comments and docstrings are ignored.";
      }
      if (elements.inspectorClaimBoundary) elements.inspectorClaimBoundary.textContent = "";
      if (elements.inspectorLimitsList) clear(elements.inspectorLimitsList);
      return;
    }

    const sc = statusClass(item.status_code, item.status);
    elements.inspectorSkillTitle.textContent = text(item.skill, "Skill");
    elements.inspectorSkillStatus.className = `status-chip status-chip--${sc}`;
    elements.inspectorSkillStatus.textContent = text(item.status, "Unreported");

    const evidence = Array.isArray(item.evidence) ? item.evidence : [];
    if (elements.inspectorFileTabs) {
      clear(elements.inspectorFileTabs);
      evidence.forEach((ev, idx) => {
        const tab = make(
          "button",
          `inspector-file-tab${idx === state.selectedEvidenceIndex ? " is-active" : ""}`,
          `${ev.path || "file"}:${ev.start_line || 1}`
        );
        tab.type = "button";
        tab.addEventListener("click", () => {
          state.selectedEvidenceIndex = idx;
          renderEvidenceInspector(item);
        });
        elements.inspectorFileTabs.append(tab);
      });
    }

    const activeEv = evidence[state.selectedEvidenceIndex] || evidence[0] || null;
    if (activeEv) {
      if (elements.inspectorFilePath) {
        clear(elements.inspectorFilePath);
        const linkOrSpan = activeEv.url
          ? externalLink(`📄 ${activeEv.path}`, activeEv.url, "evidence-file")
          : make("span", "evidence-file", `📄 ${activeEv.path}`);
        elements.inspectorFilePath.replaceWith(linkOrSpan);
        linkOrSpan.id = "inspector-file-path";
        elements.inspectorFilePath = linkOrSpan;
      }
      if (elements.inspectorLineRange) {
        elements.inspectorLineRange.textContent = `L${text(activeEv.start_line, "?")}-${text(activeEv.end_line, "?")}${activeEv.kind ? ` · ${activeEv.kind}` : ""}`;
      }
      if (elements.inspectorCodeExcerpt) {
        elements.inspectorCodeExcerpt.textContent = text(activeEv.excerpt, "No code excerpt returned.");
      }
    } else {
      if (elements.inspectorFilePath) {
        elements.inspectorFilePath.textContent = "0 validated files in inspected scope";
      }
      if (elements.inspectorLineRange) {
        elements.inspectorLineRange.textContent = "Scope Notice";
      }
      if (elements.inspectorCodeExcerpt) {
        const nextTask = item.next_evidence_contract?.task
          ? `\n\nSuggested Next Proof Task:\n→ ${item.next_evidence_contract.task}`
          : "";
        elements.inspectorCodeExcerpt.textContent = `No validated source code excerpt for ${item.skill} was found in the inspected files at this commit.${nextTask}`;
      }
    }

    if (elements.inspectorWhyText) {
      const llmNote = item.llm_interpretation ? ` AI summary: ${item.llm_interpretation}` : "";
      elements.inspectorWhyText.textContent = `${item.explanation || ""}${llmNote}`;
    }
    if (elements.inspectorClaimBoundary) {
      elements.inspectorClaimBoundary.textContent = item.claim_boundary || "";
    }
    if (elements.inspectorLimitsList) {
      clear(elements.inspectorLimitsList);
      (Array.isArray(item.limitations) ? item.limitations : []).forEach((lim) => {
        elements.inspectorLimitsList.append(make("li", "", lim));
      });
    }
  }

  function renderSkillCard(item) {
    const skillName = item.skill || item.name || "Unnamed requirement";
    const skillKey = item.skill_key || item.key || skillName;
    const sc = statusClass(item.status_code, item.status);
    const isSelected = state.selectedSkillKey === skillKey;
    const card = make("article", `skill-card skill-card--${sc}${isSelected ? " is-selected" : ""}`);
    const header = make("div", "skill-card-header");
    header.append(make("h3", "", text(skillName, "Unnamed requirement")));
    const icon = sc === "demonstrated" ? "✓ " : sc === "partial" ? "◐ " : sc === "awaiting" ? "⏳ " : "○ ";
    header.append(make("span", `status-chip status-chip--${sc}`, `${icon}${text(item.status, "Unreported")}`));
    card.append(header);

    card.append(make("p", "skill-summary", item.explanation || "No explanation was returned for this requirement."));

    const reqBox = make("div", "skill-req-box");
    const requirement = item.job_requirement;
    if (requirement?.source_excerpt) {
      const targetPill = make("div", "skill-pill skill-pill--target");
      targetPill.append(make("strong", "", "Target: "));
      targetPill.append(document.createTextNode(requirement.source_excerpt));
      reqBox.append(targetPill);
    }
    if (item.llm_interpretation) {
      const insightPill = make("div", "skill-pill skill-pill--insight");
      insightPill.append(make("strong", "", "AI Insight: "));
      insightPill.append(document.createTextNode(item.llm_interpretation));
      reqBox.append(insightPill);
    }
    card.append(reqBox);

    const evidence = Array.isArray(item.evidence) ? item.evidence : [];
    const uniqueFiles = new Set(evidence.map((e) => e.path).filter(Boolean));
    const footer = make("div", "skill-card-footer");
    const fileLabel = uniqueFiles.size
      ? `📄 ${uniqueFiles.size} file${uniqueFiles.size === 1 ? "" : "s"}${item.changed_evidence?.length ? " · ⚡ modified" : ""}`
      : item.status_code === "awaiting"
      ? "⏳ Pending scan"
      : "0 files in scope";
    footer.append(make("span", "skill-file-count", fileLabel));
    const viewBtn = make("button", "view-evidence-btn", "View Evidence →");
    viewBtn.type = "button";
    footer.append(viewBtn);
    card.append(footer);

    card.addEventListener("click", () => {
      state.selectedSkillKey = skillKey;
      state.selectedEvidenceIndex = 0;
      document.querySelectorAll(".skill-card").forEach((el) => el.classList.remove("is-selected"));
      card.classList.add("is-selected");
      renderEvidenceInspector({ ...item, skill: skillName, skill_key: skillKey });
    });

    return card;
  }

  function renderSkills() {
    clear(elements.skillsGrid);
    const rawItems = state.snapshot?.assessment?.skill_assessments;
    const filterStatus = state.skillFilterStatus || "all";
    const filterQuery = (state.skillFilterSearch || "").trim().toLowerCase();

    if (Array.isArray(rawItems) && rawItems.length) {
      const filtered = rawItems.filter((item) => {
        if (filterStatus !== "all" && item.status_code !== filterStatus) return false;
        if (!filterQuery) return true;
        const hay = `${item.skill || ""} ${item.explanation || ""} ${item.job_requirement?.source_excerpt || ""}`.toLowerCase();
        return hay.includes(filterQuery);
      });

      if (!state.selectedSkillKey || !rawItems.some((i) => i.skill_key === state.selectedSkillKey)) {
        const firstWithEv = rawItems.find((i) => i.evidence?.length) || rawItems[0];
        state.selectedSkillKey = firstWithEv?.skill_key || null;
        state.selectedEvidenceIndex = 0;
      }

      if (!filtered.length) {
        elements.skillsGrid.append(make("div", "history-empty", "No skills match the active status or search filter."));
      } else {
        filtered.forEach((item) => elements.skillsGrid.append(renderSkillCard(item)));
      }
      const selectedObj = rawItems.find((i) => i.skill_key === state.selectedSkillKey) || rawItems[0];
      renderEvidenceInspector(selectedObj);

      const limits = state.snapshot?.assessment?.inspection_limits || {};
      elements.skillsNote.textContent = `${text(limits.inspected_file_count, "0")} files inspected (${text(limits.skipped_file_count, "0")} skipped); every citation is verified against inspected content.`;
      if (elements.inspectedFilesSummary) {
        elements.inspectedFilesSummary.textContent = `${text(limits.inspected_file_count, "0")} files inspected · max 20 files`;
      }
      return;
    }

    const jobSkills = state.job?.skills;
    if (Array.isArray(jobSkills) && jobSkills.length) {
      const mapped = jobSkills.map((s) => ({
        skill_key: s.key || s.name,
        skill: s.name || s.skill || "Requirement",
        status: "awaiting evidence",
        status_code: "awaiting",
        requirement_type: s.requirement_type || "required",
        confidence: "pending",
        explanation: `Extracted requirement: "${s.source_excerpt || s.matched_phrase}". Connect repository to inspect AST evidence.`,
        job_requirement: s,
        evidence: [],
      }));
      mapped.forEach((item) => elements.skillsGrid.append(renderSkillCard(item)));
      renderEvidenceInspector(mapped[0]);
      elements.skillsNote.textContent = `${jobSkills.length} job requirements established. Connect a GitHub repository to evaluate evidence and calculate score.`;
      return;
    }

    renderEvidenceInspector(null);
    const empty = make("div", "empty-state empty-state--wide");
    empty.append(make("span", "empty-state-icon", "⌘"));
    const copy = document.createElement("div");
    copy.append(make("h3", "", "No supported requirements assessed"));
    copy.append(make("p", "", "Select a job card or save requirements in Setup to extract benchmark skills."));
    empty.append(copy);
    elements.skillsGrid.append(empty);
    elements.skillsNote.textContent = "No supported skills were returned by the assessment API.";
  }

  function renderGuidance() {
    clear(elements.guidanceList);
    const recommendations = state.snapshot?.assessment?.recommendations;
    if (!Array.isArray(recommendations) || !recommendations.length) {
      elements.guidanceList.append(make("div", "history-empty", "No future evidence-building tasks were returned for this assessment."));
      return;
    }
    recommendations.forEach((item) => {
      const guide = make("article", "guidance-item");
      guide.append(make("span", "guidance-tag", "Future recommendation"));
      guide.append(make("h3", "", text(item.skill, "Skill gap")));
      guide.append(make("p", "", text(item.action, "No suggested task returned.")));
      guide.append(make("p", "", text(item.reason, "This is a suggested next step, not a recorded achievement.")));
      elements.guidanceList.append(guide);
    });
  }

  function renderJobSearchResults() {
    clear(elements.jobSearchResults);
    if (!state.jobSearchResults.length) return;
    state.jobSearchResults.forEach((result, index) => {
      const item = make("article", "job-search-result");
      const copy = document.createElement("div");
      copy.append(make("h3", "", `${text(result.title, "Untitled role")} - ${text(result.company, "Unknown company")}`));
      const tags = [
        result.provider ? `Provider: ${result.provider}` : "",
        result.source && result.source !== result.provider ? `Source: ${result.source}` : "",
        result.location,
        result.employment_type,
        result.posted_at ? formatDate(result.posted_at) : "",
      ].filter(Boolean).join(" • ");
      copy.append(make("p", "", tags || "Real-time tech opportunity"));
      if (result.description) {
        const snippetText = result.description.length > 180 ? `${result.description.slice(0, 180)}...` : result.description;
        copy.append(make("p", "job-snippet", snippetText));
      }
      item.append(copy);
      const use = make("button", "button button--quiet", "Use this posting");
      use.type = "button";
      use.disabled = false;
      use.dataset.jobSearchIndex = String(index);
      item.append(use);
      elements.jobSearchResults.append(item);
    });
  }

  async function useJobSearchResult(index, { autoSave = true } = {}) {
    const result = state.jobSearchResults[index];
    if (!result) return;
    elements.jobTitle.value = result.title || "";
    elements.jobCompany.value = result.company === "Company not specified" ? "" : (result.company || "");
    if (elements.jobCity) elements.jobCity.value = result.location || "";
    elements.jobSourceUrl.value = result.posting_url || "";
    elements.jobDescription.value = result.description || "";
    if (autoSave) {
      await submitJob(new Event("submit"));
      return;
    }
    const descriptionNotice = result.description
      ? "Selected posting loaded into the form. You can adjust details or save directly."
      : "Selected role title and company loaded. Review or save to auto-benchmark requirements.";
    setFeedback(elements.jobFeedback, descriptionNotice, "success");
    elements.saveJobButton.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function renderTelegram() {
    clear(elements.telegramPairing);
    elements.telegramPairing.hidden = true;
    const telegram = state.telegram || state.serverTelegram;
    const isAvailable = Boolean(state.serverTelegram?.available || telegram?.available);

    if (!isAvailable) {
      setTone(elements.telegramState, "warning", "Unavailable");
      elements.telegramDescription.textContent =
        state.serverTelegram?.reason || "Telegram alerts are not configured on this server. The assessment flow remains fully functional.";
      elements.telegramPairButton.disabled = true;
      return;
    }

    elements.telegramPairButton.disabled = false;

    if (state.telegram?.state === "paired") {
      setTone(elements.telegramState, "ready", "Paired");
      elements.telegramDescription.textContent =
        "A paired chat receives a concise alert whenever a new commit is automatically reassessed. Evidence excerpts and credentials are never sent.";
      elements.telegramPairButton.querySelector(":scope > span:first-child")?.replaceChildren("Re-pair Telegram");
      return;
    }

    if (state.telegram?.state === "pairing_pending") {
      setTone(elements.telegramState, "working", "Pairing pending");
      elements.telegramDescription.textContent = `Pairing code active. Complete /start in Telegram or request a fresh code.`;
    } else if (state.repository) {
      setTone(elements.telegramState, "", "Ready to pair");
      elements.telegramDescription.textContent = `Pair your Telegram chat to receive instant proof delta alerts when commits arrive on ${state.repository.owner}/${state.repository.name}.`;
    } else {
      setTone(elements.telegramState, "", "Bot available");
      const botName = state.serverTelegram?.bot_username ? `@${state.serverTelegram.bot_username}` : "SkillPath Bot";
      elements.telegramDescription.textContent = `Telegram bot ${botName} is ready. Pair now to link your repository and receive commit push updates.`;
    }

    const label = elements.telegramPairButton.querySelector(":scope > span:first-child");
    if (label) label.textContent = state.telegram?.state === "paired" ? "Re-pair Telegram" : "Pair Telegram";

    const pairing = state.telegramPairing;
    if (!pairing) return;
    elements.telegramPairing.hidden = false;
    elements.telegramPairing.append(make("span", "", "Open the bot or send this command:"));
    if (pairing.deep_link) elements.telegramPairing.append(externalLink("Open Telegram bot", pairing.deep_link, "context-link"));
    if (pairing.start_command) elements.telegramPairing.append(make("code", "", pairing.start_command));
  }

  function renderHistory() {
    clear(elements.historyList);
    if (!state.history.length) {
      elements.historyList.append(make("li", "history-empty", "No snapshots received yet."));
      elements.refreshHistoryButton.disabled = true;
      elements.viewComparisonButton.disabled = true;
      return;
    }
    elements.refreshHistoryButton.disabled = false;
    state.history.forEach((snapshot, index) => {
      const item = make("li", "history-item");
      item.append(make("span", `history-marker ${index === 0 ? "history-marker--current" : "history-marker--previous"}`));
      const copy = make("div", "history-copy");
      copy.append(make("p", "history-title", `${index === 0 ? "Current" : "Earlier"} · ${text(snapshot.trigger, "assessment")}`));
      const score = Number.isFinite(snapshot.fit_score) ? ` · ${snapshot.fit_score}%` : "";
      copy.append(make("p", "history-details", `${shortSha(snapshot.commit_sha)}${score} · ${formatDate(snapshot.assessed_at)}`));
      item.append(copy);
      const compare = make("button", "history-compare", index < state.history.length - 1 ? "Compare" : "Baseline");
      compare.type = "button";
      compare.disabled = index >= state.history.length - 1;
      if (!compare.disabled) {
        compare.dataset.currentSnapshot = String(snapshot.id);
        compare.dataset.previousSnapshot = String(state.history[index + 1].id);
      }
      item.append(compare);
      elements.historyList.append(item);
    });
    elements.viewComparisonButton.disabled = state.history.length < 2;
  }

  function renderMonitor() {
    clear(elements.monitorFacts);
    const monitor = state.monitor?.monitor || state.monitor;
    if (!state.repository || !monitor) {
      elements.monitorFacts.append(
        factRow("Last checked", "Not reported"),
        factRow("Last assessed", "Not reported"),
        factRow("Next action", "Connect a repository")
      );
      setTone(elements.monitorState, "", "Not started");
      elements.checkMonitorButton.disabled = true;
      if (elements.toggleMonitorButton) elements.toggleMonitorButton.disabled = true;
      return;
    }
    const stateText = text(monitor.state, "unknown");
    const tone = stateText === "error" ? "error" : stateText === "checking" ? "working" : "ready";
    const nextAction = monitor.last_error?.message || (monitor.enabled ? `Polls every ${monitor.poll_interval_seconds || "configured"} seconds` : "Monitoring is paused");
    elements.monitorFacts.append(
      factRow("Last checked", formatDate(monitor.last_checked_at)),
      factRow("Last assessed", formatDate(monitor.last_assessed_at)),
      factRow("Next action", nextAction)
    );
    setTone(elements.monitorState, tone, monitor.enabled ? (stateText === "active" ? "Watching commits" : stateText) : "Paused");
    elements.checkMonitorButton.disabled = !monitor.enabled;
    if (elements.toggleMonitorButton) {
      elements.toggleMonitorButton.disabled = false;
      elements.toggleMonitorButton.textContent = monitor.enabled ? "Pause Monitor" : "Resume Monitor";
    }
  }

  function renderEvent() {
    const event = state.events?.find((item) =>
      item?.event_type?.includes("automatic_reassessment") || item?.event_type?.includes("initial_assessment")
    ) || state.events?.[0];
    clear(elements.reassessmentMeta);
    if (!event) {
      elements.reassessmentHeading.textContent = "No repository event received";
      elements.reassessmentMessage.textContent = "Once the server detects a different commit SHA and completes reassessment, the before-and-after evidence will appear here.";
      elements.eventIcon.dataset.tone = "";
      return;
    }
    const isError = event.event_type?.includes("error");
    const isAuto = event.event_type?.includes("automatic");
    elements.reassessmentHeading.textContent = isAuto ? "Automatic reassessment recorded" : event.event_type?.includes("initial") ? "Initial assessment recorded" : "Repository monitor event";
    elements.reassessmentMessage.textContent = text(event.message, "The monitor returned an event without a message.");
    elements.eventIcon.dataset.tone = isError ? "error" : isAuto || event.event_type?.includes("initial") ? "ready" : "warning";
    if (event.previous_sha) elements.reassessmentMeta.append(make("span", "", `before ${shortSha(event.previous_sha)}`));
    if (event.current_sha) elements.reassessmentMeta.append(make("span", "", `after ${shortSha(event.current_sha)}`));
    if (event.created_at) elements.reassessmentMeta.append(make("span", "", formatDate(event.created_at)));
    const count = event.details?.changed_file_count;
    if (typeof count === "number") elements.reassessmentMeta.append(make("span", "", `${count} changed file${count === 1 ? "" : "s"}`));
  }

  function renderScope() {
    const assessment = state.snapshot?.assessment;
    const insp = state.snapshot?.inspection || {};
    const llm = state.snapshot?.llm || {};

    if (elements.llmModeBadge) {
      if (llm.available) {
        const countLabel = typeof llm.interpreted_skill_count === "number" ? ` (${llm.interpreted_skill_count} skills)` : "";
        setTone(elements.llmModeBadge, "ready", `✨ ${llm.mode || "OpenAI Interpretation"}${countLabel}`);
        elements.llmModeBadge.title = llm.sent_to_provider || "";
      } else {
        setTone(elements.llmModeBadge, "", "Deterministic Engine");
        elements.llmModeBadge.title = llm.reason || "Deterministic AST & pattern verification active.";
      }
    }

    const inspectedFiles = Array.isArray(insp.files) ? insp.files : [];
    const skippedFiles = Array.isArray(insp.skipped) ? insp.skipped : [];
    if (elements.scopeDrawerSummaryTitle) {
      elements.scopeDrawerSummaryTitle.textContent = `Repository Inspection Scope (${inspectedFiles.length} inspected, ${skippedFiles.length} skipped)`;
    }
    if (elements.scopeInspectedList) {
      clear(elements.scopeInspectedList);
      if (!inspectedFiles.length) {
        elements.scopeInspectedList.append(make("li", "reqs-empty", "Connect a repository to view inspected files."));
      } else {
        inspectedFiles.forEach((f) => {
          const li = document.createElement("li");
          const pathNode = f.url ? externalLink(`📄 ${f.path}`, f.url, "evidence-file") : make("span", "", `📄 ${f.path}`);
          li.append(pathNode);
          const tag = f.context_only ? "context-only (0.32)" : `${f.size ?? 0} B`;
          li.append(make("span", "", tag));
          elements.scopeInspectedList.append(li);
        });
      }
    }
    if (elements.scopeSkippedList) {
      clear(elements.scopeSkippedList);
      if (!skippedFiles.length) {
        elements.scopeSkippedList.append(make("li", "reqs-empty", "No files were skipped in this repository."));
      } else {
        skippedFiles.forEach((s) => {
          const li = document.createElement("li");
          li.append(make("span", "", s.path || "file"));
          li.append(make("span", "", s.reason || "skipped"));
          elements.scopeSkippedList.append(li);
        });
      }
    }

    const paragraph = elements.scopeNotice?.querySelector("p");
    if (!assessment || !paragraph) return;
    clear(paragraph);
    paragraph.append(make("strong", "", "How to read this dashboard: "));
    paragraph.append(document.createTextNode(assessment.scope_notice || "Evidence is limited to the inspected commit."));
  }

  function renderAll() {
    renderSetupWorkspace();
    renderContext();
    renderFit();
    renderRepositoryFacts();
    renderMonitor();
    renderEvent();
    renderSkills();
    renderHistory();
    renderGuidance();
    renderTelegram();
    renderScope();
    renderCompareDashboard();
    if (elements.navCompareBadge) {
      elements.navCompareBadge.hidden = state.history.length < 2;
      if (state.history.length >= 2) {
        const diff = (state.history[0]?.fit_score ?? 0) - (state.history[1]?.fit_score ?? 0);
        elements.navCompareBadge.textContent = Number.isFinite(diff) ? `${diff >= 0 ? "+" : ""}${diff}%` : "Δ";
      }
    }
    if (elements.disconnectRepositoryButton) {
      elements.disconnectRepositoryButton.hidden = !state.repository;
    }
    if (elements.deleteJobButton) {
      elements.deleteJobButton.disabled = !state.job?.id;
    }
    if (state.repository && state.snapshot) {
      setConnection("ready", `Watching ${state.repository.owner}/${state.repository.name} at ${shortSha(state.snapshot.commit_sha)}`);
    } else if (state.job) {
      setConnection("working", "Job saved; connect a repository for evidence");
    } else {
      setConnection("idle", "Waiting for a job and repository");
    }
  }

  async function loadHistory() {
    if (!state.repository?.id) return;
    const payload = await api(`/api/repositories/${state.repository.id}/history`);
    state.history = Array.isArray(payload.history) ? payload.history : [];
  }

  async function loadOverview(repositoryId, { includeHistory = true } = {}) {
    const overview = await api(`/api/repositories/${repositoryId}/overview`);
    state.repository = overview.repository || null;
    state.job = overview.job || state.job;
    state.snapshot = overview.latest_snapshot || null;
    state.events = Array.isArray(overview.events) ? overview.events : [];
    state.telegram = overview.telegram || null;
    state.telegramPairing = null;
    if (state.job) {
      if (elements.savedJobsSelect) {
        elements.savedJobsSelect.value = String(state.job.id);
      }
      elements.jobTitle.value = state.job.title || "";
      const isGenericComp = !state.job.company || state.job.company === "Company not specified" || state.job.company === state.job.city;
      elements.jobCompany.value = isGenericComp ? "" : state.job.company;
      if (elements.jobCity) elements.jobCity.value = state.job.city || (state.job.company === state.job.city ? state.job.city : "");
      const hasRealSource = state.job.source_url && !state.job.source_url.includes("skillpath.local");
      elements.jobSourceUrl.value = hasRealSource ? state.job.source_url : "";
      const isBenchmarkDesc = state.job.description && (
        state.job.description.startsWith("Role Benchmark:") ||
        state.job.description.startsWith("Engineering requirements for")
      );
      elements.jobDescription.value = isBenchmarkDesc ? "" : (state.job.description || "");
      elements.repositoryUrl.disabled = false;
      elements.connectRepositoryButton.disabled = false;
    }
    if (state.repository) {
      elements.repositoryUrl.value = state.repository.repository_url || "";
    }
    const monitor = await api(`/api/repositories/${repositoryId}/monitor`);
    state.monitor = monitor;
    if (includeHistory) await loadHistory();
    renderAll();
    if (state.repository) {
      localStorage.setItem(ACTIVE_REPOSITORY_KEY, String(state.repository.id));
      if (elements.savedReposSelect) elements.savedReposSelect.value = String(state.repository.id);
      if (elements.deleteRepoButton) elements.deleteRepoButton.disabled = false;
    }
  }

  async function refreshConnectedState() {
    if (state.refreshBusy || !state.repository?.id) return;
    state.refreshBusy = true;
    const oldSnapshot = state.snapshot?.id;
    try {
      const overview = await api(`/api/repositories/${state.repository.id}/overview`);
      state.repository = overview.repository || state.repository;
      state.snapshot = overview.latest_snapshot || state.snapshot;
      state.events = Array.isArray(overview.events) ? overview.events : state.events;
      state.telegram = overview.telegram || state.telegram;
      const monitor = await api(`/api/repositories/${state.repository.id}/monitor`);
      state.monitor = monitor;
      if (state.snapshot?.id && state.snapshot.id !== oldSnapshot) {
        await loadHistory();
        toast("A new assessment snapshot arrived from the repository monitor.", "success");
        if (oldSnapshot) {
          showComparison(state.snapshot.id, oldSnapshot);
        }
      }
      renderAll();
    } catch (error) {
      setConnection("error", error.message);
    } finally {
      state.refreshBusy = false;
    }
  }

  async function loadSavedJobs() {
    try {
      const payload = await api("/api/jobs");
      state.savedJobs = Array.isArray(payload.jobs) ? payload.jobs : [];
      if (!elements.savedJobsSelect) return;
      clear(elements.savedJobsSelect);
      const defaultOption = make("option", "", "-- Or select a saved job --");
      defaultOption.value = "";
      elements.savedJobsSelect.append(defaultOption);
      state.savedJobs.forEach((j) => {
        const title = j.company && j.company !== "Company not specified" ? `${j.title} (${j.company})` : j.title;
        const opt = make("option", "", title);
        opt.value = String(j.id);
        elements.savedJobsSelect.append(opt);
      });
      if (state.job?.id) {
        elements.savedJobsSelect.value = String(state.job.id);
        if (elements.deleteJobButton) elements.deleteJobButton.disabled = false;
      } else if (elements.deleteJobButton) {
        elements.deleteJobButton.disabled = true;
      }
    } catch (_) {
      // Best-effort
    }
  }

  async function onSavedJobSelectChange() {
    const selectedId = elements.savedJobsSelect.value;
    if (!selectedId) {
      state.job = null;
      state.repository = null;
      state.snapshot = null;
      state.history = [];
      state.monitor = null;
      state.events = [];
      if (elements.deleteJobButton) elements.deleteJobButton.disabled = true;
      elements.jobTitle.value = "";
      elements.jobCompany.value = "";
      if (elements.jobCity) elements.jobCity.value = "";
      elements.jobSourceUrl.value = "";
      elements.jobDescription.value = "";
      elements.repositoryUrl.value = "";
      elements.repositoryUrl.disabled = false;
      elements.connectRepositoryButton.disabled = false;
      elements.repositoryHelp.textContent = "Connect any public or authenticated GitHub repository for evidence assessment.";
      localStorage.removeItem(ACTIVE_REPOSITORY_KEY);
      renderAll();
      return;
    }
    const found = state.savedJobs.find((j) => String(j.id) === String(selectedId));
    if (!found) return;
    state.job = found;
    if (elements.deleteJobButton) elements.deleteJobButton.disabled = false;
    elements.jobTitle.value = found.title || "";
    const isGenericComp = !found.company || found.company === "Company not specified" || found.company === found.city;
    elements.jobCompany.value = isGenericComp ? "" : found.company;
    if (elements.jobCity) elements.jobCity.value = found.city || (found.company === found.city ? found.city : "");
    const hasRealSource = found.source_url && !found.source_url.includes("skillpath.local");
    elements.jobSourceUrl.value = hasRealSource ? found.source_url : "";
    const isBenchmarkDesc = found.description && (
      found.description.startsWith("Role Benchmark:") ||
      found.description.startsWith("Engineering requirements for")
    );
    elements.jobDescription.value = isBenchmarkDesc ? "" : (found.description || "");
    elements.repositoryUrl.disabled = false;
    elements.connectRepositoryButton.disabled = false;
    elements.repositoryHelp.textContent = "Connect a GitHub repository to inspect evidence for this job.";

    try {
      const repoPayload = await api(`/api/repositories?job_id=${found.id}`);
      const repos = Array.isArray(repoPayload.repositories) ? repoPayload.repositories : [];
      if (repos.length > 0) {
        const repo = repos[0];
        elements.repositoryUrl.value = repo.repository_url || "";
        await loadOverview(repo.id);
      } else {
        state.repository = null;
        state.snapshot = null;
        state.history = [];
        state.monitor = null;
        state.events = [];
        if (elements.savedReposSelect?.value) {
          const matched = (state.savedRepositories || []).find((r) => String(r.id) === String(elements.savedReposSelect.value));
          if (matched?.repository_url) elements.repositoryUrl.value = matched.repository_url;
        }
        localStorage.removeItem(ACTIVE_REPOSITORY_KEY);
        renderAll();
      }
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function deleteCurrentJob() {
    if (!state.job?.id) return;
    const confirmDelete = window.confirm(`Delete job "${state.job.title}" and any connected repositories and snapshot history?`);
    if (!confirmDelete) return;
    try {
      await api(`/api/jobs/${state.job.id}`, { method: "DELETE" });
      toast("Job deleted successfully.", "success");
      state.job = null;
      state.repository = null;
      state.snapshot = null;
      state.history = [];
      state.monitor = null;
      state.events = [];
      localStorage.removeItem(ACTIVE_REPOSITORY_KEY);
      elements.jobTitle.value = "";
      elements.jobCompany.value = "";
      elements.jobSourceUrl.value = "";
      elements.jobDescription.value = "";
      elements.repositoryUrl.value = "";
      elements.repositoryUrl.disabled = false;
      elements.connectRepositoryButton.disabled = false;
      elements.repositoryHelp.textContent = "Connect any public or authenticated GitHub repository for evidence assessment.";
      await loadSavedJobs();
      renderAll();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function loadSavedRepositories() {
    try {
      const payload = await api("/api/repositories");
      state.savedRepositories = Array.isArray(payload.repositories) ? payload.repositories : [];
      if (!elements.savedReposSelect) return;
      clear(elements.savedReposSelect);
      const defaultOption = make("option", "", "-- Or switch to an assessed repository --");
      defaultOption.value = "";
      elements.savedReposSelect.append(defaultOption);
      state.savedRepositories.forEach((r) => {
        const label = `${r.owner}/${r.name} (${r.default_branch || "main"})`;
        const opt = make("option", "", label);
        opt.value = String(r.id);
        elements.savedReposSelect.append(opt);
      });
      if (elements.savedReposBar) {
        elements.savedReposBar.hidden = state.savedRepositories.length === 0;
      }
      if (state.repository?.id && elements.savedReposSelect) {
        elements.savedReposSelect.value = String(state.repository.id);
        if (elements.deleteRepoButton) elements.deleteRepoButton.disabled = false;
      } else if (elements.deleteRepoButton) {
        elements.deleteRepoButton.disabled = true;
      }
    } catch (_) {
      // Best-effort
    }
  }

  async function onSavedRepoSelectChange() {
    const selectedId = elements.savedReposSelect?.value;
    if (!selectedId) {
      if (elements.deleteRepoButton) elements.deleteRepoButton.disabled = true;
      return;
    }
    const found = (state.savedRepositories || []).find((r) => String(r.id) === String(selectedId));
    if (!found) return;
    elements.repositoryUrl.value = found.repository_url || "";
    if (elements.deleteRepoButton) elements.deleteRepoButton.disabled = false;

    if (state.job?.id) {
      try {
        const repoPayload = await api(`/api/repositories?job_id=${state.job.id}`);
        const repos = Array.isArray(repoPayload.repositories) ? repoPayload.repositories : [];
        const existingForJob = repos.find((r) => r.repository_url === found.repository_url);
        if (existingForJob) {
          await loadOverview(existingForJob.id);
          return;
        }
        toast(`Assessing ${found.owner}/${found.name} for ${state.job.title}...`, "working");
        await submitRepository(new Event("submit"));
        return;
      } catch (_) {
        // Fall back to default overview
      }
    }
    await loadOverview(found.id);
  }

  async function deleteCurrentRepository() {
    const repoId = elements.savedReposSelect?.value || state.repository?.id;
    if (!repoId) return;
    const repoName = state.repository?.name || "this repository";
    const confirmDelete = window.confirm(`Delete repository "${repoName}" and all its recorded snapshots?`);
    if (!confirmDelete) return;
    try {
      await api(`/api/repositories/${repoId}`, { method: "DELETE" });
      toast("Repository deleted.", "success");
      state.repository = null;
      state.snapshot = null;
      state.history = [];
      state.monitor = null;
      state.events = [];
      elements.repositoryUrl.value = "";
      localStorage.removeItem(ACTIVE_REPOSITORY_KEY);
      await loadSavedRepositories();
      renderAll();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function disconnectCurrentRepository() {
    if (!state.repository?.id) return;
    const confirmDisconnect = window.confirm(
      `Disconnect repository "${state.repository.owner}/${state.repository.name}" and remove its snapshots and monitor events?`
    );
    if (!confirmDisconnect) return;
    try {
      await api(`/api/repositories/${state.repository.id}`, { method: "DELETE" });
      toast("Repository disconnected.", "success");
      state.repository = null;
      state.snapshot = null;
      state.history = [];
      state.monitor = null;
      state.events = [];
      localStorage.removeItem(ACTIVE_REPOSITORY_KEY);
      elements.repositoryUrl.value = "";
      elements.repositoryUrl.disabled = false;
      elements.connectRepositoryButton.disabled = false;
      await loadSavedRepositories();
      renderAll();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function fetchAndDisplayUserRepos(username) {
    const cleanUser = username.replace(/^@/, "").trim();
    if (!cleanUser) return;
    if (elements.userReposDrawer) {
      elements.userReposDrawer.hidden = false;
      elements.userReposTitle.textContent = `Fetching public repositories for @${cleanUser}...`;
      clear(elements.userReposList);
    }
    try {
      const payload = await api(`/api/github/users/${cleanUser}/repositories`);
      const repos = Array.isArray(payload.repositories) ? payload.repositories : [];
      if (!repos.length) {
        if (elements.userReposTitle) elements.userReposTitle.textContent = `No public repositories found for @${cleanUser}.`;
        return;
      }
      if (elements.userReposTitle) {
        elements.userReposTitle.textContent = `📁 Public repositories for @${cleanUser} (${repos.length} found) — Click to assess:`;
      }
      clear(elements.userReposList);
      repos.forEach((r) => {
        const chip = make("button", "user-repo-chip", r.name);
        chip.type = "button";
        if (r.language) {
          const langSpan = make("span", "repo-lang", `(${r.language})`);
          chip.append(langSpan);
        }
        chip.addEventListener("click", () => {
          elements.repositoryUrl.value = r.html_url;
          elements.userReposDrawer.hidden = true;
          submitRepository(new Event("submit"));
        });
        elements.userReposList.append(chip);
      });
    } catch (err) {
      if (elements.userReposTitle) elements.userReposTitle.textContent = `Could not fetch repositories for @${cleanUser}: ${err.message}`;
    }
  }

  async function onBrowseReposClick() {
    let val = elements.repositoryUrl.value.trim();
    let username = "";
    if (val) {
      const match = val.match(/(?:github\.com\/|^@?)([a-zA-Z0-9-]+)(?:\/|$)/i);
      if (match) username = match[1];
    }
    if (!username) {
      username = window.prompt("Enter a GitHub username to fetch public repositories (e.g. vedantsable56):", "vedantsable56");
    }
    if (!username || !username.trim()) return;
    const clean = username.trim().replace(/^@/, "");
    elements.repositoryUrl.value = `https://github.com/${clean}`;
    await fetchAndDisplayUserRepos(clean);
  }

  function startStatusRefresh() {
    if (state.refreshTimer) window.clearInterval(state.refreshTimer);
    state.refreshTimer = window.setInterval(refreshConnectedState, REFRESH_INTERVAL_MS);
  }

  async function submitJob(event) {
    event.preventDefault();
    setFeedback(elements.jobFeedback, "");
    const title = elements.jobTitle.value.trim();
    const company = elements.jobCompany.value.trim();
    const city = elements.jobCity ? elements.jobCity.value.trim() : "";
    const sourceUrl = elements.jobSourceUrl.value.trim();
    let description = elements.jobDescription.value.trim();
    if (!title) {
      setFeedback(elements.jobFeedback, "Enter a role title.", "error");
      return;
    }
    setButtonLoading(elements.saveJobButton, true, description ? "Saving job" : "Preparing benchmark");
    try {
      if (!description && sourceUrl) {
        const fetched = await api("/api/jobs/fetch", { method: "POST", body: { source_url: sourceUrl } });
        elements.jobDescription.value = fetched.description || "";
        setFeedback(elements.jobFeedback, "Description fetched into the form. Review it, then select Save job requirements again.", "success");
        toast("Job text fetched. Review it before saving.", "success");
        return;
      }
      const body = { title, description };
      if (company) body.company = company;
      if (city) body.city = city;
      if (sourceUrl) body.source_url = sourceUrl;
      const payload = await api("/api/jobs", {
        method: "POST",
        body,
      });
      state.job = payload.job;
      elements.repositoryUrl.disabled = false;
      elements.connectRepositoryButton.disabled = false;
      elements.repositoryHelp.textContent = payload.warning || "Job saved. Connect or assess your GitHub repository.";
      setFeedback(elements.jobFeedback, payload.warning || `${payload.job.skills?.length || 0} supported requirement${payload.job.skills?.length === 1 ? "" : "s"} established for ${payload.job.title}.`, payload.warning ? "error" : "success");
      await loadSavedJobs();
      if (elements.savedJobsSelect) {
        elements.savedJobsSelect.value = String(state.job.id);
      }
      renderAll();
      toast(payload.warning || "Job requirements saved.", payload.warning ? "warning" : "success");
      if (elements.repositoryUrl && !state.repository) {
        elements.repositoryUrl.scrollIntoView({ behavior: "smooth", block: "center" });
        elements.repositoryUrl.focus();
      }
    } catch (error) {
      setFeedback(elements.jobFeedback, error.message, "error");
      toast(error.message, "error");
    } finally {
      setButtonLoading(elements.saveJobButton, false);
    }
  }

  async function submitRepository(event) {
    if (event?.preventDefault) event.preventDefault();
    setFeedback(elements.repositoryFeedback, "");
    let repositoryUrl = elements.repositoryUrl.value.trim();
    if (!repositoryUrl && elements.savedReposSelect?.value) {
      const selected = (state.savedRepositories || []).find(
        (r) => String(r.id) === String(elements.savedReposSelect.value)
      );
      if (selected?.repository_url) {
        repositoryUrl = selected.repository_url;
        elements.repositoryUrl.value = repositoryUrl;
      }
    }
    if (!repositoryUrl) {
      setFeedback(elements.repositoryFeedback, "Enter a GitHub repository URL or select one from the dropdown.", "error");
      return;
    }
    let jobId = state.job?.id;
    if (!jobId && state.savedJobs && state.savedJobs.length > 0) {
      jobId = state.savedJobs[0].id;
      state.job = state.savedJobs[0];
      if (elements.savedJobsSelect) elements.savedJobsSelect.value = String(jobId);
    }
    setButtonLoading(elements.connectRepositoryButton, true, "Inspecting code");
    setConnection("working", "Inspecting repository evidence without executing code");
    try {
      const body = { repository_url: repositoryUrl };
      if (jobId) body.job_id = jobId;
      const payload = await api("/api/repositories", {
        method: "POST",
        body,
      });
      state.repository = payload.repository;
      state.snapshot = payload.snapshot;
      state.events = [];
      if (elements.userReposDrawer) elements.userReposDrawer.hidden = true;
      if (payload.repository?.repository_url) {
        elements.repositoryUrl.value = payload.repository.repository_url;
      }
      await loadOverview(state.repository.id);
      await loadSavedJobs();
      await loadSavedRepositories();
      setFeedback(elements.repositoryFeedback, payload.message || "Repository connected and assessed.", "success");
      toast(payload.message || "Repository connected and assessed.", "success");
      switchView("result");
    } catch (error) {
      setFeedback(elements.repositoryFeedback, error.message, "error");
      setConnection("error", error.message);
      toast(error.message, "error");
    } finally {
      setButtonLoading(elements.connectRepositoryButton, false);
    }
  }

  let profileLookupTimer = null;
  async function checkForProfileUrl() {
    const val = elements.repositoryUrl.value.trim();
    if (!val) {
      if (elements.userReposDrawer) elements.userReposDrawer.hidden = true;
      return;
    }
    const profileMatch =
      val.match(/^https?:\/\/github\.com\/([a-zA-Z0-9-]+)\/?$/i) ||
      val.match(/^@([a-zA-Z0-9-]+)$/i);
    if (!profileMatch) {
      if (elements.userReposDrawer) elements.userReposDrawer.hidden = true;
      return;
    }
    await fetchAndDisplayUserRepos(profileMatch[1]);
  }

  async function validateRepository() {
    const rawUrl = elements.repositoryUrl?.value.trim();
    if (!rawUrl) {
      setFeedback(elements.repositoryFeedback, "Enter a GitHub repository URL or @username to validate.", "error");
      return;
    }
    setButtonLoading(elements.validateRepoButton, true, "Validating");
    setFeedback(elements.repositoryFeedback, "");
    try {
      const payload = await api(`/api/github/validate?repository_url=${encodeURIComponent(rawUrl)}`);
      state.validatedRepoMeta = payload.repository || null;
      if (state.validatedRepoMeta?.repository_url && elements.repositoryUrl) {
        elements.repositoryUrl.value = state.validatedRepoMeta.repository_url;
      }
      setFeedback(
        elements.repositoryFeedback,
        `Validated ${state.validatedRepoMeta?.full_name || "repository"} (${state.validatedRepoMeta?.default_branch || "main"} · ${shortSha(state.validatedRepoMeta?.commit_sha)}). Ready to start analysis.`,
        "success"
      );
      renderAll();
      toast(`Validated ${state.validatedRepoMeta?.full_name || "repository"}.`, "success");
    } catch (error) {
      setFeedback(elements.repositoryFeedback, error.message, "error");
      toast(error.message, "error");
    } finally {
      setButtonLoading(elements.validateRepoButton, false);
    }
  }

  async function reanalyzeRepository() {
    if (!state.repository?.id) return;
    setButtonLoading(elements.reanalyzeButton, true, "Scanning");
    try {
      const payload = await api(`/api/repositories/${state.repository.id}/scan`, { method: "POST" });
      await loadOverview(state.repository.id);
      toast(payload.message || "Manual reanalysis completed.", payload.created_snapshot ? "success" : "info");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonLoading(elements.reanalyzeButton, false);
    }
  }

  async function toggleMonitor() {
    if (!state.repository?.id) return;
    const monitor = state.monitor?.monitor || state.monitor;
    const nextEnabled = !(monitor?.enabled ?? true);
    setButtonLoading(elements.toggleMonitorButton, true, nextEnabled ? "Resuming" : "Pausing");
    try {
      state.monitor = await api(`/api/repositories/${state.repository.id}/monitor`, {
        method: "PUT",
        body: { enabled: nextEnabled },
      });
      renderMonitor();
      toast(nextEnabled ? "Commit monitoring resumed." : "Commit monitoring paused.");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonLoading(elements.toggleMonitorButton, false);
      renderMonitor();
    }
  }

  async function updateSelectedJob() {
    if (!state.job?.id) return;
    const title = elements.jobTitle.value.trim();
    const company = elements.jobCompany.value.trim();
    const city = elements.jobCity ? elements.jobCity.value.trim() : "";
    const sourceUrl = elements.jobSourceUrl.value.trim();
    const description = elements.jobDescription.value.trim();
    if (!title) {
      setFeedback(elements.jobFeedback, "Enter a role title.", "error");
      return;
    }
    setButtonLoading(elements.updateJobButton, true, "Updating");
    try {
      const body = { title, description };
      if (company) body.company = company;
      if (city) body.city = city;
      if (sourceUrl) body.source_url = sourceUrl;
      const payload = await api(`/api/jobs/${state.job.id}`, { method: "PUT", body });
      state.job = payload.job;
      await loadSavedJobs();
      setFeedback(elements.jobFeedback, payload.warning || `Updated ${payload.job.title} (${payload.job.skills?.length || 0} requirements).`, payload.warning ? "error" : "success");
      renderAll();
      toast("Selected job updated.", "success");
    } catch (error) {
      setFeedback(elements.jobFeedback, error.message, "error");
      toast(error.message, "error");
    } finally {
      setButtonLoading(elements.updateJobButton, false);
    }
  }

  async function fetchJobUrlOnly() {
    const sourceUrl = elements.jobSourceUrl?.value.trim();
    if (!sourceUrl) {
      setFeedback(elements.jobFeedback, "Enter a public job posting URL first.", "error");
      return;
    }
    setButtonLoading(elements.fetchJobUrlButton, true, "Fetching");
    try {
      const fetched = await api("/api/jobs/fetch", { method: "POST", body: { source_url: sourceUrl } });
      elements.jobDescription.value = fetched.description || "";
      setFeedback(elements.jobFeedback, "Fetched readable text from URL. Review and save.", "success");
      toast("Job description text fetched.", "success");
    } catch (error) {
      setFeedback(elements.jobFeedback, error.message, "error");
      toast(error.message, "error");
    } finally {
      setButtonLoading(elements.fetchJobUrlButton, false);
    }
  }

  async function checkMonitor() {
    if (!state.repository?.id) return;
    setButtonLoading(elements.checkMonitorButton, true, "Checking");
    try {
      const payload = await api(`/api/repositories/${state.repository.id}/monitor/check`, { method: "POST" });
      const result = payload.result || {};
      if (result.event === "reassessed") {
        toast("New commit detected and reassessed automatically.", "success");
      } else if (result.event === "no_change") {
        toast("No new commit; no duplicate assessment was created.");
      } else {
        toast(result.message || "Monitor check completed.");
      }
      await loadOverview(state.repository.id);
      if (result.event === "reassessed" && state.history.length >= 2) {
        showComparison(state.history[0].id, state.history[1].id);
      }
    } catch (error) {
      toast(error.message, "error");
      await refreshConnectedState();
    } finally {
      setButtonLoading(elements.checkMonitorButton, false);
    }
  }

  async function searchJobs(event) {
    if (event?.preventDefault) event.preventDefault();
    let query = elements.jobSearchQuery.value.trim();
    if (!query && elements.jobTitle?.value) {
      query = elements.jobTitle.value.trim();
      elements.jobSearchQuery.value = query;
    }
    const country = (elements.jobSearchCountry.value.trim() || "in").toLowerCase();
    let location = elements.jobSearchLocation.value.trim();
    if (!location && elements.jobCity?.value) {
      location = elements.jobCity.value.trim();
      elements.jobSearchLocation.value = location;
    }
    if (query.length < 2 || !/^[a-z]{2}$/i.test(country)) {
      setFeedback(elements.jobSearchFeedback, "Enter search terms or a role title above to find real-time jobs.", "error");
      return;
    }
    setFeedback(elements.jobSearchFeedback, "");
    setButtonLoading(elements.searchJobsButton, true, "Searching live jobs");
    try {
      const payload = await api("/api/job-search", {
        method: "POST",
        body: { query, country, location: location || null },
      });
      const rawList = Array.isArray(payload.jobs) ? payload.jobs : (Array.isArray(payload.results) ? payload.results : []);
      state.jobSearchResults = rawList;
      renderJobSearchResults();
      setFeedback(
        elements.jobSearchFeedback,
        state.jobSearchResults.length
          ? `Found ${state.jobSearchResults.length} live tech job${state.jobSearchResults.length === 1 ? "" : "s"}. Click 'Use this posting' to automatically load requirements.`
          : "No live postings returned for these keywords. Try broadening terms (e.g. 'Python Developer').",
        state.jobSearchResults.length ? "success" : "error"
      );
    } catch (error) {
      state.jobSearchResults = [];
      renderJobSearchResults();
      setFeedback(elements.jobSearchFeedback, error.message, "error");
    } finally {
      setButtonLoading(elements.searchJobsButton, false);
    }
  }

  async function pairTelegram() {
    setButtonLoading(elements.telegramPairButton, true, "Preparing");
    try {
      if (!state.repository?.id) {
        const repoPayload = await api("/api/repositories");
        const repos = Array.isArray(repoPayload.repositories) ? repoPayload.repositories : [];
        if (repos.length > 0) {
          await loadOverview(repos[0].id);
        } else {
          if (state.serverTelegram?.bot_username) {
            state.telegramPairing = {
              deep_link: `https://t.me/${state.serverTelegram.bot_username}`,
              start_command: `/start`,
            };
            renderTelegram();
            toast(`Bot ready: @${state.serverTelegram.bot_username}. Connect your GitHub repository above for live commit alerts!`, "info");
            return;
          }
          toast("Please enter your GitHub repository above so the bot knows which repository to link.", "warning");
          elements.repositoryUrl.focus();
          return;
        }
      }
      const payload = await api(`/api/repositories/${state.repository.id}/telegram/pair`, { method: "POST" });
      state.telegramPairing = payload.pairing || null;
      state.telegram = { ...(state.telegram || {}), available: true, state: "pairing_pending", pairing_expires_at: payload.pairing?.expires_at };
      renderTelegram();
      toast("Telegram pairing code created. It expires automatically.", "success");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonLoading(elements.telegramPairButton, false);
    }
  }

  function evidenceListText(entries) {
    if (!Array.isArray(entries) || !entries.length) return "No validated evidence excerpt added or removed.";
    return entries.map((entry) => `${entry.path || "file"}:${entry.start_line || "?"}-${entry.end_line || "?"}`).join("\n");
  }

  function formatEvidenceShort(entries) {
    if (!Array.isArray(entries) || !entries.length) return "No evidence in scope";
    const files = [...new Set(entries.map((e) => e.path).filter(Boolean))];
    return files.slice(0, 2).join(", ") + (files.length > 2 ? ` (+${files.length - 2})` : "");
  }

  function renderCompareBars(container, rows, mode) {
    if (!container) return;
    clear(container);
    if (!Array.isArray(rows) || !rows.length) {
      container.append(make("p", "history-empty", "Connect a job and repository to view skill bars."));
      return;
    }
    rows.forEach((row) => {
      const statusCode = mode === "before" ? row.before_status_code : row.after_status_code;
      const statusLabel = mode === "before" ? row.before_status : row.after_status;
      const sc = statusClass(statusCode, statusLabel);
      const barRow = make("div", "compare-bar-row");
      barRow.append(make("span", "compare-bar-skill", text(row.skill, "Skill")));
      barRow.append(make("span", "compare-bar-req", text(row.requirement_type, "required")));
      const track = make("div", "compare-bar-track");
      const wrap = make("div", "compare-bar-fill-wrap");
      wrap.append(make("div", `compare-bar-fill compare-bar-fill--${sc}`));
      track.append(wrap);
      const shortStatus = sc === "demonstrated" ? "Demonstrated" : sc === "partial" ? "Partial" : "Not in scope";
      track.append(make("span", "compare-bar-label", shortStatus));
      barRow.append(track);
      container.append(barRow);
    });
  }

  function renderCompareDashboard() {
    if (!elements.compareRepoName) return;
    if (state.repository) {
      elements.compareRepoName.textContent = `${state.repository.owner}/${state.repository.name}`;
      if (elements.compareRepoBadges) {
        clear(elements.compareRepoBadges);
        const insp = state.snapshot?.inspection || {};
        elements.compareRepoBadges.append(
          make("span", "meta-pill", `Branch: ${state.repository.default_branch || "main"}`),
          make("span", "meta-pill", `Commit: ${shortSha(state.repository.latest_known_sha)}`),
          make("span", "meta-pill", `${insp.inspected_file_count ?? 0} files inspected`)
        );
      }
    } else {
      elements.compareRepoName.textContent = "No repository connected";
      if (elements.compareRepoBadges) {
        clear(elements.compareRepoBadges);
        elements.compareRepoBadges.append(make("span", "meta-pill", "Connect a repository in Setup"));
      }
    }

    if (elements.compareJobTitle) {
      elements.compareJobTitle.textContent = state.job ? state.job.title : "No job selected";
      elements.compareJobCompany.textContent = state.job ? state.job.company || "Benchmark" : "—";
    }

    // Populate snapshot pair selector
    if (elements.compareSnapshotSelect) {
      const currentVal = elements.compareSnapshotSelect.value;
      clear(elements.compareSnapshotSelect);
      if (state.history.length >= 2) {
        for (let i = 0; i < state.history.length - 1; i++) {
          const cur = state.history[i];
          const prev = state.history[i + 1];
          const opt = make(
            "option",
            "",
            `${shortSha(cur.commit_sha)} (${cur.fit_score ?? "—"}%) vs. ${shortSha(prev.commit_sha)} (${prev.fit_score ?? "—"}%)`
          );
          opt.value = `${cur.id}:${prev.id}`;
          elements.compareSnapshotSelect.append(opt);
        }
        if (currentVal && [...elements.compareSnapshotSelect.options].some((o) => o.value === currentVal)) {
          elements.compareSnapshotSelect.value = currentVal;
        }
      } else {
        const opt = make("option", "", "Single snapshot (Baseline vs. Current)");
        opt.value = "";
        elements.compareSnapshotSelect.append(opt);
      }
    }

    // Build rows from either state.lastComparison or current snapshot assessment
    const comp = state.lastComparison;
    const currentAssess = state.snapshot?.assessment;
    let rows = [];
    let strengths = [];
    let gaps = [];
    let beforeScore = null;
    let afterScore = null;

    if (comp && Array.isArray(comp.requirement_rows)) {
      rows = comp.requirement_rows;
      strengths = comp.strengths || [];
      gaps = comp.top_gaps || [];
      beforeScore = comp.previous_score;
      afterScore = comp.current_score;
      if (elements.compareBeforeSub) {
        elements.compareBeforeSub.textContent = `Commit ${shortSha(comp.previous_snapshot?.commit_sha)} (${formatDate(comp.previous_snapshot?.assessed_at)})`;
      }
      if (elements.compareAfterSub) {
        elements.compareAfterSub.textContent = `Commit ${shortSha(comp.current_snapshot?.commit_sha)} (${formatDate(comp.current_snapshot?.assessed_at)})`;
      }
      if (elements.compareDeltaBadge) {
        const d = comp.score_delta;
        setTone(
          elements.compareDeltaBadge,
          d > 0 ? "ready" : d < 0 ? "warning" : "working",
          d !== null && d !== undefined ? `Proof Delta ${d >= 0 ? "+" : ""}${d}%` : "Compared"
        );
      }
    } else if (currentAssess && Array.isArray(currentAssess.skill_assessments)) {
      beforeScore = null;
      afterScore = currentAssess.fit_score?.value ?? null;
      if (elements.compareBeforeSub) {
        elements.compareBeforeSub.textContent = "Baseline unavailable (single commit snapshot)";
      }
      if (elements.compareAfterSub) {
        elements.compareAfterSub.textContent = `Commit ${shortSha(state.snapshot?.commit_sha)} (Initial scan)`;
      }
      if (elements.compareDeltaBadge) {
        setTone(elements.compareDeltaBadge, "working", "Baseline unavailable");
      }
      rows = currentAssess.skill_assessments.map((s) => ({
        skill_key: s.skill_key,
        skill: s.skill,
        requirement_type: s.requirement_type || "required",
        before_status: "Baseline unavailable",
        before_status_code: "awaiting",
        after_status: s.status,
        after_status_code: s.status_code,
        status_changed: false,
        before_evidence: [],
        after_evidence: s.evidence || [],
        evidence_added: [],
        evidence_removed: [],
        claim_boundary: s.claim_boundary,
        next_evidence_contract: s.next_evidence_contract,
      }));
      strengths = rows
        .filter((r) => r.after_status_code === "demonstrated")
        .map((r) => ({
          skill_key: r.skill_key,
          skill: r.skill,
          file_count: new Set((r.after_evidence || []).map((e) => e.path)).size,
        }));
      gaps = rows
        .filter((r) => r.after_status_code !== "demonstrated")
        .map((r) => ({
          skill_key: r.skill_key,
          skill: r.skill,
          status: r.after_status,
          task: r.next_evidence_contract?.task || "",
        }));
    }

    if (elements.compareBeforeScore) {
      elements.compareBeforeScore.textContent = Number.isFinite(beforeScore) ? `${beforeScore}%` : "N/A";
    }
    if (elements.compareAfterScore) {
      elements.compareAfterScore.textContent = Number.isFinite(afterScore) ? `${afterScore}%` : "—";
    }

    renderCompareBars(elements.compareBeforeBars, rows, "before");
    renderCompareBars(elements.compareAfterBars, rows, "after");

    // Distribution
    const total = rows.length;
    const demoCount = rows.filter((r) => r.after_status_code === "demonstrated").length;
    const partCount = rows.filter((r) => r.after_status_code === "partially_demonstrated").length;
    const missCount = Math.max(0, total - demoCount - partCount);
    const pct = (n) => (total ? Math.round((n / total) * 100) : 0);
    if (elements.distSegDemo) elements.distSegDemo.style.width = `${pct(demoCount)}%`;
    if (elements.distSegPart) elements.distSegPart.style.width = `${pct(partCount)}%`;
    if (elements.distSegMiss) elements.distSegMiss.style.width = `${total ? pct(missCount) : 100}%`;
    if (elements.distLabelDemo) elements.distLabelDemo.textContent = `${demoCount} (${pct(demoCount)}%)`;
    if (elements.distLabelPart) elements.distLabelPart.textContent = `${partCount} (${pct(partCount)}%)`;
    if (elements.distLabelMiss) elements.distLabelMiss.textContent = `${missCount} (${pct(missCount)}%)`;

    // Top Skill Gaps
    if (elements.compareTopGaps) {
      clear(elements.compareTopGaps);
      if (!gaps.length) {
        elements.compareTopGaps.append(make("p", "history-empty", total ? "All tracked requirements are demonstrated!" : "No gaps computed yet."));
      } else {
        gaps.forEach((g) => {
          const div = make("div", "analytics-item");
          div.append(make("strong", "", text(g.skill, "Gap")));
          div.append(make("span", "", text(g.task || g.status, "Not demonstrated in this inspected scope")));
          elements.compareTopGaps.append(div);
        });
      }
    }

    // Strengths
    if (elements.compareStrengths) {
      clear(elements.compareStrengths);
      if (!strengths.length) {
        elements.compareStrengths.append(make("p", "history-empty", "No demonstrated strengths recorded yet."));
      } else {
        strengths.forEach((s) => {
          const div = make("div", "analytics-item");
          div.append(make("strong", "", `✓ ${text(s.skill, "Skill")}`));
          div.append(make("span", "", `Verified across ${s.file_count || 1} inspected file${s.file_count === 1 ? "" : "s"}`));
          elements.compareStrengths.append(div);
        });
      }
    }

    // Requirements Comparison Table
    if (elements.compareTableBody) {
      clear(elements.compareTableBody);
      const q = (state.compareTableSearch || "").trim().toLowerCase();
      const f = state.compareTableFilter || "all";
      const filteredRows = rows.filter((r) => {
        if (f === "changed" && !r.status_changed && !(r.evidence_added?.length || r.evidence_removed?.length)) return false;
        if (f !== "all" && f !== "changed" && r.after_status_code !== f) return false;
        if (!q) return true;
        return `${r.skill || ""} ${r.before_status || ""} ${r.after_status || ""}`.toLowerCase().includes(q);
      });

      if (!filteredRows.length) {
        const tr = document.createElement("tr");
        const td = make("td", "history-empty", rows.length ? "No requirements match the filter." : "Connect a job and repository to view the comparison matrix.");
        td.colSpan = 7;
        tr.append(td);
        elements.compareTableBody.append(tr);
      } else {
        filteredRows.forEach((r, idx) => {
          const tr = document.createElement("tr");
          tr.append(make("td", "", String(idx + 1)));
          tr.append(make("td", "", text(r.skill, "Requirement")));
          tr.append(make("td", "", formatEvidenceShort(r.before_evidence)));
          tr.append(make("td", "", formatEvidenceShort(r.after_evidence)));
          const sc = statusClass(r.after_status_code, r.after_status);
          const statusTd = document.createElement("td");
          statusTd.append(make("span", `status-chip status-chip--${sc}`, text(r.after_status, "Unreported")));
          tr.append(statusTd);

          const deltaTd = document.createElement("td");
          const addedCount = (r.evidence_added || []).length;
          if (r.status_changed) {
            deltaTd.append(make("span", "delta-pill delta-pill--up", `↑ ${r.before_status_code === "not_demonstrated" ? "New Proof" : "Updated"}`));
          } else if (addedCount > 0) {
            deltaTd.append(make("span", "delta-pill delta-pill--up", `+${addedCount} file${addedCount === 1 ? "" : "s"}`));
          } else {
            deltaTd.append(make("span", "delta-pill delta-pill--same", "Unchanged"));
          }
          tr.append(deltaTd);

          const actionTd = document.createElement("td");
          const viewBtn = make("button", "view-evidence-btn", "View");
          viewBtn.type = "button";
          viewBtn.addEventListener("click", () => {
            state.selectedSkillKey = r.skill_key;
            state.selectedEvidenceIndex = 0;
            switchView("result");
            renderSkills();
          });
          actionTd.append(viewBtn);
          tr.append(actionTd);
          elements.compareTableBody.append(tr);
        });
      }
    }
  }

  async function showComparison(currentId, previousId, { stayInView = false } = {}) {
    try {
      const comparison = await api(`/api/assessments/${currentId}/compare/${previousId}`);
      state.lastComparison = comparison;
      clear(elements.comparisonMeta);
      clear(elements.comparisonGrid);
      elements.comparisonPanel.hidden = false;
      elements.comparisonMeta.append(
        make("span", "", `before ${shortSha(comparison.previous_snapshot?.commit_sha)}`),
        make("span", "", `after ${shortSha(comparison.current_snapshot?.commit_sha)}`)
      );
      if (comparison.score_delta !== null && comparison.score_delta !== undefined) {
        elements.comparisonMeta.append(make("span", "", `fit score ${comparison.score_delta >= 0 ? "+" : ""}${comparison.score_delta}%`));
      }
      const changes = Array.isArray(comparison.skill_changes) ? comparison.skill_changes : [];
      if (!changes.length) {
        elements.comparisonGrid.append(make("p", "history-empty", comparison.message || "No validated evidence change was reported."));
      } else {
        changes.forEach((change) => {
          const item = make("article", "comparison-item");
          item.append(make("h3", "", text(change.skill, "Requirement")));
          const transition = change.status_changed
            ? `${text(change.before_status, "unreported")} → ${text(change.after_status, "unreported")}`
            : "Status unchanged; validated evidence changed.";
          item.append(make("p", "comparison-change", transition));
          if (change.evidence_added?.length) {
            const added = make("p", "comparison-evidence", `Added evidence\n${evidenceListText(change.evidence_added)}`);
            item.append(added);
          }
          if (change.evidence_removed?.length) {
            const removed = make("p", "comparison-evidence", `Removed evidence\n${evidenceListText(change.evidence_removed)}`);
            item.append(removed);
          }
          if (change.claim_boundary) item.append(make("p", "comparison-change", change.claim_boundary));
          if (change.next_evidence_contract?.task) {
            item.append(make("p", "comparison-change", `Future evidence task: ${change.next_evidence_contract.task}`));
          }
          elements.comparisonGrid.append(item);
        });
      }
      renderCompareDashboard();
      if (!stayInView) {
        switchView("compare");
      }
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function initialize() {
    try {
      const health = await api("/api/health");
      if (health.status !== "ok") throw new Error("The local backend did not report a healthy state.");
      if (elements.backendOfflineBanner) elements.backendOfflineBanner.hidden = true;
      state.serverTelegram = health.telegram || null;
      state.serverJobSearch = health.job_search || null;
      await loadSavedJobs();
      await loadSavedRepositories();
      const savedId = localStorage.getItem(ACTIVE_REPOSITORY_KEY);
      if (savedId && /^\d+$/.test(savedId)) {
        await loadOverview(savedId);
      } else {
        setConnection("idle", "Ready to connect a repository or select a job");
      }
      elements.repositoryUrl.disabled = false;
      elements.connectRepositoryButton.disabled = false;
      renderAll();
    } catch (error) {
      if (elements.backendOfflineBanner) elements.backendOfflineBanner.hidden = false;
      setConnection("error", error.message || "The local backend is unavailable.");
    }
    startStatusRefresh();
  }

  if (elements.savedJobsSelect) elements.savedJobsSelect.addEventListener("change", onSavedJobSelectChange);
  if (elements.deleteJobButton) elements.deleteJobButton.addEventListener("click", deleteCurrentJob);
  if (elements.savedReposSelect) elements.savedReposSelect.addEventListener("change", onSavedRepoSelectChange);
  if (elements.deleteRepoButton) elements.deleteRepoButton.addEventListener("click", deleteCurrentRepository);
  if (elements.browseReposButton) elements.browseReposButton.addEventListener("click", onBrowseReposClick);
  if (elements.closeUserReposButton) elements.closeUserReposButton.addEventListener("click", () => {
    if (elements.userReposDrawer) elements.userReposDrawer.hidden = true;
  });
  if (elements.disconnectRepositoryButton) elements.disconnectRepositoryButton.addEventListener("click", disconnectCurrentRepository);
  elements.jobForm.addEventListener("submit", submitJob);
  elements.jobSearchForm.addEventListener("submit", searchJobs);
  if (elements.quickLiveJobsButton) {
    elements.quickLiveJobsButton.addEventListener("click", () => {
      if (elements.jobDiscovery) elements.jobDiscovery.open = true;
      const title = elements.jobTitle.value.trim() || "Python Developer";
      const city = elements.jobCity ? elements.jobCity.value.trim() : "";
      if (elements.jobSearchQuery) elements.jobSearchQuery.value = title;
      if (elements.jobSearchLocation && city) elements.jobSearchLocation.value = city;
      elements.jobDiscovery?.scrollIntoView({ behavior: "smooth", block: "start" });
      searchJobs(new Event("submit"));
    });
  }
  if (elements.jobDiscovery) {
    elements.jobDiscovery.addEventListener("toggle", () => {
      if (elements.jobDiscovery.open && !elements.jobSearchQuery.value) {
        if (elements.jobTitle.value) elements.jobSearchQuery.value = elements.jobTitle.value.trim();
        if (elements.jobCity && elements.jobCity.value) elements.jobSearchLocation.value = elements.jobCity.value.trim();
      }
    });
  }
  elements.jobSearchResults.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target.closest("button[data-job-search-index]") : null;
    if (!target) return;
    const index = Number(target.dataset.jobSearchIndex);
    if (Number.isInteger(index)) useJobSearchResult(index);
  });
  elements.repositoryForm.addEventListener("submit", submitRepository);
  elements.repositoryUrl.addEventListener("input", () => {
    clearTimeout(profileLookupTimer);
    profileLookupTimer = setTimeout(checkForProfileUrl, 350);
  });
  elements.repositoryUrl.addEventListener("change", checkForProfileUrl);
  elements.checkMonitorButton.addEventListener("click", checkMonitor);
  elements.refreshHistoryButton.addEventListener("click", async () => {
    try {
      await loadHistory();
      renderHistory();
      toast("Assessment history refreshed.");
    } catch (error) {
      toast(error.message, "error");
    }
  });
  elements.historyList.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target.closest("button[data-current-snapshot]") : null;
    if (!target) return;
    showComparison(target.dataset.currentSnapshot, target.dataset.previousSnapshot);
  });
  elements.viewComparisonButton.addEventListener("click", () => {
    if (state.history.length >= 2) {
      showComparison(state.history[0].id, state.history[1].id);
    } else {
      switchView("compare");
    }
  });
  elements.telegramPairButton.addEventListener("click", pairTelegram);
  elements.closeComparisonButton.addEventListener("click", () => {
    state.compareTableSearch = "";
    state.compareTableFilter = "all";
    if (elements.compareTableSearch) elements.compareTableSearch.value = "";
    if (elements.compareTableFilter) elements.compareTableFilter.value = "all";
    renderCompareDashboard();
  });

  // Top 3-Screen Navigation
  [elements.navTabSetup, elements.navTabResult, elements.navTabCompare].forEach((btn) => {
    if (!btn) return;
    btn.addEventListener("click", () => switchView(btn.dataset.navView));
  });
  if (elements.brandHomeLink) {
    elements.brandHomeLink.addEventListener("click", (e) => {
      e.preventDefault();
      switchView("setup");
    });
  }

  // Role Category Filter Pills
  if (elements.roleCategoryPills) {
    elements.roleCategoryPills.addEventListener("click", (event) => {
      const btn = event.target instanceof Element ? event.target.closest("button[data-category]") : null;
      if (!btn) return;
      state.roleCategory = btn.dataset.category || "all";
      elements.roleCategoryPills.querySelectorAll(".category-pill").forEach((el) => {
        el.classList.toggle("is-active", el === btn);
      });
      renderSetupWorkspace();
    });
  }
  if (elements.jobSearchQuery) {
    elements.jobSearchQuery.addEventListener("input", () => renderSetupWorkspace());
  }

  // Custom / Edit Job Form Drawer Controls
  if (elements.toggleCustomJobButton) {
    elements.toggleCustomJobButton.addEventListener("click", () => {
      if (elements.customJobDrawer) {
        elements.customJobDrawer.hidden = !elements.customJobDrawer.hidden;
      }
    });
  }
  if (elements.closeCustomJobButton) {
    elements.closeCustomJobButton.addEventListener("click", () => {
      if (elements.customJobDrawer) elements.customJobDrawer.hidden = true;
    });
  }
  if (elements.newJobModeButton) {
    elements.newJobModeButton.addEventListener("click", () => {
      if (elements.savedJobsSelect) elements.savedJobsSelect.value = "";
      state.job = null;
      elements.jobTitle.value = "";
      elements.jobCompany.value = "";
      if (elements.jobCity) elements.jobCity.value = "";
      elements.jobSourceUrl.value = "";
      elements.jobDescription.value = "";
      renderAll();
    });
  }
  if (elements.updateJobButton) {
    elements.updateJobButton.addEventListener("click", updateSelectedJob);
  }
  if (elements.fetchJobUrlButton) {
    elements.fetchJobUrlButton.addEventListener("click", fetchJobUrlOnly);
  }
  if (elements.validateRepoButton) {
    elements.validateRepoButton.addEventListener("click", validateRepository);
  }

  // Result View Controls: KPI Status Filter Cards, Search, Status Select, Reanalyze, Monitor Toggle
  [elements.kpiCardDemonstrated, elements.kpiCardPartial, elements.kpiCardMissing, elements.kpiCardTotal].forEach((card) => {
    if (!card) return;
    card.addEventListener("click", () => {
      const filter = card.dataset.statusFilter || "all";
      state.skillFilterStatus = filter;
      if (elements.skillFilterStatus) elements.skillFilterStatus.value = filter;
      [elements.kpiCardDemonstrated, elements.kpiCardPartial, elements.kpiCardMissing, elements.kpiCardTotal].forEach((c) => {
        if (c) c.classList.toggle("is-active", c === card);
      });
      renderSkills();
    });
  });
  if (elements.skillFilterSearch) {
    elements.skillFilterSearch.addEventListener("input", () => {
      state.skillFilterSearch = elements.skillFilterSearch.value;
      renderSkills();
    });
  }
  if (elements.skillFilterStatus) {
    elements.skillFilterStatus.addEventListener("change", () => {
      state.skillFilterStatus = elements.skillFilterStatus.value || "all";
      renderSkills();
    });
  }
  if (elements.reanalyzeButton) {
    elements.reanalyzeButton.addEventListener("click", reanalyzeRepository);
  }
  if (elements.toggleMonitorButton) {
    elements.toggleMonitorButton.addEventListener("click", toggleMonitor);
  }
  if (elements.toggleScopeDrawerButton) {
    elements.toggleScopeDrawerButton.addEventListener("click", () => {
      if (elements.scopeFilesDrawer) {
        elements.scopeFilesDrawer.open = !elements.scopeFilesDrawer.open;
        elements.scopeFilesDrawer.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  }

  // Compare View Controls
  if (elements.compareSnapshotSelect) {
    elements.compareSnapshotSelect.addEventListener("change", () => {
      const val = elements.compareSnapshotSelect.value;
      if (val && val.includes(":")) {
        const [curId, prevId] = val.split(":");
        showComparison(curId, prevId, { stayInView: true });
      }
    });
  }
  if (elements.compareTableSearch) {
    elements.compareTableSearch.addEventListener("input", () => {
      state.compareTableSearch = elements.compareTableSearch.value;
      renderCompareDashboard();
    });
  }
  if (elements.compareTableFilter) {
    elements.compareTableFilter.addEventListener("change", () => {
      state.compareTableFilter = elements.compareTableFilter.value || "all";
      renderCompareDashboard();
    });
  }
  window.addEventListener("beforeunload", () => {
    if (state.refreshTimer) window.clearInterval(state.refreshTimer);
  });

  renderAll();
  initialize();
})();
