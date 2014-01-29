(function (undefined) {
    describe('VideoPlayer', function () {
        var state, oldOTBD;

        beforeEach(function () {
            oldOTBD = window.onTouchBasedDevice;
            window.onTouchBasedDevice = jasmine.createSpy('onTouchBasedDevice')
                .andReturn(null);
        });

        afterEach(function () {
            $('source').remove();
            window.onTouchBasedDevice = oldOTBD;
        });

        describe('constructor', function () {
            describe('always', function () {
                beforeEach(function () {
                    state = jasmine.initializePlayer();

                    state.videoEl = $('video, iframe');
                });

                it('instanticate current time to zero', function () {
                    expect(state.videoPlayer.currentTime).toEqual(0);
                });

                it('set the element', function () {
                    expect(state.el).toHaveId('video_id');
                });

                it('create video control', function () {
                    expect(state.videoControl).toBeDefined();
                    expect(state.videoControl.el).toHaveClass('video-controls');
                });

                it('create video caption', function () {
                    expect(state.videoCaption).toBeDefined();
                    expect(state.youtubeId('1.0')).toEqual('Z5KLxerq05Y');
                    expect(state.speed).toEqual('1.50');
                    expect(state.config.captionAssetPath)
                        .toEqual('/static/subs/');
                });

                it('create video speed control', function () {
                    expect(state.videoSpeedControl).toBeDefined();
                    expect(state.videoSpeedControl.el).toHaveClass('speeds');
                    expect(state.videoSpeedControl.speeds)
                        .toEqual([ '0.75', '1.0', '1.25', '1.50' ]);
                    expect(state.speed).toEqual('1.50');
                });

                it('create video progress slider', function () {
                    expect(state.videoProgressSlider).toBeDefined();
                    expect(state.videoProgressSlider.el).toHaveClass('slider');
                });

                // All the toHandleWith() expect tests are not necessary for
                // this version of Video. jQuery event system is not used to
                // trigger and invoke methods. This is an artifact from
                // previous version of Video.
            });

            it('create Youtube player', function () {
                var events;

                jasmine.stubRequests();

                spyOn(window.YT, 'Player').andCallThrough();

                state = jasmine.initializePlayerYouTube();

                state.videoEl = $('video, iframe');

                events = {
                    onReady:                 state.videoPlayer.onReady,
                    onStateChange:           state.videoPlayer.onStateChange,
                    onPlaybackQualityChange: state.videoPlayer
                        .onPlaybackQualityChange
                };

                expect(YT.Player).toHaveBeenCalledWith('id', {
                    playerVars: {
                        controls: 0,
                        wmode: 'transparent',
                        rel: 0,
                        showinfo: 0,
                        enablejsapi: 1,
                        modestbranding: 1,
                        html5: 1
                    },
                    videoId: 'cogebirgzzM',
                    events: events
                });
            });

            // We can't test the invocation of HTML5Video because it is not
            // available globally. It is defined within the scope of Require
            // JS.

            describe('when on a touch based device', function () {
                $.each(['iPad', 'Android'], function (index, device) {
                    it('create video volume control on' + device, function () {
                        window.onTouchBasedDevice.andReturn([device]);
                        state = jasmine.initializePlayer();

                        state.videoEl = $('video, iframe');

                        expect(state.videoVolumeControl).toBeUndefined();
                        expect(state.el.find('div.volume')).not.toExist();
                    });
                });
            });

            describe('when not on a touch based device', function () {
                var oldOTBD;

                beforeEach(function () {
                    state = jasmine.initializePlayer();

                    state.videoEl = $('video, iframe');
                });

                it('controls are in paused state', function () {
                    expect(state.videoControl.isPlaying).toBe(false);
                });
            });
        });

        describe('onReady', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer, 'log').andCallThrough();
                spyOn(state.videoPlayer, 'play').andCallThrough();
                state.videoPlayer.onReady();
            });

            it('log the load_video event', function () {
                expect(state.videoPlayer.log).toHaveBeenCalledWith('load_video');
            });

            it('autoplay the first video', function () {
                expect(state.videoPlayer.play).not.toHaveBeenCalled();
            });
        });

        describe('onStateChange', function () {
            describe('when the video is unstarted', function () {
                beforeEach(function () {
                    state = jasmine.initializePlayer();

                    state.videoEl = $('video, iframe');

                    spyOn(state.videoControl, 'pause').andCallThrough();
                    spyOn(state.videoCaption, 'pause').andCallThrough();

                    state.videoPlayer.onStateChange({
                        data: YT.PlayerState.PAUSED
                    });
                });

                it('pause the video control', function () {
                    expect(state.videoControl.pause).toHaveBeenCalled();
                });

                it('pause the video caption', function () {
                    expect(state.videoCaption.pause).toHaveBeenCalled();
                });
            });

            describe('when the video is playing', function () {
                var oldState;

                beforeEach(function () {
                    // Create the first instance of the player.
                    state = jasmine.initializePlayer();
                    oldState = state;

                    spyOn(oldState.videoPlayer, 'onPause').andCallThrough();

                    // Now initialize a second instance.
                    state = jasmine.initializePlayer();

                    state.videoEl = $('video, iframe');

                    spyOn(state.videoPlayer, 'log').andCallThrough();
                    spyOn(window, 'setInterval').andReturn(100);
                    spyOn(state.videoControl, 'play');
                    spyOn(state.videoCaption, 'play');

                    state.videoPlayer.onStateChange({
                        data: YT.PlayerState.PLAYING
                    });
                });

                it('log the play_video event', function () {
                    expect(state.videoPlayer.log).toHaveBeenCalledWith(
                        'play_video', { currentTime: 0 }
                    );
                });

                it('pause other video player', function () {
                    expect(oldState.videoPlayer.onPause).toHaveBeenCalled();
                });

                it('set update interval', function () {
                    expect(window.setInterval).toHaveBeenCalledWith(
                        state.videoPlayer.update, 200
                    );
                    expect(state.videoPlayer.updateInterval).toEqual(100);
                });

                it('play the video control', function () {
                    expect(state.videoControl.play).toHaveBeenCalled();
                });

                it('play the video caption', function () {
                    expect(state.videoCaption.play).toHaveBeenCalled();
                });
            });

            describe('when the video is paused', function () {
                var currentUpdateIntrval;

                beforeEach(function () {
                    state = jasmine.initializePlayer();

                    state.videoEl = $('video, iframe');

                    spyOn(state.videoPlayer, 'log').andCallThrough();
                    spyOn(state.videoControl, 'pause').andCallThrough();
                    spyOn(state.videoCaption, 'pause').andCallThrough();

                    state.videoPlayer.onStateChange({
                        data: YT.PlayerState.PLAYING
                    });

                    currentUpdateIntrval = state.videoPlayer.updateInterval;

                    state.videoPlayer.onStateChange({
                        data: YT.PlayerState.PAUSED
                    });
                });

                it('log the pause_video event', function () {
                    expect(state.videoPlayer.log).toHaveBeenCalledWith(
                        'pause_video', { currentTime: 0 }
                    );
                });

                it('clear update interval', function () {
                    expect(state.videoPlayer.updateInterval).toBeUndefined();
                });

                it('pause the video control', function () {
                    expect(state.videoControl.pause).toHaveBeenCalled();
                });

                it('pause the video caption', function () {
                    expect(state.videoCaption.pause).toHaveBeenCalled();
                });
            });

            describe('when the video is ended', function () {
                beforeEach(function () {
                    state = jasmine.initializePlayer();

                    state.videoEl = $('video, iframe');

                    spyOn(state.videoControl, 'pause').andCallThrough();
                    spyOn(state.videoCaption, 'pause').andCallThrough();

                    state.videoPlayer.onStateChange({
                        data: YT.PlayerState.ENDED
                    });
                });

                it('pause the video control', function () {
                    expect(state.videoControl.pause).toHaveBeenCalled();
                });

                it('pause the video caption', function () {
                    expect(state.videoCaption.pause).toHaveBeenCalled();
                });
            });
        });

        describe('onSeek', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                runs(function () {
                    state.videoPlayer.play();
                });

                waitsFor(function () {
                    duration = state.videoPlayer.duration();

                    return duration > 0 && state.videoPlayer.isPlaying();
                }, 'video begins playing', WAIT_TIMEOUT);
            });

            it('Slider event causes log update', function () {

                runs(function () {
                    var currentTime = state.videoPlayer.currentTime;

                    spyOn(state.videoPlayer, 'log');
                    state.videoProgressSlider.onSlide(
                        jQuery.Event('slide'), { value: 2 }
                    );

                    expect(state.videoPlayer.log).toHaveBeenCalledWith(
                        'seek_video',
                        {
                            old_time: currentTime,
                            new_time: 2,
                            type: 'onSlideSeek'
                        }
                    );
                });
            });

            it('seek the player', function () {
                runs(function () {
                    spyOn(state.videoPlayer.player, 'seekTo');
                    state.videoProgressSlider.onSlide(
                        jQuery.Event('slide'), { value: 60 }
                    );

                    expect(state.videoPlayer.player.seekTo)
                        .toHaveBeenCalledWith(60, true);
                });
            });

            it('call updatePlayTime on player', function () {
                runs(function () {
                    spyOn(state.videoPlayer, 'updatePlayTime');
                    state.videoProgressSlider.onSlide(
                        jQuery.Event('slide'), { value: 60 }
                    );

                    expect(state.videoPlayer.updatePlayTime)
                        .toHaveBeenCalledWith(60);
                });
            });

            // Disabled 10/25/13 due to flakiness in master
            xit(
                'when the player is not playing: set the current time',
                function ()
            {
                runs(function () {
                    state.videoProgressSlider.onSlide(
                        jQuery.Event('slide'), { value: 20 }
                    );
                    state.videoPlayer.pause();
                    state.videoProgressSlider.onSlide(
                        jQuery.Event('slide'), { value: 10 }
                    );

                    waitsFor(function () {
                        return Math.round(state.videoPlayer.currentTime) === 10;
                    }, 'currentTime got updated', 10000);
                });
            });
        });

        describe('onSpeedChange', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer, 'updatePlayTime').andCallThrough();
                spyOn(state, 'setSpeed').andCallThrough();
                spyOn(state.videoPlayer, 'log').andCallThrough();
                spyOn(state.videoPlayer.player, 'setPlaybackRate').andCallThrough();
            });

            describe('always', function () {
                beforeEach(function () {

                    state.videoPlayer.currentTime = 60;
                    state.videoPlayer.onSpeedChange('0.75', false);
                });

                it('check if speed_change_video is logged', function () {
                    expect(state.videoPlayer.log).toHaveBeenCalledWith(
                        'speed_change_video',
                        {
                            current_time: state.videoPlayer.currentTime,
                            old_speed: '1.50',
                            new_speed: '0.75'
                        }
                    );
                });

                it('convert the current time to the new speed', function () {
                    expect(state.videoPlayer.currentTime).toEqual(60);
                });

                it('set video speed to the new speed', function () {
                    expect(state.setSpeed).toHaveBeenCalledWith('0.75', true);
                });
            });

            describe('when the video is playing', function () {
                beforeEach(function () {
                    state.videoPlayer.currentTime = 60;
                    state.videoPlayer.play();
                    state.videoPlayer.onSpeedChange('0.75', false);
                });

                it('trigger updatePlayTime event', function () {
                    expect(state.videoPlayer.player.setPlaybackRate)
                        .toHaveBeenCalledWith('0.75');
                });
            });

            describe('when the video is not playing', function () {
                beforeEach(function () {
                    state.videoPlayer.onSpeedChange('0.75', false);
                });

                it('trigger updatePlayTime event', function () {
                    expect(state.videoPlayer.player.setPlaybackRate)
                        .toHaveBeenCalledWith('0.75');
                });

                it('video has a correct speed', function () {
                    spyOn(state.videoPlayer, 'onSpeedChange');
                    state.speed = '2.0';
                    state.videoPlayer.onPlay();
                    expect(state.videoPlayer.onSpeedChange)
                        .toHaveBeenCalledWith('2.0');
                    state.videoPlayer.onPlay();
                    expect(state.videoPlayer.onSpeedChange.calls.length).toEqual(1);
                });

                it('video has a correct volume', function () {
                    spyOn(state.videoPlayer.player, 'setVolume');
                    state.currentVolume = '0.26';
                    state.videoPlayer.onPlay();
                    expect(state.videoPlayer.player.setVolume)
                        .toHaveBeenCalledWith('0.26');
                });
            });
        });

        describe('onVolumeChange', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');
            });

            it('set the volume on player', function () {
                spyOn(state.videoPlayer.player, 'setVolume');
                state.videoPlayer.onVolumeChange(60);
                expect(state.videoPlayer.player.setVolume).toHaveBeenCalledWith(60);
            });

            describe('when the video is not playing', function () {
                beforeEach(function () {
                    state.videoPlayer.player.setVolume('1');
                });

                it('video has a correct volume', function () {
                    spyOn(state.videoPlayer.player, 'setVolume');
                    state.currentVolume = '0.26';
                    state.videoPlayer.onPlay();
                    expect(state.videoPlayer.player.setVolume)
                        .toHaveBeenCalledWith('0.26');
                });
            });
        });

        describe('update', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer, 'updatePlayTime').andCallThrough();
            });

            describe(
                'when the current time is unavailable from the player',
                function ()
            {
                beforeEach(function () {
                    state.videoPlayer.player.getCurrentTime = function () {
                        return NaN;
                    };
                    state.videoPlayer.update();
                });

                it('does not trigger updatePlayTime event', function () {
                    expect(state.videoPlayer.updatePlayTime).not.toHaveBeenCalled();
                });
            });

            describe(
                'when the current time is available from the player',
                function ()
            {
                beforeEach(function () {
                    state.videoPlayer.player.getCurrentTime = function () {
                        return 60;
                    };
                    state.videoPlayer.update();
                });

                it('trigger updatePlayTime event', function () {
                    expect(state.videoPlayer.updatePlayTime)
                        .toHaveBeenCalledWith(60);
                });
            });
        });

        // Disabled 1/13/14 due to flakiness observed in master
        xdescribe('update with start & end time', function () {
            var START_TIME = 1, END_TIME = 2;

            beforeEach(function () {
                state = jasmine.initializePlayer(
                    {
                        start: START_TIME,
                        end: END_TIME
                    }
                );

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer, 'update').andCallThrough();
                spyOn(state.videoPlayer, 'pause').andCallThrough();
                spyOn(state.videoProgressSlider, 'notifyThroughHandleEnd')
                    .andCallThrough();
            });

            it(
                'video is paused on first endTime, start & end time are reset',
                function ()
            {
                var duration;

                state.videoProgressSlider.notifyThroughHandleEnd.reset();
                state.videoPlayer.pause.reset();
                state.videoPlayer.play();

                waitsFor(function () {
                    duration = Math.round(state.videoPlayer.currentTime);

                    return state.videoPlayer.pause.calls.length === 1;
                }, 'pause() has been called', WAIT_TIMEOUT);

                runs(function () {
                    expect(state.videoPlayer.startTime).toBe(0);
                    expect(state.videoPlayer.endTime).toBe(null);

                    expect(duration).toBe(END_TIME);

                    expect(state.videoProgressSlider.notifyThroughHandleEnd)
                        .toHaveBeenCalledWith({end: true});
                });
            });
        });

        describe('updatePlayTime', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                spyOn(state.videoCaption, 'updatePlayTime').andCallThrough();
                spyOn(state.videoProgressSlider, 'updatePlayTime').andCallThrough();
            });

            it('update the video playback time', function () {
                var duration = 0;

                waitsFor(function () {
                    duration = state.videoPlayer.duration();

                    if (duration > 0) {
                        return true;
                    }

                    return false;
                }, 'Video is fully loaded.', WAIT_TIMEOUT);

                runs(function () {
                    var htmlStr;

                    state.videoPlayer.updatePlayTime(60);

                    htmlStr = $('.vidtime').html();

                    // We resort to this trickery because Firefox and Chrome
                    // round the total time a bit differently.
                    if (
                        htmlStr.match('1:00 / 1:01') ||
                        htmlStr.match('1:00 / 1:00')
                    ) {
                        expect(true).toBe(true);
                    } else {
                        expect(true).toBe(false);
                    }

                    // The below test has been replaced by above trickery:
                    //
                    //     expect($('.vidtime')).toHaveHtml('1:00 / 1:01');
                });
            });

            it('update the playback time on caption', function () {
                waitsFor(function () {
                    return state.videoPlayer.duration() > 0;
                }, 'Video is fully loaded.', WAIT_TIMEOUT);

                runs(function () {
                    state.videoPlayer.updatePlayTime(60);

                    expect(state.videoCaption.updatePlayTime)
                        .toHaveBeenCalledWith(60);
                });
            });

            it('update the playback time on progress slider', function () {
                var duration = 0;

                waitsFor(function () {
                    duration = state.videoPlayer.duration();

                    return duration > 0;
                }, 'Video is fully loaded.', WAIT_TIMEOUT);

                runs(function () {
                    state.videoPlayer.updatePlayTime(60);

                    expect(state.videoProgressSlider.updatePlayTime)
                        .toHaveBeenCalledWith({
                            time: 60,
                            duration: duration
                        });
                });
            });
        });

        // Disabled 1/13/14 due to flakiness observed in master
        xdescribe(
            'updatePlayTime when start & end times are defined',
            function ()
        {
            var START_TIME = 1,
                END_TIME = 2;

            beforeEach(function () {
                state = jasmine.initializePlayer(
                    {
                        start: START_TIME,
                        end: END_TIME
                    }
                );

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer, 'updatePlayTime').andCallThrough();
                spyOn(state.videoPlayer.player, 'seekTo').andCallThrough();
                spyOn(state.videoProgressSlider, 'updateStartEndTimeRegion')
                    .andCallThrough();
            });

            it(
                'when duration becomes available, updatePlayTime() is called',
                function ()
            {
                var duration;

                expect(state.videoPlayer.initialSeekToStartTime).toBeTruthy();
                expect(state.videoPlayer.seekToStartTimeOldSpeed).toBe('void');

                state.videoPlayer.play();

                waitsFor(function () {
                    duration = state.videoPlayer.duration();

                    return state.videoPlayer.isPlaying() &&
                        state.videoPlayer.initialSeekToStartTime === false;
                }, 'duration becomes available', WAIT_TIMEOUT);

                runs(function () {
                    expect(state.videoPlayer.startTime).toBe(START_TIME);
                    expect(state.videoPlayer.endTime).toBe(END_TIME);

                    expect(state.videoPlayer.player.seekTo)
                        .toHaveBeenCalledWith(START_TIME);

                    expect(state.videoProgressSlider.updateStartEndTimeRegion)
                        .toHaveBeenCalledWith({duration: duration});

                    expect(state.videoPlayer.seekToStartTimeOldSpeed)
                        .toBe(state.speed);
                });
            });
        });

        describe('updatePlayTime with invalid endTime', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer(
                    {
                        end: 100000
                    }
                );

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer, 'updatePlayTime').andCallThrough();
            });

            it('invalid endTime is reset to null', function () {
                var duration;

                state.videoPlayer.updatePlayTime.reset();
                state.videoPlayer.play();

                waitsFor(
                    function () {
                        return state.videoPlayer.isPlaying() &&
                            state.videoPlayer.initialSeekToStartTime === false;
                    },
                    'updatePlayTime was invoked and duration is set',
                    WAIT_TIMEOUT
                );

                runs(function () {
                    expect(state.videoPlayer.endTime).toBe(null);
                });
            });
        });

        describe('toggleFullScreen', function () {
            describe('when the video player is not full screen', function () {
                beforeEach(function () {
                    state = jasmine.initializePlayer();

                    state.videoEl = $('video, iframe');

                    spyOn(state.videoCaption, 'resize').andCallThrough();
                    state.videoControl.toggleFullScreen(jQuery.Event('click'));
                });

                it('replace the full screen button tooltip', function () {
                    expect($('.add-fullscreen'))
                        .toHaveAttr('title', 'Exit full browser');
                });

                it('add the video-fullscreen class', function () {
                    expect(state.el).toHaveClass('video-fullscreen');
                });

                it('tell VideoCaption to resize', function () {
                    expect(state.videoCaption.resize).toHaveBeenCalled();
                    expect(state.resizer.setMode).toHaveBeenCalled();
                });
            });

            describe('when the video player already full screen', function () {
                beforeEach(function () {
                    state = jasmine.initializePlayer();

                    state.videoEl = $('video, iframe');

                    spyOn(state.videoCaption, 'resize').andCallThrough();

                    state.el.addClass('video-fullscreen');
                    state.videoControl.fullScreenState = true;
                    isFullScreen = true;
                    state.videoControl.fullScreenEl.attr('title', 'Exit-fullscreen');

                    state.videoControl.toggleFullScreen(jQuery.Event('click'));
                });

                it('replace the full screen button tooltip', function () {
                    expect($('.add-fullscreen'))
                        .toHaveAttr('title', 'Fill browser');
                });

                it('remove the video-fullscreen class', function () {
                    expect(state.el).not.toHaveClass('video-fullscreen');
                });

                it('tell VideoCaption to resize', function () {
                    expect(state.videoCaption.resize).toHaveBeenCalled();
                    expect(state.resizer.setMode)
                        .toHaveBeenCalledWith('width');
                });
            });
        });

        describe('play', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer.player, 'playVideo').andCallThrough();
            });

            describe('when the player is not ready', function () {
                beforeEach(function () {
                    state.videoPlayer.player.playVideo = void 0;
                    state.videoPlayer.play();
                });

                it('does nothing', function () {
                    expect(state.videoPlayer.player.playVideo).toBeUndefined();
                });
            });

            describe('when the player is ready', function () {
                beforeEach(function () {
                    state.videoPlayer.player.playVideo.andReturn(true);
                    state.videoPlayer.play();
                });

                it('delegate to the player', function () {
                    expect(state.videoPlayer.player.playVideo).toHaveBeenCalled();
                });
            });
        });

        describe('isPlaying', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer.player, 'getPlayerState').andCallThrough();
            });

            describe('when the video is playing', function () {
                beforeEach(function () {
                    state.videoPlayer.player.getPlayerState.andReturn(YT.PlayerState.PLAYING);
                });

                it('return true', function () {
                    expect(state.videoPlayer.isPlaying()).toBeTruthy();
                });
            });

            describe('when the video is not playing', function () {
                beforeEach(function () {
                    state.videoPlayer.player.getPlayerState.andReturn(YT.PlayerState.PAUSED);
                });

                it('return false', function () {
                    expect(state.videoPlayer.isPlaying()).toBeFalsy();
                });
            });
        });

        describe('pause', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer.player, 'pauseVideo').andCallThrough();
                state.videoPlayer.pause();
            });

            it('delegate to the player', function () {
                expect(state.videoPlayer.player.pauseVideo).toHaveBeenCalled();
            });
        });

        describe('duration', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer.player, 'getDuration').andCallThrough();
                state.videoPlayer.duration();
            });

            it('delegate to the player', function () {
                expect(state.videoPlayer.player.getDuration).toHaveBeenCalled();
            });
        });

        describe('getDuration', function () {
            beforeEach(function () {
                // We need to make sure that metadata is returned via an AJAX
                // request. Without the jasmine.stubRequests() below we will
                // get the error:
                //
                //     this.metadata[this.youtubeId(...)] is undefined
                jasmine.stubRequests();

                state = jasmine.initializePlayerYouTube();

                state.videoEl = $('video, iframe');

                spyOn(state, 'getDuration').andCallThrough();

                // When `state.videoPlayer.player.getDuration()` returns a `0`,
                // the fall-back function `state.getDuration()` will be called.
                state.videoPlayer.player.getDuration.andReturn(0);
            });

            it('getDuration is called as a fall-back', function () {
                state.videoPlayer.duration();

                expect(state.getDuration).toHaveBeenCalled();
            });
        });

        describe('playback rate', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                state.videoPlayer.player.setPlaybackRate(1.5);
            });

            it('set the player playback rate', function () {
                expect(state.videoPlayer.player.video.playbackRate).toEqual(1.5);
            });
        });

        describe('volume', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                spyOn(state.videoPlayer.player, 'getVolume').andCallThrough();
            });

            it('set the player volume', function () {
                var expectedValue = 60,
                realValue;

                state.videoPlayer.player.setVolume(60);
                realValue = Math.round(state.videoPlayer.player.getVolume()*100);

                expect(realValue).toEqual(expectedValue);
            });
        });

        describe('on Touch devices', function () {
            it('`is-touch` class name is added to container', function () {
                $.each(
                    ['iPad', 'Android', 'iPhone'],
                    function (index, device)
                {
                    window.onTouchBasedDevice.andReturn([device]);
                    state = jasmine.initializePlayer();

                    state.videoEl = $('video, iframe');

                    expect(state.el).toHaveClass('is-touch');
                });
            });

            it('modules are not initialized on iPhone', function () {
                window.onTouchBasedDevice.andReturn(['iPhone']);
                state = jasmine.initializePlayer();

                state.videoEl = $('video, iframe');

                var modules = [
                    state.videoControl, state.videoCaption, state.videoProgressSlider,
                    state.videoSpeedControl, state.videoVolumeControl
                ];

                $.each(modules, function (index, module) {
                    expect(module).toBeUndefined();
                });
            });

            $.each(['iPad', 'Android'], function (index, device) {
                var message = 'controls become visible after playing starts ' +
                    'on ' + device;

                it(message, function () {
                    var controls;

                    window.onTouchBasedDevice.andReturn([device]);

                    runs(function () {
                        state = jasmine.initializePlayer();

                        state.videoEl = $('video, iframe');

                        controls = state.el.find('.video-controls');
                    });

                    waitsFor(function () {
                        return state.el.hasClass('is-initialized');
                    },'Video is not initialized.' , WAIT_TIMEOUT);

                    runs(function () {
                        expect(controls).toHaveClass('is-hidden');
                        state.videoPlayer.play();
                    });

                    waitsFor(function () {
                        duration = state.videoPlayer.duration();

                        return duration > 0 && state.videoPlayer.isPlaying();
                    },'Video does not play.' , WAIT_TIMEOUT);

                    runs(function () {
                        expect(controls).not.toHaveClass('is-hidden');
                    });
                });
            });
        });
    });

}).call(this);
