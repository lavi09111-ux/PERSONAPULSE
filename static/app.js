/**
 * PersonaPulse - Web App Frontend Core Script
 */

document.addEventListener("DOMContentLoaded", () => {
  // Global State
  const state = {
    personas: {},
    activePersonaId: "tech_professional",
    currentDigest: null,
    articles: [],
    artifacts: {},
    activeTab: "feed",
    activeArtifactKey: "step5_presentation",
    isSpeaking: false,
    viewMode: "grid", // grid | list
    likedArticles: new Set(),
    dislikedArticles: new Set(),
    bookmarkedArticles: new Set()
  };

  // Persona Icons Mapping
  const personaIcons = {
    tech_professional: "💻",
    student: "🎓",
    finance_enthusiast: "📈",
    sports_fan: "⚽",
    default: "👤"
  };

  // DOM Elements
  const personaContainer = document.getElementById("persona-cards-container");
  const heroInsightText = document.getElementById("hero-insight-text");
  const metaPersonaName = document.getElementById("meta-persona-name");
  const metaArticleCount = document.getElementById("meta-article-count");
  const metaGeneratedAt = document.getElementById("meta-generated-at");
  const articlesContainer = document.getElementById("articles-container");
  const feedCountBadge = document.getElementById("feed-count-badge");
  const searchInput = document.getElementById("feed-search-input");
  
  const btnRunPipelineMain = document.getElementById("btn-run-pipeline-main");
  const btnRunPipelineTab = document.getElementById("btn-run-pipeline-tab");
  const btnReadAloud = document.getElementById("btn-read-aloud");
  const btnCopyInsight = document.getElementById("btn-copy-insight");
  
  const btnViewGrid = document.getElementById("btn-view-grid");
  const btnViewList = document.getElementById("btn-view-list");
  
  const customModal = document.getElementById("custom-persona-modal");
  const btnAddPersonaModal = document.getElementById("btn-add-persona-modal");
  const btnCancelModal = document.getElementById("btn-cancel-modal");
  const createPersonaForm = document.getElementById("create-persona-form");

  const matrixJsonViewer = document.getElementById("matrix-json-viewer");
  const pipelineLogOutput = document.getElementById("pipeline-log-output");

  // ---------------------------------------------------------------------------
  // Initialize Application
  // ---------------------------------------------------------------------------
  async function init() {
    setupTabNavigation();
    setupEventListeners();
    await fetchPersonas();
    if (Object.keys(state.personas).length > 0) {
      const firstId = Object.keys(state.personas)[0];
      state.activePersonaId = state.personas["tech_professional"] ? "tech_professional" : firstId;
    }
    renderPersonas();
    await loadPersonaDigest(state.activePersonaId);
    await fetchArtifacts();
  }

  // ---------------------------------------------------------------------------
  // Tab Navigation
  // ---------------------------------------------------------------------------
  function setupTabNavigation() {
    document.querySelectorAll(".nav-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        const targetTab = tab.dataset.tab;
        state.activeTab = targetTab;

        document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");

        document.querySelectorAll(".tab-view").forEach(view => {
          view.style.display = "none";
          view.classList.remove("active");
        });

        const activeView = document.getElementById(`view-${targetTab}`);
        if (activeView) {
          activeView.style.display = "block";
          activeView.classList.add("active");
        }
      });
    });
  }

  // ---------------------------------------------------------------------------
  // API Calls & Data Fetching
  // ---------------------------------------------------------------------------

  async function fetchPersonas() {
    try {
      const res = await fetch("/api/personas");
      const data = await res.json();
      if (data.success) {
        state.personas = data.personas;
      }
    } catch (err) {
      showToast("⚠️ Could not load personas from backend", "error");
    }
  }

  async function loadPersonaDigest(personaId) {
    state.activePersonaId = personaId;
    renderPersonas();

    heroInsightText.innerHTML = `<span style="opacity: 0.6;">Loading latest weekly digest pulse for ${getPersonaDisplayName(personaId)}...</span>`;
    articlesContainer.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">
      <div style="font-size: 2rem; margin-bottom: 0.5rem; animation: spin 1s infinite linear;">⚡</div>
      Loading curated news digest...
    </div>`;

    try {
      const res = await fetch(`/api/digests/${personaId}`);
      const data = await res.json();

      if (data.success && data.digest) {
        state.currentDigest = data.digest;
        state.articles = data.digest.articles || [];
        renderDigestHero(data.digest);
        renderArticles(state.articles);
      } else {
        // No digest present yet - suggest running pipeline
        heroInsightText.innerHTML = `<em>No pre-cached digest found for <strong>${getPersonaDisplayName(personaId)}</strong>. Click "Refresh Pulse Live" to execute the 5-agent pipeline now!</em>`;
        metaPersonaName.textContent = `Persona: ${getPersonaDisplayName(personaId)}`;
        metaArticleCount.textContent = "Articles: 0";
        metaGeneratedAt.textContent = "Updated: Never";
        articlesContainer.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; background: var(--bg-card); border-radius: var(--radius-md); border: 1px dashed var(--border-color);">
          <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🤖</div>
          <p style="color: var(--text-secondary); margin-bottom: 1rem;">No news articles available for this persona yet.</p>
          <button class="btn-primary" onclick="document.getElementById('btn-run-pipeline-main').click()">
            ⚡ Run 5-Agent Pipeline Now
          </button>
        </div>`;
      }
    } catch (err) {
      showToast("❌ Error loading digest payload", "error");
    }
  }

  async function fetchArtifacts() {
    try {
      const res = await fetch("/api/agent-artifacts");
      const data = await res.json();
      if (data.success) {
        state.artifacts = data.artifacts;
        renderArtifactViewer(state.activeArtifactKey);
      }
    } catch (err) {
      console.error("Artifact load error:", err);
    }
  }

  // ---------------------------------------------------------------------------
  // Rendering UI Components
  // ---------------------------------------------------------------------------

  function getPersonaDisplayName(personaId) {
    return state.personas[personaId]?.display_name || personaId;
  }

  function renderPersonas() {
    personaContainer.innerHTML = "";

    Object.entries(state.personas).forEach(([id, p]) => {
      const icon = personaIcons[id] || personaIcons.default;
      const isActive = id === state.activePersonaId;

      const card = document.createElement("div");
      card.className = `persona-card ${isActive ? "active" : ""}`;
      card.onclick = () => loadPersonaDigest(id);

      const topicsHTML = (p.topics || [])
        .map(t => `<span class="topic-tag">#${t}</span>`)
        .join("");

      const excludeHTML = (p.exclude_keywords || []).length > 0
        ? `<span class="exclude-tag">🚫 Exclude: ${p.exclude_keywords.join(", ")}</span>`
        : "";

      card.innerHTML = `
        <div class="persona-header">
          <div class="persona-avatar">${icon}</div>
          <div class="persona-name">${p.display_name}</div>
        </div>
        <div class="persona-topics">${topicsHTML}</div>
        ${excludeHTML}
      `;

      personaContainer.appendChild(card);
    });

    // Add Persona Card Button
    const addCard = document.createElement("div");
    addCard.className = "persona-card add-persona-card";
    addCard.onclick = () => openModal();
    addCard.innerHTML = `
      <div style="font-size: 1.5rem;">➕</div>
      <div style="font-size: 0.9rem; font-weight: 600;">Custom Persona</div>
    `;
    personaContainer.appendChild(addCard);
  }

  function renderDigestHero(digest) {
    heroInsightText.textContent = digest.insight || "No summary available.";
    metaPersonaName.textContent = `Persona: ${digest.persona || getPersonaDisplayName(state.activePersonaId)}`;
    metaArticleCount.textContent = `Articles: ${digest.article_count || digest.articles?.length || 0}`;

    const dateStr = digest.generated_at ? new Date(digest.generated_at).toLocaleString() : "Recently";
    metaGeneratedAt.textContent = `Updated: ${dateStr}`;
  }

  function renderArticles(articlesList) {
    articlesContainer.innerHTML = "";
    feedCountBadge.textContent = `Showing ${articlesList.length} stories`;

    if (!articlesList || articlesList.length === 0) {
      articlesContainer.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2.5rem; color: var(--text-muted);">
        No articles match your search filter.
      </div>`;
      return;
    }

    articlesList.forEach((art, index) => {
      const card = document.createElement("article");
      card.className = "article-card";

      const pubDate = art.published_at ? new Date(art.published_at).toLocaleDateString() : "";
      const source = art.source || "News Source";

      const bulletsHTML = (art.bullet_points || [])
        .map(b => `<li class="bullet-item">${b}</li>`)
        .join("");

      const isLiked = state.likedArticles.has(index);
      const isDisliked = state.dislikedArticles.has(index);
      const isBookmarked = state.bookmarkedArticles.has(index);

      card.innerHTML = `
        <div>
          <div class="article-meta">
            <span class="source-badge">${source}</span>
            <span class="date-text">${pubDate}</span>
          </div>
          <h3 class="article-title">${art.title}</h3>
          <ul class="bullet-list">${bulletsHTML}</ul>
        </div>
        <div class="article-footer">
          <a href="${art.url}" target="_blank" rel="noopener noreferrer" class="article-link">
            <span>Read Original</span> <span>↗</span>
          </a>
          <div class="feedback-btns">
            <button class="feedback-btn ${isLiked ? 'active-like' : ''}" data-action="like" data-idx="${index}" title="Like story">👍</button>
            <button class="feedback-btn ${isDisliked ? 'active-dislike' : ''}" data-action="dislike" data-idx="${index}" title="Dislike story">👎</button>
            <button class="feedback-btn ${isBookmarked ? 'active-like' : ''}" data-action="bookmark" data-idx="${index}" title="Bookmark">🔖</button>
            <button class="feedback-btn" data-action="copy" data-url="${art.url}" title="Copy Link">📋</button>
          </div>
        </div>
      `;

      articlesContainer.appendChild(card);
    });

    // Attach article button listeners
    articlesContainer.querySelectorAll(".feedback-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const action = btn.dataset.action;
        const idx = parseInt(btn.dataset.idx, 10);
        
        if (action === "like") {
          if (state.likedArticles.has(idx)) {
            state.likedArticles.delete(idx);
          } else {
            state.likedArticles.add(idx);
            state.dislikedArticles.delete(idx);
          }
          renderArticles(getFilteredArticles());
        } else if (action === "dislike") {
          if (state.dislikedArticles.has(idx)) {
            state.dislikedArticles.delete(idx);
          } else {
            state.dislikedArticles.add(idx);
            state.likedArticles.delete(idx);
          }
          renderArticles(getFilteredArticles());
        } else if (action === "bookmark") {
          if (state.bookmarkedArticles.has(idx)) {
            state.bookmarkedArticles.delete(idx);
            showToast("Removed from bookmarks");
          } else {
            state.bookmarkedArticles.add(idx);
            showToast("Saved to bookmarks 🔖");
          }
          renderArticles(getFilteredArticles());
        } else if (action === "copy") {
          navigator.clipboard.writeText(btn.dataset.url);
          showToast("Article URL copied to clipboard! 📋");
        }
      });
    });
  }

  function getFilteredArticles() {
    const q = searchInput.value.toLowerCase().trim();
    if (!q) return state.articles;

    return state.articles.filter(art => {
      const titleMatch = (art.title || "").toLowerCase().includes(q);
      const sourceMatch = (art.source || "").toLowerCase().includes(q);
      const bulletMatch = (art.bullet_points || []).some(b => b.toLowerCase().includes(q));
      return titleMatch || sourceMatch || bulletMatch;
    });
  }

  // ---------------------------------------------------------------------------
  // Live Pipeline Execution Animation
  // ---------------------------------------------------------------------------

  async function triggerPipelineRun() {
    const personaId = state.activePersonaId;
    const displayName = getPersonaDisplayName(personaId);

    showToast(`⚡ Starting 5-agent pipeline run for ${displayName}...`);

    // Switch to Pipeline tab view to display telemetry
    const pipelineTabBtn = document.querySelector('[data-tab="pipeline"]');
    if (pipelineTabBtn) pipelineTabBtn.click();

    btnRunPipelineMain.disabled = true;
    btnRunPipelineTab.disabled = true;

    // Reset Stepper UI
    for (let i = 1; i <= 5; i++) {
      const step = document.getElementById(`step-${i}`);
      step.classList.remove("completed", "active");
    }

    pipelineLogOutput.textContent = `[PIPELINE LAUNCHED] Persona: '${personaId}' (${displayName})\nInitializing Google ADK Multi-Agent Runners...\n`;

    // Step-by-step progress simulation while server runs
    updateStepUI(1, "active");
    appendLog(`[Step 1/5] Executing News Fetch Agent via NewsAPI / MCP tool...`);

    try {
      const responsePromise = fetch("/api/pipeline/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ persona_id: personaId })
      });

      // Animate progress steps smoothly
      await sleep(1500);
      updateStepUI(1, "completed");
      updateStepUI(2, "active");
      appendLog(`[Step 2/5] Executing Ranking & Filtering Agent (Evaluating topic relevance)...`);

      await sleep(1800);
      updateStepUI(2, "completed");
      updateStepUI(3, "active");
      appendLog(`[Step 3/5] Executing Content Reshaping Agent (Extracting concise key bullet points)...`);

      await sleep(1500);
      updateStepUI(3, "completed");
      updateStepUI(4, "active");
      appendLog(`[Step 4/5] Executing Insight Generation Agent (Synthesizing executive pulse)...`);

      await sleep(1500);
      updateStepUI(4, "completed");
      updateStepUI(5, "active");
      appendLog(`[Step 5/5] Executing Presentation Agent (Compiling final digest payload)...`);

      const res = await responsePromise;
      const data = await res.json();

      if (data.success && data.digest) {
        updateStepUI(5, "completed");
        appendLog(`\n[PIPELINE COMPLETED SUCCESSFULLY!]`);
        appendLog(`- Persona: ${data.digest.persona}`);
        appendLog(`- Articles Processed: ${data.digest.article_count || data.digest.articles?.length}`);
        appendLog(`- Insight Summary: "${data.digest.insight}"`);

        showToast(`✨ Pipeline finished successfully for ${displayName}!`, "success");

        state.currentDigest = data.digest;
        state.articles = data.digest.articles || [];
        renderDigestHero(data.digest);
        renderArticles(state.articles);

        await fetchArtifacts();
      } else {
        appendLog(`\n[ERROR] Pipeline run failed: ${data.error}`);
        showToast(`❌ Pipeline failed: ${data.error}`, "error");
      }

    } catch (err) {
      appendLog(`\n[ERROR] Connection error: ${err.message}`);
      showToast(`❌ Connection error running pipeline`, "error");
    } finally {
      btnRunPipelineMain.disabled = false;
      btnRunPipelineTab.disabled = false;
    }
  }

  function updateStepUI(stepNum, status) {
    const step = document.getElementById(`step-${stepNum}`);
    if (!step) return;
    if (status === "active") {
      step.classList.add("active");
      step.classList.remove("completed");
    } else if (status === "completed") {
      step.classList.remove("active");
      step.classList.add("completed");
    }
  }

  function appendLog(text) {
    pipelineLogOutput.textContent += text + "\n";
    pipelineLogOutput.scrollTop = pipelineLogOutput.scrollHeight;
  }

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ---------------------------------------------------------------------------
  // Data Matrix Viewer
  // ---------------------------------------------------------------------------

  function renderArtifactViewer(key) {
    state.activeArtifactKey = key;
    document.querySelectorAll(".matrix-tab").forEach(tab => {
      tab.classList.toggle("active", tab.dataset.artifact === key);
    });

    const payload = state.artifacts[key];
    if (payload) {
      matrixJsonViewer.textContent = JSON.stringify(payload, null, 2);
    } else {
      matrixJsonViewer.textContent = "// No JSON output available for this step yet. Run the pipeline to generate artifacts.";
    }
  }

  document.querySelectorAll(".matrix-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      renderArtifactViewer(tab.dataset.artifact);
    });
  });

  // ---------------------------------------------------------------------------
  // Event Listeners
  // ---------------------------------------------------------------------------

  function setupEventListeners() {
    // Pipeline Trigger Buttons
    btnRunPipelineMain.addEventListener("click", triggerPipelineRun);
    btnRunPipelineTab.addEventListener("click", triggerPipelineRun);

    // Search input
    searchInput.addEventListener("input", () => {
      renderArticles(getFilteredArticles());
    });

    // View mode toggle
    btnViewGrid.addEventListener("click", () => {
      state.viewMode = "grid";
      btnViewGrid.classList.add("active");
      btnViewList.classList.remove("active");
      articlesContainer.classList.remove("list-view");
    });

    btnViewList.addEventListener("click", () => {
      state.viewMode = "list";
      btnViewList.classList.add("active");
      btnViewGrid.classList.remove("active");
      articlesContainer.classList.add("list-view");
    });

    // Text to Speech
    btnReadAloud.addEventListener("click", () => {
      if (!('speechSynthesis' in window)) {
        showToast("Text-to-speech is not supported in this browser.", "error");
        return;
      }

      if (state.isSpeaking) {
        window.speechSynthesis.cancel();
        state.isSpeaking = false;
        btnReadAloud.textContent = "🔊";
        showToast("Audio stopped");
      } else {
        const text = heroInsightText.textContent;
        if (!text || text.includes("Loading")) return;

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.onend = () => {
          state.isSpeaking = false;
          btnReadAloud.textContent = "🔊";
        };

        window.speechSynthesis.speak(utterance);
        state.isSpeaking = true;
        btnReadAloud.textContent = "⏹️";
        showToast("Reading executive pulse aloud... 🔊");
      }
    });

    // Copy Insight
    btnCopyInsight.addEventListener("click", () => {
      const text = heroInsightText.textContent;
      navigator.clipboard.writeText(text);
      showToast("Insight copied to clipboard! 📋");
    });

    // Create Custom Persona Modal
    btnAddPersonaModal.addEventListener("click", openModal);
    btnCancelModal.addEventListener("click", closeModal);
    customModal.addEventListener("click", (e) => {
      if (e.target === customModal) closeModal();
    });

    createPersonaForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("persona-name").value.trim();
      const topicsStr = document.getElementById("persona-topics").value.trim();
      const excludeStr = document.getElementById("persona-exclude").value.trim();

      if (!name || !topicsStr) {
        showToast("Please fill in the required fields.", "error");
        return;
      }

      const topics = topicsStr.split(",").map(t => t.trim()).filter(Boolean);
      const exclude_keywords = excludeStr ? excludeStr.split(",").map(k => k.trim()).filter(Boolean) : [];
      const id = name.toLowerCase().replace(/[^a-z0-9]/g, "_");

      try {
        const res = await fetch("/api/personas", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id, display_name: name, topics, exclude_keywords })
        });
        const data = await res.json();

        if (data.success) {
          state.personas = data.personas;
          state.activePersonaId = id;
          closeModal();
          renderPersonas();
          showToast(`Persona '${name}' created! Click "Refresh Pulse Live" to fetch news.`);
          loadPersonaDigest(id);
        } else {
          showToast(`Error: ${data.error}`, "error");
        }
      } catch (err) {
        showToast("Failed to create persona.", "error");
      }
    });
  }

  function openModal() {
    customModal.classList.add("open");
  }

  function closeModal() {
    customModal.classList.remove("open");
    createPersonaForm.reset();
  }

  function showToast(message, type = "info") {
    const toast = document.getElementById("toast-notification");
    const toastMsg = document.getElementById("toast-message");
    const toastIcon = document.getElementById("toast-icon");

    toastIcon.textContent = type === "error" ? "❌" : type === "success" ? "✨" : "⚡";
    toastMsg.textContent = message;

    toast.classList.add("show");
    setTimeout(() => {
      toast.classList.remove("show");
    }, 3500);
  }

  // Run initial setup
  init();
});
