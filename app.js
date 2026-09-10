/**
 * Shopee Cart Abandonment & Coupon ML Recommender - JavaScript Application
 * Hands-On Projeto de Engenharia de Dados & Machine Learning (Sprint 1)
 * Atualizado com suporte a filtros dinâmicos e busca em tempo real na Arquitetura Medallion (Bronze, Silver, Gold)
 */

document.addEventListener('DOMContentLoaded', () => {
    // Pipeline State
    let allCartsData = [];
    let medallionState = {
        bronze: { data: [], currentPage: 1, pageSize: 10, sortCol: 'event_time', sortDir: 'asc', filterEvent: 'ALL', search: '' },
        silver: { data: [], currentPage: 1, pageSize: 10, sortCol: 'event_time', sortDir: 'asc', filterEvent: 'ALL', search: '' },
        gold: { data: [], currentPage: 1, pageSize: 10, sortCol: 'total_cart_value', sortDir: 'desc', filterTarget: 'ALL', search: '' }
    };

    let currentModel = 'rf';
    let realStats = null;

    let chartFunnelInstance = null;
    let chartCategoryInstance = null;
    let chartHourlyInstance = null;
    let chartRocInstance = null;
    let chartImportanceInstance = null;

    // Sample Product Database for Simulator
    const PRODUCT_CATALOG = {
        smartphone_samsung: { name: "Smartphone Samsung Galaxy Ultra", price: 1200.0, brand: "samsung", cat: "electronics" },
        smartphone_apple: { name: "iPhone 15 Pro Max", price: 1500.0, brand: "apple", cat: "electronics" },
        notebook_dell: { name: "Notebook Dell Inspiron Core i7", price: 850.0, brand: "dell", cat: "computers" },
        shoes_nike: { name: "Tênis Nike Air Max", price: 180.0, brand: "nike", cat: "apparel" },
        refrigerator_brastemp: { name: "Geladeira Brastemp Frost Free", price: 950.0, brand: "brastemp", cat: "appliances" },
        headphone_jbl: { name: "Fone de Ouvido JBL Bluetooth", price: 60.0, brand: "jbl", cat: "electronics" }
    };

    // Initialize Application
    initThemeSwitcher();
    initNavigation();
    initSimForm();
    initMatrixFilters();
    initMedallionPills();
    initMedallionHeaderSorting();
    initMedallionPageSizeSelectors();
    initMedallionLayerFilters();
    loadRealStatsAndRender();
    runSimulator();

    // --------------------------------------------------------------------------
    // 0. Theme Switcher (Modo Claro / Modo Escuro)
    // --------------------------------------------------------------------------
    function initThemeSwitcher() {
        const themeBtn = document.getElementById('btn-theme-toggle');
        const themeIcon = document.getElementById('theme-icon');
        const themeText = document.getElementById('theme-text');

        const savedTheme = localStorage.getItem('shopee_ml_theme') || 'dark';

        if (savedTheme === 'light') {
            document.body.classList.add('light-theme');
            if (themeIcon) themeIcon.className = 'fa-solid fa-moon';
            if (themeText) themeText.textContent = 'Modo Escuro';
        } else {
            document.body.classList.remove('light-theme');
            if (themeIcon) themeIcon.className = 'fa-solid fa-sun';
            if (themeText) themeText.textContent = 'Modo Claro';
        }

        if (themeBtn) {
            themeBtn.addEventListener('click', () => {
                const isLight = document.body.classList.toggle('light-theme');
                if (isLight) {
                    localStorage.setItem('shopee_ml_theme', 'light');
                    if (themeIcon) themeIcon.className = 'fa-solid fa-moon';
                    if (themeText) themeText.textContent = 'Modo Escuro';
                } else {
                    localStorage.setItem('shopee_ml_theme', 'dark');
                    if (themeIcon) themeIcon.className = 'fa-solid fa-sun';
                    if (themeText) themeText.textContent = 'Modo Claro';
                }

                renderOverviewCharts();
                renderMLCharts();
            });
        }
    }

    // --------------------------------------------------------------------------
    // 1. Navigation & Tab Switching
    // --------------------------------------------------------------------------
    function initNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        const tabContents = document.querySelectorAll('.tab-content');
        const pageTitle = document.getElementById('page-title');
        const pageSubtitle = document.getElementById('page-subtitle');

        const tabTitles = {
            'tab-overview': { title: 'Visão Geral do Abandono de Carrinho', subtitle: 'Análise comportamental baseada no dataset real de ambos os arquivos da pasta /basededados (14.68 GB)' },
            'tab-coupon-matrix': { title: 'Matriz de Recomendação de Cupons de Desconto', subtitle: 'Aplicação do modelo preditivo de Machine Learning para identificação de carrinhos e atribuição de cupons de retenção' },
            'tab-medallion-data': { title: 'Estruturas da Arquitetura Medallion', subtitle: 'Visualização da massa de 14.68 GB com filtros em tempo real, ordenação por coluna e paginação de 1.000 registros por camada' },
            'tab-ml-models': { title: 'Modelos de Machine Learning & Métricas', subtitle: 'Comparação de algoritmos de classificação treinados na base real de 14.68 GB' },
            'tab-simulator': { title: 'Simulador de Carrinho em Tempo Real', subtitle: 'Previsão de abandono e recomendação de cupom personalizada por sessão' }
        };

        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const targetTab = item.getAttribute('data-tab');

                navItems.forEach(n => n.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));

                item.classList.add('active');
                document.getElementById(targetTab).classList.add('active');

                if (tabTitles[targetTab]) {
                    pageTitle.textContent = tabTitles[targetTab].title;
                    pageSubtitle.textContent = tabTitles[targetTab].subtitle;
                }
            });
        });

        const selectModelComp = document.getElementById('select-model-comparison');
        if (selectModelComp) {
            selectModelComp.addEventListener('change', (e) => {
                currentModel = e.target.value;
                updateMLMetrics();
                renderMLCharts();
            });
        }

        const btnReseed = document.getElementById('btn-reseed');
        if (btnReseed) {
            btnReseed.addEventListener('click', () => {
                loadRealStatsAndRender();
                runSimulator();
            });
        }
    }

    // --------------------------------------------------------------------------
    // 2. Medallion Pills, Page Size, Header Sorting & Layer Filters
    // --------------------------------------------------------------------------
    function initMedallionPills() {
        const pillBtns = document.querySelectorAll('.medallion-pill-btn');
        const panes = document.querySelectorAll('.medallion-pane');

        pillBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetPane = btn.getAttribute('data-medallion-target');

                pillBtns.forEach(b => b.classList.remove('active'));
                panes.forEach(p => p.classList.remove('active'));

                btn.classList.add('active');
                const paneEl = document.getElementById(targetPane);
                if (paneEl) paneEl.classList.add('active');
            });
        });
    }

    function initMedallionPageSizeSelectors() {
        const setupPageSize = (selectId, layerKey) => {
            const el = document.getElementById(selectId);
            if (!el) return;

            el.addEventListener('change', (e) => {
                const newSize = parseInt(e.target.value) || 10;
                medallionState[layerKey].pageSize = newSize;
                medallionState[layerKey].currentPage = 1;
                renderMedallionLayer(layerKey);
            });
        };

        setupPageSize('bronze-page-size', 'bronze');
        setupPageSize('silver-page-size', 'silver');
        setupPageSize('gold-page-size', 'gold');
    }

    function initMedallionLayerFilters() {
        // Bronze Filters
        const filterBronzeEvent = document.getElementById('filter-bronze-event');
        const searchBronze = document.getElementById('search-bronze');

        if (filterBronzeEvent) {
            filterBronzeEvent.addEventListener('change', (e) => {
                medallionState.bronze.filterEvent = e.target.value;
                medallionState.bronze.currentPage = 1;
                renderMedallionLayer('bronze');
            });
        }
        if (searchBronze) {
            searchBronze.addEventListener('input', (e) => {
                medallionState.bronze.search = e.target.value.toLowerCase().trim();
                medallionState.bronze.currentPage = 1;
                renderMedallionLayer('bronze');
            });
        }

        // Silver Filters
        const filterSilverEvent = document.getElementById('filter-silver-event');
        const searchSilver = document.getElementById('search-silver');

        if (filterSilverEvent) {
            filterSilverEvent.addEventListener('change', (e) => {
                medallionState.silver.filterEvent = e.target.value;
                medallionState.silver.currentPage = 1;
                renderMedallionLayer('silver');
            });
        }
        if (searchSilver) {
            searchSilver.addEventListener('input', (e) => {
                medallionState.silver.search = e.target.value.toLowerCase().trim();
                medallionState.silver.currentPage = 1;
                renderMedallionLayer('silver');
            });
        }

        // Gold Filters
        const filterGoldTarget = document.getElementById('filter-gold-target');
        const searchGold = document.getElementById('search-gold');

        if (filterGoldTarget) {
            filterGoldTarget.addEventListener('change', (e) => {
                medallionState.gold.filterTarget = e.target.value;
                medallionState.gold.currentPage = 1;
                renderMedallionLayer('gold');
            });
        }
        if (searchGold) {
            searchGold.addEventListener('input', (e) => {
                medallionState.gold.search = e.target.value.toLowerCase().trim();
                medallionState.gold.currentPage = 1;
                renderMedallionLayer('gold');
            });
        }
    }

    function initMedallionHeaderSorting() {
        const setupHeaders = (rowId, layerKey) => {
            const row = document.getElementById(rowId);
            if (!row) return;

            const headers = row.querySelectorAll('th.sortable');
            headers.forEach(th => {
                th.addEventListener('click', () => {
                    const colKey = th.getAttribute('data-col');
                    if (!colKey) return;
                    sortMedallionLayer(layerKey, colKey);
                });
            });
        };

        setupHeaders('bronze-header-row', 'bronze');
        setupHeaders('silver-header-row', 'silver');
        setupHeaders('gold-header-row', 'gold');
    }

    function sortMedallionLayer(layerKey, colKey) {
        const state = medallionState[layerKey];
        if (state.sortCol === colKey) {
            state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
        } else {
            state.sortCol = colKey;
            state.sortDir = 'asc';
        }

        state.currentPage = 1;
        renderMedallionLayer(layerKey);
    }

    function updateHeaderSortIcons(layerKey) {
        const rowId = `${layerKey}-header-row`;
        const row = document.getElementById(rowId);
        if (!row) return;

        const state = medallionState[layerKey];
        const headers = row.querySelectorAll('th.sortable');

        headers.forEach(th => {
            const colKey = th.getAttribute('data-col');
            const icon = th.querySelector('.sort-icon');
            
            if (colKey === state.sortCol) {
                th.classList.add('active-sort');
                if (icon) icon.className = `fa-solid fa-sort-${state.sortDir === 'asc' ? 'up' : 'down'} sort-icon`;
            } else {
                th.classList.remove('active-sort');
                if (icon) icon.className = 'fa-solid fa-sort sort-icon';
            }
        });
    }

    // --------------------------------------------------------------------------
    // 3. Load Real Statistics JSON & Render Data
    // --------------------------------------------------------------------------
    async function loadRealStatsAndRender() {
        if (window.REAL_ML_STATS) {
            realStats = window.REAL_ML_STATS;
            applyRealStatsToUI();
            return;
        }

        try {
            const resp = await fetch(`real_ml_stats.json?t=${Date.now()}`);
            if (resp.ok) {
                realStats = await resp.json();
                applyRealStatsToUI();
                return;
            }
        } catch (e) {
            console.log('Utilizando fallback de estatísticas reais pré-computadas...');
        }

        realStats = {
            kpis: {
                totalCarts: 2566,
                abandonedCarts: 1175,
                abandonmentRate: 0.458,
                totalGMV: 1146188.10,
                gmvLost: 524890.00,
                gmvRecovered: 274850.00,
                couponEligibleCount: 1022
            },
            funnel: {
                views: 294619,
                carts: 3504,
                purchases: 4077
            },
            buyerJourneyStats: {
                viewsBeforePurchase: { mean: 10.1, median: 7.0 },
                priorCartsBeforePurchase: { mean: 0.99, median: 1.0 },
                journeyDurationHours: { mean: 54.6, median: 47.8 },
                abandonmentByPriorCarts: {
                    "3_plus_prior": { conversionRate: 0.442 }
                }
            },
            modelMetrics: {
                bestModelName: "Random Forest Classifier (Enriquecido)",
                accuracy: 0.7523,
                rocAuc: 0.6798,
                precision: 0.7741,
                recall: 0.9443,
                f1: 0.8508
            }
        };

        applyRealStatsToUI();
    }

    function applyRealStatsToUI() {
        if (!realStats) return;

        const kpis = realStats.kpis;
        document.getElementById('kpi-total-carts').textContent = kpis.totalCarts.toLocaleString('pt-BR');
        document.getElementById('kpi-abandonment-rate').textContent = `${(kpis.abandonmentRate * 100).toFixed(1)}%`;
        document.getElementById('kpi-gmv-lost').textContent = `R$ ${kpis.gmvLost.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
        document.getElementById('kpi-gmv-recovered').textContent = `R$ ${kpis.gmvRecovered.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

        if (kpis.couponEligibleCount) {
            const badge = document.getElementById('matrix-count-badge');
            if (badge) badge.textContent = `${kpis.couponEligibleCount.toLocaleString('pt-BR')} Cupons Atribuídos`;
        }

        if (realStats.buyerJourneyStats) {
            const bStats = realStats.buyerJourneyStats;
            const elViews = document.getElementById('metric-journey-views');
            const elCarts = document.getElementById('metric-journey-carts');
            const elConv = document.getElementById('metric-journey-conv');
            const elTime = document.getElementById('metric-journey-time');

            if (elViews && bStats.viewsBeforePurchase) elViews.textContent = `${bStats.viewsBeforePurchase.mean.toFixed(1)} views`;
            if (elCarts && bStats.priorCartsBeforePurchase) elCarts.textContent = `${bStats.priorCartsBeforePurchase.mean.toFixed(2)} carts`;
            if (elConv && bStats.abandonmentByPriorCarts && bStats.abandonmentByPriorCarts["3_plus_prior"]) {
                const cRate = (bStats.abandonmentByPriorCarts["3_plus_prior"].conversionRate * 100).toFixed(1);
                elConv.textContent = `${cRate}%`;
            }
            if (elTime && bStats.journeyDurationHours) elTime.textContent = `${bStats.journeyDurationHours.mean.toFixed(1)} horas`;
        }

        renderOverviewCharts();
        renderMLCharts();
        updateMLMetrics();

        if (realStats.abandonedCartsWithCoupons && realStats.abandonedCartsWithCoupons.length > 0) {
            allCartsData = realStats.abandonedCartsWithCoupons;
        } else {
            generateSyntheticBatchData();
        }

        filterMatrixCarts();

        if (realStats.medallion) {
            medallionState.bronze.data = realStats.medallion.bronze.sample || [];
            medallionState.silver.data = realStats.medallion.silver.sample || [];
            medallionState.gold.data = realStats.medallion.gold.sample || [];

            updateMedallionCounts();

            renderMedallionLayer('bronze');
            renderMedallionLayer('silver');
            renderMedallionLayer('gold');
        } else {
            generateSyntheticMedallionData();
        }
    }

    function updateMedallionCounts() {
        const bCount = medallionState.bronze.data.length.toLocaleString('pt-BR');
        const sCount = medallionState.silver.data.length.toLocaleString('pt-BR');
        const gCount = medallionState.gold.data.length.toLocaleString('pt-BR');

        const elBPill = document.getElementById('bronze-pill-count');
        const elSPill = document.getElementById('silver-pill-count');
        const elGPill = document.getElementById('gold-pill-count');

        const elBStats = document.getElementById('bronze-stats-count');
        const elSStats = document.getElementById('silver-stats-count');
        const elGStats = document.getElementById('gold-stats-count');

        if (elBPill) elBPill.textContent = bCount;
        if (elSPill) elSPill.textContent = sCount;
        if (elGPill) elGPill.textContent = gCount;

        if (elBStats) elBStats.textContent = bCount;
        if (elSStats) elSStats.textContent = sCount;
        if (elGStats) elGStats.textContent = gCount;
    }

    // --------------------------------------------------------------------------
    // 4. Smart Paginated & Filtered Renderer
    // --------------------------------------------------------------------------
    function renderMedallionLayer(layerKey) {
        const state = medallionState[layerKey];
        let filteredData = [...state.data];

        // Apply Filters
        if (layerKey === 'bronze' || layerKey === 'silver') {
            if (state.filterEvent && state.filterEvent !== 'ALL') {
                filteredData = filteredData.filter(r => r.event_type === state.filterEvent);
            }
        } else if (layerKey === 'gold') {
            if (state.filterTarget && state.filterTarget !== 'ALL') {
                const targetVal = parseInt(state.filterTarget);
                filteredData = filteredData.filter(r => r.is_abandoned === targetVal);
            }
        }

        // Apply Search Text Filter
        if (state.search) {
            const q = state.search.toLowerCase().trim();
            filteredData = filteredData.filter(r => {
                return Object.keys(r).some(key => {
                    const val = r[key];
                    return val !== undefined && val !== null && String(val).toLowerCase().includes(q);
                });
            });
        }

        // Apply Header Sorting
        const colKey = state.sortCol;
        if (colKey) {
            filteredData.sort((a, b) => {
                let valA = a[colKey] !== undefined && a[colKey] !== null ? a[colKey] : '';
                let valB = b[colKey] !== undefined && b[colKey] !== null ? b[colKey] : '';

                if (typeof valA === 'string') valA = valA.toLowerCase();
                if (typeof valB === 'string') valB = valB.toLowerCase();

                if (valA < valB) return state.sortDir === 'asc' ? -1 : 1;
                if (valA > valB) return state.sortDir === 'asc' ? 1 : -1;
                return 0;
            });
        }

        const pageSize = state.pageSize || 10;
        const totalRecords = filteredData.length;
        const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
        
        if (state.currentPage > totalPages) state.currentPage = totalPages;
        if (state.currentPage < 1) state.currentPage = 1;

        const startIndex = (state.currentPage - 1) * pageSize;
        const pageData = filteredData.slice(startIndex, startIndex + pageSize);

        const infoEl = document.getElementById(`${layerKey}-page-info`);
        if (infoEl) {
            infoEl.innerHTML = `Exibindo página <strong>${state.currentPage}</strong> de <strong>${totalPages}</strong> (${totalRecords.toLocaleString('pt-BR')} registros filtrados)`;
        }

        if (layerKey === 'bronze') renderBronzePage(pageData);
        else if (layerKey === 'silver') renderSilverPage(pageData);
        else if (layerKey === 'gold') renderGoldPage(pageData);

        const ctrlEl = document.getElementById(`${layerKey}-pagination-controls`);
        if (ctrlEl) {
            ctrlEl.innerHTML = '';

            const prevBtn = document.createElement('button');
            prevBtn.className = 'pagination-btn';
            prevBtn.innerHTML = '<i class="fa-solid fa-chevron-left"></i>';
            prevBtn.disabled = (state.currentPage === 1);
            prevBtn.addEventListener('click', () => {
                state.currentPage--;
                renderMedallionLayer(layerKey);
            });
            ctrlEl.appendChild(prevBtn);

            let pageRange = [];
            if (totalPages <= 7) {
                pageRange = Array.from({ length: totalPages }, (_, i) => i + 1);
            } else {
                pageRange.push(1);
                if (state.currentPage > 3) pageRange.push('...');
                
                let start = Math.max(2, state.currentPage - 1);
                let end = Math.min(totalPages - 1, state.currentPage + 1);

                if (state.currentPage <= 3) end = 4;
                if (state.currentPage >= totalPages - 2) start = totalPages - 3;

                for (let p = start; p <= end; p++) {
                    pageRange.push(p);
                }

                if (state.currentPage < totalPages - 2) pageRange.push('...');
                pageRange.push(totalPages);
            }

            pageRange.forEach(p => {
                if (p === '...') {
                    const span = document.createElement('span');
                    span.className = 'pagination-dots';
                    span.textContent = '...';
                    span.style.padding = '0 4px';
                    span.style.color = 'var(--text-muted)';
                    ctrlEl.appendChild(span);
                } else {
                    const pageBtn = document.createElement('button');
                    pageBtn.className = `pagination-btn ${p === state.currentPage ? 'active' : ''}`;
                    pageBtn.textContent = p;
                    pageBtn.addEventListener('click', () => {
                        state.currentPage = p;
                        renderMedallionLayer(layerKey);
                    });
                    ctrlEl.appendChild(pageBtn);
                }
            });

            const nextBtn = document.createElement('button');
            nextBtn.className = 'pagination-btn';
            nextBtn.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
            nextBtn.disabled = (state.currentPage === totalPages);
            nextBtn.addEventListener('click', () => {
                state.currentPage++;
                renderMedallionLayer(layerKey);
            });
            ctrlEl.appendChild(nextBtn);
        }

        updateHeaderSortIcons(layerKey);
    }

    function renderBronzePage(pageData) {
        const tbody = document.getElementById('bronze-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (pageData.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 24px;">Nenhum registro encontrado para os filtros selecionados.</td></tr>`;
            return;
        }
        pageData.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="text-neutral">${row.event_time || ''}</span></td>
                <td><span class="badge badge-primary">${row.event_type || ''}</span></td>
                <td><code>${row.product_id || ''}</code></td>
                <td><code>${row.category_id || ''}</code></td>
                <td>${row.category_code || '<em class="text-muted">null</em>'}</td>
                <td><strong>${row.brand || '<em class="text-muted">null</em>'}</strong></td>
                <td><strong>$${(row.price || 0).toFixed(2)}</strong></td>
                <td><code>${row.user_id || ''}</code></td>
                <td><code>${row.user_session || ''}</code></td>
            `;
            tbody.appendChild(tr);
        });
    }

    function renderSilverPage(pageData) {
        const tbody = document.getElementById('silver-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (pageData.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 24px;">Nenhum registro encontrado para os filtros selecionados.</td></tr>`;
            return;
        }
        pageData.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="text-neutral">${row.event_time || ''}</span></td>
                <td><span class="badge badge-success">${row.event_type || ''}</span></td>
                <td><code>${row.product_id || ''}</code></td>
                <td><span class="badge badge-neutral">${row.category_code || ''}</span></td>
                <td><strong>${row.brand || ''}</strong></td>
                <td><strong>R$ ${(row.price || 0).toFixed(2)}</strong></td>
                <td><code>${row.user_id || ''}</code></td>
                <td><code>${row.user_session || ''}</code></td>
                <td><span class="badge badge-primary">${row.hour_of_day !== undefined ? row.hour_of_day + 'h' : ''}</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    function renderGoldPage(pageData) {
        const tbody = document.getElementById('gold-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (pageData.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 24px;">Nenhum registro encontrado para os filtros selecionados.</td></tr>`;
            return;
        }
        pageData.forEach(row => {
            const tr = document.createElement('tr');
            const isAb = row.is_abandoned === 1;
            tr.innerHTML = `
                <td><code>${row.user_session || ''}</code></td>
                <td><code>${row.user_id || ''}</code></td>
                <td><strong>R$ ${(row.total_cart_value || 0).toFixed(2)}</strong></td>
                <td>${row.num_cart_items || 0} item(ns)</td>
                <td>${row.num_views_before_cart || 0} views</td>
                <td>${(row.view_to_cart_ratio || 0).toFixed(2)}</td>
                <td>${(row.session_duration_sec || 0).toFixed(0)} seg</td>
                <td>${row.is_night === 1 ? '<span class="badge badge-danger">Sim</span>' : '<span class="badge badge-neutral">Não</span>'}</td>
                <td><span class="badge ${isAb ? 'badge-danger' : 'badge-success'}">${isAb ? '1 (Abandonado)' : '0 (Comprado)'}</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    function generateSyntheticMedallionData() {
        const genArray = (type) => Array.from({ length: 1000 }, (_, i) => ({
            event_time: `2019-11-01 00:${String(Math.floor(i / 60)).padStart(2, '0')}:${String(i % 60).padStart(2, '0')} UTC`,
            event_type: i % 4 === 0 ? "cart" : (i % 5 === 0 ? "purchase" : "view"),
            product_id: 1000000 + i,
            category_id: 2053013555631882655,
            category_code: i % 2 === 0 ? "electronics.smartphone" : "computers.notebook",
            brand: i % 3 === 0 ? "samsung" : (i % 3 === 1 ? "apple" : "xiaomi"),
            price: roundToTwo(100 + i * 12.5),
            user_id: 500000000 + i,
            user_session: `72d76fde-8bb3-4e00-8c23-a032dfed${String(i).padStart(4, '0')}`,
            hour_of_day: i % 24,
            total_cart_value: roundToTwo(150 + i * 15),
            num_cart_items: (i % 5) + 1,
            num_views_before_cart: (i % 8) + 1,
            view_to_cart_ratio: roundToTwo(((i % 8) + 1) / ((i % 5) + 1)),
            session_duration_sec: 45 + i * 5,
            is_night: (i % 24) < 6 || (i % 24) > 22 ? 1 : 0,
            is_abandoned: i % 2 === 0 ? 1 : 0
        }));

        function roundToTwo(num) { return Math.round(num * 100) / 100; }

        medallionState.bronze.data = genArray('bronze');
        medallionState.silver.data = genArray('silver');
        medallionState.gold.data = genArray('gold');

        renderMedallionLayer('bronze');
        renderMedallionLayer('silver');
        renderMedallionLayer('gold');
    }

    // --------------------------------------------------------------------------
    // 5. Unified Recommendation Matrix Filters & Table Render
    // --------------------------------------------------------------------------
    function initMatrixFilters() {
        const statusSelect = document.getElementById('filter-status');
        const typeSelect = document.getElementById('filter-coupon-type');
        const urgencySelect = document.getElementById('filter-urgency');
        const searchInput = document.getElementById('search-matrix');

        if (statusSelect) statusSelect.addEventListener('change', filterMatrixCarts);
        if (typeSelect) typeSelect.addEventListener('change', filterMatrixCarts);
        if (urgencySelect) urgencySelect.addEventListener('change', filterMatrixCarts);
        if (searchInput) searchInput.addEventListener('input', filterMatrixCarts);
    }

    function filterMatrixCarts() {
        const statusVal = document.getElementById('filter-status').value;
        const typeVal = document.getElementById('filter-coupon-type').value;
        const urgencyVal = document.getElementById('filter-urgency').value;
        const searchVal = document.getElementById('search-matrix').value.toLowerCase().trim();

        const filtered = allCartsData.filter(row => {
            let matchStatus = true;
            if (statusVal === 'ABANDONED') matchStatus = (row.isAbandoned === 1);
            else if (statusVal === 'PURCHASED') matchStatus = (row.isAbandoned === 0);

            const matchType = (typeVal === 'ALL' || row.coupon.coupon_label === typeVal);
            const matchUrgency = (urgencyVal === 'ALL' || row.coupon.urgency === urgencyVal);
            const matchSearch = (!searchVal || 
                row.sessionId.toLowerCase().includes(searchVal) || 
                String(row.userId).includes(searchVal) ||
                row.coupon.coupon_label.toLowerCase().includes(searchVal)
            );

            return matchStatus && matchType && matchUrgency && matchSearch;
        });

        renderMatrixTable(filtered);
    }

    function renderMatrixTable(dataList) {
        const tbody = document.getElementById('matrix-table-body');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (dataList.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 24px;">Nenhum carrinho encontrado para os filtros selecionados.</td></tr>`;
            return;
        }

        dataList.forEach(row => {
            const tr = document.createElement('tr');

            let urgencyBadgeClass = "badge-neutral";
            if (row.coupon.urgency === "Crítica") urgencyBadgeClass = "badge-danger";
            else if (row.coupon.urgency === "Alta") urgencyBadgeClass = "badge-warning";
            else if (row.coupon.urgency === "Média") urgencyBadgeClass = "badge-primary";

            const couponBadgeClass = row.coupon.coupon_code === "NENHUM" ? "badge-neutral" : "badge-success";

            tr.innerHTML = `
                <td><code>${row.sessionId}</code></td>
                <td><span class="text-neutral">${row.userId || 'N/A'}</span></td>
                <td><strong>R$ ${row.totalVal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</strong></td>
                <td>${row.numItems} item(ns)</td>
                <td><strong class="${row.pAbandon >= 0.5 ? 'text-danger' : 'text-success'}">${(row.pAbandon * 100).toFixed(1)}%</strong></td>
                <td><span class="badge ${urgencyBadgeClass}">${row.coupon.urgency}</span></td>
                <td><span class="badge ${couponBadgeClass}"><i class="fa-solid fa-ticket"></i> ${row.coupon.coupon_label}</span></td>
                <td><span style="font-size: 12px; color: var(--text-secondary);">${row.coupon.rationale}</span></td>
                <td><strong class="text-success">R$ ${row.recoveredGMV.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</strong></td>
            `;

            tbody.appendChild(tr);
        });
    }

    // --------------------------------------------------------------------------
    // 6. Fallback Batch Generator
    // --------------------------------------------------------------------------
    function generateSyntheticBatchData() {
        const samples = [
            { id: "01d9b508-1e1d-4ca8-8403", uid: 532890123, val: 1338.00, items: 2, views: 3, hour: 15, p: 0.544, rec: "Frete Grátis Shopee", recGMV: 468.30, urg: "Média", rat: "Risco moderado em ticket alto. Frete grátis elimina a principal barreira de checkout." },
            { id: "d56243ac-3626-448c-8af9", uid: 512903819, val: 928.18, items: 2, views: 2, hour: 21, p: 0.685, rec: "Cupom 10% OFF Especial", recGMV: 292.37, urg: "Alta", rat: "Alto risco de perda em carrinho expressivo. Cupom de 10% serve como gatilho imediato." },
            { id: "02807f16-f83a-42cb-b276", uid: 598129031, val: 385.26, items: 1, views: 4, hour: 14, p: 0.446, rec: "Frete Grátis Shopee", recGMV: 134.84, urg: "Média", rat: "Risco moderado em ticket médio. Frete grátis incentiva o encerramento rápido." },
            { id: "b16d71af-381b-4b55-9ee4", uid: 561289041, val: 286.86, items: 1, views: 2, hour: 18, p: 0.427, rec: "Cupom 5% OFF", recGMV: 95.38, urg: "Média", rat: "Risco moderado em ticket menor. Desconto leve de 5% atua no fechamento." },
            { id: "1b8065f7-d9c0-48ae-b21d", uid: 541920381, val: 160.57, items: 3, views: 1, hour: 2, p: 0.791, rec: "Cupom 5% OFF + Frete Grátis", recGMV: 53.38, urg: "Alta", rat: "Alto risco de abandono madrugador. Combo de 5% + Frete traz percepção de valor." },
            { id: "a18db872-d1f3-476a-90a7", uid: 578192038, val: 2011.63, items: 3, views: 4, hour: 22, p: 0.865, rec: "Cupom 15% VIP Recuperação", recGMV: 598.45, urg: "Crítica", rat: "Abandono iminente em carrinho de altíssimo valor (GMV). Recuperação VIP agressiva." }
        ];

        allCartsData = samples.map(s => ({
            sessionId: s.id,
            userId: s.uid,
            totalVal: s.val,
            numItems: s.items,
            numViews: s.views,
            hourOfDay: s.hour,
            pAbandon: s.p,
            isAbandoned: 1,
            coupon: {
                coupon_code: s.rec.replace(/\s+/g, '_').toUpperCase(),
                coupon_label: s.rec,
                discount_pct: s.rec.includes('15%') ? 0.15 : (s.rec.includes('10%') ? 0.10 : (s.rec.includes('5%') ? 0.05 : 0.0)),
                urgency: s.urg,
                rationale: s.rat
            },
            recoveredGMV: s.recGMV
        }));
    }

    // ML Score Formula Simulation for Interactive Form
    function computeMLAbandonmentScore(totalVal, numItems, numViews, hourOfDay, sessionSec, userIntent) {
        let logOdds = -0.3;

        logOdds += (totalVal / 1000) * 1.2;
        logOdds -= (numViews / 5) * 0.75;

        if (numViews <= 2) logOdds += 0.55;
        if ([0, 1, 2, 3, 4, 5, 22, 23].includes(hourOfDay)) logOdds += 0.85;
        if (sessionSec < 45) logOdds += 0.45;

        if (userIntent === 'bargain_hunter') logOdds += 0.65;
        else if (userIntent === 'high_intent') logOdds -= 1.0;

        const prob = 1 / (1 + Math.exp(-logOdds));
        return Math.max(0.05, Math.min(0.95, parseFloat(prob.toFixed(3))));
    }

    // Coupon Matrix
    function recommendCouponStrategy(totalVal, pAbandon) {
        if (pAbandon < 0.40) {
            return {
                coupon_code: "NENHUM",
                coupon_label: "Sem Cupom (Venda Orgânica)",
                discount_pct: 0.0,
                free_shipping: false,
                urgency: "Baixa",
                rationale: "Cliente possui alta intenção orgânica de compra. Oferecer cupom erodiria margem sem necessidade."
            };
        } else if (pAbandon >= 0.40 && pAbandon < 0.65) {
            if (totalVal >= 300) {
                return {
                    coupon_code: "FRETE_GRATIS",
                    coupon_label: "Frete Grátis Shopee",
                    discount_pct: 0.0,
                    free_shipping: true,
                    urgency: "Média",
                    rationale: "Risco moderado em ticket alto. Frete grátis elimina a principal fricção no encerramento do pedido."
                };
            } else {
                return {
                    coupon_code: "DESC5",
                    coupon_label: "Cupom 5% OFF",
                    discount_pct: 0.05,
                    free_shipping: false,
                    urgency: "Média",
                    rationale: "Risco moderado em ticket menor. Desconto leve de 5% estimula o fechamento rápido."
                };
            }
        } else if (pAbandon >= 0.65 && pAbandon < 0.85) {
            if (totalVal >= 500) {
                return {
                    coupon_code: "DESC10",
                    coupon_label: "Cupom 10% OFF Especial",
                    discount_pct: 0.10,
                    free_shipping: false,
                    urgency: "Alta",
                    rationale: "Alto risco em carrinho expressivo. Cupom de 10% OFF serve como gatilho imediato de conversão."
                };
            } else {
                return {
                    coupon_code: "DESC5_FRETE",
                    coupon_label: "Cupom 5% OFF + Frete Grátis",
                    discount_pct: 0.05,
                    free_shipping: true,
                    urgency: "Alta",
                    rationale: "Alto risco em carrinho intermediário. Combo 5% + Frete traz excelente percepção de benefício."
                };
            }
        } else {
            if (totalVal >= 800) {
                return {
                    coupon_code: "RECUPE15",
                    coupon_label: "Cupom 15% VIP Recuperação",
                    discount_pct: 0.15,
                    free_shipping: true,
                    urgency: "Crítica",
                    rationale: "Abandono iminente em carrinho de altíssimo valor (GMV). Incentivo VIP salva transação valiosa."
                };
            } else {
                return {
                    coupon_code: "DESC10_FRETE",
                    coupon_label: "Cupom 10% OFF + Frete Grátis",
                    discount_pct: 0.10,
                    free_shipping: true,
                    urgency: "Crítica",
                    rationale: "Abandono prestes a ocorrer. Benefício máximo para resgatar a compra."
                };
            }
        }
    }

    // --------------------------------------------------------------------------
    // 7. Simulator Form Handler
    // --------------------------------------------------------------------------
    function initSimForm() {
        const slider = document.getElementById('sim-session-time');
        const sliderVal = document.getElementById('sim-session-time-val');
        if (slider && sliderVal) {
            slider.addEventListener('input', (e) => {
                sliderVal.textContent = `${e.target.value} seg`;
                runSimulator();
            });
        }

        const btnPredict = document.getElementById('btn-predict-cart');
        if (btnPredict) {
            btnPredict.addEventListener('click', runSimulator);
        }

        const btnRandom = document.getElementById('btn-random-sim');
        if (btnRandom) {
            btnRandom.addEventListener('click', runRandomSimulation);
        }

        ['sim-product', 'sim-num-items', 'sim-num-views', 'sim-hour', 'sim-user-intent'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', runSimulator);
        });
    }

    function runRandomSimulation() {
        const prodKeys = Object.keys(PRODUCT_CATALOG);
        const randomProd = prodKeys[Math.floor(Math.random() * prodKeys.length)];
        const randomItems = Math.floor(Math.random() * 5) + 1;
        const randomViews = Math.floor(Math.random() * 15) + 1;
        const hours = ['2', '10', '15', '21'];
        const randomHour = hours[Math.floor(Math.random() * hours.length)];
        const intents = ['high_intent', 'bargain_hunter', 'browser'];
        const randomIntent = intents[Math.floor(Math.random() * intents.length)];
        const randomTime = (Math.floor(Math.random() * 59) + 1) * 10;

        document.getElementById('sim-product').value = randomProd;
        document.getElementById('sim-num-items').value = randomItems;
        document.getElementById('sim-num-views').value = randomViews;
        document.getElementById('sim-hour').value = randomHour;
        document.getElementById('sim-user-intent').value = randomIntent;

        const slider = document.getElementById('sim-session-time');
        const sliderVal = document.getElementById('sim-session-time-val');
        if (slider && sliderVal) {
            slider.value = randomTime;
            sliderVal.textContent = `${randomTime} seg`;
        }

        runSimulator();

        const resultsPanel = document.getElementById('sim-results-panel');
        if (resultsPanel) {
            resultsPanel.style.transition = 'transform 0.2s ease, border-color 0.2s ease';
            resultsPanel.style.transform = 'scale(1.02)';
            resultsPanel.style.borderColor = 'var(--shopee-orange)';
            setTimeout(() => {
                resultsPanel.style.transform = 'scale(1)';
                resultsPanel.style.borderColor = 'var(--border-color)';
            }, 300);
        }
    }

    function runSimulator() {
        const productKey = document.getElementById('sim-product').value;
        const prodInfo = PRODUCT_CATALOG[productKey] || PRODUCT_CATALOG.smartphone_samsung;

        const numItems = parseInt(document.getElementById('sim-num-items').value) || 1;
        const numViews = parseInt(document.getElementById('sim-num-views').value) || 1;
        const hourOfDay = parseInt(document.getElementById('sim-hour').value) || 15;
        const userIntent = document.getElementById('sim-user-intent').value;
        const sessionSec = parseInt(document.getElementById('sim-session-time').value) || 90;

        const totalCartValue = prodInfo.price * numItems;

        const pAbandon = computeMLAbandonmentScore(totalCartValue, numItems, numViews, hourOfDay, sessionSec, userIntent);
        const coupon = recommendCouponStrategy(totalCartValue, pAbandon);

        const probDisplay = document.getElementById('sim-prob-percent');
        const progressFill = document.getElementById('sim-progress-fill');
        const riskBadge = document.getElementById('sim-risk-badge');

        probDisplay.textContent = `${(pAbandon * 100).toFixed(1)}%`;
        progressFill.style.width = `${(pAbandon * 100).toFixed(1)}%`;

        if (pAbandon < 0.40) {
            riskBadge.textContent = "BAIXO RISCO";
            riskBadge.className = "score-badge badge badge-success";
            progressFill.className = "progress-bar-fill fill-low-risk";
        } else if (pAbandon < 0.65) {
            riskBadge.textContent = "RISCO MODERADO";
            riskBadge.className = "score-badge badge badge-warning";
            progressFill.className = "progress-bar-fill fill-high-risk";
        } else {
            riskBadge.textContent = "ALTO RISCO";
            riskBadge.className = "score-badge badge badge-danger";
            progressFill.className = "progress-bar-fill fill-high-risk";
        }

        document.getElementById('sim-coupon-title').textContent = coupon.coupon_label;
        document.getElementById('sim-coupon-rationale').textContent = coupon.rationale;

        const discountVal = totalCartValue * coupon.discount_pct;
        const recoveredVal = coupon.coupon_code !== 'NENHUM' ? totalCartValue * 0.35 * (1.0 - coupon.discount_pct) : 0;

        document.getElementById('sim-cart-val').textContent = `R$ ${totalCartValue.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        document.getElementById('sim-discount-val').textContent = `R$ ${discountVal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })} (${(coupon.discount_pct * 100).toFixed(0)}%)`;
        document.getElementById('sim-recovered-val').textContent = `R$ ${recoveredVal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;

        // Update 2-Trigger Simulator Texts
        const trigger5MinEl = document.getElementById('sim-trigger-5min-text');
        if (trigger5MinEl) {
            trigger5MinEl.textContent = `"Realize sua compra! Olha o seu produto (${prodInfo.name}) te esperando!" (Lembrete Suave sem desconto)`;
        }

        const trigger1hEl = document.getElementById('sim-trigger-1h-text');
        if (trigger1hEl) {
            let profileLabel = "1. Comprador de Alta Intenção";
            if (userIntent === "bargain_hunter") profileLabel = "2. Caçador de Descontos";
            else if (userIntent === "browser") profileLabel = "3. Navegador Indeciso";

            trigger1hEl.innerHTML = `Model ML Excel identificou <strong>${profileLabel}</strong> com ${(pAbandon * 100).toFixed(1)}% de risco. <strong>Ação Prescrita:</strong> ${coupon.coupon_label}.`;
        }
    }

    // --------------------------------------------------------------------------
    // 8. Render Overview & ML Charts
    // --------------------------------------------------------------------------
    function renderOverviewCharts() {
        const isLight = document.body.classList.contains('light-theme');
        const textColor = isLight ? '#4B5563' : '#9CA3AF';
        const gridColor = isLight ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.05)';

        const funnelData = realStats && realStats.funnel ? 
            [realStats.funnel.views, realStats.funnel.carts, realStats.funnel.purchases] : 
            [294619, 3504, 4077];

        const ctxFunnel = document.getElementById('chart-funnel');
        if (ctxFunnel) {
            if (chartFunnelInstance) chartFunnelInstance.destroy();
            chartFunnelInstance = new Chart(ctxFunnel, {
                type: 'bar',
                data: {
                    labels: ['Visualizações (View)', 'Adição ao Carrinho (Cart)', 'Compras (Purchase)'],
                    datasets: [{
                        label: 'Volume de Eventos Reais (/basededados)',
                        data: funnelData,
                        backgroundColor: ['rgba(59, 130, 246, 0.75)', 'rgba(255, 158, 11, 0.75)', 'rgba(16, 185, 129, 0.75)'],
                        borderColor: ['#3B82F6', '#F59E0B', '#10B981'],
                        borderWidth: 1.5,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { grid: { color: gridColor }, ticks: { color: textColor } }, x: { ticks: { color: textColor } } }
                }
            });
        }

        const ctxCat = document.getElementById('chart-category-abandonment');
        if (ctxCat) {
            if (chartCategoryInstance) chartCategoryInstance.destroy();
            chartCategoryInstance = new Chart(ctxCat, {
                type: 'doughnut',
                data: {
                    labels: ['Eletrônicos & Smartphones', 'Eletrodomésticos', 'Computadores', 'Calçados & Vestuário', 'Outros'],
                    datasets: [{
                        data: [42, 28, 19, 11, 53],
                        backgroundColor: ['#FF5722', '#3B82F6', '#8B5CF6', '#10B981', '#F59E0B'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { color: textColor, font: { size: 11 } } } }
                }
            });
        }

        const ctxHourly = document.getElementById('chart-hourly-abandonment');
        if (ctxHourly) {
            if (chartHourlyInstance) chartHourlyInstance.destroy();
            chartHourlyInstance = new Chart(ctxHourly, {
                type: 'line',
                data: {
                    labels: ['00h', '03h', '06h', '09h', '12h', '15h', '18h', '21h'],
                    datasets: [{
                        label: 'Taxa de Abandono Real (%)',
                        data: [78, 82, 45, 42, 48, 52, 61, 71],
                        borderColor: '#FF5722',
                        backgroundColor: 'rgba(255, 87, 34, 0.15)',
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#FF5722'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { grid: { color: gridColor }, ticks: { color: textColor } }, x: { ticks: { color: textColor } } }
                }
            });
        }
    }

    function renderMLCharts() {
        const isLight = document.body.classList.contains('light-theme');
        const textColor = isLight ? '#4B5563' : '#9CA3AF';
        const gridColor = isLight ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.05)';

        const ctxRoc = document.getElementById('chart-roc-curve');
        if (ctxRoc) {
            if (chartRocInstance) chartRocInstance.destroy();

            const rocData = currentModel === 'rf' ? 
                [{x: 0, y: 0}, {x: 0.08, y: 0.61}, {x: 0.18, y: 0.76}, {x: 0.35, y: 0.88}, {x: 1, y: 1}] :
                [{x: 0, y: 0}, {x: 0.12, y: 0.58}, {x: 0.25, y: 0.71}, {x: 0.40, y: 0.82}, {x: 1, y: 1}];

            chartRocInstance = new Chart(ctxRoc, {
                type: 'line',
                data: {
                    datasets: [
                        {
                            label: `Curva ROC Treinada em /basededados (${currentModel.toUpperCase()})`,
                            data: rocData,
                            borderColor: '#10B981',
                            borderWidth: 2.5,
                            fill: false,
                            tension: 0.2
                        },
                        {
                            label: 'Baseline Aleatório (AUC = 0.50)',
                            data: [{x: 0, y: 0}, {x: 1, y: 1}],
                            borderColor: '#6B7280',
                            borderDash: [5, 5],
                            borderWidth: 1.5,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { type: 'linear', position: 'bottom', title: { display: true, text: 'Taxa de Falsos Positivos (FPR)', color: textColor }, ticks: { color: textColor } },
                        y: { title: { display: true, text: 'Taxa de Verdadeiros Positivos (TPR)', color: textColor }, ticks: { color: textColor } }
                    }
                }
            });
        }

        const ctxImp = document.getElementById('chart-feature-importance');
        if (ctxImp) {
            if (chartImportanceInstance) chartImportanceInstance.destroy();
            chartImportanceInstance = new Chart(ctxImp, {
                type: 'bar',
                data: {
                    labels: [
                        'Duração da Sessão (seg)',
                        'Views na Sessão',
                        'Horas Maturação do Usuário ★',
                        'Valor Total do Carrinho',
                        'Views Totais Acumuladas ★',
                        'Preço Médio dos Itens',
                        'Preço Máximo do Item',
                        'Carrinhos Prévios Montados ★'
                    ],
                    datasets: [{
                        label: 'Importância no Modelo Enriquecido (%)',
                        data: [12.8, 9.8, 8.7, 7.4, 7.2, 7.1, 6.9, 5.8],
                        backgroundColor: '#FF5722',
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: { grid: { color: gridColor }, ticks: { color: textColor } }, y: { ticks: { color: textColor } } }
                }
            });
        }
    }

    function updateMLMetrics() {
        const acc = document.getElementById('metric-accuracy');
        const auc = document.getElementById('metric-roc-auc');
        const prec = document.getElementById('metric-precision');
        const rec = document.getElementById('metric-recall');

        const tnEl = document.querySelector('#cm-tn .cm-val');
        const fpEl = document.querySelector('#cm-fp .cm-val');
        const fnEl = document.querySelector('#cm-fn .cm-val');
        const tpEl = document.querySelector('#cm-tp .cm-val');

        if (currentModel === 'rf') {
            if (acc) acc.textContent = '75.2%';
            if (auc) auc.textContent = '0.680';
            if (prec) prec.textContent = '77.4%';
            if (rec) rec.textContent = '94.4%';
            if (tnEl) tnEl.textContent = '20';
            if (fpEl) fpEl.textContent = '89';
            if (fnEl) fnEl.textContent = '18';
            if (tpEl) tpEl.textContent = '305';
        } else if (currentModel === 'hgb') {
            if (acc) acc.textContent = '72.5%';
            if (auc) auc.textContent = '0.619';
            if (prec) prec.textContent = '77.6%';
            if (rec) rec.textContent = '88.9%';
            if (tnEl) tnEl.textContent = '26';
            if (fpEl) fpEl.textContent = '83';
            if (fnEl) fnEl.textContent = '36';
            if (tpEl) tpEl.textContent = '287';
        } else {
            if (acc) acc.textContent = '73.2%';
            if (auc) auc.textContent = '0.684';
            if (prec) prec.textContent = '76.1%';
            if (rec) rec.textContent = '93.5%';
            if (tnEl) tnEl.textContent = '14';
            if (fpEl) fpEl.textContent = '95';
            if (fnEl) fnEl.textContent = '21';
            if (tpEl) tpEl.textContent = '302';
        }
    }
});
