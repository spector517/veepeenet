/* 

Jenkins Release pipeline

Required non-default plugins:

1. HTTP Request Plugin
2. Pipeline Utility Steps
3. AnsiColor

Required parameters list:

1. NODE
2. VEEPEENET_VERSION
3. HOST
4. HOST_SSH_PORT
5. HOST_SSH_CRED
6. CHECK
7. REPO_CLONE_URL
8. REPO_BRANCH

*/

node {

    cleanWs()

    stage("Checks") {
        requiredParametersNames = [
            "NODE", "VEEPEENET_VERSION", "HOST", "HOST_SSH_PORT", "HOST_SSH_CRED", "REPO_CLONE_URL", "REPO_BRANCH"
        ]
        undefinedParams = []
        requiredParametersNames.each { paramName ->
            if (!params[paramName]) {
                undefinedParams << paramName
            }
        }
        if (undefinedParams) {
            error("Required params are undefined: $undefinedParams")
        }
    }

    repoDir = "${pwd()}/veepeenet"
    inventoryPath = "${pwd()}/inventory.ini"
    deployPlaybookPath = "$repoDir/deploy-playbook.yml"
    distribFilePath = "${pwd()}/veepeenet.tar.gz"

    buildName "#$BUILD_NUMBER ${if (params.VEEPEENET_VERSION) params.VEEPEENET_VERSION else 'CUSTOM'}"

    stage("Sources") {
        dir(repoDir) {
            log "Cloning $params.REPO_CLONE_URL, branch: $params.REPO_BRANCH"
            git url: params.REPO_CLONE_URL, branch: params.REPO_BRANCH
            log "Repository cloned"
        }
    }

    stage("Prepare") {
        log("Generating inventory.ini")
        writeFile file: inventoryPath, text: params.HOST
        log("inventory.ini generated")
    }

    stage("Deploy") {
        ansiColor {
            ansiblePlaybook(
                playbook: deployPlaybookPath,
                inventory: inventoryPath,
                credentialsId: params.HOST_SSH_CRED,
                disableHostKeyChecking: true,
                extraVars: [
                    release_version: params.VEEPEENET_VERSION,
                    ansible_port:params.HOST_SSH_PORT
                ],
                extras: "${if (params.CHECK) '--check' else ''}",
                colorized: true
            )
        }
    }
}

def log(message) {
    timestamps {
        echo "$message"
    }
}