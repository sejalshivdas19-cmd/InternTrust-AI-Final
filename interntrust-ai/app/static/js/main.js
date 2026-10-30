document.addEventListener("DOMContentLoaded", function () {
  // Animate any risk meter fill bars from 0 to their target width.
  document.querySelectorAll(".risk-meter-fill").forEach(function (el) {
    var target = el.getAttribute("data-score") || 0;
    el.style.width = "0%";
    requestAnimationFrame(function () {
      setTimeout(function () {
        el.style.width = target + "%";
      }, 100);
    });
  });

  // Checklist status updates via fetch, without a full page reload.
  document.querySelectorAll(".checklist-status-select").forEach(function (select) {
    select.addEventListener("change", function () {
      var itemId = this.getAttribute("data-item-id");
      var status = this.value;
      var formData = new FormData();
      formData.append("status", status);
      var csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");

      fetch("/dashboard/checklist/" + itemId + "/update", {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrfToken },
        body: formData,
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.success) {
            var badge = document.querySelector('[data-badge-for="' + itemId + '"]');
            if (badge) {
              badge.textContent = status.replace("_", " ");
            }
          }
        })
        .catch(function () { /* fail silently, page reload will show real state */ });
    });
  });

  // Enable Bootstrap tooltips if any are present.
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.forEach(function (el) {
    if (window.bootstrap) { new bootstrap.Tooltip(el); }
  });

  // Simple file input name preview.
  var fileInput = document.getElementById("document");
  if (fileInput) {
    fileInput.addEventListener("change", function () {
      var label = document.getElementById("file-name-preview");
      if (label) { label.textContent = this.files.length ? this.files[0].name : "No file selected"; }
    });
  }
});
