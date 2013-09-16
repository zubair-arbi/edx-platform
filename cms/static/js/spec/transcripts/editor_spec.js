(function (window, undefined) {
    describe('Transcripts.Editor', function () {
        var VideoListEntry = {
                default_value: ["a thing", "another thing"],
                display_name: "Video URL",
                explicitly_set: false,
                field_name: "video_url",
                help: "A list of things.",
                options: [],
                type: CMS.Models.Metadata.VIDEO_LIST_TYPE,
                value: ["the first display value", "the second"]
            },
            models = [VideoListEntry],
            metadataDict = {
                object: {
                    "video_url":{
                        "default_value":["a thing","another thing"],
                        "display_name":"Video URL",
                        "explicitly_set":false,
                        "field_name":"video_url",
                        "help":"A list of things.",
                        "options":[],
                        "type":"VideoList",
                        "value":["the first display value","the second"]
                    }
                },
                string: '{"video_url":{"default_value":["a thing","another thing"],\
                "display_name":"Video URL","explicitly_set":false,"field_name":\
                "video_url","help":"A list of things.","options":[],"type":\
                "VideoList","value":["the first display value","the second"]}}'
            },
            container;

        beforeEach(function () {
            var tpl = sandbox({
                    'class': 'wrapper-comp-settings basic_metadata_edit',
                    'data-metadata': JSON.stringify(metadataDict['object'])
                });

            setFixtures(tpl);
        });

        $.each(metadataDict, function(index, val) {
            it('toModels with argument as ' + index, function () {
                spyOn(CMS.Models, 'MetadataCollection');
                spyOn(CMS.Views.Metadata, 'Editor');
                var container = $('.basic_metadata_edit'),
                    transcripts = new Transcripts.Editor({
                            el: container
                    });

                expect(transcripts.toModels(val)).toEqual(models);
            });
        });

        it('CMS.Views.Metadata.Editor is initialized', function () {
            spyOn(CMS.Models, 'MetadataCollection');
            spyOn(CMS.Views.Metadata, 'Editor');
            var container = $('.basic_metadata_edit'),
                transcripts = new Transcripts.Editor({
                    el: container
                });

            expect(CMS.Models.MetadataCollection).toHaveBeenCalledWith(models);
            expect(CMS.Views.Metadata.Editor).toHaveBeenCalledWith({
                el: container,
                collection: transcripts.collection
            });
        });
    });
}(window));
