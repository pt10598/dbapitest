from flask import Flask, request, make_response
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import json
import os

app = Flask(__name__)

@app.route('/api/query', methods=['POST'])
def api_query():
    data = request.get_json()
    user = data['user']
    tte = data['tte']
    tte2 = data['tte2']

    # Heroku Chrome 設定
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('--window-size=1920,1080')

    # 初始化 driver
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get('https://ppstrq.nat.gov.tw/pps/pubQuery/PropertyQuery/propertyQuery.do')
        time.sleep(1)

        # 填寫表單部分
        step1 = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/form/div[1]/div[1]/div/div/div[2]/div[1]/div[1]/div[2]/div/input[2]')
        step1.click()
        time.sleep(0.3)

        step2 = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/form/div[1]/div[1]/div/div/div[2]/div[1]/div[1]/div[3]/div/input')
        step2.send_keys(user)

        step3 = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/form/div[1]/div[1]/div/div/div[2]/div[1]/div[1]/div[4]/div/input')
        step3.send_keys(tte)

        step4 = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/form/div[1]/div[1]/div/div/div[2]/div[2]/div/input[2]')
        step4.click()
        time.sleep(0.5)

        # 查詢有幾筆資料
        mortgagees = []
        try:
            rows = driver.find_elements(By.XPATH, '/html/body/div[3]/div[3]/div/form/div/div[3]/div/div[2]/table/tbody/tr')
            count = len(rows)

            # 逐筆點擊查詢
            for i in range(count):
                try:
                    # 重新定位並點擊第i筆資料
                    current_rows = driver.find_elements(By.XPATH, '/html/body/div[3]/div[3]/div/form/div/div[3]/div/div[2]/table/tbody/tr')
                    current_row = current_rows[i]
                    first_td = current_row.find_element(By.XPATH, './td[1]')
                    first_td.click()
                    time.sleep(2)
                    
                    # 提取指定路徑的抵押權人資訊
                    try:
                        mortgagee_element = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/div/div[1]/div/div/div[4]/div/div[2]/div/div[2]/div[2]')
                        mortgagee = mortgagee_element.text.strip()
                        mortgagees.append(mortgagee)
                    except:
                        mortgagees.append("提取失敗")
                    
                    # 返回上一頁（如果不是最後一筆）
                    if i < count - 1:
                        driver.back()
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"第{i+1}筆處理錯誤: {e}")
                    mortgagees.append("處理失敗")

            results = {
                "count": count,
                "mortgagees": mortgagees
            }
        except Exception as e:
            print(f"抓取錯誤: {e}")
            results = {"count": 0, "mortgagees": []}

        # 回傳中文JSON
        response = make_response(
            json.dumps({
                "status": "success",
                "results": results
            }, ensure_ascii=False)
        )
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        response = make_response(
            json.dumps({
                "status": "error",
                "message": str(e)
            }, ensure_ascii=False)
        )
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    finally:
        driver.quit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
