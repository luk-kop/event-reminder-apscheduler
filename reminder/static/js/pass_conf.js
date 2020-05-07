
window.onload = function () {
                var txtPassword = document.getElementById("id-password");
                var txtConfirmPassword = document.getElementById("id-password2");
                txtPassword.onchange = ConfirmPassword;
                txtConfirmPassword.onkeyup = ConfirmPassword;
                function ConfirmPassword() {
                    txtConfirmPassword.setCustomValidity("");
                    if (txtPassword.value != txtConfirmPassword.value) {
                        txtConfirmPassword.setCustomValidity("Passwords do not match.");
                    }
                }
            }