Feature: Video Component Editor
  As a course author, I want to be able to create video components.

#  Scenario: User inputs YouTube source first
#    Given I have created a Video component
#    And It has no YouTube transcripts locally
#    And I edit the component
#    And I input YouTube source which doesn't have transcripts on YouTube
#    Then I see not found message

  Scenario: User inputs YouTube source first
    Given I have created a Video component
    And I edit the component
    And I enter an incorrect URL
    Then I see error message

  Scenario: User inputs two HTML5 sources with identical formats
    Given I have created a Video component
    And I edit the component
    And I enter a 123.webm source to field number 0
    And I enter a 456.webm source to field number 1
    Then I see same format error message
