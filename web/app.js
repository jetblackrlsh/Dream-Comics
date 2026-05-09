const SUPPORT_URL = "https://donate.stripe.com/7sY5kDean9QC9uzdwBbV601";

const state = {
  comics: [],
  current: null,
  siteRoot: getSiteRoot(),
};

const elements = {
  libraryView: document.querySelector("#library-view"),
  aboutView: document.querySelector("#about-view"),
  comicList: document.querySelector("#comic-list"),
  comicCount: document.querySelector("#comic-count"),
  oldestDate: document.querySelector("#oldest-date"),
  newestDate: document.querySelector("#newest-date"),
  readerDate: document.querySelector("#reader-date"),
  readerTitle: document.querySelector("#reader-title"),
  shareUrl: document.querySelector("#share-url"),
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
}

function wireEvents() {
  elements.earliestButton.addEventListener("click", () => selectComic(state.comics[0]?.slug));
  elements.latestButton.addEventListener("click", () => selectComic(state.comics.at(-1)?.slug));
  elements.firstPageButton.addEventListener("click", () => scrollToPage(0));
  elements.lastPageButton.addEventListener("click", () => scrollToPage(state.current?.pages.length - 1));
  window.addEventListener("popstate", renderRoute);

  document.querySelectorAll(`a[href="${SUPPORT_URL}"]`).forEach((link) => {
    link.addEventListener("click", () => {});
  });
}

function renderRoute() {
  const route = getRoute();
  const isAbout = route.kind === "about";
  elements.aboutView.hidden = !isAbout;
  elements.libraryView.hidden = isAbout;
  elements.routeLinks.forEach((link) => {
    link.classList.toggle("active", link.dataset.routeLink === (isAbout ? "about" : "library"));
  });

  if (isAbout) {
    document.title = "About Dream Comics";
    return;
  }

  const selectedSlug = route.slug || state.comics[0]?.slug;
  renderReader(selectedSlug);
}

function renderLibrary() {
  elements.comicList.replaceChildren();

  state.comics.forEach((comic) => {
    const card = document.createElement("button");
    card.className = "comic-card";
    card.type = "button";
    card.dataset.slug = comic.slug;
    card.innerHTML = `
      <img src="${state.siteRoot}${comic.cover}" alt="${escapeHtml(comic.title)} cover" loading="lazy">
      <span>
        <span class="comic-date">${formatDate(comic.date)}</span>
        <span class="comic-title">${escapeHtml(comic.title)}</span>
        <span class="comic-pages">${comic.pages.length} pages</span>
      </span>
    `;
    card.addEventListener("click", () => selectComic(comic.slug));
    elements.comicList.append(card);
  });

  elements.comicCount.textContent = `${state.comics.length} ${state.comics.length === 1 ? "comic" : "comics"}`;
  elements.oldestDate.textContent = state.comics[0] ? `Oldest: ${formatDate(state.comics[0].date)}` : "Oldest";
  elements.newestDate.textContent = state.comics.at(-1) ? `Newest: ${formatDate(state.comics.at(-1).date)}` : "Newest";
}

function renderReader(slug) {
  const comic = state.comics.find((candidate) => candidate.slug === slug) || state.comics[0];
  if (!comic) {
    renderError(new Error("No comics found. Add a dated comic folder with page images and rebuild the site."));
    return;
  }

  state.current = comic;
  document.title = `${comic.title} | Dream Comics`;
  elements.readerDate.textContent = formatDate(comic.date);
  elements.readerTitle.textContent = comic.title;
  elements.shareUrl.textContent = `${window.location.origin}${state.siteRoot}comics/${comic.slug}/`;
  elements.shareUrl.href = `${state.siteRoot}comics/${comic.slug}/`;
  elements.downloadButton.href = `${state.siteRoot}${comic.pdf}`;
  elements.downloadButton.setAttribute("download", comic.pdfName || `${comic.slug}.pdf`);
  elements.pageCountLabel.textContent = `${comic.pages.length} pages`;

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

function selectComic(slug) {
  if (!slug) return;
  history.pushState({}, "", `${state.siteRoot}comics/${slug}/`);
  renderRoute();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function scrollToPage(index) {
  const pages = elements.pageStack.querySelectorAll(".comic-page");
  const page = pages[index];
  if (page) {
    page.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function getRoute() {
  const path = window.location.pathname;
  if (path.endsWith("/about/") || path.endsWith("/about")) {
    return { kind: "about" };
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

