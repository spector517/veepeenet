/* 

Jenkins Release pipeline

Required non-default plugins:

1. HTTP Request
2. Pipeline Utility Steps
3. Build Name and Description Setter

Required parameters list:

1. NODE
2. DISTRIB_VERSION
3. CREATE_RELEASE
4. XRAY_VERSION
5. REPO_CLONE_URL
6. REPO_BRANCH
7. XRAY_DOWNLOADS_URL
8. CREATE_RELEASE_URL
9. UPLOAD_ASSETS_URL
10.AUTH_TOKEN

*/

node(params.NODE) {

    cleanWs()

    stage("Checks") {
        requiredParametersNames = [
            "NODE", "DISTRIB_VERSION", "XRAY_VERSION",
            "REPO_CLONE_URL", "REPO_BRANCH", "XRAY_DOWNLOADS_URL",
            "CREATE_RELEASE_URL", "UPLOAD_ASSETS_URL", "AUTH_TOKEN"
        ]
        undefinedParams = []
        requiredParametersNames.each { paramName ->
            if (params[paramName] == null || params[paramName] == "") {
                undefinedParams << paramName
            }
        }
        if (undefinedParams) {
            error("Required params are undefined: $undefinedParams")
        }
    }

    buildName "#$BUILD_NUMBER $DISTRIB_VERSION"

    repoDir = "${pwd()}/veepeenet"
    venvPath = "${pwd()}/venv"
    xrayDistribName = "Xray-linux-64"
    xrayDistribPath = "${pwd()}/$xrayDistribName"
    distribName = "veepeenet-$DISTRIB_VERSION"
    distribPath = "${pwd()}/$distribName"
    archiveDistribName = "veepeenet.tar.gz"
    archiveDistribPath = "${pwd()}/$archiveDistribName"
    metaFilePath = "${pwd()}/meta.json"
    
    stage("Sources") {
        dir(repoDir) {
            log "Cloning $params.REPO_CLONE_URL, branch: $params.REPO_BRANCH"
            git url: params.REPO_CLONE_URL, branch: params.REPO_BRANCH
            log "Repository cloned"
        }
    }

    stage("Prepare") {
        dir(repoDir) {
            log "Creating python virtual environment"
            sh "python3 -m venv $venvPath"
            log "Virtual environment created"

            log "Install python dependencies"
            sh "$venvPath/bin/pip install --upgrade pip"
            sh "$venvPath/bin/pip install mockito pylint"
            log "Dependencies installed"
        }
    }

    stage("Linting") {
        log "Start code linting"
        dir(repoDir) {
            try {
                results = []
                for (module in findFiles(glob: "*.py")) {
                    results << sh(script: "$venvPath/bin/pylint $module.name", returnStatus: true)
                }
                if (results.any {code -> code != 0 }) {
                    error("Code styling need works")
                }
                log "Linting success"
            } catch (Exception ex) {
                unstable(ex.getMessage())
                log ex.getMessage()
            }
        }
    }

    stage("Tests") {
        withEnv(["PYTHONPATH=$repoDir"]) {
            dir("$repoDir/test") {
                try {
                    log "Run tests"
                    sh "$venvPath/bin/python -m unittest discover -v -p '*_test.py'"
                    log "Tests success"
                } catch (Exception ex) {
                    message = "Tests failed"
                    println ex.getMessage()
                    unstable message
                    log message
                }
            }
        }
    }

    stage("Xray") {
        outputFileName = "Xray-linux-64.zip"

        log "Download Xray distrib"
        httpRequest url: "$XRAY_DOWNLOADS_URL/$XRAY_VERSION/Xray-linux-64.zip", outputFile: outputFileName
        log "Xray distrib downloaded"

        log "Unpack Xray distrib"
        unzip zipFile: outputFileName, dir: xrayDistribPath
        log "Xray distrib unpacked"
    }

    stage("Distrib") {
        log "Generating meta file"
        meta = [
            version: DISTRIB_VERSION,
            buildNumber: BUILD_NUMBER,
            buildDate: new Date().toString()
        ]
        writeJSON file: metaFilePath, json: meta, pretty: 2
        log "Meta file generated"
        log "Building distrib"
        dir(distribPath) {
            log "Copy required components"
            [
                "$repoDir/install.sh", "$repoDir/install-wg.sh", "$repoDir/install-xray.sh",
                "$repoDir/uninstall.sh", "$repoDir/uninstall-wg.sh", "$repoDir/uninstall-xray.sh",
                "$repoDir/*.py", "$repoDir/xray.service", metaFilePath, "$repoDir/LICENSE"
            ].each { component ->
                sh "cp $component ./"
            }
            sh "chmod 755 *.sh"
            dir(xrayDistribName) {
                sh "cp $xrayDistribPath/xray ./"
                sh "cp $xrayDistribPath/LICENSE ./"
            }
            log "Required components successfully copied"
        }
        log "Archiving distrib"
        tar file: archiveDistribPath, archive: true, compress: true, glob: "$distribName/**"
        archiveArtifacts artifacts: archiveDistribName
        log "Archive created"
    }

    if (params.CREATE_RELEASE) {
        stage("Release") {
            withCredentials([string(credentialsId: AUTH_TOKEN, variable: "github_token")]) {
                log "Creating release draft"
                releaseResponse = httpRequest url: CREATE_RELEASE_URL, contentType: "APPLICATION_JSON_UTF8", httpMode: 'POST',
                    customHeaders: [
                        [name: "Authorization", value: "Bearer $github_token"],
                    ],
                    requestBody: writeJSON(
                        json: [
                            tag_name: DISTRIB_VERSION,
                            target_commitish: REPO_BRANCH,
                            name: "VeePeeNET $DISTRIB_VERSION",
                            draft: true,
                            prerelease: false,
                            generate_release_notes: false
                        ],
                        returnText: true
                    )
                releaseId = readJSON(text: releaseResponse.content)["id"]
                log "Release draft created (id: $releaseId)"

                log "Uploading archive distrib to release draft"
                httpRequest url: "$UPLOAD_ASSETS_URL/$releaseId/assets?name=$archiveDistribName", httpMode: 'POST',
                    contentType: "APPLICATION_OCTETSTREAM",
                    customHeaders: [
                        [name: "Authorization", value: "Bearer $github_token"],
                    ],
                    uploadFile: archiveDistribPath,
                    wrapAsMultipart: false
                log "Archive distrib uploaded"
            }
        }
    } else {
        log "Skip release creation"
    }
}

def log(message) {
    timestamps {
        echo "$message"
    }
}