function toggleFullScreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(err => {
      console.log(`Error attempting to enable fullscreen: ${err.message}`);
    });
  } else {
    document.exitFullscreen();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('fullscreen-btn');
  const icon = document.getElementById('fullscreen-icon');
  
  if (btn) {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      toggleFullScreen();
    });
  }

  document.addEventListener('fullscreenchange', () => {
    if (document.fullscreenElement) {
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
});
