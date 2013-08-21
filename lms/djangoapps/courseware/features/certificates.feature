Feature: Verified certificates
    As a student,
    In order to earn a verified certificate
    I want to sign up for a verified certificate course.

    Scenario: I can submit photos to verify my identity
        Given I am logged in
        When I select the "paid" track
        And I submit a photo of my face
        And I confirm my face photo
        And I take my ID photo
        And I confirm my ID photo
        And I confirm both photos
        Then The course is added to my cart
        And I view the payment page

    Scenario: I can pay for a verified certificate
        Given I have submitted photos to verify my identity
        When I submit valid payment information
        Then I see that my payment was successful
        And I receive an email confirmation
        And I see that I am registered for a verified certificate course on my dashboard

    Scenario: I can re-take photos
        Given I have submitted my "<PhotoType>" photo
        When I retake my "<PhotoType>" photo
        Then I see the new photo on the confirmation page.

        Examples:
        | PhotoType     |
        | face          |
        | ID            |

    Scenario: I can edit identity information
        Given I have submitted face and ID photos
        When I edit my name
        Then I see the new name on the confirmation page.

    Scenario: I can return to the verify flow
        Given I have submitted photos
        When I leave the flow and return
        I see the payment page

    Scenario: I can audit a verified certificate course
        Given I am logged in
        When I select the "audit" track
        Then I am registered for the course
        And I return to the student dashboard

    # Design not yet finalized
    #Scenario: I can take a verified certificate course for free
    #    Given I have submitted photos to verify my identity
    #    When I give a reason why I cannot pay
    #    Then I see that I am registered for a verified certificate course on my dashboard
