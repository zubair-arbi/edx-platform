Feature: Video Component Editor
  As a course author, I want to be able to create video components.

#  Scenario: User inputs YouTube source first
#    Given I have created a Video component
#    And It has no YouTube transcripts locally
#    And I edit the component
#    And I input YouTube source which doesn't have transcripts on YouTube
#    Then I see not found message

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

  Scenario: Testing interaction with test youtube server
    Given I have created a Video component with subtitles
    And I edit the component
    # first part of url will be substituted by mock_youtube_server address
    # for trans_exist id server will respond with transcripts
    And I enter a http://youtu.be/trans_exist source to field number 1
    Then I see not found status message
    # trans_exist subs locally not presented at this moment
    And I see import button

    # for t_not_exist id server will respond with 404
    And I enter a http://youtu.be/t_not_exist source to field number 1
    Then I see not found status message
    And I do not see import button
    # why??? possible bug
    And I see download_to_edit button


Scenario: Entering youtube id only
    Given I have created a Video component with subtitles
    And I edit the component

    # first part of url will be substituted by mock_youtube_server address

    # for t_not_exist id server will respond with 404
    #And I enter a http://youtu.be/t_not_exist source to field number 1
    #Then I see not found status message

    # for trans_exist id server will respond with transcripts
    And I enter a http://youtu.be/trans_exist source to field number 1
    Then I see not found status message
    # trans_exist subs locally not presented at this moment
    And I see import button
    And I click import button
    # I see: upload new timed transcripts, and not clickable download to edit

    #btw, when i update sub, I do not create file in upload section
    Then I see found status message



