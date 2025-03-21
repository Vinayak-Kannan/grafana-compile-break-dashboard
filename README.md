# How to set up Jenkins pipeline on GCP

1. Download Docker Desktop
2. Run the command `docker build -t jenkins-custom:latest .`
3. Go to here: https://cloud.google.com/artifact-registry/docs/docker/store-docker-container-images
   1. Run the commands in Setting up local shell; note you don't need to do the stuff for linux / windows (so step 1 and 2)
   2. Run all commands in Create a Docker repository
   3. Run command in Configure authentication
   4. Run 'tag the image with registry name' command. Note, replace PROJECT with project id AND replace 'us-docker.pkg.dev/google-samples/containers/gke/hello-app:1.0' with jenkins-custom:latest
   5. Run 'Push the image to Artifact Registry' command
4. Go to GCP console and create a VM
   1. Make sure to create VM with enough Memory and CPUs (we are running large models - I dont think GPU is needed though)
   2. Change Operating System to use Debian GNU / Linux 12 bookworm
   3. Increase disk size to 100 GB (maybe more needed)
   4. Make sure you use a machine configuration that supports x86/64, amd64 architecture
   5. Go to artifact registry and find the image you just pushed there
   6. Find the pull command for the image and copy the image name ONLY. Do not copy the docker related arguments
   7. Go to your VM instance creation screen and click Deploy container under OS and storage
   8. Paste the image name into the Container image field
   9. Click on 'Run as privileged'
   10. Set Restart policy to 'On Failure'
   11. Make sure that the disk size is still 100 GB, sometimes it gets reset when you change options around
   12. Turn off Data Protection policies
   13. Enable HTTP and HTTPS traffic in Networking
   14. In your Network interfaces in the default network, add a firewall rule to allow all traffic on port 8080 and 50000
   15. Add logging and monitoring to the VM
   16. Create the VM
5. Go to the external IP of your VM and add :8080 to the end of it. You should see the Jenkins setup page. Remove https:// from the URL
6. Open your VM and run `docker ps` and then run `docker logs [id of your jenkins container]`
7. Find the initial admin password and copy it, and paste into your jenkins setup page
8. Finish the setup and install the recommended plugins
9. Create a multibranch pipeline project
10. Sync it up with the github repository. Make sure you add your github credentials (I recommend using a personal access token)
11. You should see it start running our Jenkinsfile after creation


