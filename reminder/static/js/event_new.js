
document.getElementById("id-allday").onchange = function () {
        let time_start = document.getElementById("id-time_event_start");
        let time_stop = document.getElementById("id-time_event_stop");
        if (this.value == 'True') {
            time_start.value = null;
            time_stop.value = null;
            time_start.disabled = true;
            time_stop.disabled = true;

            }
        else {
            time_start.disabled = false;
            time_stop.disabled = false;
            time_start.value = "08:00";
            time_stop.value = "09:00";
            time_stop.setCustomValidity("");
            }
    };
    document.getElementById("id-to_notify").onchange = function () {
        let date_notify = document.getElementById("id-date_notify");
        let time_notify = document.getElementById("id-time_notify");
        let users_notified = document.getElementById("id-notified_user");
        let date = new Date();
        let day = date.getDate();
        let month = date.getMonth() + 1;
        let year = date.getFullYear();
        if (month < 10) month = "0" + month;
        if (day < 10) day = "0" + day;
        let today = year + "-" + month + "-" + day;
        if (this.value == 'False') {
            date_notify.value = null;
            time_notify.value = null;
            date_notify.disabled = true;
            time_notify.disabled = true;
            users_notified.disabled = true;
            }
        else {
            date_notify.disabled = false;
            time_notify.disabled = false;
            users_notified.disabled = false;
            date_notify.value = today;
            time_notify.value = "08:00";
            if (date_start.value < date_notify.value) {
                date_notify.setCustomValidity("Should be earlier than the start date.");
                }
            else {
                date_notify.setCustomValidity("");
                };
            };
    };

function validateTimeEvent() {
    let date_start = document.getElementById("id-date_event_start");
    let date_stop = document.getElementById("id-date_event_stop");
    let time_start = document.getElementById("id-time_event_start");
    let time_stop = document.getElementById("id-time_event_stop");
    let date_notify = document.getElementById("id-date_notify");
    let all_day = document.getElementById("id-allday");


    if ((all_day.value == 'True') && (this == date_start)) {
        date_stop.value = date_start.value;
    };
    if (date_start.value > date_stop.value) {
        date_stop.setCustomValidity("Should be later than the start date.");
    } else if ((date_start.value == date_stop.value) && (time_start.value > time_stop.value)) {
        time_stop.setCustomValidity("Should be later than the start time.");
        date_stop.setCustomValidity("");
    } else {
        date_stop.setCustomValidity("");
        time_stop.setCustomValidity("");
        };
    if (date_start.value < date_notify.value) {
        date_notify.setCustomValidity("Should be earlier than the start date.");
    } else {
        date_notify.setCustomValidity("");
        };
};

function validateNotifyTimeEvent() {
    let date_start = document.getElementById("id-date_event_start");
    let date_notify = document.getElementById("id-date_notify");
    if (date_start.value < date_notify.value) {
        date_notify.setCustomValidity("Should be earlier than the start date.");
    } else {
        date_notify.setCustomValidity("");
        };
};

document.getElementById("id-date_event_start").onchange = validateTimeEvent;
document.getElementById("id-date_event_stop").onchange = validateTimeEvent;
document.getElementById("id-time_event_start").onchange = validateTimeEvent;
document.getElementById("id-time_event_stop").onchange = validateTimeEvent;
document.getElementById("id-date_notify").onchange = validateNotifyTimeEvent;