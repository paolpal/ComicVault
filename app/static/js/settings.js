document.addEventListener("DOMContentLoaded", function() {
    var modal = document.getElementById("settingsModal");
    // find all gear icons
    var gearIcons = document.querySelectorAll(".fa-gear");
    for (var i = 0; i < gearIcons.length; i++) {
        var btn = gearIcons[i].parentElement;
        btn.addEventListener("click", function(e) {
            e.preventDefault();
            modal.style.display = "block";
        });
    }

    var closeBtn = document.querySelector(".close-modal");
    if (closeBtn) {
        closeBtn.addEventListener("click", function() {
            modal.style.display = "none";
        });
    }

    window.addEventListener("click", function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    });

    function getCookie(name) {
        var value = "; " + document.cookie;
        var parts = value.split("; " + name + "=");
        if (parts.length === 2) return parts.pop().split(";").shift();
        return "high"; // default
    }

    function setCookie(name, value, days) {
        var expires = "";
        if (days) {
            var date = new Date();
            date.setTime(date.getTime() + (days*24*60*60*1000));
            expires = "; expires=" + date.toUTCString();
        }
        document.cookie = name + "=" + (value || "")  + expires + "; path=/";
    }

    var currentRes = getCookie("image_resolution");
    var resBtns = document.querySelectorAll(".res-btn");
    for (var j = 0; j < resBtns.length; j++) {
        if (resBtns[j].getAttribute("data-res") === currentRes) {
            resBtns[j].className += " active";
        }
        resBtns[j].addEventListener("click", function() {
            var res = this.getAttribute("data-res");
            setCookie("image_resolution", res, 365);
            window.location.reload();
        });
    }
});
