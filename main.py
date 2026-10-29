import os
import time
import threading
import gc
import tkinter as tk
from tkinter import scrolledtext
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.chrome.options import Options
from selenium.common import NoSuchElementException
from auto_exam import AutoAnswerBot

os.environ["SE_SKIP_DRIVER_IN_PATH"] = "true"


class MainApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("UOOC 自动化主控台")
        self.root.geometry("700x800")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black")

        # 1. 日志区
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD,
                                                   font=("Consolas", 10), fg="green", bg="black",
                                                   insertbackground="green")
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # 2. 课程按钮容器
        self.course_frame = tk.Frame(self.root, bg="black")
        self.course_frame.pack(padx=10, fill=tk.X)

        self.driver = None
        self.course_elements = []
        self.selected_index = -1
        self.course_selected_event = threading.Event()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 启动后台线程
        threading.Thread(target=self.run_logic, daemon=True).start()
        self.root.mainloop()

    def log(self, msg):
        if not self.root: return
        self.root.after(0, self._safe_log, msg)

    def _safe_log(self, msg):
        try:
            self.text_area.insert(tk.END, msg + "\n")
            self.text_area.see(tk.END)
        except:
            pass

    def render_courses(self, courses):
        self.log("\n" + "=" * 40)
        self.log("📚 当前页面的课程列表（请点击下方按钮选择）：")
        self.log("=" * 40)

        self.course_elements = courses
        for i, course in enumerate(courses):
            course_name = course.text.strip()
            btn = tk.Button(self.course_frame, text=f"{i + 1}. {course_name}",
                            bg="black", fg="green", activebackground="green", activeforeground="black",
                            highlightbackground="green", bd=1, relief="solid",
                            font=("微软雅黑", 10),
                            command=lambda idx=i: self.on_course_clicked(idx))
            btn.pack(fill=tk.X, pady=3)

    def on_course_clicked(self, index):
        self.selected_index = index
        for widget in self.course_frame.winfo_children():
            widget.destroy()
        self.log(f"🎯 你选择了: {self.course_elements[index].text.strip()}")
        self.course_selected_event.set()

    def on_close(self):
        try:
            self.root.destroy()
        except:
            pass
        if self.driver:
            self.driver.quit()
        os._exit(0)

    def run_logic(self):
        try:
            self.log("⏳ 正在连接浏览器...")
            options = Options()
            # 用自动化的时候，用终端指定端口启动浏览器，然后再把控制权交给脚本，这样人机验证不会失败
            # 终端启动指定端口浏览器的指令:
            """
                1.win+R输入cmd,回车。
                2.如果是Google浏览器-输入:"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9999 --user-data-dir="D:\SeleniumChromeProfile"
                3.前提是有Google浏览器,没有的话用Edge的
                4.Edge-"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9999 --user-data-dir="D:\SeleniumEdgeProfile"
            """
            options.debugger_address = "用终端启动的浏览器的地址"
            self.driver = webdriver.Chrome(options=options)

            self.driver.get("https://www.uooc.net.cn/home#/center/course/learn")
            time.sleep(1)
            # 添加cookie(注意：这些cookie信息要写全才能免登录进到账户页面，否则通过不了人机验证)
            self.driver.add_cookie({"name": "account", "value": "你的账号"})
            self.driver.add_cookie({"name": "formhash", "value": "/center/course/learn"})
            self.driver.add_cookie({"name": "formpath", "value": "/home"})
            self.driver.add_cookie({"name": "Hm_lpvt_d1a5821d95582e27154fc4a1624da9e3", "value": "****"})
            self.driver.add_cookie({"name": "Hm_lvt_d1a5821d95582e27154fc4a1624da9e3", "value": "*******"})
            self.driver.add_cookie({"name": "HMACCOUNT", "value": "********"})
            self.driver.add_cookie({"name": "JSESSID", "value": "**********"})
            self.driver.add_cookie({"name": "uooc_auth","value": "*******************"})
            self.driver.refresh()
            time.sleep(2)

            self.log("⏳ 正在加载课程列表...")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.course-name")))
            all_courses = self.driver.find_elements(By.CSS_SELECTOR, "a.course-name")

            self.root.after(0, self.render_courses, all_courses)

            # 等待用户点击
            self.course_selected_event.wait()

            target_course = self.course_elements[self.selected_index]
            course_url = target_course.get_attribute("href")

            if course_url:
                self.driver.get(course_url)
            else:
                self.driver.execute_script("arguments[0].click();", target_course)

            time.sleep(3)
            for window in reversed(self.driver.window_handles):
                try:
                    self.driver.switch_to.window(window)
                    if self.driver.current_url.startswith("http") and "devtools://" not in self.driver.current_url:
                        break
                except:
                    continue

            self.log(f"✅ 当前页面网址: {self.driver.current_url}")

            self.log("⏳ 正在寻找【进入学习】按钮...")
            try:
                enter_btn = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.join-btn-container"))
                )
                enter_url = enter_btn.get_attribute("href")
                if enter_url:
                    self.driver.get(enter_url)
                else:
                    self.driver.execute_script("arguments[0].click();", enter_btn)

                time.sleep(2)
                for window in reversed(self.driver.window_handles):
                    try:
                        self.driver.switch_to.window(window)
                        if self.driver.current_url.startswith("http") and "devtools://" not in self.driver.current_url:
                            break
                    except:
                        continue
                self.log(f"✅ 已成功进入学习界面！")
            except Exception as e:
                self.log(f"❌ 寻找进入学习按钮失败: {e}")
                return

            time.sleep(2)
            # 回到第一章
            origin = ScrollOrigin.from_viewport(280, 680)
            ActionChains(self.driver).scroll_from_origin(origin, 0, -700).perform()
            self.driver.find_element(By.XPATH,"//ul[@class='newlearn_left_card_chapter_list']/li[1]").click()
            self.driver.find_element(By.XPATH,"//ul[@class='newlearn_left_card_chapter_list']/li[1]").click()
            xpath = "//ul[@class='newlearn_left_card_chapter_list']/li"
            len_zhang = len(self.driver.find_elements(By.XPATH, xpath))
            self.log(f"该课程共 {len_zhang} 个章")
            # ====== 开始遍历章节 ======
            for n in range(7, len_zhang + 1):
                xpath = f"//ul[@class='newlearn_left_card_chapter_list']/li[{n}]"
                try:
                    span = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                except:
                    break

                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", span)
                time.sleep(0.3)
                span.click()
                time.sleep(1)

                sub_xpath = f"//ul[@class='newlearn_left_card_chapter_list']/li[{n}]/ul/li"
                try:
                    WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.XPATH, sub_xpath)))
                except:
                    pass

                eles = self.driver.find_elements(By.XPATH, sub_xpath)
                self.log(f"--- 第{n}章 共有 {len(eles)} 个小节 ---")

                for i in range(1, len(eles) + 1):
                    z_xpath = f"//ul[@class='level_2 ng-scope']/li[{i}]//span"
                    try:
                        z_jie = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, z_xpath)))
                    except:
                        continue

                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", z_jie)
                    time.sleep(0.3)
                    z_jie.click()
                    time.sleep(1)

                    quiz_found = False
                    try:
                        quiz_icon = self.driver.find_element(
                            By.CSS_SELECTOR,
                            "img[src='//assets.uooconline.com/index/images/newlearn/test.png']"
                        )
                        quiz_item = quiz_icon.find_element(
                            By.XPATH,
                            "./ancestor::div[contains(@class, 'level_2_resourcelist_item')]"
                        )
                        check_icons = quiz_item.find_elements(
                            By.CSS_SELECTOR,
                            "img.level_2_resourcelist_item_icon_check"
                        )
                        if len(check_icons) == 0:
                            self.log("📝 发现未完成测验，准备点击进入答题...")
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", quiz_item)
                            time.sleep(0.5)
                            self.driver.execute_script("arguments[0].click();", quiz_item)
                            quiz_found = True
                            self.log("✅ 已点击测验，等待答题页加载...")
                            time.sleep(2)
                        else:
                            self.log("✔️ 发现已完成的测验，跳过。")
                    except NoSuchElementException:
                        self.log("该小节没有测验，跳过答题环节，直接交给视频扫描处理")
                    except Exception as e:
                        self.log(f"⚠️ 检查测验时出错: {e}")

                    time.sleep(2)

                    # 🌟 实例化纯逻辑类，传入 self.log 作为回调
                    bot = AutoAnswerBot(self.driver, log_callback=self.log)

                    if quiz_found:
                        bot.run_auto_answer()
                    else:
                        # 直接开始扫描视频逻辑
                        self.log("📌 本节无测验，直接扫描未完成视频...")
                        retry_count = 0
                        while retry_count < 2:
                            has_unfinished = bot.process_unfinished_videos()
                            if not has_unfinished:
                                retry_count += 1
                                bot.log(f"⚠️ 未发现未完成视频，刷新重试 ({retry_count}/2)...")
                                self.driver.refresh()
                                time.sleep(5)
                            else:
                                retry_count = 0
                            time.sleep(2)
                        self.log("🎉 当前小节视频全部看完！")

                    self.log("✅ 答题/扫视频环节结束，主程序继续...")
                    del bot
                    gc.collect()

                    time.sleep(2)

            self.log("🎉 所有章节处理完毕！")
            time.sleep(5)
            self.driver.quit()
            self.root.after(0, self.root.destroy)

        except Exception as e:
            self.log(f"❌ 发生全局致命错误: {e}")


if __name__ == "__main__":
    MainApp()
