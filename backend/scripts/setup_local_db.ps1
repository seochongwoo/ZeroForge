# 로컬 PostgreSQL(Windows 설치본)에 ZeroForge용 사용자·DB를 만든다.
# Docker(docker-compose.yml)를 쓰는 경우에는 필요 없다.
#
# 실행: 저장소 루트에서
#   powershell -ExecutionPolicy Bypass -File backend\scripts\setup_local_db.ps1
# postgres 슈퍼유저 비밀번호를 물어본다. 여러 번 실행해도 안전하다.

$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$envFile = Join-Path $repoRoot '.env'
if (-not (Test-Path $envFile)) { throw ".env가 없습니다. .env.example을 복사해 값을 채우세요." }

$cfg = @{}
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*([A-Z_][A-Z0-9_]*)=(.*)$') { $cfg[$Matches[1]] = $Matches[2].Trim() }
}
$db = $cfg['POSTGRES_DB']; $user = $cfg['POSTGRES_USER']; $pw = $cfg['POSTGRES_PASSWORD']
$pgHost = $cfg['POSTGRES_HOST']; $port = $cfg['POSTGRES_PORT']
foreach ($k in 'POSTGRES_DB','POSTGRES_USER','POSTGRES_PASSWORD') {
    if (-not $cfg[$k] -or $cfg[$k] -eq 'change-me') { throw ".env의 $k 값을 채우세요." }
}
if ($db -notmatch '^[a-z_][a-z0-9_]*$' -or $user -notmatch '^[a-z_][a-z0-9_]*$') { throw "DB/사용자 이름은 소문자·숫자·밑줄만 쓰세요." }

$psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'
if (-not (Test-Path $psql)) { $psql = (Get-Command psql -ErrorAction Stop).Source }

$pwSql = $pw.Replace("'", "''")
$sql = @"
SELECT format('CREATE ROLE %I LOGIN CREATEDB PASSWORD %L', '$user', '$pwSql')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$user') \gexec
ALTER ROLE "$user" WITH LOGIN CREATEDB PASSWORD '$pwSql';
SELECT format('CREATE DATABASE %I OWNER %I', '$db', '$user')
 WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '$db') \gexec
\c "$db"
CREATE EXTENSION IF NOT EXISTS vector;
"@

$tmp = New-TemporaryFile
try {
    # PowerShell 5의 utf8은 BOM을 붙여 psql이 첫 줄을 못 읽으므로 BOM 없이 쓴다
    [System.IO.File]::WriteAllText($tmp, $sql, (New-Object System.Text.UTF8Encoding $false))
    & $psql -v ON_ERROR_STOP=1 -U postgres -h $pgHost -p $port -d postgres -f $tmp
    if ($LASTEXITCODE -ne 0) { throw "psql 실패 (exit $LASTEXITCODE)" }
    Write-Host "완료: 사용자 '$user', DB '$db', pgvector 확장 준비됨"
} finally {
    Remove-Item $tmp -ErrorAction SilentlyContinue
}
