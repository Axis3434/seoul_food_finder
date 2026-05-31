document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('search-form');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = document.getElementById('btn-text');
    const spinner = document.getElementById('spinner');
    
    const resultsContainer = document.getElementById('results-container');
    const resultsList = document.getElementById('results-list');
    const resultsCount = document.getElementById('results-count');
    const errorMessage = document.getElementById('error-message');

    let currentPage = 0;
    let pagesData = [];
    let lastSearch = { address: '', keyword: '' };
    let map = null;
    let markers = [];
    const mapContainer = document.getElementById('map-container');
    const pagination = document.getElementById('pagination');
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const pageIndicator = document.getElementById('page-indicator');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const address = document.getElementById('address').value.trim();
        const keyword = document.getElementById('keyword').value.trim();
        
        if (!address || !keyword) return;

        // Reset state for new search
        currentPage = 0;
        pagesData = [];
        lastSearch = { address, keyword };
        
        await loadPage(0);
    });

    async function loadPage(pageIndex) {
        // UI Reset & Loading State
        errorMessage.classList.add('hidden');
        
        btnText.classList.add('hidden');
        spinner.classList.remove('hidden');
        submitBtn.disabled = true;

        try {
            let data;
            if (pagesData[pageIndex]) {
                data = pagesData[pageIndex];
            } else {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ address: lastSearch.address, keyword: lastSearch.keyword, offset: pageIndex * 5 })
                });
                data = await response.json();
                if (!response.ok) throw new Error(data.error || '검색 중 오류가 발생했습니다.');
                pagesData[pageIndex] = data;
            }
            
            // Only clear HTML AFTER successful fetch!
            if (pageIndex === 0) {
                resultsContainer.classList.add('hidden');
            }
            resultsList.innerHTML = '';
            
            currentPage = pageIndex;
            renderResults(data.results, data.count, data.center);
            updatePaginationUI();
            
        } catch (error) {
            showError(error.message);
            if (pageIndex > currentPage) {
                nextBtn.disabled = true;
            }
        } finally {
            // Restore UI
            btnText.textContent = '가까운 맛집 찾기';
            btnText.classList.remove('hidden');
            spinner.classList.add('hidden');
            submitBtn.disabled = false;
        }
    }

    prevBtn.addEventListener('click', () => {
        if (currentPage > 0) loadPage(currentPage - 1);
    });

    nextBtn.addEventListener('click', () => {
        loadPage(currentPage + 1);
    });

    function updatePaginationUI() {
        pagination.classList.remove('hidden');
        pageIndicator.textContent = `${currentPage + 1} 페이지`;
        prevBtn.disabled = currentPage === 0;
        nextBtn.disabled = pagesData[currentPage] && pagesData[currentPage].count < 5;
    }

    // Reset offset when inputs change
    document.getElementById('address').addEventListener('input', () => {
        btnText.textContent = '가까운 맛집 찾기';
    });
    document.getElementById('keyword').addEventListener('input', () => {
        btnText.textContent = '가까운 맛집 찾기';
    });

    function renderResults(results, count, center) {
        if (!results || results.length === 0) {
            showError('검색 결과가 없습니다.');
            return;
        }

        resultsCount.textContent = `추천 맛집 ${currentPage * 5 + 1} ~ ${currentPage * 5 + count}번째`;
        resultsContainer.classList.remove('hidden');
        mapContainer.classList.remove('hidden');

        // Initialize map if not exists
        if (!map) {
            map = L.map('map').setView([center.lat, center.lng], 14);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
        }

        // Clear existing markers
        markers.forEach(m => map.removeLayer(m));
        markers = [];
        
        // Render ALL markers from all loaded pages
        pagesData.forEach((pageData, pIndex) => {
            if (!pageData) return;
            pageData.results.forEach((item, index) => {
                const actualIndex = pIndex * 5 + index + 1;
                const icon = L.divIcon({
                    className: 'custom-marker',
                    html: `<div class="marker-number"><span>${actualIndex}</span></div>`,
                    iconSize: [32, 32],
                    iconAnchor: [16, 32],
                    popupAnchor: [0, -32]
                });
                
                const marker = L.marker([item.lat, item.lng], {icon: icon}).addTo(map);
                marker.bindPopup(`<b>${actualIndex}. ${item.name}</b><br><span style="font-size:12px">${item.distance}m 떨어짐</span>`);
                markers.push(marker);
            });
        });
        
        results.forEach((item, index) => {
            const actualIndex = currentPage * 5 + index + 1;
            const card = document.createElement('div');
            card.className = 'result-card';
            card.style.cursor = 'pointer';
            // Stagger animation
            card.style.animationDelay = `${index * 0.1}s`;

            card.innerHTML = `
                <div class="result-header">
                    <h3 class="result-name">${actualIndex}. ${item.name}</h3>
                    <span class="result-distance">${item.distance}m</span>
                </div>
                <div class="result-address">
                    <span>📍</span>
                    <span>${item.address}</span>
                </div>
                <div class="result-menu">
                    ${item.menu}
                </div>
                <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="result-link">
                    <span>🔗 상세 정보 보기</span>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                        <polyline points="15 3 21 3 21 9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                </a>
            `;
            
            card.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;
                map.flyTo([item.lat, item.lng], 16, { animate: true, duration: 0.8 });
                const targetMarker = markers.find(m => m.getLatLng().lat === item.lat && m.getLatLng().lng === item.lng);
                if (targetMarker) {
                    setTimeout(() => targetMarker.openPopup(), 800);
                }
            });
            
            resultsList.appendChild(card);
        });

        // Fit map bounds to show all markers
        if (markers.length > 0) {
            const group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds().pad(0.1));
            // Ensure map resizes correctly after becoming visible
            setTimeout(() => {
                map.invalidateSize();
                map.fitBounds(group.getBounds().pad(0.1));
            }, 100);
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    }
});
