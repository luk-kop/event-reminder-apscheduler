let notifyUnit = document.getElementById("id-notify_unit");
let notifyInterval = document.getElementById("id-notify_interval");

function validateInterval() {
    if ((notifyUnit.value === 'seconds') && (notifyInterval.value < 30)) {
        notifyInterval.setCustomValidity("The interval should not be less than 30 seconds.");
    } else {
        notifyInterval.setCustomValidity("");
    };
};

function addAlert() {
    let notifyService = document.getElementById("id-notify_service");
    if ((notifyService.checked) && (notifyInterval.validity.valid)) {
        $('#alerts').append(
            '<div class="alert alert-warning alert-dismissible fade show text-center" role="alert">' +
                        'The mail service testing in progress...' +
                        '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
                            '<span aria-hidden="true">&times;</span>' +
                        '</button>' +
                    '</div>');
    }
}

window.onload = validateInterval;
notifyUnit.onchange = validateInterval;
notifyInterval.onchange = validateInterval;