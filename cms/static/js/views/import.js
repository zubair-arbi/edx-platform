/**
 * Course import-related js.
 */
define(
    ["domReady", "jquery", "underscore", "gettext"],
    function(domReady, $, _, gettext) {

        "use strict";

        /********** Private functions ************************************************/

        /**
         * Toggle the spin on the progress cog.
         * @param {boolean} isSpinning Turns cog spin on if true, off otherwise.
         */
        var updateCog = function (elem, isSpinning) {
            var cogI = elem.find('i.icon-cog');
            if (isSpinning) { cogI.addClass("icon-spin");}
            else { cogI.removeClass("icon-spin");}
        };


        /**
         * Manipulate the DOM to reflect current status of upload.
         * @param {int} stageNo Current stage.
         */
        var updateStage = function (stageNo){
            var all = $('ol.status-progress').children();
            var prevList = all.slice(0, stageNo);
            _.map(prevList, function (elem){
                $(elem).
                    removeClass("is-not-started").
                    removeClass("is-started").
                    addClass("is-complete");
                updateCog($(elem), false);
            });
            var curList = all.eq(stageNo);
            curList.removeClass("is-not-started").addClass("is-started");
            updateCog(curList, true);
        };

        /**
         * Check for import status updates every `timeout` milliseconds, and update
         * the page accordingly.
         * @param {string} url Url to call for status updates.
         * @param {int} timeout Number of milliseconds to wait in between ajax calls
         *     for new updates.
         * @param {int} stage Starting stage.
         */
        var getStatus = function (url, timeout, stage) {
            var currentStage = stage || 0;
            if (CourseImport.stopGetStatus) { return ;}
            updateStage(currentStage);
            if (currentStage == 3 ) { return ;}
            var time = timeout || 1000;
            $.getJSON(url,
                function (data) {
                    setTimeout(function () {
                        getStatus(url, time, data.ImportStatus);
                    }, time);
                }
            );
        };



        /********** Public functions *************************************************/

        var CourseImport = {

            /**
             * Whether to stop sending AJAX requests for updates on the import
             * progress.
             */
            stopGetStatus: false,

            /**
             * Update DOM to set all stages as not-started (for retrying an upload that
             * failed).
             */
            clearImportDisplay: function () {
                var all = $('ol.status-progress').children();
                _.map(all, function (elem){
                    $(elem).removeClass("is-complete").
                        removeClass("is-started").
                        removeClass("has-error").
                        addClass("is-not-started");
                    $(elem).find('p.error').remove(); // remove error messages
                    $(elem).find('p.copy').show();
                    updateCog($(elem), false);
                });
                this.stopGetStatus = false;
            },

            /**
             * Update DOM to set all stages as complete, and stop asking for status
             * updates.
             */
            displayFinishedImport: function () {
                this.stopGetStatus = true;
                var all = $('ol.status-progress').children();
                _.map(all, function (elem){
                    $(elem).
                        removeClass("is-not-started").
                        removeClass("is-started").
                        addClass("is-complete");
                    updateCog($(elem), false);
                });
            },

            /**
             * Entry point for server feedback. Makes status list visible and starts
             * sending requests to the server for status updates.
             * @param {string} url The url to send Ajax GET requests for updates.
             */
            startServerFeedback: function (url){
                this.stopGetStatus = false;
                $('div.wrapper-status').removeClass('is-hidden');
                $('.status-info').show();
                getStatus(url, 500, 0);
            },


            /**
             * Give error message at the list element that corresponds to the stage
             * where the error occurred.
             * @param {int} stageNo Stage of import process at which error occurred.
             * @param {string} msg Error message to display.
             */
            stageError: function (stageNo, msg) {
                var all = $('ol.status-progress').children();
                // Make all stages up to, and including, the error stage 'complete'.
                var prevList = all.slice(0, stageNo + 1);
                _.map(prevList, function (elem){
                    $(elem).
                        removeClass("is-not-started").
                        removeClass("is-started").
                        addClass("is-complete");
                    updateCog($(elem), false);
                });
                var message = msg || gettext("There was an error with the upload");
                var elem = $('ol.status-progress').children().eq(stageNo);
                elem.removeClass('is-started').addClass('has-error');
                elem.find('p.copy').hide().after("<p class='copy error'>" + message + "</p>");
            }

        };

        var showImportSubmit = function (e) {
            var filepath = $(this).val();
            if (filepath.substr(filepath.length - 6, 6) == 'tar.gz') {
                $('.error-block').hide();
                $('.file-name').html($(this).val().replace('C:\\fakepath\\', ''));
                $('.file-name-block').show();
                $('.view-import .choose-file-button').hide();
                $('.submit-button').show();
                $('.progress').show();
            } else {
                $('.error-block').html(gettext('File format not supported. Please upload a file with a <code>tar.gz</code> extension.')).show();
            }
        };

        domReady(function () {
            // import form setup
            $('.view-import .file-input').bind('change', showImportSubmit);
            $('.view-import .choose-file-button, .view-import .choose-file-button-inline').bind('click', function (e) {
                e.preventDefault();
                $('.view-import .file-input').click();
            });
        });

        return CourseImport;
    });
