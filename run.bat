# Create a batch file named run.bat with:
@echo off
set DATABASE_URL=postgresql://postgres:2005@localhost:5432/medsafety
set SESSION_SECRET=weareliterallysyntaxerrors
set GOOGLE_API_KEY=AIzaSyC3Bgv0NZGYrA38j8aaG5Nfc7dqLo3AKVY
python main.py