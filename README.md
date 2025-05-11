# HPML Project: Debug Tools for Compile and Export

Note: To view torchlens / model visualization repository, see it [here](https://github.com/Vinayak-Kannan/torchlens-HP`ML)

## Team Information
- **Members**:
  - Vinayak Kannan (vk2364)
  - Taejun Seo (ts3574)
  - Peter Ma (pym2104)

---

## 1. Problem Statement
Modern machine learning models - especially those shared on platforms like Hugging Face - require robust workflows for compilation and export to various inference backends. However, existing tools for model compilation (e.g., `torch.compile`) are hard to debug and not well integrated with CI/CD pipelines.

This project addresses this gap by developing a continuous debugging system for PyTorch model compilation compatibility. We use a Jenkins-based CI/CD pipeline and extend visualization/debugging tools to highlight causes as well as surface analytics for graph breaks.

---

## 2. System Description
![Grafana Pipeline Architecture Diagram](images/Grafana_Pipeline_Arch_Diagram.svg)

Our compilation and visualization pipeline consists of the following components:
- Jenkins CI/CD pipeline
   - Triggered manually or on set schedule
   - Sets up model environment
   - Pulls top N models from Hugging Face
   - Compiles models and generate metrics/logs using `torch._dynamo.explain`
   - Archives data
- Prometheus to monitor metrics, uploaded to Pushgateway
- Loki to monitor logs, stored in log files
- Grafana Alloy to continuously collect these metrics and logs
- Grafana Cloud platform to host data and visualization dashboards
- Docker to compose and containerize the multiple components

---

## 3. Final Results Summary
![Grafana Dashboard](images/Grafana_Dashboard.png)

[External Link to Grafana Dashboard](https://hpmldebug.grafana.net/public-dashboards/ad228f34c4bf4d33ada79c27157ac974)

We successfully developed a fully automated pipeline and show at the link above a sample dashboard with ingested compilation data, metrics, and logs. Here we monitor compilation graph breaks by model family, model, and break reasons over time for various sample Audio and Computer Vision models.

**Our key contrbution is that this infrastructure can be easily extended to ingest other metrics and logs, and the raw data can be manipulated using the variety of Grafana operations to generate more advanced dashboards. Other models, such as those in the IBM Foundation Model Stack, can also be plugged in**

---

## 4. Reproducibility Instructions
Note: The following is specifically configured to run for MacOS. Please adjust accordingly for other operating systems.

### A. Requirements

Install dependencies:

1. **Docker and Docker Compose**: Ensure Docker and Docker Compose are installed on your machine.
2. **Grafana Cloud Account**: Create an account on [Grafana Cloud](https://grafana.com/) to obtain the necessary credentials.

---

### B. Wandb Dashboard

Not applicable, see Grafana dashboard above instead.

---

### C. Specify for Training or For Inference or if Both 

Not applicable.

---

### D. Evaluation

Not applicable.

---

### E. Quickstart: Minimum Reproducible Result

#### Step 1: Running Docker Compose

1. Start the services using Docker Compose:
   ```bash
   docker compose up -d
   ```

2. Verify that the following services are running:
   - Jenkins: Accessible at http://localhost:8080
   - Pushgateway: Accessible at http://localhost:9091
   - Alloy: Accessible at http://localhost:12345

#### Step 2: Setting Up Grafana Cloud Credentials
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

#### Step 5: Upload Models for Analysis
Sample models and outputs are provided out of the box to use in `scripts/inputs` and `scipts/dynamo_explain_output`.

To upload your own model:
1. Refer to each model's specific input requirements on its page on Hugging Face.
2. Modify `inputs_driver.py` to support that input and serialize.

#### Step 4: Triggering the Jenkins Pipeline
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
  

#### Step 5: Verifying Metrics and Logs
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

## 5. Notes
- Full drill down for every model/family can be accessed by clicking on the "Graph Breaks by Model Family" panel. However, this requires the user to be an internal organization member.
- Repo overview
   - Config files:
      - `compose.yaml`, `Dockerfile`: Hooks up multiple the Docker containers.
      - `Jenkinsfile`: Define stages in CI/CD pipeline, pulls the top-N Hugging Face models.
      - `alloy/config.alloy`: Configures metrics (Prometheus), logs (Loki), and Alloy (collector agent).
      - `alloy/env.secrets`: Upload your own URLs, usernames, and API keys to connect Alloy to Loki/Prometheus/Grafana Cloud.
   - Driver scripts are located in `scripts/`
      - `inputs_driver.py`: serializes custom input for a specific model, currently done manually, will fully automate in the future.
      - `pull_hf_models.py`: fetches the top N (configurable) models from various model families on Hugging Face.
      - `dynamo_explain_creator.py`: pulls the corresponding model and its input, runs `torch._dynamo.explain` to compile the model and aggregate the graph breaks that are encountered, and stores the output as a serialized object.
      - `dynamo_explain_parser.py`: helper used by `dynamo_explain_creator.py` to parse the `torch._dynamo.explain` output into a more easily manipulable object.
      - `collect_compile_breaks.py`: main driver that processes generated metrics/logs and records them to Prometheus and Loki to be scraped by Alloy.
   - `scripts/inputs` stores serialized inputs for models that are to be processed by `torch._dynamo.explain`.
   - `scripts/dynamo_explain_output` stores serialized dynamo explain outputs for models that are to be extracted for compile breaks information.
   - Other unmentioned files have been kept for unused implementations/future functionalities.
