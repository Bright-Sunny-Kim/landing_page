@echo off
cd /d "C:\Users\CLAUD\landing_page"
echo ========================================= >> parser_cron.log
echo [LlamaParse Daily Job] 시작 시간: %date% %time% >> parser_cron.log
python scripts/rag_pipeline/process_llama_parse.py >> parser_cron.log 2>&1
echo [LlamaParse Daily Job] 종료 시간: %date% %time% >> parser_cron.log
echo ========================================= >> parser_cron.log
