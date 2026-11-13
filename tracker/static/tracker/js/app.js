(function () {
  var sidebar = document.getElementById("sidebar");
  var backdrop = document.getElementById("sidebarBackdrop");
  var toggle = document.getElementById("sidebarToggle");
  if (!sidebar || !backdrop || !toggle) {
    return;
  }

  function isMobile() {
    return window.matchMedia("(max-width: 991.98px)").matches;
  }

  function closeSidebar() {
    sidebar.classList.remove("is-open");
    backdrop.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
  }

  function openSidebar() {
    sidebar.classList.add("is-open");
    backdrop.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
  }

  toggle.addEventListener("click", function () {
    if (!isMobile()) {
      return;
    }
    if (sidebar.classList.contains("is-open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  backdrop.addEventListener("click", closeSidebar);
  sidebar.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      if (isMobile()) {
        closeSidebar();
      }
    });
  });
  window.addEventListener("resize", function () {
    if (!isMobile()) {
      closeSidebar();
    }
  });
})();
