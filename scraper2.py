from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
from datetime import datetime

print("=== 네이버 블로그 전체 글 + 카테고리 정보 스크래핑 시작 ===")

# 브라우저 설정
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-logging")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

blog_id = "tiger_bubu"
base_url = f"https://blog.naver.com/{blog_id}"

driver.get(base_url)
time.sleep(2)

# 1단계: 카테고리 정보 수집
driver.switch_to.frame("mainFrame")
category_elements = driver.find_elements(By.CSS_SELECTOR, "#categoryList ul li")

categories = []
for elem in category_elements:
    try:
        link = elem.find_element(By.TAG_NAME, "a")
        href = link.get_attribute("href")
        name = link.text.strip()
        if "categoryNo=" in href:
            category_no = href.split("categoryNo=")[-1].split("&")[0]
            categories.append({"name": name, "no": category_no})
    except:
        continue

print(f"▶ 총 {len(categories)}개 카테고리 발견")

# 2단계: 각 카테고리 글 목록 수집
posts = []
for cat in categories:
    print(f"\n📂 카테고리: {cat['name']} (번호: {cat['no']})")
    page = 1
    while True:
        list_url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}&categoryNo={cat['no']}&from=postList&currentPage={page}"
        driver.get(list_url)
        time.sleep(1.5)

        try:
            driver.switch_to.frame("mainFrame")
        except:
            continue

        rows = driver.find_elements(By.CSS_SELECTOR, "#postBottomTitleListBody tr")
        if not rows:
            break

        new_posts = 0
        for row in rows:
            try:
                a_tag = row.find_element(By.CSS_SELECTOR, "td.title a")
                title = a_tag.text.strip()
                url = a_tag.get_attribute("href")
                if title and url and not any(p['url'] == url for p in posts):
                    posts.append({
                        "title": title,
                        "url": url,
                        "category_no": cat["no"],
                        "category_name": cat["name"]
                    })
                    new_posts += 1
            except:
                continue

        if new_posts == 0:
            break
        page += 1

print(f"\n✔ 총 {len(posts)}개 게시글 URL 수집 완료")

# 3단계: 각 글의 본문 및 썸네일 수집
print("\n본문 및 썸네일 수집 중...")
for i, post in enumerate(posts):
    try:
        driver.get(post["url"])
        time.sleep(1.5)
        try:
            driver.switch_to.frame("mainFrame")
        except:
            pass

        content = ""
        for selector in ["div.se-main-container", "div#postViewArea", "div.post-view", "div[class*='content']"]:
            try:
                content_elem = driver.find_element(By.CSS_SELECTOR, selector)
                content = content_elem.text.strip()
                if content:
                    post['content_preview'] = content[:200] + "..." if len(content) > 200 else content
                    break
            except:
                continue

        thumbnail = ""
        for selector in ["div.se-main-container img", "div#postViewArea img", "div.post-view img", "img.se-image-resource"]:
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

        post["thumbnail"] = thumbnail
        driver.switch_to.default_content()

        print(f"  {i+1}/{len(posts)} 완료: {post['title'][:30]}")

    except Exception as e:
        print(f"  {i+1} 오류: {e}")
        post['content_preview'] = ""
        post['thumbnail'] = ""

# 저장
today = datetime.today().strftime("%Y%m%d")
output_file = f"all_posts_detail_{today}.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(posts, f, ensure_ascii=False, indent=2)

driver.quit()

print(f"\n✅ 전체 스크래핑 완료: {output_file}")
