# ============================================================
# מנתח הונאות ביטוח בריאות - PowerShell
# ============================================================
# שימוש: .\FraudAnalyzer.ps1 [קובץ_CSV] [קובץ_פלט]
# ברירת מחדל: claims.csv -> fraud-report.html

param(
    [string]$InputFile = "claims.csv",
    [string]$OutputFile = "fraud-report.html"
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "============================================================"
Write-Host "  מנתח הונאות ביטוח בריאות"
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path $InputFile)) {
    Write-Host "שגיאה: הקובץ '$InputFile' לא נמצא!" -ForegroundColor Red
    exit 1
}

Write-Host "קורא: $InputFile" -ForegroundColor Cyan
$claims = Import-Csv -Path $InputFile -Encoding UTF8
$total = $claims.Count
Write-Host "נטענו $total תביעות" -ForegroundColor Green
Write-Host ""

# ============================================================
# ניתוח
# ============================================================
$alerts = @()

# סטטיסטיקות
$stats = @{
    total = $total
    totalClaimed = ($claims | Measure-Object -Property amount_claimed -Sum).Sum
    totalPaid = ($claims | Measure-Object -Property amount_paid -Sum).Sum
    uniqInsured = ($claims | Select-Object -Unique insured_id).Count
    uniqProv = ($claims | Select-Object -Unique provider).Count
}

Write-Host "סטטיסטיקות:" -ForegroundColor Yellow
Write-Host "  סה`"כ תביעות:    $($stats.total)"
Write-Host "  סה`"כ נתבע:      $($stats.totalClaimed) ₪"
Write-Host "  סה`"כ שולם:      $($stats.totalPaid) ₪"
Write-Host "  מבוטחים:        $($stats.uniqInsured)"
Write-Host "  נותני שירות:    $($stats.uniqProv)"
Write-Host ""

# 1. תדירות חריגה
Write-Host "1. בודק תדירות חריגה..." -ForegroundColor Cyan
$avgClaims = $total / $stats.uniqInsured
$byPerson = $claims | Group-Object -Property insured_id
foreach ($person in $byPerson) {
    if ($person.Count -ge ($avgClaims * 4)) {
        $first = $person.Group[0]
        $sum = ($person.Group | Measure-Object -Property amount_claimed -Sum).Sum
        $alerts += @{
            type = "תדירות_חריגה"
            severity = "גבוה"
            title = "$($first.insured_name) - $($person.Count) תביעות"
            detail = "ממוצע: $([math]::Round($avgClaims)). מבוטח: $($person.Count). סה`"כ: $sum ₪"
        }
    }
}

# 2. ריכוז נותני שירות
Write-Host "2. בודק ריכוז נותני שירות..." -ForegroundColor Cyan
$byProvider = $claims | Group-Object -Property provider
foreach ($prov in $byProvider) {
    $pct = [math]::Round(($prov.Count / $total) * 100, 1)
    if ($pct -gt 5) {
        $empGroup = $prov.Group | Group-Object -Property employer | Sort-Object Count -Descending | Select-Object -First 1
        $empPct = [math]::Round(($empGroup.Count / $prov.Count) * 100)
        $severity = if ($pct -gt 8) { "גבוה" } else { "בינוני" }
        $alerts += @{
            type = "ריכוז_נותן_שירות"
            severity = $severity
            title = "$($prov.Name) - $($prov.Count) תביעות ($pct%)"
            detail = "מעסיק דומיננטי: $($empGroup.Name) ($($empGroup.Count) תביעות, $empPct%)"
        }
    }
}

# 3. סכומים אחידים
Write-Host "3. בודק סכומים אחידים..." -ForegroundColor Cyan
foreach ($prov in $byProvider) {
    if ($prov.Count -ge 10) {
        $amtGroup = $prov.Group | Group-Object -Property amount_claimed | Sort-Object Count -Descending | Select-Object -First 1
        $amtPct = $amtGroup.Count / $prov.Count
        if ($amtPct -gt 0.6) {
            $alerts += @{
                type = "סכום_אחיד"
                severity = "בינוני"
                title = "$($prov.Name) - $($amtGroup.Count)/$($prov.Count) תביעות בסכום $($amtGroup.Name) ₪"
                detail = "$([math]::Round($amtPct * 100))% מהתביעות באותו סכום"
            }
        }
    }
}

# 4. סכומים עגולים
Write-Host "4. בודק סכומים עגולים..." -ForegroundColor Cyan
$roundClaims = $claims | Where-Object { ([int]$_.amount_claimed % 500 -eq 0) -and ([int]$_.amount_claimed -ge 500) }
if (($roundClaims.Count / $total) -gt 0.03) {
    $topProvs = $roundClaims | Group-Object -Property provider | Sort-Object Count -Descending | Select-Object -First 3
    $detail = ($topProvs | ForEach-Object { "$($_.Name) ($($_.Count))" }) -join ", "
    $alerts += @{
        type = "סכומים_עגולים"
        severity = "בינוני"
        title = "$($roundClaims.Count) תביעות בסכומים עגולים"
        detail = "נותני שירות: $detail"
    }
}

# 5. אשכולות משפחתיים
Write-Host "5. בודק אשכולות משפחתיים..." -ForegroundColor Cyan
$families = @{}
foreach ($c in $claims) {
    $parts = $c.insured_name -split ' '
    $last = $parts[-1]
    $key = "$last|$($c.city)|$($c.provider)"
    if (-not $families.ContainsKey($key)) {
        $families[$key] = @()
    }
    $families[$key] += $c
}
foreach ($key in $families.Keys) {
    $fam = $families[$key]
    $uniq = ($fam | Select-Object -Unique insured_id).Count
    if ($uniq -ge 3 -and $fam.Count -ge 8) {
        $parts = $key -split '\|'
        $totalAmt = ($fam | Measure-Object -Property amount_claimed -Sum).Sum
        $alerts += @{
            type = "אשכול_משפחתי"
            severity = "גבוה"
            title = "משפחת $($parts[0]) - $uniq מבוטחים, $($fam.Count) תביעות"
            detail = "עיר: $($parts[1]), נותן שירות: $($parts[2]), סה`"כ: $totalAmt ₪"
        }
    }
}

Write-Host ""
Write-Host "נמצאו $($alerts.Count) התראות" -ForegroundColor Green
Write-Host ""

# ============================================================
# יצירת HTML
# ============================================================
Write-Host "יוצר דוח HTML..." -ForegroundColor Cyan

# מיון התראות - גבוה קודם
$sortedAlerts = $alerts | Sort-Object -Property @{Expression={if($_.severity -eq "גבוה"){0}else{1}}}
$highCount = ($alerts | Where-Object { $_.severity -eq "גבוה" }).Count

$html = @"
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<title>דוח זיהוי הונאות</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#f1f5f9;color:#1e293b;padding:16px;line-height:1.6;max-width:1000px;margin:0 auto}
h1{text-align:center;color:#dc2626;margin:16px 0;font-size:1.6em}
h2{color:#0f172a;margin:24px 0 10px;font-size:1.2em;border-bottom:2px solid #e2e8f0;padding-bottom:6px}
.card{background:#fff;border-radius:12px;padding:14px;margin:8px 0;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.05)}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:12px 0}
.stat{background:#fff;border-radius:10px;padding:14px;text-align:center;border:1px solid #e2e8f0}
.stat .num{font-size:1.5em;font-weight:bold;color:#2563eb;display:block}
.stat .label{font-size:0.8em;color:#64748b}
.alert{border-radius:10px;padding:14px;margin:8px 0;border-right:5px solid}
.alert-high{background:#fef2f2;border-color:#dc2626}
.alert-med{background:#fffbeb;border-color:#f59e0b}
.alert h4{color:#0f172a;margin-bottom:4px}
.alert p{font-size:0.85em;color:#64748b}
.tag{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.75em;font-weight:bold}
.tag-h{background:#dc2626;color:#fff}.tag-m{background:#f59e0b;color:#fff}
</style>
</head>
<body>
<h1>🔍 דוח זיהוי הונאות - ביטוח בריאות</h1>
<div class="card" style="text-align:center"><p>נותח אוטומטית | $($stats.total) תביעות | $($alerts.Count) התראות</p></div>
<h2>📊 סטטיסטיקות</h2>
<div class="stat-grid">
<div class="stat"><span class="num">$($stats.total)</span><span class="label">תביעות</span></div>
<div class="stat"><span class="num">$($stats.totalClaimed)₪</span><span class="label">נתבע</span></div>
<div class="stat"><span class="num">$($stats.totalPaid)₪</span><span class="label">שולם</span></div>
<div class="stat"><span class="num">$($stats.uniqInsured)</span><span class="label">מבוטחים</span></div>
<div class="stat"><span class="num">$($stats.uniqProv)</span><span class="label">נותני שירות</span></div>
<div class="stat" style="border-color:#dc2626"><span class="num" style="color:#dc2626">$highCount</span><span class="label">🔴 גבוהות</span></div>
</div>
<h2>🚨 התראות</h2>
"@

foreach ($a in $sortedAlerts) {
    $cls = if ($a.severity -eq "גבוה") { "alert-high" } else { "alert-med" }
    $tagCls = if ($a.severity -eq "גבוה") { "tag-h" } else { "tag-m" }
    $icon = if ($a.severity -eq "גבוה") { "🔴" } else { "🟡" }
    $html += @"

<div class="alert $cls">
<h4><span class="tag $tagCls">$icon $($a.type)</span> $($a.title)</h4>
<p>$($a.detail)</p>
</div>
"@
}

$html += @"

</body>
</html>
"@

# שמירה עם UTF-8
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$fullPath = Join-Path -Path (Get-Location) -ChildPath $OutputFile
[System.IO.File]::WriteAllText($fullPath, $html, $utf8NoBom)

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  ✅ הסתיים בהצלחה!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  📊 $($alerts.Count) התראות נמצאו ($highCount גבוהות)"
Write-Host "  🌐 דוח HTML: $OutputFile"
Write-Host ""
Write-Host "  לפתיחה: פתח את $OutputFile בדפדפן"
Write-Host ""
