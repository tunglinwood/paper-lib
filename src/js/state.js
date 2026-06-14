// Global application state
export const state = {
    allPapers: [],
    filteredPapers: [],
    selectedYears: new Set(),
    selectedPapers: new Set(),
    currentPaper: null,
    currentPage: 1,
    currentTrendingWindow: '7',
    trendingRefreshTimer: null,
    PAGE_SIZE: 20,
};
