# Canvas Auto-Grading Status Dashboard
# Shows current grading progress and queue status

param(
    [switch]$Detailed,
    [switch]$Failed,
    [switch]$Completed
)

$ErrorActionPreference = "SilentlyContinue"

# Read queue data
if (-not (Test-Path "queue.json")) {
    Write-Host "❌ No queue.json found. Run the daemon first." -ForegroundColor Red
    exit 1
}

$queue = Get-Content "queue.json" | ConvertFrom-Json

# Calculate stats
$totalSubmissions = $queue.pending.Count + $queue.completed.Count + $queue.failed.Count + $(if ($queue.processing) { 1 } else { 0 })
$completedCount = $queue.completed.Count
$pendingCount = $queue.pending.Count
$failedCount = $queue.failed.Count
$processingCount = if ($queue.processing) { 1 } else { 0 }

# Header
Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         Canvas Auto-Grading Status Dashboard         ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Progress bar
$percentage = if ($totalSubmissions -gt 0) { [math]::Round(($completedCount / $totalSubmissions) * 100) } else { 0 }
$barLength = 40
$filledLength = [math]::Round(($percentage / 100) * $barLength)
$bar = "#" * $filledLength + "-" * ($barLength - $filledLength)

Write-Host "Overall Progress: " -NoNewline
Write-Host "[$bar] $percentage%" -ForegroundColor $(if ($percentage -ge 80) { "Green" } elseif ($percentage -ge 50) { "Yellow" } else { "Red" })
Write-Host ""

# Summary stats
Write-Host "📊 Summary" -ForegroundColor Cyan
Write-Host "  Total Submissions:  $totalSubmissions"
Write-Host "  ✅ Completed:       " -NoNewline
Write-Host "$completedCount" -ForegroundColor Green
Write-Host "  ⚙️  Processing:      " -NoNewline
Write-Host "$processingCount" -ForegroundColor Yellow
Write-Host "  ⏳ Pending:         " -NoNewline
Write-Host "$pendingCount" -ForegroundColor Yellow
Write-Host "  ❌ Failed:          " -NoNewline
Write-Host "$failedCount" -ForegroundColor Red
Write-Host ""

# Currently processing
if ($queue.processing) {
    Write-Host "🔄 Currently Processing:" -ForegroundColor Cyan
    $item = $queue.processing
    Write-Host "  Student: $($item.student_login)"
    Write-Host "  Assignment: $($item.assignment_title)"
    Write-Host "  Started: $($item.started_at)"
    Write-Host ""
}

# Recently completed (last 5)
if ($Completed -or $Detailed) {
    Write-Host "✅ Recently Completed:" -ForegroundColor Green
    $recentCompleted = $queue.completed | Select-Object -Last 5
    if ($recentCompleted.Count -gt 0) {
        foreach ($item in $recentCompleted) {
            Write-Host "  • $($item.student_login) - Score: $($item.score) - $($item.completed_at)"
        }
    } else {
        Write-Host "  None yet" -ForegroundColor Gray
    }
    Write-Host ""
}

# Failed items
if ($Failed -or $Detailed) {
    Write-Host "❌ Failed Submissions:" -ForegroundColor Red
    if ($queue.failed.Count -gt 0) {
        $failureGroups = $queue.failed | Group-Object -Property error
        foreach ($group in $failureGroups) {
            Write-Host "  $($group.Count)x: $($group.Name)" -ForegroundColor Yellow
            if ($Detailed) {
                foreach ($item in $group.Group) {
                    Write-Host "    - $($item.student_login)" -ForegroundColor Gray
                }
            }
        }
    } else {
        Write-Host "  None" -ForegroundColor Gray
    }
    Write-Host ""
}

# Pending queue
if ($Detailed -and $pendingCount -gt 0) {
    Write-Host "⏳ Pending Queue (next 5):" -ForegroundColor Yellow
    $nextItems = $queue.pending | Select-Object -First 5
    foreach ($item in $nextItems) {
        Write-Host "  • $($item.student_login) - $($item.assignment_title)"
    }
    if ($pendingCount -gt 5) {
        Write-Host "  ... and $($pendingCount - 5) more" -ForegroundColor Gray
    }
    Write-Host ""
}

# Quick tips
if (-not $Detailed) {
    Write-Host "Tips:" -ForegroundColor Cyan
    Write-Host "  Use -Detailed for full details"
    Write-Host "  Use -Failed to see failure reasons"
    Write-Host "  Use -Completed to see recent grades"
    Write-Host ""
}

# Footer with timestamp
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "Last updated: $ts" -ForegroundColor Gray
Write-Host ""
