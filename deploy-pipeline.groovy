/* 

Jenkins Release pipeline

Required non-default plugins:

1. HTTP Request Plugin
2. Pipeline Utility Steps
3. AnsiColor

Required parameters list:

1. NODE
2. VEEPEENET_VERSION
3. DISTRIB_URL
4. AUTH_TOKEN
5. HOST
6. HOST_SSH_PORT
7. HOST_SSH_CRED
8. CHECK
9. REPO_CLONE_URL
10. REPO_BRANCH

*/

node {

    cleanWs()

    stage("Checks") {
        requiredParametersNames = [
            "NODE", "HOST", "HOST_SSH_PORT", "HOST_SSH_CRED", "REPO_CLONE_URL", "REPO_BRANCH"
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
        if (!params.VEEPEENET_VERSION && !params.DISTRIB_URL) {
            error("Params 'VEEPEENET_VERSION' or 'DISTRIB_URL' must be defined")
        }
    }

    buildName "#$BUILD_NUMBER ${if (params.VEEPEENET_VERSION) params.VEEPEENET_VERSION else 'CUSTOM'}"

    repoDir = "${pwd()}/veepeenet"
    inventoryPath = "${pwd()}/inventory.ini"
    deployPlaybookPath = "$repoDir/deploy-playbook.yml"

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
        if (params.params.DISTRIB_URL) {
            extraVars = [
                distrib_url: params.DISTRIB_URL,
                distrib_auth: "Bearer $params.AUTH_TOKEN"
            ]
        } else {
            extraVars = [release_version: params.VEEPEENET_VERSION]
        }
        extraVars << [ansible_port:params.HOST_SSH_PORT]
        ansiColor {
            ansiblePlaybook(
                playbook: deployPlaybookPath,
                inventory: inventoryPath,
                credentialsId: params.HOST_SSH_CRED,
                disableHostKeyChecking: true,
                extraVars: extraVars,
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