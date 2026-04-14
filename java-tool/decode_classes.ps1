# ========================================
# ממיר את Base64 חזרה לקבצי .class
# ========================================
# שים את הסקריפט הזה באותה תיקייה עם קבצי .b64
# הרץ: powershell -ExecutionPolicy Bypass -File .\decode_classes.ps1
# אם PowerShell חסום - אפשר גם לעשות את זה ב-cmd.exe עם certutil
# ========================================

Write-Host "ממיר קבצי Base64 חזרה ל-.class..."

function Convert-B64 {
    param($InputFile, $OutputFile)
    if (Test-Path $InputFile) {
        $b64 = Get-Content $InputFile -Raw
        $bytes = [Convert]::FromBase64String($b64.Trim())
        [System.IO.File]::WriteAllBytes((Join-Path (Get-Location) $OutputFile), $bytes)
        Write-Host "  ✓ $OutputFile"
    } else {
        Write-Host "  ✗ $InputFile לא נמצא!" -ForegroundColor Red
    }
}

Convert-B64 "FraudAnalyzer.class.b64" "FraudAnalyzer.class"
Convert-B64 "Claim.class.b64" "FraudAnalyzer`$Claim.class"
Convert-B64 "Alert.class.b64" "FraudAnalyzer`$Alert.class"

Write-Host ""
Write-Host "✅ הסתיים! עכשיו הרץ:"
Write-Host "   java FraudAnalyzer"
