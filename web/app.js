const SUPPORT_URL = "https://donate.stripe.com/7sY5kDean9QC9uzdwBbV601";
const SITE_NAME = "Dream Comics";
const FOLLOW_FORM_HASH = "#follow-form";
const DEFAULT_DESCRIPTION = "Dream Comics adapts actual dream journal entries and lucid dream adventures in the Storyverse into browser-readable comics and downloadable PDFs.";

const state = {
  comics: [],
  filteredComics: [],
  current: null,
  siteRoot: getSiteRoot(),
  readerMode: false,
};

const elements = {
  libraryView: document.querySelector("#library-view"),
  aboutView: document.querySelector("#about-view"),
  followView: document.querySelector("#follow-view"),
  whosView: document.querySelector("#whos-view"),
  librarySearch: document.querySelector("#library-search"),
  titleSearch: document.querySelector("#title-search"),
  dateSearch: document.querySelector("#date-search"),
  clearSearchButton: document.querySelector("#clear-search-button"),
  comicList: document.querySelector("#comic-list"),
  comicCount: document.querySelector("#comic-count"),
  oldestDate: document.querySelector("#oldest-date"),
  newestDate: document.querySelector("#newest-date"),
  readerPanel: document.querySelector(".reader-panel"),
  readerDate: document.querySelector("#reader-date"),
  readerTitle: document.querySelector("#reader-title"),
  shareUrl: document.querySelector("#share-url"),
  shareButton: document.querySelector("#share-button"),
  fullscreenButton: document.querySelector("#fullscreen-button"),
  downloadButton: document.querySelector("#download-button"),
  pageCountLabel: document.querySelector("#page-count-label"),
  pageStack: document.querySelector("#page-stack"),
  earliestButton: document.querySelector("#earliest-button"),
  latestButton: document.querySelector("#latest-button"),
  firstPageButton: document.querySelector("#first-page-button"),
  lastPageButton: document.querySelector("#last-page-button"),
  routeLinks: document.querySelectorAll("[data-route-link]"),
};

init();

async function init() {
  setAssetUrls();
  wireEvents();

  try {
    const response = await fetch(`${state.siteRoot}data/comics.json`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Comic manifest failed: ${response.status}`);
    }
    const payload = await response.json();
    state.comics = payload.comics || [];
    state.filteredComics = state.comics;
    renderLibrary();
    renderRoute();
  } catch (error) {
    renderError(error);
  }
}

function setAssetUrls() {
  document.querySelectorAll("[src^='assets/']").forEach((node) => {
    node.src = `${state.siteRoot}${node.getAttribute("src")}`;
  });
  document.querySelectorAll("[href='./']").forEach((node) => {
    node.href = state.siteRoot;
  });
  document.querySelectorAll("[href='./about/']").forEach((node) => {
    node.href = `${state.siteRoot}about/`;
  });
  document.querySelectorAll("[href='./follow/'], [href='./follow/#follow-form']").forEach((node) => {
    const hash = node.getAttribute("href").includes(FOLLOW_FORM_HASH) ? FOLLOW_FORM_HASH : "";
    node.href = `${state.siteRoot}follow/${hash}`;
  });
  document.querySelectorAll("[href='./whos-who/']").forEach((node) => {
    node.href = `${state.siteRoot}whos-who/`;
  });
}

function wireEvents() {
  elements.earliestButton.addEventListener("click", () => selectComic(state.filteredComics[0]?.slug));
  elements.latestButton.addEventListener("click", () => selectComic(state.filteredComics.at(-1)?.slug));
  elements.librarySearch.addEventListener("submit", (event) => event.preventDefault());
  elements.titleSearch.addEventListener("input", applySearchFilter);
  elements.dateSearch.addEventListener("input", applySearchFilter);
  elements.clearSearchButton.addEventListener("click", clearSearch);
  elements.firstPageButton.addEventListener("click", () => scrollToPage(0));
  elements.lastPageButton.addEventListener("click", () => scrollToPage(state.current?.pages.length - 1));
  elements.shareButton.addEventListener("click", () => copyComicLink(state.current, elements.shareButton));
  elements.fullscreenButton.addEventListener("click", () => toggleReaderMode());
  document.addEventListener("fullscreenchange", syncReaderModeFromFullscreen);
  document.querySelectorAll("[data-follow-link]").forEach((link) => {
    link.addEventListener("click", (event) => {
      if (!shouldHandleInternalClick(event)) return;
      event.preventDefault();
      navigateToFollowForm();
    });
  });
  window.addEventListener("popstate", renderRoute);

  document.querySelectorAll(`a[href="${SUPPORT_URL}"]`).forEach((link) => {
    link.addEventListener("click", () => {});
  });
}

function renderRoute() {
  const route = getRoute();
  const isAbout = route.kind === "about";
  const isFollow = route.kind === "follow";
  const isWhosWho = route.kind === "whos-who";
  elements.aboutView.hidden = !isAbout;
  elements.followView.hidden = !isFollow;
  elements.whosView.hidden = !isWhosWho;
  elements.libraryView.hidden = isAbout || isFollow || isWhosWho;
  elements.routeLinks.forEach((link) => {
    const activeRoute = isAbout ? "about" : isFollow ? "follow" : isWhosWho ? "whos-who" : "library";
    link.classList.toggle("active", link.dataset.routeLink === activeRoute);
  });

  if ((isAbout || isFollow || isWhosWho) && state.readerMode) {
    setReaderMode(false);
  }

  if (isAbout) {
    updatePageMeta({
      title: "About Dream Comics",
      description: "Learn how Dream Comics adapts actual dream journal entries, lucid dreams, and Storyverse adventures into a growing comic series.",
      url: `${state.siteRoot}about/`,
      image: `${state.siteRoot}assets/generated/dream-comics-logo.png`,
    });
    return;
  }

  if (isFollow) {
    updatePageMeta({
      title: "Follow Dream Comics",
      description: "Follow Dream Comics by email and get new lucid dream comic releases when the site updates.",
      url: `${state.siteRoot}follow/`,
      image: `${state.siteRoot}assets/generated/dream-comics-logo.png`,
    });
    if (window.location.hash === FOLLOW_FORM_HASH) {
      scrollToFollowForm();
    }
    return;
  }

  if (isWhosWho) {
    updatePageMeta({
      title: "Who's Who | Dream Comics",
      description: "Meet Jet, Leon, Johnson, Second Brain, Skelebot, Overdrive, Savannah, Tecton, Chipper, and Lucid Light from Dream Comics.",
      url: `${state.siteRoot}whos-who/`,
      image: `${state.siteRoot}assets/characters/jet.png`,
    });
    return;
  }

  const selectedSlug = route.slug || state.comics[0]?.slug;
  renderReader(selectedSlug);
}

function renderLibrary() {
  elements.comicList.replaceChildren();

  state.comics.forEach((comic) => {
    const card = document.createElement("article");
    card.className = "comic-card";
    card.dataset.slug = comic.slug;
    card.innerHTML = `
      <button class="comic-card-main" type="button">
        <img src="${state.siteRoot}${comic.cover}" alt="${escapeHtml(comic.title)} cover" loading="lazy">
        <span>
          <span class="comic-date">${formatDate(comic.date)}</span>
          <span class="comic-title">${escapeHtml(comic.title)}</span>
          <span class="comic-pages">${comic.pages.length} pages</span>
        </span>
      </button>
      <button class="comic-share-button" type="button" aria-label="Copy share link for ${escapeHtml(comic.title)}">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 10.6 6.8-4.2"/><path d="m8.6 13.4 6.8 4.2"/></svg>
        <span>Copy Link</span>
      </button>
    `;
    card.querySelector(".comic-card-main").addEventListener("click", () => selectComic(comic.slug));
    card.querySelector(".comic-share-button").addEventListener("click", (event) => {
      copyComicLink(comic, event.currentTarget);
    });
    elements.comicList.append(card);
  });

  const noResults = document.createElement("p");
  noResults.id = "no-search-results";
  noResults.className = "no-search-results";
  noResults.textContent = "No comics match that search.";
  noResults.hidden = true;
  elements.comicList.append(noResults);

  setSearchDateBounds();
  applySearchFilter();
}

function renderReader(slug) {
  const comic = state.comics.find((candidate) => candidate.slug === slug) || state.comics[0];
  if (!comic) {
    renderError(new Error("No comics found. Add a dated comic folder with page images and rebuild the site."));
    return;
  }

  state.current = comic;
  updatePageMeta({
    title: `${comic.title} | Dream Comics`,
    description: comic.description || `Read ${comic.title}, a Dream Comics lucid dream comic dated ${comic.date}.`,
    url: `${state.siteRoot}comics/${comic.slug}/`,
    image: `${state.siteRoot}${comic.cover}`,
    type: "article",
  });
  elements.readerDate.textContent = formatDate(comic.date);
  elements.readerTitle.textContent = comic.title;
  elements.shareUrl.textContent = getComicUrl(comic);
  elements.shareUrl.href = `${state.siteRoot}comics/${comic.slug}/`;
  resetCopyButton(elements.shareButton);
  elements.downloadButton.href = `${state.siteRoot}${comic.pdf}`;
  elements.downloadButton.setAttribute("download", comic.pdfName || `${comic.slug}.pdf`);
  elements.pageCountLabel.textContent = `${comic.pages.length} pages`;
  resetReaderModeButton();

  elements.pageStack.replaceChildren();
  comic.pages.forEach((page, index) => {
    const image = document.createElement("img");
    image.className = "comic-page";
    image.id = `page-${index + 1}`;
    image.src = `${state.siteRoot}${page}`;
    image.alt = `${comic.title} page ${index + 1}`;
    image.loading = index < 2 ? "eager" : "lazy";
    elements.pageStack.append(image);
  });

  document.querySelectorAll(".comic-card").forEach((card) => {
    card.classList.toggle("active", card.dataset.slug === comic.slug);
  });
}

function setSearchDateBounds() {
  if (!state.comics.length) return;
  elements.dateSearch.min = state.comics[0].date;
  elements.dateSearch.max = state.comics.at(-1).date;
}

function applySearchFilter() {
  const titleQuery = normalizeSearch(elements.titleSearch.value);
  const dateQuery = elements.dateSearch.value;

  state.filteredComics = state.comics.filter((comic) => {
    const matchesTitle = !titleQuery || normalizeSearch(comic.title).includes(titleQuery);
    const matchesDate = !dateQuery || comic.date === dateQuery;
    return matchesTitle && matchesDate;
  });

  const resultSlugs = new Set(state.filteredComics.map((comic) => comic.slug));
  elements.comicList.querySelectorAll(".comic-card").forEach((card) => {
    card.hidden = !resultSlugs.has(card.dataset.slug);
  });

  const noResults = document.querySelector("#no-search-results");
  if (noResults) {
    noResults.hidden = state.filteredComics.length > 0;
  }

  updateLibrarySummary();
}

function clearSearch() {
  elements.titleSearch.value = "";
  elements.dateSearch.value = "";
  applySearchFilter();
  elements.titleSearch.focus();
}

function updateLibrarySummary() {
  const filteredCount = state.filteredComics.length;
  const totalCount = state.comics.length;
  const hasSearch = Boolean(elements.titleSearch.value || elements.dateSearch.value);
  const comicWord = totalCount === 1 ? "comic" : "comics";
  elements.comicCount.textContent = hasSearch ? `${filteredCount} of ${totalCount} ${comicWord}` : `${totalCount} ${totalCount === 1 ? "comic" : "comics"}`;
  elements.oldestDate.textContent = state.filteredComics[0] ? `Oldest: ${formatDate(state.filteredComics[0].date)}` : "Oldest";
  elements.newestDate.textContent = state.filteredComics.at(-1) ? `Newest: ${formatDate(state.filteredComics.at(-1).date)}` : "Newest";
}

function normalizeSearch(value) {
  return value.trim().toLocaleLowerCase();
}

function selectComic(slug) {
  if (!slug) return;
  history.pushState({}, "", `${state.siteRoot}comics/${slug}/`);
  renderRoute();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function navigateToFollowForm() {
  history.pushState({}, "", `${state.siteRoot}follow/${FOLLOW_FORM_HASH}`);
  renderRoute();
  scrollToFollowForm();
}

function scrollToFollowForm() {
  window.requestAnimationFrame(() => {
    document.querySelector(FOLLOW_FORM_HASH)?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function shouldHandleInternalClick(event) {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

function scrollToPage(index) {
  const pages = elements.pageStack.querySelectorAll(".comic-page");
  const page = pages[index];
  if (page) {
    page.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

async function toggleReaderMode() {
  await setReaderMode(!state.readerMode);
}

async function setReaderMode(enabled) {
  state.readerMode = enabled;
  document.body.classList.toggle("reader-fullscreen", enabled);
  resetReaderModeButton();

  if (enabled && elements.readerPanel.requestFullscreen && document.fullscreenElement !== elements.readerPanel) {
    try {
      await elements.readerPanel.requestFullscreen();
    } catch (error) {
      document.body.classList.add("reader-fullscreen");
    }
    return;
  }

  if (!enabled && document.fullscreenElement) {
    try {
      await document.exitFullscreen();
    } catch (error) {
      document.body.classList.remove("reader-fullscreen");
    }
  }
}

function syncReaderModeFromFullscreen() {
  const enabled = document.fullscreenElement === elements.readerPanel;
  state.readerMode = enabled;
  document.body.classList.toggle("reader-fullscreen", state.readerMode);
  resetReaderModeButton();
}

function resetReaderModeButton() {
  if (!elements.fullscreenButton) return;
  const text = elements.fullscreenButton.querySelector("span");
  if (text) {
    text.textContent = state.readerMode ? "Exit Reader" : "Reader Mode";
  }
  elements.fullscreenButton.setAttribute("aria-pressed", String(state.readerMode));
}

async function copyComicLink(comic, button) {
  if (!comic || !button) return;

  const url = getComicUrl(comic);
  try {
    await copyText(url);
    setCopyButtonState(button, "Copied");
  } catch (error) {
    setCopyButtonState(button, "Copy Failed");
  }
}

async function copyText(value) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const field = document.createElement("textarea");
  field.value = value;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.top = "-9999px";
  document.body.append(field);
  field.select();

  const copied = document.execCommand("copy");
  field.remove();
  if (!copied) {
    throw new Error("Copy command failed");
  }
}

function setCopyButtonState(button, label) {
  const text = button.querySelector("span");
  if (text) {
    text.textContent = label;
  } else {
    button.append(label);
  }
  button.classList.toggle("copied", label === "Copied");
  window.setTimeout(() => resetCopyButton(button), 1800);
}

function resetCopyButton(button) {
  if (!button) return;
  const text = button.querySelector("span");
  if (text) {
    text.textContent = "Copy Link";
  }
  button.classList.remove("copied");
}

function getComicUrl(comic) {
  return new URL(`${state.siteRoot}comics/${comic.slug}/`, window.location.origin).href;
}

function updatePageMeta({ title, description, url, image, type = "website" }) {
  const absoluteUrlValue = absoluteUrl(url || state.siteRoot);
  const absoluteImageValue = absoluteUrl(image || `${state.siteRoot}assets/generated/dream-comics-logo.png`);
  document.title = title;
  setMeta("name", "description", description || DEFAULT_DESCRIPTION);
  setMeta("name", "robots", "index, follow");
  setLink("canonical", absoluteUrlValue);
  setMeta("property", "og:type", type);
  setMeta("property", "og:site_name", SITE_NAME);
  setMeta("property", "og:title", title);
  setMeta("property", "og:description", description || DEFAULT_DESCRIPTION);
  setMeta("property", "og:url", absoluteUrlValue);
  setMeta("property", "og:image", absoluteImageValue);
  setMeta("name", "twitter:card", "summary_large_image");
  setMeta("name", "twitter:title", title);
  setMeta("name", "twitter:description", description || DEFAULT_DESCRIPTION);
  setMeta("name", "twitter:image", absoluteImageValue);
}

function setMeta(attribute, key, content) {
  let node = document.querySelector(`meta[${attribute}="${key}"]`);
  if (!node) {
    node = document.createElement("meta");
    node.setAttribute(attribute, key);
    document.head.append(node);
  }
  node.setAttribute("content", content);
}

function setLink(rel, href) {
  let node = document.querySelector(`link[rel="${rel}"]`);
  if (!node) {
    node = document.createElement("link");
    node.setAttribute("rel", rel);
    document.head.append(node);
  }
  node.setAttribute("href", href);
}

function absoluteUrl(value) {
  return new URL(value, window.location.origin).href;
}

function getRoute() {
  const path = window.location.pathname;
  if (path.endsWith("/about/") || path.endsWith("/about")) {
    return { kind: "about" };
  }

  if (path.endsWith("/follow/") || path.endsWith("/follow")) {
    return { kind: "follow" };
  }

  if (path.endsWith("/whos-who/") || path.endsWith("/whos-who")) {
    return { kind: "whos-who" };
  }

  const match = path.match(/\/comics\/([^/]+)\/?$/);
  return { kind: "library", slug: match ? decodeURIComponent(match[1]) : "" };
}

function getSiteRoot() {
  const path = window.location.pathname;
  const repoSegment = "/Dream-Comics/";
  if (path.startsWith(repoSegment)) {
    return repoSegment;
  }
  return "/";
}

function formatDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

function renderError(error) {
  elements.readerTitle.textContent = "Dream Comics could not load";
  elements.pageStack.innerHTML = `<p class="share-url">${escapeHtml(error.message)}</p>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#039;",
    };
    return entities[char];
  });
}
