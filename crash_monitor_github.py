import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright
import time
import os
import sys

class CrashMonitorGitHub:
    def __init__(self, duration_minutes=6):
        self.last_crash_value = None
        self.records = []
        self.running = True
        self.duration_minutes = duration_minutes
        self.load_records()
        
    def load_records(self):
        if os.path.exists('crash_records.json'):
            try:
                with open('crash_records.json', 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    self.records = json.loads(content) if content else []
                print(f"✅ تم تحميل {len(self.records)} سجل محفوظ")
            except Exception as e:
                print(f"⚠️ خطأ في تحميل السجلات: {e}")
                self.records = []
        else:
            self.records = []
            print("📝 لا توجد سجلات سابقة - سيتم إنشاء ملف جديد")
    
    def save_record(self, crash_value):
        record = {
            'id': int(time.time() * 1000),
            'crash_value': crash_value,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.records.insert(0, record)
        
        with open('crash_records.json', 'w', encoding='utf-8') as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)
        
        if not os.path.exists('crash_records.csv'):
            with open('crash_records.csv', 'w', encoding='utf-8') as f:
                f.write('ID,Crash Value,Timestamp\n')
        
        with open('crash_records.csv', 'a', encoding='utf-8') as f:
            f.write(f"{record['id']},{record['crash_value']},{record['timestamp']}\n")
        
        print(f"💾 [{record['timestamp']}] تم الحفظ: {crash_value} | الإجمالي: {len(self.records)}")
    
    async def monitor(self):
        print(f"🚀 بدء المراقبة لمدة {self.duration_minutes} دقائق...")
        print(f"📊 عدد السجلات الحالية: {len(self.records)}")
        
        start_time = time.time()
        end_time = start_time + (self.duration_minutes * 60)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            
            page = await browser.new_page()
            
            try:
                print("⏳ فتح الموقع...")
                await page.goto('https://faucetpay.io/crash', wait_until='networkidle', timeout=60000)
                
                print(f"✅ المراقبة نشطة حتى {datetime.fromtimestamp(end_time).strftime('%H:%M:%S')}\n")
                
                consecutive_errors = 0
                
                while self.running and time.time() < end_time:
                    try:
                        remaining = int((end_time - time.time()) / 60)
                        
                        element = await page.query_selector('#crash-payout-text')
                        
                        if element:
                            text = await element.inner_text()
                            text = text.strip()
                            
                            if 'Crashed @' in text:
                                crash_value = text.replace('Crashed @', '').strip()
                                
                                if crash_value and crash_value != self.last_crash_value:
                                    self.last_crash_value = crash_value
                                    self.save_record(crash_value)
                                    consecutive_errors = 0
                            
                            if remaining % 2 == 0:
                                print(f"⏰ متبقي: {remaining} دقيقة | السجلات: {len(self.records)}")
                        else:
                            consecutive_errors += 1
                            if consecutive_errors > 10:
                                print("⚠️ لم يتم العثور على العنصر - إعادة تحميل الصفحة...")
                                await page.reload(wait_until='networkidle')
                                consecutive_errors = 0
                        
                        await asyncio.sleep(3)
                        
                    except asyncio.TimeoutError:
                        print("⏱️ انتهت مهلة التحميل - إعادة المحاولة...")
                        await page.reload(wait_until='networkidle', timeout=60000)
                        
                    except Exception as e:
                        consecutive_errors += 1
                        print(f"⚠️ خطأ ({consecutive_errors}): {e}")
                        
                        if consecutive_errors > 5:
                            print("🔄 إعادة تحميل الصفحة...")
                            await page.reload(wait_until='networkidle', timeout=60000)
                            consecutive_errors = 0
                        
                        await asyncio.sleep(5)
            
            except Exception as e:
                print(f"❌ خطأ فادح: {e}")
            
            finally:
                await browser.close()
                print(f"\n📊 النتائج النهائية: {len(self.records)} سجل")
                print(f"⏱️ مدة التشغيل: {int((time.time() - start_time) / 60)} دقيقة")

async def main():
    print("=" * 70)
    print("🎰 Crash Monitor - GitHub Actions Edition")
    print("=" * 70)
    
    duration = int(os.getenv('MONITOR_DURATION', '6'))
    
    monitor = CrashMonitorGitHub(duration_minutes=duration)
    await monitor.monitor()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ تم الإيقاف بنجاح")
    except Exception as e:
        print(f"❌ خطأ: {e}")
        sys.exit(1)
