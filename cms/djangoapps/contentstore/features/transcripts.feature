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
