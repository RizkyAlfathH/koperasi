// TAMPILKAN LOADER
function showLoader() {
  const loader = document.getElementById("global-loader");
  if (loader) {
    loader.classList.remove("hide");
  }
}

// MATIKAN LOADER SAAT HALAMAN SELESAI LOAD
window.addEventListener("load", function () {
  const loader = document.getElementById("global-loader");
  if (loader) {
    loader.classList.add("hide");
  }
});
