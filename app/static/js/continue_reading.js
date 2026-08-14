document.addEventListener("DOMContentLoaded", function() {
    var grid = document.getElementById("history-grid");
    var progressStr = localStorage.getItem("comic_progress");
    var progress = progressStr ? JSON.parse(progressStr) : {};
    
    var items = [];
    for (var slug in progress) {
        if (progress.hasOwnProperty(slug)) {
            var item = progress[slug];
            item.slug = slug;
            items.push(item);
        }
    }
    
    // Sort by most recent
    items.sort(function(a, b) {
        return b.timestamp - a.timestamp;
    });
    
    if (items.length === 0) {
        grid.innerHTML = '<div class="empty-state">Nessun fumetto in lettura su questo dispositivo.</div>';
        return;
    }
    
    var html = '';
    for (var i = 0; i < items.length; i++) {
        var item = items[i];
        var percentage = 0;
        if (item.total_pages > 1) {
            percentage = Math.floor((item.page_number / (item.total_pages - 1)) * 100);
        }
        
        html += '<div class="comic">';
        // Link per riprendere la lettura
        html += '<a href="' + item.url + '">';
        html += '<img src="' + item.cover + '" alt="Cover">';
        html += '<div class="comic-title">' + item.title + '</div>';
        html += '<div class="comic-meta">Cap. ' + item.chapter_number + ' - Pag. ' + (item.page_number + 1) + ' / ' + item.total_pages + '</div>';
        html += '<div class="progress-bar-container"><div class="progress-bar-fill" style="width: ' + percentage + '%"></div></div>';
        html += '</a></div>';
    }
    
    grid.innerHTML = html;
});
