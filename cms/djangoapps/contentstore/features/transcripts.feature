Feature: Video Component Editor
  As a course author, I want to be able to create video components.

#  Scenario: User inputs YouTube source first
#    Given I have created a Video component
#    And It has no YouTube transcripts locally
#    And I edit the component
#    And I input YouTube source which doesn't have transcripts on YouTube
#    Then I see not found message

  #Scenario: User inputs YouTube source first
  #  Given I have created a Video component
  #  And I edit the component
  #  And I enter a htt://link.c source to field number 1
  #  Then I see url_format error message

  Scenario: Check input error messages
    Given I have created a Video component
    And I edit the component
    And I enter a 123.webm source to field number 1
    And I enter a 456.webm source to field number 2
    Then I see file_type error message
    When I clear fields
    And I enter a htt://link.c source to field number 1
    Then I see url_format error message
    And I enter a http://youtu.be/OEoXaMPEzfM source to field number 1
    Then I do_not see error message
