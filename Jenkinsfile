def cronExpr = env.BRANCH_IS_PRIMARY ? '@hourly' : ''

pipeline {
  agent {
    label 'jnlp-linux-arm64'
  }

  options {
    buildDiscarder logRotator(daysToKeepStr: '90')
    lock(resource: "csp-compatibility-${env.BRANCH_NAME}", inversePrecedence: true)
    timeout(time: 10, unit: 'MINUTES')
    disableConcurrentBuilds()
  }

  triggers {
    cron( cronExpr )
  }

  stages {
    stage('Generate Report') {
      steps {
        sh 'python3 ./scripts/generate_plugin_report_json.py'
        dir('output') {
          archiveArtifacts '**'
        }
      }
    }

    stage('Publish Report') {
      when {
        anyOf {
          expression { env.BRANCH_IS_PRIMARY }
        }
      }
      steps {
        sh 'rm -rf csp-compatibility ; mv output csp-compatibility'
        publishReports (["csp-compatibility/index.html", "csp-compatibility/plugin_report.json"])
      }
    }
  }
}
