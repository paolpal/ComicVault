function toggleFullScreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(err => {
      console.log(`Error attempting to enable fullscreen: ${err.message}`);
    });
  } else {
    document.exitFullscreen();
  }
}

document.addEventListener('click', (e) => {
  const btn = e.target.closest('#fullscreen-btn');
  if (btn) {
    e.preventDefault();
    toggleFullScreen();
  }
});

document.addEventListener('fullscreenchange', () => {
  const icon = document.getElementById('fullscreen-icon');
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
