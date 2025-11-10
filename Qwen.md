You must follow the Test Driven Development workflow described below to implement the feature request from user.

<workflow>
0. Before starting work on user request, remind user of this workflow you will be following.
1. Understand the feature request and ask questions to clarify if needed.
2. Understand current code and configuration which are already existing.
3. Update/Create new pytest automated unit test to include the functional tests for this feature request. 
4. Execute this test to ensure that it fails. If it does not fail, that means you have not updated/added effective test case. Please redo.
4. For the new test cases added, plan the implementation steps and get it confirmed by showing it to user.
5. Proceed with implementation as per the plan. 
6. As you complete the step, check of the steps in this implementation plan. Do not implement any backward compatibility.
7. Refactor the code to remove the rendant code / logic and create reusable functions instead.
8. Refactor the code to remove unused code.
9. Add or update code documentation for the code changes to improve the readability of the code.
10. Execute ALL the test cases. If some test cases are failing then go back to step 3 above and implement the fix for code.
11. Create/Update a README.md file detailing everything about this project accurately.
12. Always remove temporary and debug files created in the project directory.
13. Confirm with user if the code changes are to be committed and pushed. After confirmation execute commit and push.
</workflow>