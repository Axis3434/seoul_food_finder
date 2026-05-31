document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('search-form');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = document.getElementById('btn-text');
    const spinner = document.getElementById('spinner');
    
    const addressInput = document.getElementById('address');
    const addressLabel = document.getElementById('address-label');
    const gpsBtn = document.getElementById('gps-btn');
    const modeTabs = document.querySelectorAll('.mode-tab');
    
    const resultsContainer = document.getElementById('results-container');
    const resultsList = document.getElementById('results-list');
    const resultsCount = document.getElementById('results-count');
    const errorMessage = document.getElementById('error-message');
    const infoMessage = document.getElementById('info-message');

    let currentMode = 'address'; // 'address', 'landmark', 'gps'
    let gpsLocation = null; // {lat, lng}

    let currentPage = 0;
    let pagesData = [];
    let lastSearch = null; 
    let map = null;
    let markers = [];
    const mapContainer = document.getElementById('map-container');
    const pagination = document.getElementById('pagination');
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const pageIndicator = document.getElementById('page-indicator');

    modeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            modeTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentMode = tab.dataset.mode;
            
            addressInput.readOnly = false;
            gpsBtn.classList.add('hidden');
            gpsLocation = null;
            addressInput.value = '';
            
            if (currentMode === 'address') {
                addressLabel.textContent = '현재 주소';
                addressInput.placeholder = '예: 서울특별시 종로구 대학로';
            } else if (currentMode === 'landmark') {
                addressLabel.textContent = '장소/랜드마크';
                addressInput.placeholder = '예: 강남역, 숭실대학교';
            } else if (currentMode === 'gps') {
                addressLabel.textContent = 'GPS 위치';
                addressInput.placeholder = '우측 [📍 내 위치] 버튼을 눌러주세요';
                addressInput.readOnly = true;
                gpsBtn.classList.remove('hidden');
            }
        });
    });

    gpsBtn.addEventListener('click', () => {
        if (!navigator.geolocation) {
            showError('이 브라우저에서는 GPS 기능을 지원하지 않습니다.');
            return;
        }
        
        gpsBtn.textContent = '위치 찾는 중...';
        gpsBtn.disabled = true;
        
        navigator.geolocation.getCurrentPosition(async (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            gpsLocation = { lat, lng };
            
            try {
                const response = await fetch('/api/reverse-geocode', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ lat, lng })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || '주소 변환 실패');
                
                addressInput.value = data.address;
                errorMessage.classList.add('hidden');
            } catch (err) {
                showError(err.message);
                gpsLocation = null;
            } finally {
                gpsBtn.textContent = '📍 내 위치';
                gpsBtn.disabled = false;
            }
        }, (error) => {
            showError('위치 정보를 가져올 수 없습니다. 권한을 허용해 주세요.');
            gpsBtn.textContent = '📍 내 위치';
            gpsBtn.disabled = false;
        });
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const keyword = document.getElementById('keyword').value.trim();
        if (!keyword) return;

        let payload = { keyword };
        
        if (currentMode === 'gps') {
            if (!gpsLocation) {
                showError('먼저 [📍 내 위치] 버튼을 눌러 GPS 위치를 가져와주세요.');
                return;
            }
            payload.lat = gpsLocation.lat;
            payload.lng = gpsLocation.lng;
        } else {
            const address = addressInput.value.trim();
            if (!address) {
                showError('주소나 장소를 입력해 주세요.');
                return;
            }
            payload.address = address;
        }

        currentPage = 0;
        pagesData = [];
        lastSearch = payload;
        
        await loadPage(0);
    });

    async function loadPage(pageIndex) {
        errorMessage.classList.add('hidden');
        infoMessage.classList.add('hidden');
        
        if (pageIndex === 0) {
            btnText.classList.add('hidden');
            spinner.classList.remove('hidden');
            submitBtn.disabled = true;
        } else {
            document.getElementById('global-spinner').classList.remove('hidden');
        }

        try {
            let data;
            if (pagesData[pageIndex]) {
                data = pagesData[pageIndex];
            } else {
                const payload = { ...lastSearch, offset: pageIndex * 5 };
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                data = await response.json();
                if (!response.ok) throw new Error(data.error || '검색 중 오류가 발생했습니다.');
                pagesData[pageIndex] = data;
            }
            
            if (data.warning) {
                infoMessage.textContent = data.warning;
                infoMessage.classList.remove('hidden');
            }
            
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
            if (pageIndex === 0) {
                btnText.textContent = '가까운 맛집 찾기';
                btnText.classList.remove('hidden');
                spinner.classList.add('hidden');
                submitBtn.disabled = false;
            } else {
                document.getElementById('global-spinner').classList.add('hidden');
            }
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

    function renderResults(results, count, center) {
        if (!results || results.length === 0) {
            showError('검색 결과가 없습니다.');
            return;
        }

        resultsCount.textContent = `추천 맛집 ${currentPage * 5 + 1} ~ ${currentPage * 5 + count}번째`;
        resultsContainer.classList.remove('hidden');
        mapContainer.classList.remove('hidden');

        if (!map) {
            map = L.map('map').setView([center.lat, center.lng], 14);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
        }

        markers.forEach(m => map.removeLayer(m));
        markers = [];
        
        // Add Origin (Start) Marker
        const originIcon = L.divIcon({
            className: 'custom-marker',
            html: `<div class="marker-number" style="background: #3b82f6;"><span>📍</span></div>`,
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -32]
        });
        const originMarker = L.marker([center.lat, center.lng], {icon: originIcon, zIndexOffset: 1000}).addTo(map);
        originMarker.bindPopup(`<b>출발지 (검색 기준 위치)</b>`).openPopup();
        markers.push(originMarker);
        
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
                marker.bindPopup(`<b>${actualIndex}. ${item.name}</b><br><span style="font-size:12px">${item.distance} ${item.walk_time ? '| '+item.walk_time : ''}</span>`);
                markers.push(marker);
            });
        });
        
        results.forEach((item, index) => {
            const actualIndex = currentPage * 5 + index + 1;
            const card = document.createElement('div');
            card.className = 'result-card';
            card.style.cursor = 'pointer';
            card.style.animationDelay = `${index * 0.1}s`;

            const distHTML = `<span class="result-distance">${item.distance}</span>`;
            const timeHTML = item.walk_time ? `<span class="result-time" style="font-weight:bold; color:var(--primary-gradient); margin-left:8px;">${item.walk_time}</span>` : '';

            card.innerHTML = `
                <div class="result-header">
                    <h3 class="result-name">${actualIndex}. ${item.name}</h3>
                    <div style="display:flex; align-items:center;">
                        ${distHTML}
                        ${timeHTML}
                    </div>
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

        if (markers.length > 0) {
            const group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds().pad(0.1));
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
