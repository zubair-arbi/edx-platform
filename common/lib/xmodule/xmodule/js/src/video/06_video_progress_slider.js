(function (requirejs, require, define) {

/*
"This is as true in everyday life as it is in battle: we are given one life
and the decision is ours whether to wait for circumstances to make up our
mind, or whether to act, and in acting, to live."
— Omar N. Bradley
 */

// VideoProgressSlider module.
define(
'video/06_video_progress_slider.js',
[],
function () {
    // VideoProgressSlider() function - what this module "exports".
    return function (state) {
        var dfd = $.Deferred();

        state.videoProgressSlider = {};

        _makeFunctionsPublic(state);
        _renderElements(state);
        // No callbacks to DOM events (click, mousemove, etc.).

        dfd.resolve();
        return dfd.promise();
    };

    // ***************************************************************
    // Private functions start here.
    // ***************************************************************

    // function _makeFunctionsPublic(state)
    //
    //     Functions which will be accessible via 'state' object. When called,
    //     these functions will get the 'state' object as a context.
    function _makeFunctionsPublic(state) {
        var methodsDict = {
            buildSlider: buildSlider,
            getRangeParams: getRangeParams,
            onSlide: onSlide,
            onStop: onStop,
            updatePlayTime: updatePlayTime,
            updateStartEndTimeRegion: updateStartEndTimeRegion,
            notifyThroughHandleEnd: notifyThroughHandleEnd
        };

        state.bindTo(methodsDict, state.videoProgressSlider, state);
    }

    // function _renderElements(state)
    //
    //     Create any necessary DOM elements, attach them, and set their
    //     initial configuration. Also make the created DOM elements available
    //     via the 'state' object. Much easier to work this way - you don't
    //     have to do repeated jQuery element selects.
    function _renderElements(state) {
        state.videoProgressSlider.el = state.videoControl.sliderEl;

        state.videoProgressSlider.buildSlider();
        _buildHandle(state);
    }

    function _buildHandle(state) {
        state.videoProgressSlider.handle = state.videoProgressSlider.el
            .find('.ui-slider-handle');

        // ARIA
        // We just want the knob to be selectable with keyboard
        state.videoProgressSlider.el.attr('tabindex', -1);
        // Let screen readers know that this anchor, representing the slider
        // handle, behaves as a slider named 'video position'.
        state.videoProgressSlider.handle.attr({
            'role': 'slider',
            'title': 'video position',
            'aria-disabled': false,
            'aria-valuetext': getTimeDescription(state.videoProgressSlider
                .slider.slider('option', 'value'))
        });
    }

    // ***************************************************************
    // Public functions start here.
    // These are available via the 'state' object. Their context ('this'
    // keyword) is the 'state' object. The magic private function that makes
    // them available and sets up their context is makeFunctionsPublic().
    // ***************************************************************

    function buildSlider() {
        this.videoProgressSlider.slider = this.videoProgressSlider.el
            .slider({
                range: 'min',
                slide: this.videoProgressSlider.onSlide,
                stop: this.videoProgressSlider.onStop
            });

        this.videoProgressSlider.sliderProgress = this.videoProgressSlider
            .slider
            .find('.ui-slider-range.ui-widget-header.ui-slider-range-min');
    }

    // Rebuild the slider start-end range (if it doesn't take up the
    // whole slider). Remember that endTime === null means the end time
    // is set to the end of video by default.
    function updateStartEndTimeRegion(params) {
        var left, width, start, end, duration, rangeParams;

        // We must have a duration in order to determine the area of range.
        // It also must be non-zero.
        if (!params.duration) {
            return;
        } else {
            duration = params.duration;
        }

        start = this.config.startTime;
        end = this.config.endTime;

        if (start > duration) {
            start = 0;
        } else {
            if (this.currentPlayerMode === 'flash') {
                start /= Number(this.speed);
            }
        }

        // If end is set to null, or it is greater than the duration of the
        // video, then we set it to the end of the video.
        if (
            end === null || end > duration
        ) {
            end = duration;
        } else if (end !== null) {
            if (this.currentPlayerMode === 'flash') {
                end /= Number(this.speed);
            }
        }

        // Don't build a range if it takes up the whole slider.
        if (start === 0 && end === duration) {
            return;
        }

        // Because JavaScript has weird rounding rules when a series of
        // mathematical operations are performed in a single statement, we will
        // split everything up into smaller statements.
        //
        // This will ensure that visually, the start-end range aligns nicely
        // with actual starting and ending point of the video.

        rangeParams = getRangeParams(start, end, duration);

        if (!this.videoProgressSlider.sliderRange) {
            this.videoProgressSlider.sliderRange = $('<div />', {
                class: 'ui-slider-range ' +
                       'ui-widget-header ' +
                       'ui-corner-all ' +
                       'slider-range'
            }).css(rangeParams);

            this.videoProgressSlider.sliderProgress
                .after(this.videoProgressSlider.sliderRange);
        } else {
            this.videoProgressSlider.sliderRange
                .css(rangeParams);
        }
    }

    function getRangeParams(startTime, endTime, duration) {
        var step = 100 / duration,
            left = startTime * step,
            width = endTime * step - left;

        return {
            left: left + '%',
            width: width + '%'
        };
    }

    function onSlide(event, ui) {
        this.videoProgressSlider.frozen = true;

        this.trigger(
            'videoPlayer.onSlideSeek',
            {'type': 'onSlideSeek', 'time': ui.value}
        );

        // ARIA
        this.videoProgressSlider.handle.attr(
            'aria-valuetext', getTimeDescription(this.videoPlayer.currentTime)
        );
    }

    function onStop(event, ui) {
        var _this = this;

        this.videoProgressSlider.frozen = true;

        this.trigger(
            'videoPlayer.onSlideSeek',
            {'type': 'onSlideSeek', 'time': ui.value}
        );

        // ARIA
        this.videoProgressSlider.handle.attr(
            'aria-valuetext', getTimeDescription(this.videoPlayer.currentTime)
        );

        setTimeout(function() {
            _this.videoProgressSlider.frozen = false;
        }, 200);
    }

    function updatePlayTime(params) {
        var time = Math.floor(params.time),
            duration = Math.floor(params.duration);

        if (
            (this.videoProgressSlider.slider) &&
            (!this.videoProgressSlider.frozen)
        ) {
            this.videoProgressSlider.slider
                .slider('option', 'max', duration)
                .slider('option', 'value', time);
        }
    }

    // When the video stops playing (either because the end was reached, or
    // because endTime was reached), the screen reader must be notified that
    // the video is no longer playing. We do this by a little trick. Setting
    // the title attribute of the slider know to "video ended", and focusing
    // on it. The screen reader will read the attr text.
    //
    // The user can then tab his way forward, landing on the next control
    // element, the Play button.
    //
    // @param params  -  object with property `end`. If set to true, the
    //                   function must set the title attribute to
    //                   `video ended`;
    //                   if set to false, the function must reset the attr to
    //                   it's original state.
    //
    // This function will be triggered from VideoPlayer methods onEnded(),
    // onPlay(), and update() (update method handles endTime).
    function notifyThroughHandleEnd(params) {
        if (params.end) {
            this.videoProgressSlider.handle
                .attr('title', 'video ended')
                .focus();
        } else {
            this.videoProgressSlider.handle.attr('title', 'video position');
        }
    }

    // Returns a string describing the current time of video in hh:mm:ss
    // format.
    function getTimeDescription(time) {
        var seconds = Math.floor(time),
            minutes = Math.floor(seconds / 60),
            hours = Math.floor(minutes / 60),
            hrStr, minStr, secStr;

        seconds = seconds % 60;
        minutes = minutes % 60;

        hrStr = hours.toString(10);
        minStr = minutes.toString(10);
        secStr = seconds.toString(10);

        if (hours) {
            hrStr += (hours < 2 ? ' hour ' : ' hours ');

            if (minutes) {
                minStr += (minutes < 2 ? ' minute ' : ' minutes ');
            } else {
                minStr += ' 0 minutes ';
            }

            if (seconds) {
                secStr += (seconds < 2 ? ' second ' : ' seconds ');
            } else {
                secStr += ' 0 seconds ';
            }

            return hrStr + minStr + secStr;
        } else if (minutes) {
            minStr += (minutes < 2 ? ' minute ' : ' minutes ');

            if (seconds) {
                secStr += (seconds < 2 ? ' second ' : ' seconds ');
            } else {
                secStr += ' 0 seconds ';
            }

            return minStr + secStr;
        } else if (seconds) {
            secStr += (seconds < 2 ? ' second ' : ' seconds ');

            return secStr;
        }

        return '0 seconds';
    }

});

}(RequireJS.requirejs, RequireJS.require, RequireJS.define));
