document.addEventListener("DOMContentLoaded", function () {

    const password = document.getElementById("password");
    const togglePassword = document.getElementById("togglePassword");

    if (password && togglePassword) {

        togglePassword.addEventListener("click", function () {

            const icon = this.querySelector("i");

            if (password.type === "password") {

                password.type = "text";

                icon.classList.remove("fa-eye");
                icon.classList.add("fa-eye-slash");

            } else {

                password.type = "password";

                icon.classList.remove("fa-eye-slash");
                icon.classList.add("fa-eye");

            }

        });

    }

});