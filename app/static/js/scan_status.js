(async function pollScan() {
    const target = document.getElementById('scan-status');
    try {
        const response = await fetch('/scan/status');
        if (!response.ok) throw new Error('scan status unavailable');
        const status = await response.json();
        target.textContent = status.message || '';
        if (status.state === 'running') setTimeout(pollScan, 2000);
    } catch (error) {
        target.textContent = 'Impossibile verificare lo stato della scansione.';
    }
})();
