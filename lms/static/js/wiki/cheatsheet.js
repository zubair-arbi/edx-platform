$(document).ready(function () {
    $('#cheatsheetLink').click(function() {
        $('#cheatsheetModal').leanModal();
    });
    accessible_modal("#cheatsheetModal", "#cheatesheetModal .close-modal", "#cheatesheetModal", ".wiki.edit");
});