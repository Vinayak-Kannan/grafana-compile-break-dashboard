pipeline {
    agent any

    environment {
    //     PROM_USERNAME          = credentials('grafana-cloud-prom-user')
    //     LOKI_USERNAME          = credentials('grafana-cloud-logs-user')
    //     GRAFANA_CLOUD_API_KEY  = credentials('grafana-cloud-api-key')
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
