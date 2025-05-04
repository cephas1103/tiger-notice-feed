from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
from datetime import datetime, timedelta

print("=== 네이버 블로그 전체 게시글 스크래핑 시작 ===")

# 브라우저 설정
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument('--log-level=3')
options.add_experimental_option('excludeSwitches', ['enable-logging'])

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 변수 초기화
blog_id = "tiger_bubu"
base_url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}"
posts = []
categories = {}

# 1단계: 카테고리 정보 수집
print("1단계: 카테고리 정보 수집 중...")
driver.get(f"https://blog.naver.com/{blog_id}")
time.sleep(2)

try:
    # iframe으로 전환
    driver.switch_to.frame("mainFrame")
    
    # 카테고리 목록 찾기
    category_elements = driver.find_elements(By.CSS_SELECTOR, "#category-list li a")
    
    for elem in category_elements:
        try:
            href = elem.get_attribute("href")
            if "categoryNo=" in href:
                category_no = href.split("categoryNo=")[1].split("&")[0]
                category_name = elem.text.strip()
                if category_name and category_no:
                    categories[category_no] = category_name
                    print(f"  카테고리 발견: {category_no} - {category_name}")
        except:
            continue
    
    # 전체 카테고리 추가 (categoryNo=0)
    categories["0"] = "전체"
    
    driver.switch_to.default_content()
except Exception as e:
    print(f"카테고리 수집 오류: {e}")

print(f"총 {len(categories)}개 카테고리 발견")

# 2단계: 각 카테고리별로 게시글 수집
print("\n2단계: 각 카테고리별 게시글 수집 중...")

for category_no, category_name in categories.items():
    print(f"\n처리 중: [{category_no}] {category_name}")
    
    current_page = 1
    consecutive_no_new_posts = 0
    max_consecutive_empty = 5
    
    while True:
        url = f"{base_url}&categoryNo={category_no}&currentPage={current_page}"
        driver.get(url)
        time.sleep(2)
        
        try:
            post_rows = driver.find_elements(By.CSS_SELECTOR, "#postBottomTitleListBody tr")
            
            if not post_rows:
                break
            
            new_posts_count = 0
            
            for row in post_rows:
                try:
                    a_tag = row.find_element(By.CSS_SELECTOR, "td.title a")
                    title = a_tag.text.strip()
                    url = a_tag.get_attribute("href")
                    
                    if title and url and not any(post['url'] == url for post in posts):
                        posts.append({
                            "title": title,
                            "url": url,
                            "category_no": category_no,
                            "category_name": category_name
                        })
                        new_posts_count += 1
                except:
                    continue
            
            if new_posts_count > 0:
                print(f"  페이지 {current_page} - {new_posts_count}개 새 글 발견")
                consecutive_no_new_posts = 0
            else:
                consecutive_no_new_posts += 1
            
            if consecutive_no_new_posts >= max_consecutive_empty:
                break
            
            current_page += 1
            
        except Exception as e:
            print(f"  페이지 {current_page} 오류: {e}")
            break

print(f"\n총 {len(posts)}개 게시글 URL 수집 완료")

# 3단계: 각 게시글의 상세 정보 수집
print("\n3단계: 각 게시글 상세 정보 수집 중...")
for i, post in enumerate(posts):
    try:
        driver.get(post['url'])
        time.sleep(2)
        
        # iframe 전환
        try:
            driver.switch_to.frame("mainFrame")
        except:
            pass
        
        # 본문 내용 추출
        content = ""
        content_selectors = [
            "div.se-main-container",  # 스마트에디터 ONE
            "div#postViewArea",       # 구형 에디터
            "div.post-view",
            "div[class*='content']"
        ]
        
        for selector in content_selectors:
            try:
                content_elem = driver.find_element(By.CSS_SELECTOR, selector)
                content = content_elem.text.strip()
                if content:
                    post['content_preview'] = content[:200] + "..." if len(content) > 200 else content
                    break
            except:
                continue
        
        # 썸네일 이미지 추출
        thumbnail = ""
        thumbnail_selectors = [
            "div.se-main-container img",
            "div#postViewArea img",
            "div.post-view img",
            "img.se-image-resource"
        ]
        
        for selector in thumbnail_selectors:
            try:
                images = driver.find_elements(By.CSS_SELECTOR, selector)
                for img in images:
                    src = img.get_attribute("src")
                    if src and ("pstatic.net" in src or "blogfiles" in src):
                        thumbnail = src
                        break
                if thumbnail:
                    break
            except:
                continue
        
        post['thumbnail'] = thumbnail
        
        # 날짜 정보 추출
        date = ""
        date_selectors = [
            "span.se_publishDate",
            "span.se_date",
            "div.post_info_box span.se_publishDate",
            ".date",
            ".post-date", 
            "p.date",
            "span.date",
            "strong.date",
            ".blog2_series_date",
            ".se-component-content .se-date-text",
            "div.blog2_container span.date",
            "p.se_date",
            "strong.se_publishDate",
            ".post_info_date",
            "time"
        ]
        
        for selector in date_selectors:
            try:
                date_elem = driver.find_element(By.CSS_SELECTOR, selector)
                date = date_elem.text.strip()
                if date:
                    post['date'] = date
                    break
            except:
                continue
        
        if not date:  # 날짜를 찾지 못한 경우
            try:
                # URL에서 날짜 추출 시도 (223854674551 같은 형식)
                logNo = post['url'].split("logNo=")[1].split("&")[0]
                if logNo and logNo.startswith('22'):  # 2022년 이후 작성된 글
                    # 22YYDDD 형식에서 연도와 날짜 추출
                    year = "20" + logNo[0:2]
                    try:
                        day_of_year = int(logNo[2:5])
                        start_date = datetime(int(year), 1, 1)
                        result_date = start_date + timedelta(days=day_of_year - 1)
                        post['date'] = result_date.strftime("%Y.%m.%d")
                    except:
                        post['date'] = ""
                else:
                    post['date'] = ""
            except:
                post['date'] = ""
        
        driver.switch_to.default_content()
        
        print(f"  {i+1}/{len(posts)}: [{post['category_name']}] {post['title'][:30]}... 완료")
        
    except Exception as e:
        print(f"  {i+1}/{len(posts)}: 오류 발생 - {e}")
        post['content_preview'] = ""
        post['thumbnail'] = ""
        post['date'] = ""

# 결과 저장
with open("all_blog_posts.json", "w", encoding="utf-8") as f:
    json.dump(posts, f, ensure_ascii=False, indent=2)

driver.quit()

print(f"\n=== 스크래핑 완료 ===")
print(f"총 {len(posts)}개 게시글 상세 정보 수집")
print(f"파일 저장: all_blog_posts.json")

# 카테고리별 통계
category_stats = {}
for post in posts:
    cat_name = post['category_name']
    if cat_name in category_stats:
        category_stats[cat_name] += 1
    else:
        category_stats[cat_name] = 1

print("\n[카테고리별 게시글 수]")
for cat_name, count in category_stats.items():
    print(f"  {cat_name}: {count}개")

# 결과 미리보기
print("\n[수집된 글 상세 정보 미리보기]")
for i, post in enumerate(posts[:5]):  # 처음 5개만 미리보기
    print(f"\n{i+1}. 제목: {post['title']}")
    print(f"   카테고리: [{post['category_no']}] {post['category_name']}")
    print(f"   URL: {post['url']}")
    print(f"   날짜: {post.get('date', '')}")
    print(f"   본문 미리보기: {post.get('content_preview', '')[:100]}...")
    print(f"   썸네일: {post.get('thumbnail', '없음')}")