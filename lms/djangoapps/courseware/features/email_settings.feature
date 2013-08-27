Feature: Set email settings for a course
    As a registered user
    In order to choose whether or not to get email
    I want to set my email preferences on my dashboard

    Scenario: I can opt out of email
        Given The course "6.002x" exists
        And I am logged in
        And I visit the courses page
        When I register for the course "6.002x"
        Then I should see the course numbered "6.002x" in my dashboard
	When I click on email settings for the course numbered "6.002x"
	Then I should be receiving course emails for the course numbered "6.002x"
	When I opt out of emails
	Then I should NOT be receiving course emails for the course numbered "6.002x"
