// Page Agent integration — relies on page-agent.demo.js IIFE auto-init
// Config is passed via script URL query params in index.html

let agentReady = false;

/**
 * Check if the Page Agent demo UI has initialized successfully.
 * The demo script auto-inits and sets window.pageAgent.
 */
async function initAgent() {
    // Wait briefly for the demo script's setTimeout auto-init
    await new Promise(r => setTimeout(r, 500));

    if (typeof window.pageAgent === 'undefined') {
        console.warn('Page Agent: auto-init did not create window.pageAgent');
        return;
    }

    agentReady = true;
    console.log('Page Agent: ready, using demo UI');
}

async function execute(command) {
    if (!agentReady || typeof window.pageAgent === 'undefined') {
        console.warn('Page Agent: not ready');
        return;
    }
    try {
        await window.pageAgent.execute(command);
    } catch (err) {
        console.error('Page Agent execute failed:', err);
    }
}

export { initAgent, execute };
