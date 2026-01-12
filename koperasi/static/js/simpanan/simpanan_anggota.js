document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".btn-penarikan").forEach(btn => {
    btn.addEventListener("click", function (e) {
      const saldo = parseFloat(this.dataset.saldo);

      if (!saldo || saldo <= 0) {
        e.preventDefault();
        Swal.fire({
          icon: 'warning',
          title: 'Saldo Tidak Cukup',
          text: 'Saldo simpanan masih 0, tidak bisa melakukan penarikan.',
          confirmButtonColor: '#c9a227'
        });
      }
    });
  });
});
