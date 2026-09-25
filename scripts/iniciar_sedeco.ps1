$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $ProjectDir ".sedeco_runtime"
$VenvDir = Join-Path $RuntimeDir "venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Requirements = Join-Path $ProjectDir "requirements.txt"
$RequirementsStamp = Join-Path $RuntimeDir "requirements.sha256"
$PidFile = Join-Path $RuntimeDir "server.pid"
$PortFile = Join-Path $RuntimeDir "server.port"
$StdoutLog = Join-Path $RuntimeDir "streamlit.stdout.log"
$StderrLog = Join-Path $RuntimeDir "streamlit.stderr.log"
$LauncherVersion = "2026-09-14-v4"
$LauncherStamp = Join-Path $RuntimeDir "launcher.version"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-SedecoHealth([int]$Port) {
    try {
        $Response = Invoke-WebRequest `
            -Uri "http://127.0.0.1:$Port/_stcore/health" `
            -UseBasicParsing `
            -TimeoutSec 2
        return $Response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Test-LocalPortInUse([int]$Port) {
    $Client = New-Object System.Net.Sockets.TcpClient
    try {
        $Connection = $Client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $Connection.AsyncWaitHandle.WaitOne(250)) {
            return $false
        }
        $Client.EndConnect($Connection)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $Client.Close()
    }
}

function Open-Sedeco([int]$Port) {
    Start-Process "http://127.0.0.1:$Port"
}

function Test-PythonCandidate([string]$Command, [array]$Prefix) {
    if (-not (Test-Path $Command -PathType Leaf)) {
        return $null
    }

    try {
        $ProbeArguments = @()
        $ProbeArguments += $Prefix
        $ProbeArguments += @(
            "-c",
            "import sys; print(sys.executable); print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        )

        $ProbeOutput = @(& $Command @ProbeArguments 2>$null)
        if (($LASTEXITCODE -ne 0) -or ($ProbeOutput.Count -lt 2)) {
            return $null
        }

        $Executable = [string]$ProbeOutput[$ProbeOutput.Count - 2]
        $VersionText = [string]$ProbeOutput[$ProbeOutput.Count - 1]
        $VersionParts = $VersionText.Trim().Split(".")
        if ($VersionParts.Count -lt 2) {
            return $null
        }

        $Major = [int]$VersionParts[0]
        $Minor = [int]$VersionParts[1]
        # Para despliegue institucional usamos Python 3.10 a 3.13.
        # Python 3.14 se omite hasta validar todas las dependencias del sistema.
        if (($Major -ne 3) -or ($Minor -lt 10) -or ($Minor -gt 13)) {
            return $null
        }

        if (-not (Test-Path $Executable.Trim() -PathType Leaf)) {
            return $null
        }

        return @{
            Command = $Executable.Trim()
            Prefix = @()
            Version = "$Major.$Minor"
        }
    }
    catch {
        return $null
    }
}

function Get-BasePython {
    $Candidates = @()
    $SearchRoots = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python"),
        (Join-Path $env:ProgramFiles "Python")
    )

    if (${env:ProgramFiles(x86)}) {
        $SearchRoots += (Join-Path ${env:ProgramFiles(x86)} "Python")
    }

    foreach ($Root in $SearchRoots) {
        if (Test-Path $Root) {
            $RootPython = Join-Path $Root "python.exe"
            if (Test-Path $RootPython -PathType Leaf) {
                $Candidates += @{
                    Command = $RootPython
                    Prefix = @()
                }
            }

            $InstallFolders = Get-ChildItem `
                -Path $Root `
                -Directory `
                -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending

            foreach ($InstallFolder in $InstallFolders) {
                $PythonPath = Join-Path $InstallFolder.FullName "python.exe"
                if (Test-Path $PythonPath -PathType Leaf) {
                    $Candidates += @{
                        Command = $PythonPath
                        Prefix = @()
                    }
                }
            }
        }
    }

    $PathPythons = Get-Command "python.exe" -All -ErrorAction SilentlyContinue
    foreach ($Python in $PathPythons) {
        $Candidates += @{
            Command = $Python.Source
            Prefix = @()
        }
    }

    $PyLaunchers = Get-Command "py.exe" -All -ErrorAction SilentlyContinue
    foreach ($PyLauncher in $PyLaunchers) {
        $Candidates += @{
            Command = $PyLauncher.Source
            Prefix = @("-3")
        }
    }

    $Checked = @{}
    foreach ($Candidate in $Candidates) {
        $CandidateCommand = [string]$Candidate.Command
        $CandidatePrefix = [array]$Candidate.Prefix
        $CandidateKey = "$CandidateCommand|$($CandidatePrefix -join ' ')"
        if ($Checked.ContainsKey($CandidateKey)) {
            continue
        }
        $Checked[$CandidateKey] = $true

        $ValidPython = Test-PythonCandidate `
            -Command $CandidateCommand `
            -Prefix $CandidatePrefix
        if ($ValidPython) {
            return $ValidPython
        }
    }

    return $null
}

function Backup-DailyData {
    $DataDir = Join-Path $ProjectDir "data"
    if (-not (Test-Path $DataDir)) {
        return
    }

    $BackupRoot = Join-Path $ProjectDir "backups\automaticos"
    $TodayDir = Join-Path $BackupRoot (Get-Date -Format "yyyy-MM-dd")
    if (Test-Path $TodayDir) {
        return
    }

    New-Item -ItemType Directory -Path $TodayDir -Force | Out-Null
    Get-ChildItem -Path $DataDir -Filter "*.csv" -File -ErrorAction SilentlyContinue |
        Copy-Item -Destination $TodayDir -Force
}

try {
    Write-Host "Lanzador SEDECO: $LauncherVersion" -ForegroundColor DarkGray
    Write-Host "Carpeta: $ProjectDir" -ForegroundColor DarkGray
    Set-Location $ProjectDir
    New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null

    # Si se actualizo el lanzador, reconstruir solo el entorno tecnico local.
    $SavedLauncherVersion = ""
    if (Test-Path $LauncherStamp) {
        $SavedLauncherVersion = (Get-Content $LauncherStamp -Raw).Trim()
    }
    if ($SavedLauncherVersion -ne $LauncherVersion) {
        Write-Step "Actualizando el entorno local de SEDECO"
        Remove-Item $VenvDir -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item $RequirementsStamp, $PidFile, $PortFile -Force -ErrorAction SilentlyContinue
    }

    if ((Test-Path $PortFile) -and (Test-Path $PidFile)) {
        $SavedPort = [int](Get-Content $PortFile -Raw)
        if (Test-SedecoHealth -Port $SavedPort) {
            Write-Host "El Sistema Integral Vincúlate SEDECO ya esta funcionando. Abriendo..." -ForegroundColor Green
            Open-Sedeco $SavedPort
            exit 0
        }

        Remove-Item $PidFile, $PortFile -Force -ErrorAction SilentlyContinue
    }

    if ((Test-Path $VenvDir) -and (-not (Test-Path $VenvPython))) {
        Write-Step "Limpiando una preparacion anterior incompleta"
        Remove-Item $VenvDir -Recurse -Force
        Remove-Item $RequirementsStamp -Force -ErrorAction SilentlyContinue
    }

    if (Test-Path $VenvPython) {
        $ExistingVenv = Test-PythonCandidate -Command $VenvPython -Prefix @()
        if (-not $ExistingVenv) {
            Write-Step "Reparando el entorno local de SEDECO"
            Remove-Item $VenvDir -Recurse -Force
            Remove-Item $RequirementsStamp -Force -ErrorAction SilentlyContinue
        }
    }

    if (-not (Test-Path $VenvPython)) {
        # Un sello de dependencias sin un entorno virtual valido no sirve.
        Remove-Item $RequirementsStamp -Force -ErrorAction SilentlyContinue
        Write-Step "Preparando el Sistema Integral Vincúlate SEDECO por primera vez"
        $BasePython = Get-BasePython

        if (-not $BasePython) {
            Write-Host ""
            Write-Host "No se encontro una instalacion valida de Python." -ForegroundColor Yellow
            Write-Host "SEDECO necesita Python 3.10, 3.11, 3.12 o 3.13 de 64 bits."
            Write-Host "Se abrira la pagina oficial de Python."
            Write-Host "Durante la instalacion activa la opcion: Add Python to PATH."
            Start-Process "https://www.python.org/downloads/windows/"
            throw "Instala Python 3.12 o 3.13 de 64 bits y despues vuelve a abrir INICIAR_SEDECO.bat."
        }

        Write-Host "Python valido encontrado: $($BasePython.Version)" -ForegroundColor Green
        $VenvArguments = @()
        $VenvArguments += $BasePython.Prefix
        $VenvArguments += @("-m", "venv", $VenvDir)
        & $BasePython.Command @VenvArguments
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo crear el entorno local de SEDECO."
        }
    }

    $CurrentHash = (Get-FileHash $Requirements -Algorithm SHA256).Hash
    $SavedHash = ""
    if (Test-Path $RequirementsStamp) {
        $SavedHash = (Get-Content $RequirementsStamp -Raw).Trim()
    }

    # No confiar solo en el hash: un venv reparado puede conservar un sello viejo.
    $DependenciesOk = $false
    try {
        & $VenvPython -c "import streamlit, pandas, plotly, openpyxl, pydeck, supabase" 2>$null
        $DependenciesOk = ($LASTEXITCODE -eq 0)
    }
    catch {
        $DependenciesOk = $false
    }

    if (($CurrentHash -ne $SavedHash) -or (-not $DependenciesOk)) {
        if (-not $DependenciesOk) {
            Write-Step "Reparando componentes faltantes del Sistema Integral Vinculate SEDECO"
        }
        else {
            Write-Step "Instalando componentes necesarios; esto solo tarda la primera vez"
        }

        # Asegura que pip exista incluso si la instalacion de Python vino incompleta.
        & $VenvPython -m ensurepip --upgrade 2>$null
        & $VenvPython -m pip install --disable-pip-version-check --upgrade pip
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo preparar el instalador de componentes."
        }

        & $VenvPython -m pip install --disable-pip-version-check -r $Requirements
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudieron instalar los componentes. Verifica tu conexion a internet."
        }

        # Verificacion final antes de guardar el sello.
        & $VenvPython -c "import streamlit, pandas, plotly, openpyxl, pydeck, supabase"
        if ($LASTEXITCODE -ne 0) {
            throw "Los componentes se instalaron de forma incompleta."
        }

        Set-Content -Path $RequirementsStamp -Value $CurrentHash -Encoding ASCII
    }

    Set-Content -Path $LauncherStamp -Value $LauncherVersion -Encoding ASCII

    Backup-DailyData

    $Port = 8501
    while (($Port -le 8510) -and (Test-LocalPortInUse -Port $Port)) {
        $Port++
    }
    if ($Port -gt 8510) {
        throw "No hay un puerto local disponible entre 8501 y 8510."
    }

    Write-Step "Iniciando la aplicacion"
    Remove-Item $StdoutLog, $StderrLog -Force -ErrorAction SilentlyContinue

    $StreamlitArguments = @(
        "-m", "streamlit", "run", "app.py",
        "--server.address", "127.0.0.1",
        "--server.port", "$Port",
        "--server.headless", "true",
        "--server.runOnSave", "false",
        "--browser.gatherUsageStats", "false"
    )

    $Server = Start-Process `
        -FilePath $VenvPython `
        -ArgumentList $StreamlitArguments `
        -WorkingDirectory $ProjectDir `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -WindowStyle Hidden `
        -PassThru

    Set-Content -Path $PidFile -Value $Server.Id -Encoding ASCII
    Set-Content -Path $PortFile -Value $Port -Encoding ASCII

    $Ready = $false
    for ($Attempt = 0; $Attempt -lt 120; $Attempt++) {
        Start-Sleep -Milliseconds 500
        if (Test-SedecoHealth -Port $Port) {
            $Ready = $true
            break
        }
        if ($Server.HasExited) {
            break
        }
    }

    if (-not $Ready) {
        if (-not $Server.HasExited) {
            Stop-Process -Id $Server.Id -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $PidFile, $PortFile -Force -ErrorAction SilentlyContinue
        Write-Host ""
        Write-Host "Detalle del inicio:" -ForegroundColor Yellow
        if (Test-Path $StderrLog) {
            Get-Content $StderrLog -Tail 20
        }
        throw "La aplicacion no respondio a tiempo."
    }

    Write-Host ""
    Write-Host "Sistema Integral Vincúlate SEDECO listo. Abriendo en el navegador..." -ForegroundColor Green
    Open-Sedeco $Port
    exit 0
}
catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
