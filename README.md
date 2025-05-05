# How to run Grafana Pipeline
## Prerequisites

1. **Docker and Docker Compose**: Ensure Docker and Docker Compose are installed on your machine.
2. **Grafana Cloud Account**: Create an account on [Grafana Cloud](https://grafana.com/) to obtain the necessary credentials.

---

## Step 1: Running Docker Compose

1. Start the services using Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Verify that the following services are running:
   - Jenkins: Accessible at http://localhost:8080
   - Pushgateway: Accessible at http://localhost:9091
   - Alloy: Accessible at http://localhost:12345

---

## Step 2: Setting Up Grafana Cloud Credentials
1. Log in to your Grafana Cloud account and navigate to "Connections" -> "Add new connection" section. The necessary credentials can be obtained as follows.
2. Select "Hosted Prometheus Metrics" and generate a new API token.
   - Choose a method for forwarding metrics: "Via Grafana Alloy"
   - Set the configuration: "Create a new token"
   - The "url" will be your `PROM_URL`, the "username" will be your `PROM_USERNAME`, and the "password" will be your `PROM_GRAFANA_CLOUD_API_KEY`

3. Select `Hosted logs` and generate an Access Policy token.
   - Choose your use case: "Send logs from a standalone host"
   - Select: "Create a new token"
   - The "client: url:" contains https://`LOKI_USERNAME`:`LOKI_GRAFANA_CLOUD_API_KEY`@ENDPOINT
   - The `LOKI_URL` will be the ENDPOINT appended with "loki/api/v1/push" instead of "api/prom/push" (i.e. https://logs-prod-XXX.grafana.net/loki/api/v1/push)

4. Update the `env.secrets` file located at `alloy/env.secrets` with your credentials:
   - LOKI_URL=\<Your Loki Push API URL\>
   - LOKI_USERNAME=\<Your Loki Username\>
   - LOKI_GRAFANA_CLOUD_API_KEY=\<Your Loki API Key\>

   - PROM_URL=\<Your Prometheus URL\>
   - PROM_USERNAME=\<Your Prometheus Username\>
   - PROM_GRAFANA_CLOUD_API_KEY=\<Your Prometheus API Key\>

5. Restart the Alloy service to apply the changes:
   ```bash
      docker compose restart alloy
   ```

---
## Step 3: Triggering the Jenkins Pipeline
1. Access the Jenkins UI at http://localhost:8080.
2. During the initial setup:
   - Retrieve the admin password by running:
     ```bash
        docker logs jenkins
     ```
   - Copy the password and paste it into the Jenkins setup page.
3. Install the recommended plugins and set up a new **Multibranch Pipeline** project.
4. Configure the pipeline:
   - Link it to your GitHub repository containing this project.
   - Add your GitHub credentials (use a Personal Access Token with repo access).
5. Trigger the pipeline:
   - Jenkins will automatically detect the Jenkinsfile in the repository and start running the pipeline.
  
---
## Step 4: Verifying Metrics and Logs
1. Prometheus Metrics: Metrics are pushed to the Prometheus Pushgateway and can be viewed in Grafana Cloud Dashboards.
   - Select the default Prometheus data source.
   - Select `compile_breaks_total` as the metric.
   - Run the query `sum by(model, commit, reason) (compile_breaks_total)`.
   - View the total compile breaks as a line graph or bar chart.
2. Loki Logs: Compile-break logs are sent to Loki and can be visualized in Grafana Cloud Dashboards.
   - Select the default Loki data source.
   - Filter by label.
4. Artifacts:
   - Pipeline artifacts (e.g., metrics files) are archived in Jenkins and can be downloaded from the Jenkins UI.

---

### How to set up Jenkins pipeline on GCP
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
