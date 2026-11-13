# Rebuilds the paper: knit to HTML, print to PDF with Chrome, write the code-only .R.
# Run from this folder:  powershell -ExecutionPolicy Bypass -File build_paper.ps1
# (RStudio's Knit button for pdf_document needs LaTeX, which Smart App Control blocks on this PC.)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$rscript = 'C:\Program Files\R\R-4.6.0\bin\Rscript.exe'
$env:RSTUDIO_PANDOC = 'C:\Program Files\RStudio\resources\app\bin\quarto\bin\tools'
$chrome = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1

Push-Location $here
try {
    & $rscript -e "rmarkdown::render('storm_outage_cost_jakemoore.Rmd', output_format = 'html_document', intermediates_dir = tempdir()); knitr::purl('storm_outage_cost_jakemoore.Rmd', output = 'storm_outage_cost_jakemoore.R', documentation = 1, quiet = TRUE)"
    if ($LASTEXITCODE -ne 0) { throw "Knit failed" }
    $profile = Join-Path $env:TEMP 'storm_paper_chrome'
    $html = 'file:///' + ((Join-Path $here 'storm_outage_cost_jakemoore.html') -replace '\\', '/')
    $proc = Start-Process -FilePath $chrome -Wait -PassThru -WindowStyle Hidden -ArgumentList @(
        '--headless=new', '--disable-gpu', "--user-data-dir=$profile", '--no-pdf-header-footer',
        '--virtual-time-budget=15000', "--print-to-pdf=$(Join-Path $here 'storm_outage_cost_jakemoore.pdf')", $html)
    Write-Host "PDF written: $(Join-Path $here 'storm_outage_cost_jakemoore.pdf')"
} finally { Pop-Location }
