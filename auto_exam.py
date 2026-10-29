import time
import json
import re
import random
import pyautogui
from openai import OpenAI
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 初始化 AI 客户端
client = OpenAI(
    api_key="你的DeepSeek API Key",
    base_url="https://api.deepseek.com"
)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02


def get_screen_coords(driver, element):
    """Selenium 元素坐标 → 屏幕绝对坐标（元素中心）"""
    win = driver.get_window_rect()
    rect = element.rect
    sx = driver.execute_script("return window.pageXOffset;")
    sy = driver.execute_script("return window.pageYOffset;")
    x = win['x'] + rect['x'] - sx + rect['width'] / 2
    y = win['y'] + rect['y'] - sy + rect['height'] / 2
    return int(x), int(y)


def human_move_to(driver, element):
    """贝塞尔曲线拟人化移动指针到元素中心，不点击"""
    tx, ty = get_screen_coords(driver, element)
    sx, sy = pyautogui.position()

    if abs(tx - sx) < 15 and abs(ty - sy) < 15:
        for _ in range(random.randint(3, 5)):
            pyautogui.moveTo(tx + random.randint(-3, 3), ty + random.randint(-3, 3), duration=0.04)
            time.sleep(random.uniform(0.01, 0.03))
        return tx, ty

    cp1 = (sx + (tx - sx) * 0.3 + random.randint(-40, 40), sy + (ty - sy) * 0.3 + random.randint(-40, 40))
    cp2 = (sx + (tx - sx) * 0.7 + random.randint(-40, 40), sy + (ty - sy) * 0.7 + random.randint(-40, 40))

    steps = random.randint(30, 50)
    for i in range(steps + 1):
        t = i / steps
        x = ((1 - t) ** 3 * sx + 3 * (1 - t) ** 2 * t * cp1[0] + 3 * (1 - t) * t ** 2 * cp2[0] + t ** 3 * tx)
        y = ((1 - t) ** 3 * sy + 3 * (1 - t) ** 2 * t * cp1[1] + 3 * (1 - t) * t ** 2 * cp2[1] + t ** 3 * ty)
        pyautogui.moveTo(int(x), int(y), duration=0.008)
        time.sleep(random.uniform(0.004, 0.015))

    pyautogui.moveTo(tx, ty, duration=0.08)
    for _ in range(random.randint(2, 3)):
        pyautogui.moveTo(tx + random.randint(-2, 2), ty + random.randint(-2, 2), duration=0.03)
        time.sleep(random.uniform(0.01, 0.03))
    return tx, ty


def human_click(driver, element):
    """先拟人化移动指针，再真实点击；pyautogui 不可用时退回 Selenium"""
    try:
        human_move_to(driver, element)
        time.sleep(random.uniform(0.15, 0.35))
        pyautogui.click()
        return True
    except Exception:
        try:
            element.click()
        except Exception:
            driver.execute_script("arguments[0].click();", element)
        return False


class AutoAnswerBot:
    """纯逻辑类，不包含任何 Tkinter 窗口代码"""

    def __init__(self, driver, log_callback):
        self.driver = driver
        self.log_func = log_callback
        self.wait = WebDriverWait(self.driver, 15)

    def log(self, message):
        self.log_func(message)

    def get_ai_answer_blank(self, question_text):
        prompt = f"""请回答以下填空题。题目中的“＿＿”代表空格。
请直接输出 JSON 格式，例如：{{"answer": ["要填入的内容"]}}。
如果有多个空，请在列表中按顺序填入对应的答案。
题目：{question_text}"""
        try:
            response = client.chat.completions.create(
                model="deepseek-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            content = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', content, re.S)
            if json_match:
                return json.loads(json_match.group(0)).get("answer", [])
            return []
        except Exception as e:
            self.log(f"❌ AI 请求失败: {e}")
            return []

    def get_ai_answer(self, question_text, options_list):
        options_str = "\n".join(options_list)
        prompt = f"请回答以下题目。只输出JSON格式：{{\"answer\": [\"A\"]}}，多选返回多个，判断为正确/错误。\n注意：选项可能包含 A、B、C、D、E、F 等多个，请务必仔细阅读所有选项后再作答。\n题目：{question_text}\n选项：\n{options_str}"
        try:
            response = client.chat.completions.create(
                model="deepseek-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            content = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', content, re.S)
            if json_match:
                return json.loads(json_match.group(0)).get("answer", [])
            return []
        except Exception as e:
            self.log(f"❌ AI 请求失败: {e}")
            return []

    def run_auto_answer(self):
        global submit_btn_in_modal
        self.log("🔄 正在寻找答题标签页...")
        time.sleep(2)

        windows = self.driver.window_handles
        self.log(f"当前浏览器共有 {len(windows)} 个标签页")

        target_found = False
        for handle in windows:
            self.driver.switch_to.window(handle)
            current_url = self.driver.current_url
            if "uooc.net.cn/exam" in current_url:
                self.log(f"✅ 已精准定位到答题页面: {current_url}")
                target_found = True
                break

        if not target_found:
            self.log("⚠️ 没找到带有 /exam 的答题页面，尝试在当前页面继续...")
            try:
                WebDriverWait(self.driver, 5).until(EC.url_contains("uooc.net.cn/exam"))
                self.log(f"✅ 延迟后成功定位: {self.driver.current_url}")
            except:
                self.log("❌ 依然未找到答题页面特征，请检查网页是否卡住。")
                return

        self.log("⏳ 正在等待题目元素加载...")
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ti")))
        question_blocks = self.driver.find_elements(By.CSS_SELECTOR, ".ti")
        self.log(f"✅ 页面上共发现 {len(question_blocks)} 道题目，开始自动答题...")

        for index, block in enumerate(question_blocks, start=1):
            self.log(f"\n--- 正在处理第 {index} 题 ---")
            try:
                q_text = block.find_element(By.CSS_SELECTOR, ".ti-q").text.strip()
            except:
                q_text = ""

            if not q_text:
                continue

            input_boxes = block.find_elements(By.CSS_SELECTOR, "textarea, input[type='text']")
            option_labels = block.find_elements(By.CSS_SELECTOR, "label.ti-a")

            # 题型1：填空题
            if input_boxes:
                self.log(f"📝 识别为【填空题】，共 {len(input_boxes)} 个空")
                ai_answers = self.get_ai_answer_blank(q_text)
                self.log(f"🤖 AI 给出填空答案: {ai_answers}")

                if not ai_answers:
                    continue

                for i, box in enumerate(input_boxes):
                    if i < len(ai_answers):
                        ans_text = str(ai_answers[i]).strip()
                        if not ans_text: continue
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", box)
                        time.sleep(0.3)
                        try:
                            box.click()
                            box.clear()
                            box.send_keys(ans_text)
                            self.log(f"  -> 已填入第 {i + 1} 个空: {ans_text}")
                            time.sleep(0.5)
                        except Exception as e:
                            self.log(f"  -> 第 {i + 1} 个空输入失败: {e}")

                try:
                    self.driver.execute_script("arguments[0].click();", block.find_element(By.CSS_SELECTOR, ".ti-q"))
                except:
                    pass
                time.sleep(1)

            # 题型2：选择题
            elif option_labels:
                option_texts = [opt.text.strip() for opt in option_labels]
                self.log(f"📝 识别为【选择题】，共提取到 {len(option_texts)} 个选项")
                ai_answers = self.get_ai_answer(q_text, option_texts)
                self.log(f"🤖 AI 给出答案: {ai_answers}")

                if not ai_answers:
                    continue

                for answer_letter in ai_answers:
                    clicked = False
                    current_labels = block.find_elements(By.CSS_SELECTOR, "label.ti-a")
                    for label in current_labels:
                        try:
                            try:
                                letter_span = label.find_element(By.CSS_SELECTOR, "span.ti-a-i")
                                span_text = letter_span.text.strip()
                            except:
                                span_text = label.text.strip()

                            if answer_letter in span_text or span_text.startswith(answer_letter):
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
                                time.sleep(0.3)
                                try:
                                    label.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", label)
                                self.log(f"  -> 已成功点击选项: {answer_letter}")
                                clicked = True
                                time.sleep(0.8)
                                break
                        except Exception:
                            continue
                    if not clicked:
                        self.log(f"  ⚠️ 未找到选项: {answer_letter}")
                    time.sleep(random.uniform(0.5, 1.0))
            else:
                self.log("⚠️ 未识别出选项或输入框，跳过。")

            time.sleep(random.uniform(1.0, 2.0))

        # 提交与验证逻辑
        self.log("\n🎉 所有题目作答完毕，准备提交...")
        try:
            submit_btn = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'提交')]")))
            self.driver.execute_script("arguments[0].click();", submit_btn)
            self.log("已点击外层提交按钮，等待弹窗...")
            time.sleep(1.5)
        except:
            self.log("⚠️ 未找到提交按钮")

        try:
            self.log("正在处理智能验证...")
            checkbox = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "aliyunCaptcha-checkbox-icon")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
            time.sleep(0.5)

            if human_click(self.driver, checkbox):
                self.log("✅ 已（真实指针）点击验证复选框，等待结果...")
            else:
                self.log("⚠️ pyautogui 不可用，已回退 Selenium 点击，等待结果...")

            time.sleep(3)
            self.log("等待弹窗里的提交按钮亮起...")

            max_retries = 5
            submit_ready = False
            submit_btn_xpath = "//div[contains(@class, 'btn-warning') and contains(text(), '提交')]"

            for attempt in range(max_retries):
                self.log(f"⏳ 第 {attempt + 1} 次检查弹窗提交按钮是否亮起...")
                try:
                    submit_btn_in_modal = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, submit_btn_xpath)))
                    if submit_btn_in_modal.is_enabled() and submit_btn_in_modal.get_attribute("disabled") is None:
                        self.log("✅ 提交按钮已亮起，准备点击！")
                        submit_ready = True
                        break
                    else:
                        self.log("⚠️ 提交按钮未亮起，尝试重新点击验证...")
                        time.sleep(3)
                        try:
                            checkbox = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.ID, "aliyunCaptcha-checkbox-icon")))
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                            time.sleep(0.5)
                            try:
                                checkbox.click()
                            except Exception:
                                self.driver.execute_script("arguments[0].click();", checkbox)
                            time.sleep(3)
                        except Exception as e:
                            self.log(f"❌ 重新点击验证码失败: {e}")
                except Exception as e:
                    self.log(f"❌ 查找提交按钮失败: {e}")
                    time.sleep(1)

            time.sleep(1)
            try:
                self.driver.find_element(By.XPATH, "/html/body/div[1]/div[3]/div[5]/div[2]/div/div[2]/div").click()
                self.log("使用绝对路径点击了提交按钮。")
            except Exception:
                self.driver.execute_script("arguments[0].click();", submit_btn_in_modal)
                self.log("使用通用 XPath 兜底点击了提交按钮。")
            time.sleep(2.5)

            self.log("尝试点击确认成绩按钮...")
            self.driver.find_element(By.XPATH, "/html/body/div[4]/div[3]/a").click()
            time.sleep(3)

            self.log("当前标签页任务完成，准备关闭并返回...")
            time.sleep(1)

            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.log("已关闭当前答题标签页。")
                for handle in self.driver.window_handles:
                    self.driver.switch_to.window(handle)
                    current_url = self.driver.current_url
                    if "/home/learn/new" in current_url:
                        self.log(f"✅ 已精准切回视频主页面: {current_url}")
                        break
            else:
                self.log("只有当前一个标签页，未执行关闭。")

            time.sleep(3)
            self.log("🎬 答题任务结束，准备进入视频扫描与挂机模式...")
            self.process_unfinished_videos()

        except Exception as verify_e:
            self.log(f"\n❌ 验证或提交失败: {verify_e}")
            self.log("请手动在弹出的网页中完成验证和提交。")

    def handle_popup_quiz(self):
        self.log("🚨 发现防挂机弹窗，开始自动作答...")
        try:
            popup = self.driver.find_element(By.CSS_SELECTOR, "div.smallTest-view")
            q_text = popup.find_element(By.CSS_SELECTOR, ".ti-q").text.strip()
            if not q_text: return

            option_labels = popup.find_elements(By.CSS_SELECTOR, "label.ti-a")
            option_texts = [opt.text.strip() for opt in option_labels]
            self.log(f"📝 弹窗题目: {q_text[:20]}...")

            ai_answers = self.get_ai_answer(q_text, option_texts)
            self.log(f"🤖 AI 给出答案: {ai_answers}")

            if not ai_answers: return

            for answer_letter in ai_answers:
                for label in option_labels:
                    try:
                        letter_span = label.find_element(By.CSS_SELECTOR, "span.ti-a-i")
                        if answer_letter in letter_span.text.strip():
                            self.driver.execute_script("arguments[0].click();", label)
                            self.log(f"  -> 已成功点击弹窗选项: {answer_letter}")
                            time.sleep(0.5)
                            break
                    except:
                        continue
            time.sleep(1)
            try:
                submit_btn = popup.find_element(By.XPATH, "//button[contains(text(),'确定')]")
                submit_btn.click()
            except:
                pass
            self.log("✅ 防挂机弹窗处理完毕！")
            time.sleep(2)
        except Exception as e:
            self.log(f"❌ 处理弹窗失败: {e}")

    def process_unfinished_videos(self):
        self.log("🔍 开始扫描未完成的视频...")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.level_2_resourcelist_item")))
            items = self.driver.find_elements(By.CSS_SELECTOR, "div.level_2_resourcelist_item")
        except Exception:
            self.log("⚠️ 等待资源列表加载超时。")
            return False

        for index, item in enumerate(items):
            try:
                try:
                    text_span = item.find_element(By.CSS_SELECTOR, "span.level_2_resourcelist_item_text")
                    item_title = text_span.text.strip()
                except:
                    continue

                if ".mp4" not in item_title.lower():
                    continue

                is_finished = False
                check_icons = item.find_elements(By.CSS_SELECTOR, "img.level_2_resourcelist_item_icon_check")
                for icon in check_icons:
                    if icon.is_displayed():
                        is_finished = True
                        break

                if is_finished:
                    self.log(f"✔️ 视频 [{item_title[:15]}...] 已完成，跳过。")
                    continue

                self.log(f"▶️ 发现未完成视频 [{item_title[:15]}...]，准备点击播放...")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                time.sleep(1)

                try:
                    clickable_el = item.find_element(By.CSS_SELECTOR, "span.level_2_resourcelist_item_text")
                    self.driver.execute_script("arguments[0].click();", clickable_el)
                except:
                    self.driver.execute_script("arguments[0].click();", item)

                time.sleep(3)

                video = None
                try:
                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "video")))
                    videos = self.driver.find_elements(By.TAG_NAME, "video")
                    for v in videos:
                        if v.is_displayed():
                            video = v
                            break
                except:
                    pass

                if not video:
                    self.log("⚠️ 无法找到当前可见的视频播放器，刷新重试。")
                    return True

                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return arguments[0].readyState >= 1", video))
                duration = self.driver.execute_script("return arguments[0].duration", video)

                if not duration or duration == 0:
                    self.log("⚠️ 视频时长获取失败，可能卡住，刷新重试。")
                    return True

                new_duration = int(duration / 2 + 3)
                self.log(f"⏳ 视频长度 {duration:.0f} 秒，将挂机播放 {new_duration} 秒...")

                self.driver.execute_script("arguments[0].muted = true;", video)
                self.driver.execute_script("arguments[0].play();", video)
                self.driver.execute_script("arguments[0].playbackRate = 2.0;", video)

                start_time = time.time()
                pause_retry_count = 0

                while time.time() - start_time < new_duration:
                    popups = self.driver.find_elements(By.CSS_SELECTOR, "div.smallTest-view")
                    popup_visible = any(p.is_displayed() for p in popups)

                    if popup_visible:
                        pause_start = time.time()
                        self.handle_popup_quiz()
                        start_time += (time.time() - pause_start)

                    current_video = None
                    try:
                        videos = self.driver.find_elements(By.TAG_NAME, "video")
                        for v in videos:
                            if v.is_displayed():
                                current_video = v
                                break
                    except:
                        pass

                    if current_video and not popup_visible:
                        try:
                            is_paused = self.driver.execute_script("return arguments[0].paused;", current_video)
                            if is_paused:
                                pause_retry_count += 1
                                if pause_retry_count % 5 == 0:
                                    self.log(f"▶️ 尝试恢复播放 (第 {pause_retry_count} 次)...")

                                self.driver.execute_script("arguments[0].muted = true;", current_video)
                                self.driver.execute_script("arguments[0].play();", current_video)

                                if pause_retry_count >= 10:
                                    self.log("❌ 视频卡死无法播放，强制跳过该视频！")
                                    break
                        except Exception:
                            pass

                    time.sleep(2)

                self.log("✅ 视频挂机时长已满")
                self.log("🔄 等待平台同步进度并刷新页面...")
                time.sleep(5)
                self.driver.refresh()
                time.sleep(3)
                return True

            except Exception as e:
                self.log(f"⚠️ 检查资源时出错: {e}")
                continue

        self.log("🎉 扫描完毕，当前页面没有未完成的视频了。")
        return False
