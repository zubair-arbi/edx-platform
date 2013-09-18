(function (window, undefined) {
    describe('CMS.Views.Metadata.VideoList', function () {
        var utils = Transcripts.Utils,
            correctMessanger = Transcripts.MessageManager,
            messenger = correctMessanger.prototype,
            abstractEditor = CMS.Views.Metadata.AbstractEditor.prototype,
            component_id = 'component_id',
            videoList = [
                {
                    mode: "youtube",
                    type: "youtube",
                    video: "12345678901"
                },
                {
                    mode: "html5",
                    type: "mp4",
                    video: "video"
                },
                {
                    mode: "html5",
                    type: "webm",
                    video: "video"
                }
            ],
            modelStub = {
                default_value: ['a thing', 'another thing'],
                display_name: 'Video URL',
                explicitly_set: true,
                field_name: 'video_url',
                help: 'A list of things.',
                options: [],
                type: CMS.Models.Metadata.VIDEO_LIST_TYPE,
                value: [
                    'http://youtu.be/12345678901',
                    'video.mp4',
                    'video.webm'
                ]
            },
            view;

        beforeEach(function () {
            jasmine.stubRequests();

            var tpl = sandbox({
                    'class': 'component',
                    'data-id': component_id
                }),
                videoListEntryTemplate = readFixtures(
                    'transcripts/metadata-videolist-entry.underscore'
                ),
                model = new CMS.Models.Metadata(modelStub),
                videoList, $el;

            setFixtures(tpl);

            appendSetFixtures(
                $("<script>",
                    {
                        id: "metadata-videolist-entry",
                        type: "text/template"
                    }
                ).text(videoListEntryTemplate)
            );

            spyOn(messenger, 'initialize');
            spyOn(messenger, 'render');
            spyOn(messenger, 'showError');
            spyOn(messenger, 'hideError');
            spyOn(utils, 'command').andCallThrough();
            spyOn(abstractEditor, 'initialize').andCallThrough();
            spyOn(abstractEditor, 'render').andCallThrough();

            Transcripts.MessageManager = function () {
                messenger.initialize();

                return messenger;
            };

            $el = $('.component');

            spyOn(console, 'error');

            view = new CMS.Views.Metadata.VideoList({
                el: $el,
                model: model
            });
        });

        afterEach(function () {
            Transcripts.MessageManager = correctMessanger;
        });

        it('Initialize', function () {
            expect(abstractEditor.initialize).toHaveBeenCalled();
            expect(messenger.initialize).toHaveBeenCalled();
            expect(view.component_id).toBe(component_id);
            expect(view.$el).toHandle('input');
        });

        describe('Render', function () {
            var assertRendering = function (videoList) {
                    expect(abstractEditor.render).toHaveBeenCalled();
                    expect(utils.command).toHaveBeenCalledWith(
                        'check',
                        component_id,
                        videoList
                    );
                    expect(messenger.render).toHaveBeenCalled();
                },
                resetSpies = function() {
                    abstractEditor.render.reset();
                    utils.command.reset();
                    messenger.render.reset();
                };

            it('is rendered in correct way', function () {
                assertRendering(videoList);
            });

            it('is rendered with opened extra videos bar', function () {
                var videoListLength = [
                        {
                            mode: "youtube",
                            type: "youtube",
                            video: "12345678901"
                        },
                        {
                            mode: "html5",
                            type: "mp4",
                            video: "video"
                        }
                    ],
                    videoListHtml5mode = [
                        {
                            mode: "html5",
                            type: "mp4",
                            video: "video"
                        }
                    ];

                spyOn(view, 'getVideoObjectsList').andReturn(videoListLength);
                spyOn(view, 'openExtraVideosBar');

                resetSpies();
                view.render();

                assertRendering(videoListLength);
                expect(view.openExtraVideosBar).toHaveBeenCalled();

                resetSpies();
                view.openExtraVideosBar.reset();
                view.getVideoObjectsList.andReturn(videoListHtml5mode);
                view.render();

                assertRendering(videoListHtml5mode);
                expect(view.openExtraVideosBar).toHaveBeenCalled();
            });

            it('is rendered without opened extra videos bar', function () {
                var videoList = [
                        {
                            mode: "youtube",
                            type: "youtube",
                            video: "12345678901"
                        }
                    ];

                spyOn(view, 'getVideoObjectsList').andReturn(videoList);
                spyOn(view, 'closeExtraVideosBar');

                resetSpies();
                view.render();

                assertRendering(videoList);
                expect(view.closeExtraVideosBar).toHaveBeenCalled();
            });

        });

        describe('isUniqVideoTypes', function () {

            it('Unique data', function () {
                var data = videoList,
                    result = view.isUniqVideoTypes(data);

                expect(result).toBe(true);
            });

            it('Not Unique data', function () {
                var data = [
                        {
                            mode: "html5",
                            type: "mp4",
                            video: "video"
                        },
                        {
                            mode: "html5",
                            type: "mp4",
                            video: "video"
                        },
                        {
                            mode: "youtube",
                            type: "youtube",
                            video: "12345678901"
                        }
                    ],
                    result = view.isUniqVideoTypes(data);

                expect(result).toBe(false);
            });
        });

        describe('checkIsUniqVideoTypes', function () {

            it('Error is shown', function () {
                var data = [
                        {
                            mode: "html5",
                            type: "mp4",
                            video: "video"
                        },
                        {
                            mode: "html5",
                            type: "mp4",
                            video: "video"
                        },
                        {
                            mode: "youtube",
                            type: "youtube",
                            video: "12345678901"
                        }
                    ],
                    result = view.checkIsUniqVideoTypes(data);

                expect(messenger.showError).toHaveBeenCalled();
                expect(result).toBe(false);
            });

            it('Arguments is not provided', function () {
                spyOn(view, 'getVideoObjectsList').andReturn(videoList);
                var result = view.checkIsUniqVideoTypes();

                expect(view.getVideoObjectsList).toHaveBeenCalled();
                expect(messenger.showError).not.toHaveBeenCalled();
                expect(result).toBe(true);
            });
        });

        describe('checkValidity', function () {
            beforeEach(function () {
                spyOn(view, 'checkIsUniqVideoTypes');
            });

            it('Error message are shown', function () {
                var data = { mode: 'incorrect' },
                    result = view.checkValidity(data, true);

                expect(messenger.showError).toHaveBeenCalled();
                expect(view.checkIsUniqVideoTypes).toHaveBeenCalled();
                expect(result).toBe(false);
            });

            it('Error message are shown when flag is not provided', function () {
                var data = { mode: 'incorrect' },
                    result = view.checkValidity(data);

                expect(messenger.showError).not.toHaveBeenCalled();
                expect(view.checkIsUniqVideoTypes).toHaveBeenCalled();
                expect(result).toBe(true);
            });

            it('Correct data', function () {
                var data = videoList,
                    result = view.checkValidity(data);

                expect(messenger.showError).not.toHaveBeenCalled();
                expect(view.checkIsUniqVideoTypes).toHaveBeenCalled();
                expect(result).toBe(true);
            });
        });

        it('openExtraVideosBar', function () {
            view.$extraVideosBar.removeClass('is-visible');

            view.openExtraVideosBar();
            expect(view.$extraVideosBar).toHaveClass('is-visible');
        });

        it('closeExtraVideosBar', function () {
            view.$extraVideosBar.addClass('is-visible');

            view.closeExtraVideosBar();
            expect(view.$extraVideosBar).not.toHaveClass('is-visible');
        });

        it('toggleExtraVideosBar', function () {
            view.$extraVideosBar.addClass('is-visible');
            view.toggleExtraVideosBar();
            expect(view.$extraVideosBar).not.toHaveClass('is-visible');
            view.toggleExtraVideosBar();
            expect(view.$extraVideosBar).toHaveClass('is-visible');
        });

        var assertValueInView = function (view, expectedValue) {
            expect(view.getValueFromEditor()).toEqual(expectedValue);
        };

        var assertCanUpdateView = function (view, newValue) {
            view.setValueInEditor(newValue);
            expect(view.getValueFromEditor()).toEqual(newValue);
        };

        it('getValueFromEditor', function () {
            assertValueInView(view, modelStub.value);
        });

        it('setValueInEditor', function () {
            assertCanUpdateView(view, ['abc.mp4']);
        });

        var assertVideoList = function (view, newValue) {
            expect(view.getVideoObjectsList()).toEqual(newValue);
        };

        it('getVideoObjectsList', function () {
            var value = [
                {
                    mode: 'youtube',
                    type: 'youtube',
                    video: '12345678901'
                },
                {
                    mode: 'html5',
                    type: 'mp4',
                    video: 'video'
                }
            ];

            view.setValueInEditor([
                'http://youtu.be/12345678901',
                'video.mp4',
                'video'
            ]);
            assertVideoList(view, value);
        });

    });
}(window));
