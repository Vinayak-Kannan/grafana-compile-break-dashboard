pipeline {
    agent any

    // environment {
    //     PROM_USERNAME          = credentials('grafana-cloud-prom-user')
    //     LOKI_USERNAME          = credentials('grafana-cloud-logs-user')
    //     GRAFANA_CLOUD_API_KEY  = credentials('grafana-cloud-api-key')
    // }
    
    stages {
        stage('Hello') {
            steps {
                echo 'Hello World'
            }
        }

        stage('Download Requirements') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Collect compile-breaks') {
            steps {
                sh '''
                python scripts/collect_compile_breaks.py
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
