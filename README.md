# How to set up Jenkins pipeline on GCP

1. Download Docker Desktop
2. Run the command `docker build --platform=linux/amd64 -t jenkins-custom:latest .`
3. Go to here: https://cloud.google.com/artifact-registry/docs/docker/store-docker-container-images
   1. Run the commands in Setting up local shell; note you don't need to do the stuff for linux / windows (so step 1 and 2)
   2. Run all commands in Create a Docker repository
   3. Run command in Configure authentication
   4. Run 'tag the image with registry name' command. Note, replace PROJECT with project id AND replace 'us-docker.pkg.dev/google-samples/containers/gke/hello-app:1.0' with jenkins-custom:latest
   5. Run 'Push the image to Artifact Registry' command
4. Go to GCP console and create a VM
   1. Make sure to create VM with enough Memory and CPUs (we are running large models - I dont think GPU is needed though)
   2. Go to artifact registry and find the image you just pushed there
   3. Find the "pull by tag" command for the image and copy the image name ONLY (e.g. us-west1-docker.pkg.dev/capable-code-450601-a6/jenkins-docker-repo/jenkins-image:tag1). Do not copy the docker related arguments
   4. Go to your VM instance creation screen and click Deploy container under OS and storage
   5. Paste the image name into the Container image field
   6. Click on 'Run as privileged'
   7. Set Restart policy to 'On Failure'
   8. For the operating system, use the default selected container optimized OS
   9. Increase disk size to 100 GB
   10. Turn off Data Protection policies
   11. Enable HTTP and HTTPS traffic in Networking
   12. Add logging and monitoring to the VM
   13. Create the VM
   14. Go to Firewall policies and add a new firewall rule.
   15. Set the direction as ingress, target the created VM instance, set the source IPv4 range for 0.0.0.0/0, and enable TCP ports 8080 and 50000
5. Go to the external IP of your VM and add :8080 to the end of it. You should see the Jenkins setup page. Remove https:// from the URL
6. Open your VM and run `docker ps` and then run `docker logs [id of your jenkins container]`
7. Find the initial admin password and copy it, and paste into your jenkins setup page
8. Finish the setup and install the recommended plugins
9. Create a multibranch pipeline project
10. Sync it up with the github repository. Make sure you add your github credentials (I recommend using a personal access token (classic with repo access))
11. You should see it start running our Jenkinsfile after creation


