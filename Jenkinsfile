pipeline {
    agent any

    // Poll every hour on the hour
    triggers {  // The triggers block instruct Jenkins to run on a cron schedule (e.g. every hour)
        cron('0 * * * *')
    }

    environment {
        //     PROM_USERNAME          = credentials('grafana-cloud-prom-user')
        //     LOKI_USERNAME          = credentials('grafana-cloud-logs-user')
        //     GRAFANA_CLOUD_API_KEY  = credentials('grafana-cloud-api-key')

        // Tell fetch_hf_models.py to do the scheduled scan
        SCHEDULED_SCAN = '1'

        // your existing env
        PUSHGATEWAY_URL = 'http://pushgateway:9091'
    }
    
    stages {
        stage('Hello') {
            steps {
                echo 'Hello World'
            }
        }

        stage('Python?') {
            steps {
                sh 'python --version'
                sh 'pip --version'
                sh 'pwd'
            }
        }

        stage('Download Requirements') {
            steps {
                sh '''
                    . /opt/venv/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }

        // Scan HF models & analyze any updates
        stage('HF Model Scan & Analysis') {
            steps {
                sh '''
                   . /opt/venv/bin/activate
                   # environment SCHEDULED_SCAN=1, set in the enviornment block above, triggers the scan→analyze logic
                   python pull_hf_models.py 15
                '''
            }
        }

        stage('Collect compile-breaks') {
            steps {
                sh '''
                . /opt/venv/bin/activate
                python collect_compile_breaks.py
                '''
            }
        }

        stage('Archive artifacts') {
            steps {
                archiveArtifacts artifacts: 'metrics/**',
                fingerprint: true
            }
        }
    }
}
