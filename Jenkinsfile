pipeline {
    agent any
    
    stages {
        stage('Testing') {
            steps {
                echo 'Testing'
            }
        }

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

        stage('Run Dynamo Explain') {
                steps {
                    // Execute a Python script that runs dynamo.explain
                    sh '''
                        python3 pull_model_run_dynamo_explain.py
                    '''
                }
            }

        stage('Get Number Graph Breaks') {
            steps {
                // Execute a Python script that runs dynamo.explain
                sh '''
                    python3 parse_dynamo_explain.py
                '''
            }
        }
    }
}
