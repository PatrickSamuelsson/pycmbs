Feature: load and print config file contents
    As a user of the software
    When I run pycmbs-benchmarking
    I want config file contents to be displayed

    Scenario: Empty YAML config file
        Given config file is empty
        Then read yaml config file
        Then check the config contents are empty

    Scenario: Empty JSON config file
        Given config file is empty
        Then read json config file
        Then check the config contents are empty

    Scenario: Non-empty config file
        Given config file is not empty
        Then read yaml config file
        Then check the config contents are not empty
