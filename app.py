import os
import time
import json
import threading
from flask import Flask, request, make_response
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# 建立線程鎖，確保同一時間只有一個動產擔保查詢在執行，避免多人併發導致的資源衝突
query_lock = threading.Lock()

def init_driver():
    """初始化瀏覽器驅動"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    # 增加隱身參數，防止被網站偵測為機器人
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

@app.route('/api/query', methods=['POST'])
def api_query():
    data = request.get_json()
    user = data.get('user', '')
    tte = data.get('tte', '')
    
    # 使用 Lock 確保排隊處理
    with query_lock:
        driver = None
        try:
            print(f"🔍 開始動產擔保查詢: {user} {tte}")
            driver = init_driver()
            
            driver.get('https://ppstrq.nat.gov.tw/pps/pubQuery/PropertyQuery/propertyQuery.do')
            
            wait = WebDriverWait(driver, 15)
            
            # 填寫表單
            # 選取「身分證字號」選項
            step1 = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div[3]/div/form/div[1]/div[1]/div/div/div[2]/div[1]/div[1]/div[2]/div/input[2]')))
            step1.click()
            time.sleep(0.5)
            
            # 輸入姓名
            step2 = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/form/div[1]/div[1]/div/div/div[2]/div[1]/div[1]/div[3]/div/input')
            step2.send_keys(user)
            
            # 輸入身分證字號
            step3 = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/form/div[1]/div[1]/div/div/div[2]/div[1]/div[1]/div[4]/div/input')
            step3.send_keys(tte)
            
            # 點擊查詢
            step4 = driver.find_element(By.XPATH, '/html/body/div[3]/div[3]/div/form/div[1]/div[1]/div/div/div[2]/div[2]/div/input[2]')
            step4.click()
            
            # 查詢結果處理
            mortgagees = []
            try:
                # 等待結果表格出現，如果沒出現代表查無資料
                wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[3]/div[3]/div/form/div/div[3]/div/div[2]/table/tbody/tr')))
                
                rows = driver.find_elements(By.XPATH, '/html/body/div[3]/div[3]/div/form/div/div[3]/div/div[2]/table/tbody/tr')
                count = len(rows)
                print(f"✅ 找到 {count} 筆動產擔保紀錄")
                
                # 逐筆點擊查詢詳細資訊
                for i in range(count):
                    try:
                        # 每次迴圈重新定位 rows 以免失效
                        current_rows = driver.find_elements(By.XPATH, '/html/body/div[3]/div[3]/div/form/div/div[3]/div/div[2]/table/tbody/tr')
                        current_row = current_rows[i]
                        first_td = current_row.find_element(By.XPATH, './td[1]')
                        first_td.click()
                        
                        # 等待詳細頁面載入
                        time.sleep(2)
                        
                        # 提取抵押權人資訊
                        mortgagee_element = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[3]/div[3]/div/div/div[1]/div/div/div[4]/div/div[2]/div/div[2]/div[2]')))
                        mortgagee = mortgagee_element.text.strip()
                        mortgagees.append(mortgagee)
                        
                        # 返回上一頁
                        if i < count - 1:
                            driver.back()
                            # 等待回列表頁渲染
                            wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[3]/div[3]/div/form/div/div[3]/div/div[2]/table/tbody/tr')))
                            time.sleep(1)
                            
                    except Exception as inner_e:
                        print(f"第{i+1}筆處理錯誤: {inner_e}")
                        mortgagees.append("處理失敗")
                
                results = {"count": count, "mortgagees": mortgagees}
            except:
                # 沒找到表格，視為 0 筆
                print("ℹ️ 查無動產擔保資料")
                results = {"count": 0, "mortgagees": []}
            
            response_data = {"status": "success", "results": results}
            
        except Exception as e:
            print(f"❌ 查詢失敗: {e}")
            response_data = {"status": "error", "message": f"伺服器查詢出錯: {str(e)}"}
        finally:
            if driver:
                driver.quit()

    # 回傳 JSON
    response = make_response(json.dumps(response_data, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
