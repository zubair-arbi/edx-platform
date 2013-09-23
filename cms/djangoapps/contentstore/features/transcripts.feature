Feature: Video Component Editor
  As a course author, I want to be able to create video components.
    #1
    Scenario: Check input error messages
        Given I have created a Video component
        And I edit the component
        And I enter a 123.webm source to field number 1
        And I enter a 456.webm source to field number 2
        Then I see file_type error message
        # Currently we are working with 2nd field. It means, that if 2nd field
        # contain incorrect value, 1st and 3rd fields should be disabled until
        # 2nd field will be filled by correct correct value
        And I expect 1, 3 inputs are disabled
        When I clear fields
        And I expect inputs are enabled
        And I enter a htt://link.c source to field number 1
        Then I see url_format error message
        # Currently we are working with 1st field. It means, that if 1st field
        # contain incorrect value, 2nd and 3rd fields should be disabled until
        # 1st field will be filled by correct correct value
        And I expect 2, 3 inputs are disabled
        # We are not clearing fields here,
        # Because we changing same field.
        And I enter a http://youtu.be/OEoXaMPEzfM source to field number 1
        Then I do not see error message
        And I expect inputs are enabled
    #2
    Scenario: Testing interaction with test youtube server
        Given I have created a Video component with subtitles
        And I edit the component
        # first part of url will be substituted by mock_youtube_server address
        # for t__eq_exist id server will respond with transcripts
        And I enter a http://youtu.be/t__eq_exist source to field number 1
        Then I see not found status message
        # t__eq_exist subs locally not presented at this moment
        And I see import button

        # for t_not_exist id server will respond with 404
        And I enter a http://youtu.be/t_not_exist source to field number 1
        Then I see not found status message
        And I do not see import button
        # why??? possible bug
        And I see download_to_edit button
    #3
    Scenario: Entering youtube id only - 1a and 1c
        Given I have created a Video component with subtitles
        And I edit the component

        # first part of transcripts url of requests to youtube will be substituted by mock_youtube_server address

        # 1a
        # for t_not_exist id server will respond with 404
        And I remove t_not_exist transcripts id from store
        And I enter a http://youtu.be/t_not_exist source to field number 1
        Then I see not found status message

        # 1c
        # for t__eq_exist id server will respond with transcripts
        And I remove t__eq_exist transcripts id from store
        And I enter a http://youtu.be/t__eq_exist source to field number 1
        Then I see not found status message
        And I see import button
        And I click import button
        Then I see found status message
        And I see upload_new_timed_transcripts button
        And I see download_to_edit button
        #btw, when i update sub, I do not create file in upload section
        And I remove t__eq_exist transcripts id from store
    #4
    Scenario: Entering youtube id only - 1b
        # Separate from previous, because we need to close editor
        # to upload subtitles, that's why we uploading them before
        #opening editor
        Given I have created a Video component with t_not_exist subtitles
        And I edit the component
        And I enter a http://youtu.be/t_not_exist source to field number 1
        Then I see found status message
        And I remove t_not_exist transcripts id from store
    #5
    Scenario: Entering youtube id only - 1d-1
        Given I have created a Video component with t__eq_exist subtitles
        And I edit the component
        And I enter a http://youtu.be/t__eq_exist source to field number 1
        And I see found status message
        And I remove t__eq_exist transcripts id from store
    #6
    Scenario: Entering youtube id only - 1d-2
        Given I have created a Video component with t_neq_exist subtitles
        And I edit the component
        And I enter a http://youtu.be/t_neq_exist source to field number 1
        And I see replace status message
        And I see replace button
        And I click replace button
        And I see found status message
        And I remove t_neq_exist transcripts id from store
    #7
    Scenario: Entering html5 source only - Timed Transcripts found 2a
        Given I have created a Video component
        And I edit the component
        And I enter a t_not_exist.mp4 source to field number 1
        Then I see not found status message
    #8
    Scenario: Entering html5 source only - Timed Transcripts not found 2b
        Given I have created a Video component with t_not_exist subtitles
        And I edit the component
        And I enter a t_not_exist.mp4 source to field number 1
        Then I see found status message
    #9
    Scenario: Entering youtube - html5 - 3a
        Given I have created a Video component with t_not_exist subtitles
        And I edit the component
        And I enter a http://youtu.be/t_not_exist source to field number 1
        Then I see found status message
        And I enter a t_not_exist.mp4 source to field number 2
        Then I see found status message
    #10
    Scenario: Entering youtube - html5 w/o transcripts with import - 3b
        Given I have created a Video component
        And I edit the component
        And I enter a http://youtu.be/t__eq_exist source to field number 1
        Then I see not found status message
        And I see import button
        And I click import button
        Then I see found status message
        And I enter a t_not_exist.mp4 source to field number 2
        Then I see found status message

    #11
    Scenario: Entering youtube - html5 w/o transcripts w/o import - html5 w/o transcripts
        Given I have created a Video component
        And I edit the component
        And I enter a http://youtu.be/t__eq_exist source to field number 1
        Then I see not found status message
        And I see import button
        And I don't see upload_new_timed_transcripts button
        And I enter a t_not_exist.mp4 source to field number 2
        Then I see not found status message
        And I see import button
        And I don't see upload_new_timed_transcripts button
        And I enter a t_not_exist.webm source to field number 3
        Then I see not found status message
        And I see import button
        And I don't see upload_new_timed_transcripts button

    #12
    Scenario: Entering youtube w/o transcripts - html5 w/o transcripts w/o import - html5 w/o transcripts
        Given I have created a Video component
        And I edit the component
        And I enter a http://youtu.be/t_not_exist source to field number 1
        Then I see not found status message
        And I see disabled_download_to_edit button
        And I don't see upload_new_timed_transcripts button
        And I enter a t_not_exist.mp4 source to field number 2
        Then I see not found status message
        And I don't see upload_new_timed_transcripts button
        And I see disabled_download_to_edit button
        And I enter a t_not_exist.webm source to field number 3
        Then I see not found status message
        And I see disabled_download_to_edit button
        And I don't see upload_new_timed_transcripts button

    #13
    #12
    Scenario: Entering youtube with imported transcripts - html5 w/o transcripts w/o import - html5 w/o transcripts
        Given I have created a Video component
        And I edit the component
        And I enter a http://youtu.be/t__eq_exist source to field number 1
        Then I see not found status message
        And I see import button
        And I click import button
        Then I see found status message
        And I don't see upload_new_timed_transcripts button
        And I enter a t_not_exist.mp4 source to field number 2
        Then I see found status message
        And I see download_to_edit button
        And I don't see upload_new_timed_transcripts button
        And I enter a t_not_exist.webm source to field number 3
        Then I see found status message
        And I see download_to_edit button
        And I don't see upload_new_timed_transcripts button
