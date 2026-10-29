
(() => {
  const progress = document.getElementById('progress-bar');
  const menuButton = document.getElementById('menu-toggle');
  const nav = document.getElementById('main-nav');
  const year = document.getElementById('year');

  // Update the scroll progress bar
  const updateProgress = () => {
    if (!progress) return;

    const max =
      document.documentElement.scrollHeight - window.innerHeight;

    progress.style.width =
      `${max > 0 ? (window.scrollY / max) * 100 : 0}%`;
  };

  window.addEventListener('scroll', updateProgress, {
    passive: true
  });

  updateProgress();

  // Automatically update the copyright year
  if (year) {
    year.textContent = new Date().getFullYear();
  }

  // Mobile navigation menu
  if (menuButton && nav) {
    menuButton.addEventListener('click', () => {
      const open = nav.classList.toggle('open');

      menuButton.setAttribute(
        'aria-expanded',
        String(open)
      );

      menuButton.innerHTML = open
        ? '<i class="fa-solid fa-xmark"></i>'
        : '<i class="fa-solid fa-bars"></i>';
    });

    // Close the menu after clicking a navigation link
    nav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        nav.classList.remove('open');

        menuButton.setAttribute(
          'aria-expanded',
          'false'
        );

        menuButton.innerHTML =
          '<i class="fa-solid fa-bars"></i>';
      });
    });
  }
})();

