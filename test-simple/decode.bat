@echo off
certutil -decode Hello.class.b64 Hello.class > /dev/null
echo Done! Run: java Hello
pause
