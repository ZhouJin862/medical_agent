# Docker build script for Medical Agent (PowerShell)

# Configuration
$Env:IMAGE_NAME = if ($Env:IMAGE_NAME) { $Env:IMAGE_NAME } else { "medical-agent" }
$Env:IMAGE_TAG = if ($Env:IMAGE_TAG) { $Env:IMAGE_TAG } else { "latest" }
$Env:REGISTRY = if ($Env:REGISTRY) { $Env:REGISTRY } else { "" }
$Env:VERSION = if ($Env:VERSION) { $Env:VERSION } else { "0.1.0" }

$BuildDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
try {
    $VcsRef = (git rev-parse --short HEAD 2>$null)
    if (-not $VcsRef) { $VcsRef = "unknown" }
} catch {
    $VcsRef = "unknown"
}

# Build image name
$FullImageName = "${Env:IMAGE_NAME}:${Env:IMAGE_TAG}"
if ($Env:REGISTRY) {
    $FullImageName = "${Env:REGISTRY}/${FullImageName}"
}

Write-Host "Building Docker image: ${FullImageName}" -ForegroundColor Green
Write-Host "Version: ${Env:VERSION}"
Write-Host "Build Date: ${BuildDate}"
Write-Host "VCS Ref: ${VcsRef}"

# Parse arguments
$SkipTests = $false
$Push = $false
for ($i = 0; $i -lt $args.Count; $i++) {
    switch ($args[$i]) {
        "--skip-tests" {
            $SkipTests = $true
        }
        "--push" {
            $Push = $true
        }
        "--tag" {
            $Env:IMAGE_TAG = $args[$i + 1]
            $i++
        }
        "--version" {
            $Env:VERSION = $args[$i + 1]
            $i++
        }
        default {
            Write-Host "Unknown option: $($args[$i])" -ForegroundColor Red
            exit 1
        }
    }
}

# Run tests if not skipped
if (-not $SkipTests) {
    Write-Host "Running tests before build..." -ForegroundColor Green
    $testResult = pytest -xvs tests/unit/
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Tests failed. Aborting build." -ForegroundColor Red
        Write-Host "Use --skip-tests to bypass this check." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Tests passed."
}

# Build arguments
$BuildArgs = @(
    "--build-arg", "VERSION=${Env:VERSION}",
    "--build-arg", "BUILD_DATE=${BuildDate}",
    "--build-arg", "VCS_REF=${VcsRef}",
    "--tag", "${FullImageName}"
)

# Add version tag
if ($Env:IMAGE_TAG -ne $Env:VERSION) {
    $VersionTag = "${Env:IMAGE_NAME}:${Env:VERSION}"
    if ($Env:REGISTRY) {
        $VersionTag = "${Env:REGISTRY}/${VersionTag}"
    }
    $BuildArgs += "--tag", "${VersionTag}"
}

# Add latest tag
if ($Env:IMAGE_TAG -ne "latest") {
    $LatestTag = "${Env:IMAGE_NAME}:latest"
    if ($Env:REGISTRY) {
        $LatestTag = "${Env:REGISTRY}/${LatestTag}"
    }
    $BuildArgs += "--tag", "${LatestTag}"
}

# Build image
Write-Host "Executing docker build..." -ForegroundColor Green
$buildResult = docker build $BuildArgs -f Dockerfile .

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful!" -ForegroundColor Green

    # Show image info
    Write-Host "`nImage details:"
    docker images "${Env:IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

    # Push if requested
    if ($Push) {
        Write-Host "Pushing image to registry..." -ForegroundColor Green
        docker push "${FullImageName}"

        if ($Env:IMAGE_TAG -ne $Env:VERSION) {
            docker push "${VersionTag}"
        }

        if ($Env:IMAGE_TAG -ne "latest") {
            docker push "${LatestTag}"
        }

        Write-Host "Push completed."
    }
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Done! Image: ${FullImageName}" -ForegroundColor Green
