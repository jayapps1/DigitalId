document.querySelectorAll(".dropdown-toggle").forEach(btn => {
    btn.addEventListener("click", function(e) {
        e.preventDefault();
        let parent = this.parentElement;
        parent.classList.toggle("active");
    });
});

// zoom cropping for profile pic 

function initCropper(fileInputId, imgPreviewId, hiddenInputId) {
    let cropper = null;
    const input = document.getElementById(fileInputId);
    const preview = document.getElementById(imgPreviewId);
    const hiddenInput = document.getElementById(hiddenInputId);
    const form = input.closest("form");

    if (!input) return;

    input.addEventListener("change", function () {
        const file = this.files[0];
        if (!file || !file.type.startsWith("image/")) return;

        const reader = new FileReader();
        reader.onload = function (e) {
            preview.src = e.target.result;
            preview.classList.remove("d-none");

            if (cropper) cropper.destroy();

            cropper = new Cropper(preview, {
                aspectRatio: 3 / 4,
                viewMode: 1,
                dragMode: "move",
                autoCropArea: 1,
                background: false,
                responsive: true,
                zoomOnWheel: true,
                movable: true,
                scalable: true,
                cropBoxResizable: false,
            });
        };
        reader.readAsDataURL(file);
    });

    form.addEventListener("submit", function () {
        if (cropper) {
            const canvas = cropper.getCroppedCanvas({
                width: 450,
                height: 600,
                imageSmoothingQuality: "high"
            });
            hiddenInput.value = canvas.toDataURL("image/jpeg", 0.9);
        }
    });
}




// ================================
// pending count refresh auto 
// ================================

function updateBadge() {
    fetch('/admin/api/pending-requests-count/')  // <- fixed path
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('pending-badge');
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        })
        .catch(err => console.error("Failed to fetch badge count:", err)); // graceful error handling
}

setInterval(updateBadge, 10000); // update every 10 seconds


 
// ================================
// CSRF helper (Django official)
// ================================
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie("csrftoken");

document.addEventListener("DOMContentLoaded", function () {

    const unreadBadge = document.querySelector("#notificationDropdown .badge");

    // ================================
    // Update unread count
    // ================================
    function updateUnreadCount() {
        const url = document.body.dataset.unreadCountUrl;
        if (!url || !unreadBadge) return;

        fetch(url, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(res => res.json())
        .then(data => {
            if (data.unread_count > 0) {
                unreadBadge.textContent = data.unread_count;
                unreadBadge.classList.remove("d-none");
            } else {
                unreadBadge.classList.add("d-none");
            }
        })
        .catch(() => {});
    }

    // ================================
    // Mark as read (dropdown + list)
    // ================================
    document.querySelectorAll("[data-mark-read-url]").forEach(el => {
        el.addEventListener("click", function (e) {

            const markUrl = this.dataset.markReadUrl;
            if (!markUrl) return;

            fetch(markUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrftoken,
                    "X-Requested-With": "XMLHttpRequest"
                }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    this.classList.remove("fw-bold");
                    const li = this.closest("li");
                    if (li) li.classList.remove("fw-bold");
                    updateUnreadCount();
                }
            })
            .catch(() => {});
        });
    });

    // ================================
    // Poll every 30s (optional)
    // ================================
    setInterval(updateUnreadCount, 30000);
});
