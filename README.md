THis script does the following things:
1. Determine the instance state using its DNS name (need at least 2 verifications: TCP and HTTP).
2. Create an AMI of the stopped EC2 instance and add a descriptive tag based on the EC2 name along with the current date.
3. Terminate stopped EC2 after AMI creation.
4. Clean up AMIs older than 7 days.
5. Print all instances in fine-grained output, INCLUDING terminated one, with highlighting their current state.
