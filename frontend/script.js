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
    refreshTimer: null,
    refreshBusy: false,
  };

  const byId = (id) => document.getElementById(id);
  const elements = {
    backendOfflineBanner: byId("backend-offline-banner"),
    connectionStatus: byId("connection-status"),
    savedJobsSelect: byId("saved-jobs-select"),
    deleteJobButton: byId("delete-job-button"),
    jobForm: byId("job-form"),
    jobTitle: byId("job-title"),
    jobCompany: byId("job-company"),
    jobSourceUrl: byId("job-source-url"),
    jobDescription: byId("job-description"),
    saveJobButton: byId("save-job-button"),
    jobFeedback: byId("job-form-feedback"),
    jobSearchForm: byId("job-search-form"),
    jobSearchQuery: byId("job-search-query"),
    jobSearchLocation: byId("job-search-location"),
    jobSearchCountry: byId("job-search-country"),
    searchJobsButton: byId("search-jobs-button"),
    jobSearchFeedback: byId("job-search-feedback"),
    jobSearchResults: byId("job-search-results"),
    repositoryForm: byId("repository-form"),
    repositoryUrl: byId("repository-url"),
    connectRepositoryButton: byId("connect-repository-button"),
    disconnectRepositoryButton: byId("disconnect-repository-button"),
    repositoryHelp: byId("repository-help"),
    repositoryFeedback: byId("repository-form-feedback"),
    userReposDrawer: byId("user-repos-drawer"),
    userReposTitle: byId("user-repos-title"),
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
    const jobLink = externalLink(`${state.job.company} job source`, state.job.source_url, "context-link");
    const repoLink = externalLink(`${state.repository.owner}/${state.repository.name}`, state.repository.repository_url, "context-link");
    elements.contextLinks.append(jobLink, repoLink);
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
    if (!assessment) {
      elements.fitScore.textContent = "—";
      elements.fitTitle.textContent = "No score received";
      elements.fitDescription.textContent = "A score is shown only when the assessment API returns its calculation or summary.";
      elements.fitFormula.textContent = "No calculation has been reported.";
      setTone(elements.assessmentState, "", "Awaiting assessment");
      return;
    }
    elements.fitScore.textContent = Number.isFinite(score?.value) ? `${score.value}%` : "—";
    const summary = assessment.summary || {};
    elements.fitTitle.textContent = Number.isFinite(score?.value) ? "Traceable evidence fit" : "No supported score";
    elements.fitDescription.textContent = `${summary.demonstrated || 0} demonstrated, ${summary.partially_demonstrated || 0} partial, and ${summary.not_demonstrated || 0} not demonstrated in this inspected scope.`;
    elements.fitFormula.textContent = score?.formula || "The backend did not return a score calculation.";
    setTone(elements.assessmentState, "ready", "Evidence assessed");
  }

  function renderSkillCard(item) {
    const card = make("article", `skill-card skill-card--${statusClass(item.status_code, item.status)}`);
    const header = make("div", "skill-card-header");
    header.append(make("h3", "", text(item.skill, "Unnamed requirement")));
    header.append(make("span", `status-chip status-chip--${statusClass(item.status_code, item.status)}`, text(item.status, "Unreported")));
    card.append(header);
    card.append(make("p", "skill-summary", item.explanation || "No explanation was returned for this requirement."));

    const meta = make("div", "skill-meta");
    meta.append(make("span", "", `Requirement: ${text(item.requirement_type, "required")}`));
    meta.append(make("span", "", `Confidence: ${text(item.confidence, "not reported")}`));
    if (item.changed_evidence?.length) meta.append(make("span", "", `${item.changed_evidence.length} changed evidence signal${item.changed_evidence.length === 1 ? "" : "s"}`));
    card.append(meta);

    const requirement = item.job_requirement;
    if (requirement?.source_excerpt) {
      const source = make("p", "limitation");
      source.append(make("strong", "", "Job requirement: "));
      source.append(document.createTextNode(requirement.source_excerpt));
      card.append(source);
    }
    if (item.llm_interpretation) {
      const interpretation = make("p", "limitation");
      interpretation.append(make("strong", "", "Optional interpretation: "));
      interpretation.append(document.createTextNode(item.llm_interpretation));
      card.append(interpretation);
    }
    if (Array.isArray(item.limitations) && item.limitations.length) {
      const limitation = make("p", "limitation");
      limitation.append(make("strong", "", "Limit: "));
      limitation.append(document.createTextNode(item.limitations[0]));
      card.append(limitation);
    }

    const evidence = Array.isArray(item.evidence) ? item.evidence : [];
    if (!evidence.length) {
      card.append(make("p", "evidence-empty", "No validated repository evidence was returned for this requirement in the inspected scope."));
      return card;
    }
    const list = make("ul", "evidence-list");
    evidence.forEach((entry) => {
      const evidenceItem = make("li", "evidence-item");
      const evidenceHeader = make("div", "evidence-head");
      const location = `${text(entry.path, "file")} · lines ${text(entry.start_line, "?")}-${text(entry.end_line, "?")}`;
      const pathNode = entry.url ? externalLink(text(entry.path, "file"), entry.url, "evidence-file") : make("span", "evidence-file", text(entry.path, "file"));
      evidenceHeader.append(pathNode, make("span", "evidence-line", `lines ${text(entry.start_line, "?")}-${text(entry.end_line, "?")}`));
      evidenceItem.append(evidenceHeader);
      evidenceItem.append(make("pre", "code-excerpt", text(entry.excerpt, "No excerpt returned.")));
      const note = `${text(entry.kind, "validated evidence")}${entry.changed_in_commit ? " · changed in this commit" : ""}`;
      evidenceItem.append(make("p", "evidence-note", note));
      evidenceItem.title = location;
      list.append(evidenceItem);
    });
    card.append(list);
    return card;
  }

  function renderSkills() {
    clear(elements.skillsGrid);
    const items = state.snapshot?.assessment?.skill_assessments;
    if (!Array.isArray(items) || !items.length) {
      const empty = make("div", "empty-state empty-state--wide");
      empty.append(make("span", "empty-state-icon", "⌘"));
      const copy = document.createElement("div");
      copy.append(make("h3", "", "No supported requirements assessed"));
      copy.append(make("p", "", "The job source was retained, but no supported requirement phrases were available for an evidence assessment."));
      empty.append(copy);
      elements.skillsGrid.append(empty);
      elements.skillsNote.textContent = "No supported skills were returned by the assessment API.";
      return;
    }
    items.forEach((item) => elements.skillsGrid.append(renderSkillCard(item)));
    const limits = state.snapshot?.assessment?.inspection_limits || {};
    elements.skillsNote.textContent = `${text(limits.inspected_file_count, "0")} files inspected; excerpts and paths are validated against that inspected content.`;
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

  function useJobSearchResult(index) {
    const result = state.jobSearchResults[index];
    if (!result) return;
    elements.jobTitle.value = result.title || "";
    elements.jobCompany.value = result.company === "Company not specified" ? "" : (result.company || "");
    elements.jobSourceUrl.value = result.posting_url || "";
    elements.jobDescription.value = result.description || "";
    const descriptionNotice = result.description
      ? "Selected posting loaded into the form. You can adjust details or save directly."
      : "Selected role title and company loaded. Enter skill requirements before saving.";
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
    setTone(elements.monitorState, tone, stateText === "active" ? "Watching commits" : stateText);
    elements.checkMonitorButton.disabled = !monitor.enabled;
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
    const paragraph = elements.scopeNotice.querySelector("p");
    if (!assessment || !paragraph) return;
    clear(paragraph);
    paragraph.append(make("strong", "", "How to read this dashboard: "));
    paragraph.append(document.createTextNode(assessment.scope_notice || "Evidence is limited to the inspected commit."));
  }

  function renderAll() {
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
      elements.jobCompany.value = state.job.company === "Company not specified" ? "" : (state.job.company || "");
      elements.jobSourceUrl.value = state.job.source_url || "";
      elements.jobDescription.value = state.job.description || "";
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
    if (state.repository) localStorage.setItem(ACTIVE_REPOSITORY_KEY, String(state.repository.id));
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
    elements.jobCompany.value = found.company === "Company not specified" ? "" : (found.company || "");
    elements.jobSourceUrl.value = found.source_url || "";
    elements.jobDescription.value = found.description || "";
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
        elements.repositoryUrl.value = "";
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
      renderAll();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  function startStatusRefresh() {
    if (state.refreshTimer) window.clearInterval(state.refreshTimer);
    state.refreshTimer = window.setInterval(refreshConnectedState, REFRESH_INTERVAL_MS);
  }

  async function submitJob(event) {
    event.preventDefault();
    setFeedback(elements.jobFeedback, "");
    const title = elements.jobTitle.value.trim();
    const company = elements.jobCompany.value.trim() || "Company not specified";
    const sourceUrl = elements.jobSourceUrl.value.trim();
    let description = elements.jobDescription.value.trim();
    if (!title) {
      setFeedback(elements.jobFeedback, "Enter a role title.", "error");
      return;
    }
    if (!description && !sourceUrl) {
      setFeedback(elements.jobFeedback, "Enter job-description requirements or a posting URL to fetch.", "error");
      return;
    }
    setButtonLoading(elements.saveJobButton, true, description ? "Saving job" : "Fetching page");
    try {
      if (!description && sourceUrl) {
        const fetched = await api("/api/jobs/fetch", { method: "POST", body: { source_url: sourceUrl } });
        elements.jobDescription.value = fetched.description || "";
        setFeedback(elements.jobFeedback, "Description fetched into the form. Review it, then select Save job requirements again.", "success");
        toast("Job text fetched. Review it before saving.", "success");
        return;
      }
      const body = { title, company, description };
      if (sourceUrl) body.source_url = sourceUrl;
      const payload = await api("/api/jobs", {
        method: "POST",
        body,
      });
      state.job = payload.job;
      elements.repositoryUrl.disabled = false;
      elements.connectRepositoryButton.disabled = false;
      elements.repositoryHelp.textContent = payload.warning || "Job saved. Connect or assess your GitHub repository.";
      setFeedback(elements.jobFeedback, payload.warning || `${payload.job.skills?.length || 0} supported requirement${payload.job.skills?.length === 1 ? "" : "s"} extracted from the supplied text.`, payload.warning ? "error" : "success");
      await loadSavedJobs();
      if (elements.savedJobsSelect) {
        elements.savedJobsSelect.value = String(state.job.id);
      }
      renderAll();
      toast(payload.warning || "Job requirements saved.", payload.warning ? "warning" : "success");
    } catch (error) {
      setFeedback(elements.jobFeedback, error.message, "error");
      toast(error.message, "error");
    } finally {
      setButtonLoading(elements.saveJobButton, false);
    }
  }

  async function submitRepository(event) {
    event.preventDefault();
    setFeedback(elements.repositoryFeedback, "");
    const repositoryUrl = elements.repositoryUrl.value.trim();
    if (!repositoryUrl) {
      setFeedback(elements.repositoryFeedback, "Enter a GitHub repository URL.", "error");
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
      setFeedback(elements.repositoryFeedback, payload.message || "Repository connected and assessed.", "success");
      toast(payload.message || "Repository connected and assessed.", "success");
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
    const username = profileMatch[1];
    if (elements.userReposDrawer) {
      elements.userReposDrawer.hidden = false;
      elements.userReposTitle.textContent = `Fetching public repositories for @${username}...`;
      clear(elements.userReposList);
    }
    try {
      const payload = await api(`/api/github/users/${username}/repositories`);
      const repos = Array.isArray(payload.repositories) ? payload.repositories : [];
      if (!repos.length) {
        if (elements.userReposTitle) elements.userReposTitle.textContent = `No public repositories found for @${username}.`;
        return;
      }
      if (elements.userReposTitle) {
        elements.userReposTitle.textContent = `📁 Public repositories for @${username} (${repos.length} found) — Click to select:`;
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
      if (elements.userReposTitle) elements.userReposTitle.textContent = `Could not fetch repositories for @${username}: ${err.message}`;
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
    event.preventDefault();
    const query = elements.jobSearchQuery.value.trim();
    const country = elements.jobSearchCountry.value.trim().toLowerCase();
    const location = elements.jobSearchLocation.value.trim();
    if (query.length < 2 || !/^[a-z]{2}$/i.test(country)) {
      setFeedback(elements.jobSearchFeedback, "Enter search terms and a two-letter country code, for example in.", "error");
      return;
    }
    setFeedback(elements.jobSearchFeedback, "");
    setButtonLoading(elements.searchJobsButton, true, "Searching");
    try {
      const payload = await api("/api/job-search", {
        method: "POST",
        body: { query, country, location: location || null },
      });
      state.jobSearchResults = Array.isArray(payload.results) ? payload.results : [];
      renderJobSearchResults();
      setFeedback(
        elements.jobSearchFeedback,
        state.jobSearchResults.length
          ? `${state.jobSearchResults.length} result${state.jobSearchResults.length === 1 ? "" : "s"} returned. Select one only after reviewing its URL and text.`
          : "No usable public posting URLs were returned. Paste a posting URL and description instead.",
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

  async function showComparison(currentId, previousId) {
    try {
      const comparison = await api(`/api/assessments/${currentId}/compare/${previousId}`);
      clear(elements.comparisonMeta);
      clear(elements.comparisonGrid);
      elements.comparisonPanel.hidden = false;
      elements.comparisonMeta.append(
        make("span", "", `before ${shortSha(comparison.previous_snapshot?.commit_sha)}`),
        make("span", "", `after ${shortSha(comparison.current_snapshot?.commit_sha)}`)
      );
      if (comparison.score_delta !== null && comparison.score_delta !== undefined) {
        elements.comparisonMeta.append(make("span", "", `fit score ${comparison.score_delta >= 0 ? "+" : ""}${comparison.score_delta}`));
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
      elements.comparisonPanel.scrollIntoView({ behavior: "smooth", block: "start" });
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
  if (elements.disconnectRepositoryButton) elements.disconnectRepositoryButton.addEventListener("click", disconnectCurrentRepository);
  elements.jobForm.addEventListener("submit", submitJob);
  elements.jobSearchForm.addEventListener("submit", searchJobs);
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
    if (state.history.length >= 2) showComparison(state.history[0].id, state.history[1].id);
  });
  elements.telegramPairButton.addEventListener("click", pairTelegram);
  elements.closeComparisonButton.addEventListener("click", () => {
    elements.comparisonPanel.hidden = true;
  });
  window.addEventListener("beforeunload", () => {
    if (state.refreshTimer) window.clearInterval(state.refreshTimer);
  });

  renderAll();
  initialize();
})();
