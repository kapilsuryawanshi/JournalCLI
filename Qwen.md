You must follow the Test Driven Development workflow described below to implement the feature request from user.

1. Understand the feature request and ask questions to clarify if needed. Understand current code and configuration which are already existing.
2. Update TestCases.txt to include the functional tests for this feature request, in plain English language.
3. For the new test cases added, plan the implementation steps and get it confirmed by showing it to user.
4. Proceed with implementation as per the plan. As you complete the step, check of the steps in this implementation plan.
5. After implementation, refactor the code to a) remove the code / logic duplication by adding reusable functions instead b) remove unused code.
6. Add or update code documentation for the code changes to improve the readability of the code.
7. Execute all the test cases from TestCases.txt, to ensure a) the new implementation is perfectly working b) the existing implementation is still intact and no regression issues are introduced. If some test cases are failing then go back to step 3 above and implement the fix for code.
8. Ensure the PRD.txt reflect the current applications product requirement document.
9. Never delete or remove file jrnl.db which is the production database. You may take backup of this file, perform your testing and then restore this file from backup.
