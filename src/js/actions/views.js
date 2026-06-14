import { state } from '../state.js';
import { trackView, fetchRankings } from '../api.js';
import { renderTrending, updateTrendingTabs } from '../render/trending.js';
import { t } from '../i18n.js';

export { trackView };

export function trackAndRefresh(paperId, type = 'preview') {
    trackView(paperId, type);
    refreshTrending();
}

export async function loadTrending(windowDays) {
    state.currentTrendingWindow = windowDays;
    updateTrendingTabs(windowDays);

    try {
        const rankings = await fetchRankings(windowDays);
        renderTrending(rankings, state.allPapers);
    } catch {
        document.getElementById('trendingList').innerHTML =
            '<li class="trending-empty">' + t('trendingUnavailable') + '</li>';
    }
}

export function refreshTrending() {
    clearTimeout(state.trendingRefreshTimer);
    state.trendingRefreshTimer = setTimeout(
        () => loadTrending(state.currentTrendingWindow), 1000
    );
}
