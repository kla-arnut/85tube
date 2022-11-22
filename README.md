# 85tube

this project only run on linux and run on python virtual env

1. cd {to-your-project-path}
2. python3.10 -m venv python3.10-venv
3. source python3.10-venv/bin/activate
4. pip install -r requirements.txt
5. python main.py
   

test call api on server script
curl -H "Content-Type : application/json;charset-UTF-8" -X POST http://globalrc.crossrobots.cn/api/open/syn/video/getCategory
curl -H "Content-Type : application/json;charset-UTF-8" -X POST http://globalrc.crossrobots.cn/api/open/syn/video/serverList