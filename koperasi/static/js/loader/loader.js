let loaderTimeout;

function showLoader() {
  const loader = document.getElementById("global-loader");
  if (loader) {
    loader.classList.remove("hide");

    // ✅ Auto-matikan loader maksimal 5 detik
    clearTimeout(loaderTimeout);
    loaderTimeout = setTimeout(() => {
      hideLoader();
    }, 5000);
  }
}

function hideLoader() {
  const loader = document.getElementById("global-loader");
  if (loader) {
    loader.classList.add("hide");
  }
  clearTimeout(loaderTimeout);
}

window.addEventListener("load", function () {
  hideLoader();
});