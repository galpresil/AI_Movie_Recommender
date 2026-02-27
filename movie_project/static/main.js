/* =========================================================
   GLOBAL STATE
   Holds runtime data shared across pages
========================================================= */
const selectedGenres = new Set();   // Selected filter genres (Explore page)
let currentMovies = [];             // Movies currently rendered in table
let sortState = { key: null, direction: 'desc' }; // (future sorting)

/* =========================================================
   COMMON UTILITIES
========================================================= */

// Reset whole page
function confirmReset() {
    if (confirm("Are you sure you want to reset the page?"))
        window.location.reload();
}

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Scroll-to-top button visibility
window.onscroll = function () {
    const scrollBtn = document.getElementById("scrollTopBtn");
    if (!scrollBtn) return;

    const scrolled = document.body.scrollTop > 300 || document.documentElement.scrollTop > 300;
    scrollBtn.classList.toggle("show", scrolled);
};

/* =========================================================
   EXPLORE PAGE — GENRE FILTERING & TABLE
========================================================= */

// Toggle genre selection button
// Adds or removes genre from the Set and updates button styling
async function toggleGenre(genre, btn) {
    if (selectedGenres.has(genre)) {
        selectedGenres.delete(genre);
        btn.classList.remove('active');
    } else {
        selectedGenres.add(genre);
        btn.classList.add('active');
    }
    await fetchMovies();
}

// Request movies from backend by selected genres
// Constructs the query string and updates the global currentMovies list
async function fetchMovies() {
    const genreString = Array.from(selectedGenres).join(',');

    try {
        const response = await fetch(`/get_movies_by_genre?genres=${encodeURIComponent(genreString)}`);
        const data = await response.json();

        currentMovies = data;
        renderTable();

    } catch (e) {
        console.log("Not on Explore page or fetch failed.");
    }
}

// Function to generate a consistent light blue shade based on text
const getGenreColor = (genre) => {
    let hash = 0;
    for (let i = 0; i < genre.length; i++) {
        hash = genre.charCodeAt(i) + ((hash << 5) - hash);
    }
    // HSL: Blue Hue (200-230), Saturation (70-90%), Lightness (85-95%)
    const h = 200 + (Math.abs(hash) % 30); 
    const s = 70 + (Math.abs(hash) % 20); 
    const l = 85 + (Math.abs(hash) % 10); 
    return `hsl(${h}, ${s}%, ${l}%)`;
};

// ... Your existing mapping logic remains the same ...

// Sort table by column key
function sortTable(key) {
    if (sortState.key === key) {
        sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
    } else {
        sortState.key = key;
        sortState.direction = (key === 'rating' || key === 'year') ? 'desc' : 'asc';
    }

    currentMovies.sort((a, b) => {
        let valA = a[key];
        let valB = b[key];

        if (key === 'rating' || key === 'year') {
            valA = parseFloat(valA) || 0;
            valB = parseFloat(valB) || 0;
        } else {
            valA = String(valA).toLowerCase();
            valB = String(valB).toLowerCase();
        }

        if (valA < valB) return sortState.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortState.direction === 'asc' ? 1 : -1;
        return 0;
    });

    updateSortIcons(key, sortState.direction);
    renderTable();
}

function updateSortIcons(activeKey, direction) {
    document.querySelectorAll('th span').forEach(s => {
        s.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 15l5 5 5-5"/><path d="M7 9l5-5 5 5"/></svg>';
        s.classList.remove('active');
    });

    const activeSpan = document.getElementById(`sort-${activeKey}`);
    if (activeSpan) {
        activeSpan.innerHTML = direction === 'asc' 
            ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>' 
            : '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M19 12l-7 7-7-7"/></svg>';
        activeSpan.classList.add('active');
    }
}

// Render movies table
// Generates HTML for the table rows based on currentMovies data
function renderTable() {
    const table = document.getElementById('movieTable');
    const tbody = document.getElementById('tableBody');
    if (!tbody) return;

    tbody.innerHTML = '';

    // Empty state
    if (currentMovies.length === 0) {
        tbody.innerHTML =
            `<tr><td colspan="6" style="text-align:center; padding:20px; color:#666;">
                No movies found matching selected genres.
            </td></tr>`;
        table?.classList.add('visible');
        return;
    }

    // Build rows
    let rows = '';

    currentMovies.forEach((m, index) => {

        // Check if poster exists, otherwise show placeholder
        const poster = (m.poster && m.poster !== "nan")
            ? `<img src="${m.poster}" class="table-poster">`
            : `<div class="poster-placeholder">?</div>`;

        // Generate colorful tags for genres
        const genreHtml = (m.genres && m.genres !== 'nan')
            ? m.genres.split(',').map(g => {
                const genre = g.trim();
                return `<span class="genre-tag" style="background-color:${getGenreColor(genre)}">${genre}</span>`;
            }).join('')
            : `<span style="color:#ccc;font-size:0.8rem;">-</span>`;

        // Note: data-label attributes are used for the Mobile Card View (see style.css)
        rows += `
        <tr>
            <td data-label="Poster">${poster}</td>
            <td data-label="Title" style="font-weight:500;">${m.title}</td>
            <td data-label="Year">${m.year}</td>
            <td data-label="Rating"><span class="rating-badge">${m.rating} / 10</span></td>
            <td data-label="Genre">${genreHtml}</td>
            <td data-label="Details">
                <button onclick="showDescription(${index})" class="view-btn" title="View Details">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>
                    </svg>
                </button>
            </td>
        </tr>`;
    });

    tbody.innerHTML = rows;
    table?.classList.add('visible');
}

// Clear genre filters
function clearAllGenres() {
    selectedGenres.clear();
    document.querySelectorAll('.genre-btn').forEach(btn => btn.classList.remove('active'));
    fetchMovies();
}

/* =========================================================
   SEARCH PAGE — AI MOVIE RECOMMENDATION
========================================================= */

// Handles the main search interaction on the Home page
async function performSearch() {

    const queryInput = document.getElementById('userQuery');
    if (!queryInput) return;

    const query = queryInput.value;
    if (!query) return;

    const summaryDiv = document.getElementById('ai-summary-container');
    const moviesDiv = document.getElementById('movie-results-container');
    const cinemaImg = document.getElementById('cinema-image');

    // Hide the cinema image when search starts
    cinemaImg && (cinemaImg.style.display = 'none');

    // Loading state
    summaryDiv.innerHTML =
        `<div style="text-align:center;padding:20px;">
            <div class="spinner"></div>
            <p style="color:#aaa;font-size:12px;">AI IS ANALYZING...</p>
        </div>`;
    moviesDiv.innerHTML = "";

    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });

        const data = await response.json();

        // AI Summary
                if (data.ai_summary) {
                    summaryDiv.innerHTML = `
                        <div class="ai-summary">
                            <div style="border-bottom: 1px solid #e0e0e0; padding-bottom: 8px; margin-bottom: 10px; font-weight: 300; display: flex; align-items: center;">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 8px;">
                                    <path class="sparkle-main" d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" fill="#FFC107" />
                                    <path class="sparkle-mini" style="animation-delay: 0.2s" d="M19 5L20 7L22 8L20 9L19 11L18 9L16 8L18 7L19 5Z" fill="#FFC107" />
                                    <path class="sparkle-mini" style="animation-delay: 1.0s" d="M5 16L6 18L8 19L6 20L5 22L4 20L2 19L4 18L5 16Z" fill="#FFC107" />
                                </svg>
                                AI Recommendation
                            </div>
                            <div style="color:#444; font-size: 0.95rem;">${data.ai_summary}</div>
                        </div>`;
                } else {
                    summaryDiv.innerHTML = "";
                }

        /* ---- MOVIES ---- */
        if (data.movies?.length) {
            moviesDiv.innerHTML = data.movies.map(m => `
                <div class="movie-card">
                    ${m.poster ? `<img src="${m.poster}" class="poster-img">` : `<div class="poster-img">NO IMAGE</div>`}
                    <div class="movie-info">
                        <div class="movie-title">${m.title}</div>
                        <div class="rating">⭐ ${m.rating}</div>
                        <p class="overview">${m.overview}</p>
                    </div>
                </div>
            `).join('');
        } else if (!data.ai_summary) {
            moviesDiv.innerHTML = `<p style="text-align:center;color:#999;">No matches found.</p>`;
        }

    } catch (e) {
        summaryDiv.innerHTML = "";
        moviesDiv.innerHTML = `<p style="color:red;text-align:center;">Server Error. Please try again.</p>`;
    }
}

/* =========================================================
   MODAL — MOVIE DESCRIPTION
========================================================= */

function showDescription(index) {
    const movie = currentMovies[index];
    if (!movie) return;

    document.getElementById('modalTitle').innerText = movie.title;
    document.getElementById('modalDesc').innerText = movie.overview || "No description available.";
    document.getElementById('descModal').classList.add('open');
}

function closeModal(e) {
    const modal = document.getElementById('descModal');
    if (!modal) return;

    if (e.target.id === 'descModal' || e.target.classList.contains('close-modal'))
        modal.classList.remove('open');
}

/* =========================================================
   INITIALIZATION (ENTRY POINT)
========================================================= */

document.addEventListener('DOMContentLoaded', () => {

    // Search page listeners
    const queryInput = document.getElementById("userQuery");
    if (queryInput) {
        queryInput.addEventListener("keypress", e => e.key === "Enter" && performSearch());

        queryInput.addEventListener("input", function () {
            const icon = document.getElementById("sparkle-icon");
            icon && (icon.style.display = this.value ? 'none' : 'block');
        });
    }

    // Explore page initial load
    if (document.getElementById('movieTable'))
        fetchMovies();
});
