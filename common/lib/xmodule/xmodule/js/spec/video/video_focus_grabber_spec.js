(function () {
    describe('Video FocusGrabber', function () {
        var state;

        beforeEach(function () {
            // https://github.com/pivotal/jasmine/issues/184
            //
            // This is a known issue. jQuery animations depend on setTimeout
            // and the jasmine mock clock stubs that function. You need to turn
            // off jQuery animations ($.fx.off()) in a global beforeEach.
            //
            // I think this is a good pattern - you don't want animations
            // messing with your tests. If you need to test with animations on
            // I suggest you add incremental browser-based testing to your
            // stack.
            jQuery.fx.off = true;

            loadFixtures('video_html5.html');
            state = new Video('#example');

            spyOnEvent(state.el, 'mousemove');
            spyOn(state.focusGrabber, 'disableFocusGrabber').andCallThrough();
            spyOn(state.focusGrabber, 'enableFocusGrabber').andCallThrough();
        });

        afterEach(function () {
            // Turn jQuery animations back on.
            jQuery.fx.off = true;
        });

        it(
            'check existence of focus grabber elements and their position',
            function () {

            var firstFGEl = state.el.find('.focus_grabber.first'),
                lastFGEl = state.el.find('.focus_grabber.last'),
                tcWrapperEl = state.el.find('.tc-wrapper');

            // Existence check.
            expect(firstFGEl.length).toBe(1);
            expect(lastFGEl.length).toBe(1);

            // Position check.
            expect(firstFGEl.index() + 1).toBe(tcWrapperEl.index());
            expect(lastFGEl.index() - 1).toBe(tcWrapperEl.index());
        });

        it('from the start, focus grabbers are disabled', function () {
            expect(state.focusGrabber.elFirst.attr('tabindex')).toBe(-1);
            expect(state.focusGrabber.elLast.attr('tabindex')).toBe(-1);
        });

        it(
            'when first focus grabber is focused "mousemove" event is ' +
            'triggered, grabbers are disabled',
            function () {

            state.focusGrabber.elFirst.triggerHandler('focus');

            expect('mousemove').toHaveBeenTriggeredOn(state.el);
            expect(state.focusGrabber.disableFocusGrabber).toHaveBeenCalled();
        });

        it(
            'when last focus grabber is focused "mousemove" event is ' +
            'triggered, grabbers are disabled',
            function () {

            state.focusGrabber.elLast.triggerHandler('focus');

            expect('mousemove').toHaveBeenTriggeredOn(state.el);
            expect(state.focusGrabber.disableFocusGrabber).toHaveBeenCalled();
        });

        xit('after controls hide focus grabbers are enabled', function () {
            runs(function () {
                // Captions should not be "sticky" for the autohide mechanism
                // to work.
                state.videoCaption.hideCaptions(true);

                // Make sure that the controls are visible. After this event
                // is triggered a count down is started to autohide captions.
                state.el.triggerHandler('mousemove');
            });

            // Wait for the autohide to happen. We make it +100ms to make sure
            // that there is clearly no race conditions for our expect below.
            waits(state.videoControl.fadeOutTimeout + 100);

            runs(function () {
                expect(
                    state.focusGrabber.enableFocusGrabber
                ).toHaveBeenCalled();
            });
        });
    });
}).call(this);
