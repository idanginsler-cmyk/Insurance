@echo off
REM ========================================
REM ממיר Base64 חזרה ל-.class ב-CMD
REM ========================================
REM שים קובץ זה באותה תיקייה עם קבצי .b64
REM לחץ כפול על הקובץ או הרץ בטרמינל
REM ========================================

echo ממיר קבצי Base64 ל-.class...

certutil -decode FraudAnalyzer.class.b64 FraudAnalyzer.class > /dev/null
certutil -decode Claim.class.b64 "FraudAnalyzer$Claim.class" > /dev/null
certutil -decode Alert.class.b64 "FraudAnalyzer$Alert.class" > /dev/null

echo.
echo הסתיים! עכשיו הרץ:
echo    java FraudAnalyzer
echo.
pause
