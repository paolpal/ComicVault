document.addEventListener('DOMContentLoaded', function() {
  var icon = document.getElementById('fullscreen-icon');
  
  if (window !== window.parent || document.fullscreenElement) {
    if (icon) {
      icon.classList.remove('fa-expand');
      icon.classList.add('fa-compress');
    }
  } else {
    if (icon) {
      icon.classList.remove('fa-compress');
      icon.classList.add('fa-expand');
    }
  }
});

document.addEventListener('click', function(e) {
  var node = e.target;
  var btn = null;
  while (node && node.nodeName !== 'BODY') {
    if (node.id === 'fullscreen-btn') {
      btn = node;
      break;
    }
    node = node.parentNode;
  }
  
  if (btn) {
    e.preventDefault();
    
    if (window !== window.parent) {
      window.parent.postMessage('toggleFullscreen', '*');
      return;
    }

    if (!document.fullscreenElement) {
      var iframe = document.createElement('iframe');
      iframe.src = window.location.href; 
      iframe.id = 'fullscreen-iframe';
      iframe.style.position = 'fixed';
      iframe.style.top = '0';
      iframe.style.left = '0';
      iframe.style.width = '100vw';
      iframe.style.height = '100vh';
      iframe.style.border = 'none';
      iframe.style.zIndex = '9999';
      iframe.style.backgroundColor = 'black';
      
      document.body.appendChild(iframe);
      document.body.style.overflow = 'hidden';

      if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(function(err) {
          console.log('Error attempting to enable fullscreen: ' + err.message);
          if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
          document.body.style.overflow = '';
        });
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  }
});

window.addEventListener('message', function(e) {
  if (e.data === 'toggleFullscreen') {
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen();
    }
  }
});

document.addEventListener('fullscreenchange', function() {
  if (!document.fullscreenElement) {
    var iframe = document.getElementById('fullscreen-iframe');
    if (iframe) {
      try {
        var iframeUrl = iframe.contentWindow.location.pathname + iframe.contentWindow.location.search;
        if (iframeUrl !== window.location.pathname + window.location.search) {
          window.location.href = iframeUrl;
          return;
        }
      } catch (e) {
        console.error("Non posso accedere all'iframe location:", e);
      }
      if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
      document.body.style.overflow = '';
      
      var icon = document.getElementById('fullscreen-icon');
      if (icon) {
        icon.classList.remove('fa-compress');
        icon.classList.add('fa-expand');
      }
    }
  }
});

// Fix per iOS Standalone Web App (compatibile con iOS 5 iPad 1)
if (("standalone" in window.navigator) && window.navigator.standalone) {
  document.addEventListener('click', function(event) {
    var node = event.target;
    while (node && node.nodeName !== "A") {
      node = node.parentNode;
    }
    
    if (node && node.nodeName === "A" && node.getAttribute("href")) {
      var href = node.getAttribute("href");
      
      // Se è un link placeholder (es. href="#"), blocchiamo comunque il comportamento
      // di default per evitare che iOS apra Safari, ma non navighiamo da nessuna parte.
      if (!href || href.indexOf("#") === 0 || href.indexOf("javascript:") === 0) {
        event.preventDefault();
        return;
      }
      
      if (node.getAttribute("target") === "_blank") return;

      event.preventDefault();
      window.location.href = node.href;
    }
  }, false);
}
