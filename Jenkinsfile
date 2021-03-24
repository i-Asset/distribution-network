#!/usr/bin/env groovy

node('iasset-jenkins-slave') {

    // -----------------------------------------------
    // --------------- Staging Branch ----------------
    // -----------------------------------------------
    if (env.BRANCH_NAME == 'staging') {

        stage('Clone and Update') {
            git(url: 'https://github.com/i-Asset/distribution-network.git', branch: env.BRANCH_NAME)
        }

        stage('Compose Build Docker') {
            sh 'docker build ./server -t iassetplatform/distribution-network:staging'
        }

        stage('Push Docker') {
            sh 'docker push iassetplatform/distribution-network:staging'
        }

        stage('Deploy') {
            sh 'ssh staging "cd /srv/docker_setup/staging/ && ./run-staging.sh restart-single distribution-network"'
        }
    }

    // -----------------------------------------------
    // ---------------- Master Branch ----------------
    // -----------------------------------------------
    if (env.BRANCH_NAME == 'master') {

        stage('Clone and Update') {
            git(url: 'https://github.com/i-Asset/distribution-network.git', branch: env.BRANCH_NAME)
        }

        stage('Compose Build Docker') {
            sh 'docker build ./server -t iassetplatform/distribution-network:staging'
        }
    }

    // -----------------------------------------------
    // ---------------- Release Tags -----------------
    // -----------------------------------------------
    if( env.TAG_NAME ==~ /^\d+.\d+.\d+$/) {

        stage('Clone and Update') {
            git(url: 'https://github.com/i-Asset/distribution-network.git', branch: env.BRANCH_NAME)
        }

        stage('Compose Build Docker') {
            sh 'docker build ./server -t iassetplatform/distribution-network:staging'
        }

        stage('Push Docker') {
            sh 'docker push iassetplatform/distribution-network:' + env.TAG_NAME
            sh 'docker push iassetplatform/distribution-network:latest'
        }

        stage('Deploy PROD') {
            sh 'ssh prod "cd /data/deployment_setup/prod/ && sudo ./run-prod.sh restart-single distribution-network"'
        }
    }
}